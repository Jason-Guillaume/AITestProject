"""
Celery：生成 k6 脚本、subprocess 执行、解析 stderr 并通过 Channels 推送实时指标。
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
import time
from pathlib import Path

try:
    from celery import shared_task
except Exception:  # pragma: no cover —无 Celery 时仍可 import 本模块

    def shared_task(*_a, **_kw):  # type: ignore
        def _wrap(fn):
            return fn

        return _wrap


from asgiref.sync import async_to_sync
from django.conf import settings

logger = logging.getLogger(__name__)


def _celery_request_id() -> str:
    try:
        from celery import current_task

        req = getattr(current_task, "request", None)
        return str(getattr(req, "id", "") or "")
    except Exception:
        return ""


def _broadcast(run_id_str: str, payload: dict) -> None:
    try:
        from channels.layers import get_channel_layer
    except ImportError:
        return
    layer = get_channel_layer()
    if not layer:
        return
    try:
        async_to_sync(layer.group_send)(
            f"k6_run_{run_id_str}",
            {"type": "k6.metrics", "payload": payload},
        )
    except Exception:
        logger.exception("Channels group_send 失败 run_id=%s", run_id_str)


@shared_task(
    name="execution.run_k6_load_test",
    soft_time_limit=3600,
    time_limit=3660,
)
def run_k6_load_test(session_pk: int) -> dict:
    from execution.models import K6LoadTestSession
    from execution.services.k6_ai_generator import generate_k6_script_with_ai
    from execution.services.k6_chain_builder import collect_api_chain
    from execution.services.k6_stderr_parser import K6LiveSample, feed_line
    from execution.services.k6_template_generator import build_k6_script

    try:
        session = K6LoadTestSession.objects.get(pk=session_pk, is_deleted=False)
    except K6LoadTestSession.DoesNotExist:
        return {"ok": False, "error": "session not found"}

    run_id_str = str(session.run_id)
    session.celery_task_id = _celery_request_id()
    session.status = K6LoadTestSession.STATUS_GENERATING
    session.error_message = ""
    session.save(
        update_fields=["celery_task_id", "status", "error_message", "update_time"]
    )

    _broadcast(
        run_id_str,
        {"type": "status", "phase": "generating", "message": "正在生成 k6 脚本"},
    )

    case_ids = list(session.test_case_ids or [])
    steps, chain_err = collect_api_chain(case_ids, session.target_base_url or "")
    if chain_err:
        session.status = K6LoadTestSession.STATUS_FAILED
        session.error_message = chain_err
        session.save(update_fields=["status", "error_message", "update_time"])
        _broadcast(
            run_id_str,
            {"type": "error", "message": chain_err},
        )
        return {"ok": False, "error": chain_err}

    script: str | None = None
    source = "template"
    ai_err: str | None = None

    if session.use_ai:
        script, ai_err = generate_k6_script_with_ai(
            steps,
            session.vus,
            session.duration,
        )
        if script:
            source = "ai"
        else:
            logger.warning("k6 AI 生成失败，回退模板: %s", ai_err)

    if not script:
        script = build_k6_script(steps, session.vus, session.duration)
        source = "template"

    base_dir = Path(settings.MEDIA_ROOT) / "k6_runs" / run_id_str
    base_dir.mkdir(parents=True, exist_ok=True)
    script_path = base_dir / "script.js"
    summary_path = base_dir / "summary.json"
    script_path.write_text(script, encoding="utf-8")

    rel = str(script_path.relative_to(Path(settings.MEDIA_ROOT)))
    session.script_rel_path = rel.replace("\\", "/")
    session.script_body = script[:200_000]
    session.generation_source = source
    session.status = K6LoadTestSession.STATUS_RUNNING
    session.save(
        update_fields=[
            "script_rel_path",
            "script_body",
            "generation_source",
            "status",
            "update_time",
        ]
    )

    _broadcast(
        run_id_str,
        {
            "type": "status",
            "phase": "running",
            "message": "k6 进程已启动",
            "generation_source": source,
            "ai_note": ai_err if source == "template" and ai_err else None,
        },
    )

    k6_bin = shutil.which("k6") or shutil.which("k6.exe")
    if not k6_bin:
        msg = "未找到 k6 可执行文件，请安装 k6 并加入 PATH"
        session.status = K6LoadTestSession.STATUS_FAILED
        session.error_message = msg
        session.save(update_fields=["status", "error_message", "update_time"])
        _broadcast(run_id_str, {"type": "error", "message": msg})
        return {"ok": False, "error": msg}

    proc = subprocess.Popen(
        [
            k6_bin,
            "run",
            "--summary-export",
            str(summary_path),
            str(script_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    sample = K6LiveSample()
    last_push = 0.0
    stderr_tail: list[str] = []

    def on_line(line: str) -> None:
        nonlocal sample, last_push
        if len(stderr_tail) > 200:
            stderr_tail.pop(0)
        stderr_tail.append(line.rstrip()[:500])
        feed_line(sample, line)
        if not sample.has_metrics():
            return
        now = time.time()
        if now - last_push < 0.55:
            return
        last_push = now
        body = sample.to_payload()
        body["type"] = "tick"
        body["ts"] = now
        _broadcast(run_id_str, body)

    def reader() -> None:
        assert proc.stderr
        for line in iter(proc.stderr.readline, ""):
            if not line:
                break
            on_line(line)
        proc.stderr.close()

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    code = proc.wait()
    t.join(timeout=5)

    summary_obj = None
    if summary_path.is_file():
        try:
            summary_obj = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("解析 summary.json 失败: %s", exc)

    session.summary = summary_obj
    session.status = (
        K6LoadTestSession.STATUS_COMPLETED
        if code == 0
        else K6LoadTestSession.STATUS_FAILED
    )
    if code != 0:
        tail = "\n".join(stderr_tail[-30:])
        session.error_message = (tail or f"k6 退出码 {code}")[:8000]
    else:
        session.error_message = ""
    session.save(
        update_fields=["summary", "status", "error_message", "update_time"]
    )

    _broadcast(
        run_id_str,
        {
            "type": "final",
            "exit_code": code,
            "summary": summary_obj,
            "error_message": session.error_message or None,
        },
    )

    return {"ok": code == 0, "exit_code": code}
