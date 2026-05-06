"""Celery tasks for CI/CD Pipeline execution."""

from __future__ import annotations

import queue
import re
import subprocess
import threading
import time
from typing import List, Optional, Tuple

from django.utils import timezone

from AITestProduct.celery import app
from .models import BuildRecord, Pipeline, PipelineLog


def _pipe_to_queue(pipe, prefix: str, out_q: queue.Queue) -> None:
    try:
        for raw in iter(pipe.readline, ""):
            if raw == "":
                break
            line = raw.rstrip("\n\r")
            if line:
                out_q.put((prefix, line))
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def _drain_queue_to_db(build_record: BuildRecord, out_q: queue.Queue) -> None:
    while True:
        try:
            prefix, line = out_q.get_nowait()
        except queue.Empty:
            break
        PipelineLog.objects.create(
            build_record=build_record, log_text=f"[{prefix}] {line}"
        )


def _split_stage_chunks(script: str) -> List[Tuple[str, str]]:
    """按行首 ``# stage: 名称`` 将 Shell 分段（流水线脚本类型）。"""
    script = (script or "").strip()
    if not script:
        return []
    pattern = re.compile(r"^\s*#\s*stage:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
    matches = list(pattern.finditer(script))
    if not matches:
        return [("build", script)]
    chunks: List[Tuple[str, str]] = []
    first_start = matches[0].start()
    preamble = script[:first_start].strip()
    if preamble:
        chunks.append(("setup", preamble))
    for i, m in enumerate(matches):
        name = m.group(1).strip() or f"stage-{i + 1}"
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(script)
        body = script[m.end() : next_start].strip()
        if body:
            chunks.append((name, body))
    return chunks or [("build", script)]


def _run_one_shell(build_record: BuildRecord, command: str) -> int:
    """执行单段 Shell，日志写入 ``PipelineLog``，返回进程退出码。"""
    proc: subprocess.Popen | None = None
    t_out: threading.Thread | None = None
    t_err: threading.Thread | None = None
    out_q: queue.Queue = queue.Queue()

    proc = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None and proc.stderr is not None
    t_out = threading.Thread(
        target=_pipe_to_queue, args=(proc.stdout, "stdout", out_q), daemon=True
    )
    t_err = threading.Thread(
        target=_pipe_to_queue, args=(proc.stderr, "stderr", out_q), daemon=True
    )
    t_out.start()
    t_err.start()

    while True:
        _drain_queue_to_db(build_record, out_q)
        done_process = proc.poll() is not None
        readers_done = not t_out.is_alive() and not t_err.is_alive()
        if done_process and readers_done and out_q.empty():
            break
        time.sleep(0.05)

    return_code = proc.wait()
    _drain_queue_to_db(build_record, out_q)
    return int(return_code)


def _finalize_shell_build(
    *,
    pipeline: Pipeline,
    build_record: BuildRecord,
    success: bool,
    log_line: Optional[str] = None,
) -> None:
    now = timezone.now()
    build_record.end_time = now
    build_record.duration = (now - build_record.start_time).total_seconds()
    build_record.status = (
        BuildRecord.STATUS_SUCCESS if success else BuildRecord.STATUS_FAIL
    )
    u_fields = ["status", "end_time", "duration"]
    build_record.save(update_fields=u_fields)
    pipeline.status = (
        Pipeline.STATUS_SUCCESS if success else Pipeline.STATUS_FAIL
    )
    pipeline.save(update_fields=["status"])
    if log_line:
        PipelineLog.objects.create(build_record=build_record, log_text=log_line)


@app.task(bind=True, name="run_pipeline_task")
def run_pipeline_task(
    self,
    pipeline_id: int,
    command: Optional[str] = None,
    build_record_id: Optional[int] = None,
) -> None:
    """执行构建：``command`` 优先，否则使用 ``Pipeline.build_definition``。"""
    try:
        pipeline = Pipeline.objects.get(id=pipeline_id)
    except Pipeline.DoesNotExist:
        return

    if build_record_id is None:
        return

    try:
        build_record = BuildRecord.objects.get(
            id=build_record_id, pipeline_id=pipeline_id
        )
    except BuildRecord.DoesNotExist:
        return

    celery_id = self.request.id or ""
    build_record.status = BuildRecord.STATUS_RUNNING
    build_record.celery_task_id = celery_id
    build_record.save(update_fields=["status", "celery_task_id"])

    pipeline.status = Pipeline.STATUS_RUNNING
    pipeline.save(update_fields=["status"])

    effective = (command or "").strip() or (pipeline.build_definition or "").strip()
    if not effective:
        effective = "echo 'No command supplied for pipeline'"

    try:
        if pipeline.kind == Pipeline.KIND_PIPELINE:
            chunks = _split_stage_chunks(effective)
            if len(chunks) <= 1:
                rc = _run_one_shell(
                    build_record, chunks[0][1] if chunks else effective
                )
                _finalize_shell_build(
                    pipeline=pipeline,
                    build_record=build_record,
                    success=rc == 0,
                )
                return

            for stage_name, body in chunks:
                PipelineLog.objects.create(
                    build_record=build_record,
                    log_text=f"[system] ===== 阶段: {stage_name} =====",
                )
                rc = _run_one_shell(build_record, body)
                if rc != 0:
                    _finalize_shell_build(
                        pipeline=pipeline,
                        build_record=build_record,
                        success=False,
                        log_line=f"[system] 阶段「{stage_name}」退出码 {rc}，构建失败",
                    )
                    return

            _finalize_shell_build(pipeline=pipeline, build_record=build_record, success=True)
            return

        rc = _run_one_shell(build_record, effective)
        _finalize_shell_build(pipeline=pipeline, build_record=build_record, success=rc == 0)
    except Exception as exc:
        try:
            pipeline.refresh_from_db()
            build_record.refresh_from_db()
        except Exception:
            return
        PipelineLog.objects.create(build_record=build_record, log_text=str(exc))
        now = timezone.now()
        build_record.end_time = now
        build_record.duration = (now - build_record.start_time).total_seconds()
        build_record.status = BuildRecord.STATUS_FAIL
        build_record.save(update_fields=["status", "end_time", "duration"])
        pipeline.status = Pipeline.STATUS_FAIL
        pipeline.save(update_fields=["status"])
