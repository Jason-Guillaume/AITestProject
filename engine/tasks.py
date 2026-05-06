"""Docker 容器构建 Celery 任务（实时 Redis 日志 + BuildRecord 状态）。"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import List, Sequence, Union

from django.db import close_old_connections
from django.utils import timezone

from AITestProduct.celery import app

logger = logging.getLogger(__name__)

BUILD_LOG_TTL_SECONDS = 3600
_DURATION_FLUSH_INTERVAL_S = 5.0

CommandType = Union[str, Sequence[str]]


def _redis_client():
    """返回用于 LIST 操作的 Redis 客户端（decode_responses=True）。"""
    from django.conf import settings

    try:
        from django_redis import get_redis_connection

        return get_redis_connection("default")
    except Exception:
        pass

    import redis as redis_lib

    caches = getattr(settings, "CACHES", {}).get("default", {})
    loc = caches.get("LOCATION")
    if isinstance(loc, str) and loc.startswith("redis://"):
        return redis_lib.from_url(
            loc,
            decode_responses=True,
            socket_connect_timeout=getattr(
                settings, "REDIS_SOCKET_CONNECT_TIMEOUT", 3
            ),
            socket_timeout=getattr(settings, "REDIS_SOCKET_TIMEOUT", 20),
        )

    host = os.environ.get("REDIS_HOST", "127.0.0.1")
    port = int(os.environ.get("REDIS_PORT", "6379"))
    db = int(os.environ.get("REDIS_DB", "0"))
    return redis_lib.Redis(
        host=host,
        port=port,
        db=db,
        decode_responses=True,
        socket_connect_timeout=getattr(
            settings, "REDIS_SOCKET_CONNECT_TIMEOUT", 3
        ),
        socket_timeout=getattr(settings, "REDIS_SOCKET_TIMEOUT", 20),
    )


def _redis_push_line(r, key: str, line: str) -> None:
    r.rpush(key, line)
    r.expire(key, BUILD_LOG_TTL_SECONDS)


def _normalize_command(command: CommandType) -> Union[str, List[str]]:
    if isinstance(command, str):
        return ["sh", "-c", command]
    return list(command)


def _decode_chunk(chunk: bytes) -> str:
    return chunk.decode("utf-8", errors="replace")


def _flush_line_buffer(
    buf: str,
    stream: str,
    *,
    r,
    log_key: str,
    collected: list[str],
    lock: threading.Lock,
) -> str:
    """将 buffer 中完整行推入 Redis 与 collected；返回剩余不完整后缀。"""
    if not buf:
        return ""
    if "\n" not in buf:
        return buf
    parts = buf.split("\n")
    tail = parts.pop()
    for raw_line in parts:
        line = raw_line.rstrip("\r")
        text = f"[{stream}] {line}" if line else f"[{stream}]"
        _redis_push_line(r, log_key, text)
        with lock:
            collected.append(text)
    return tail


def _force_remove_container(client, container) -> None:
    if container is None:
        return
    cid = getattr(container, "id", None)
    if not cid:
        return
    try:
        try:
            container.reload()
        except Exception:
            pass
        if getattr(container, "status", None) == "running":
            try:
                container.kill()
            except Exception:
                pass
        container.remove(force=True)
    except Exception as exc:
        logger.warning("remove container %s failed: %s", cid, exc)


@app.task(bind=True, name="run_build_task")
def run_build_task(
    self,
    build_record_id: int,
    image: str,
    command: CommandType,
    timeout_seconds: int = 3600,
    pull: bool = False,
) -> None:
    """
    在指定镜像的临时容器中执行命令；日志写入 Redis List ``build_log_<task_id>``，
    并同步 ``BuildRecord`` / ``Pipeline`` 状态。

    :param build_record_id: 已存在的构建记录主键（由调用方创建）。
    :param image: Docker 镜像，例如 ``python:3.10``、``node:18``。
    :param command: Shell 字符串或 argv 列表。
    :param timeout_seconds: 容器运行超时（秒），超时后 kill 并标记失败。
    :param pull: 为 True 时先 ``docker pull``（仍可能因网络失败）。
    """
    close_old_connections()

    try:
        import docker
        from docker.errors import APIError, DockerException, ImageNotFound
    except ImportError:
        _fail_import_error(build_record_id)
        return

    from requests.exceptions import ConnectionError as RequestsConnectionError

    from project.models import BuildRecord, Pipeline, PipelineLog

    try:
        br = BuildRecord.objects.select_related("pipeline").get(pk=build_record_id)
    except BuildRecord.DoesNotExist:
        logger.error("run_build_task: BuildRecord %s not found", build_record_id)
        return

    pipeline = br.pipeline
    celery_tid = self.request.id or ""
    task_id = celery_tid or f"br-{build_record_id}"
    log_key = f"build_log_{task_id}"

    br.status = BuildRecord.STATUS_RUNNING
    br.celery_task_id = celery_tid
    br.log_key = log_key
    br.save(update_fields=["status", "celery_task_id", "log_key"])

    pipeline.status = Pipeline.STATUS_RUNNING
    pipeline.save(update_fields=["status"])

    r = _redis_client()
    try:
        r.delete(log_key)
    except Exception as exc:
        logger.warning("redis delete %s: %s", log_key, exc)

    client = None
    container = None
    timed_out = False
    pump_error: list[str] = []
    collected: list[str] = []
    collected_lock = threading.Lock()
    buf_out = ""
    buf_err = ""
    started = time.monotonic()
    last_duration_flush = started

    def _maybe_flush_duration() -> None:
        nonlocal last_duration_flush
        now_m = time.monotonic()
        if now_m - last_duration_flush < _DURATION_FLUSH_INTERVAL_S:
            return
        last_duration_flush = now_m
        elapsed = now_m - started
        try:
            BuildRecord.objects.filter(pk=br.pk).update(duration=elapsed)
        except Exception as exc:
            logger.debug("duration flush failed: %s", exc)

    try:
        try:
            client = docker.from_env()
        except DockerException as exc:
            _finalize_failure(
                br=br,
                pipeline=pipeline,
                r=r,
                log_key=log_key,
                collected=collected,
                collected_lock=collected_lock,
                message=f"[system] Docker 客户端初始化失败: {exc}",
            )
            return

        img = (image or "").strip()
        if not img:
            _finalize_failure(
                br=br,
                pipeline=pipeline,
                r=r,
                log_key=log_key,
                collected=collected,
                collected_lock=collected_lock,
                message="[system] 镜像名为空",
            )
            return

        cmd = _normalize_command(command)

        try:
            if pull:
                client.images.pull(img)
        except ImageNotFound:
            _finalize_failure(
                br=br,
                pipeline=pipeline,
                r=r,
                log_key=log_key,
                collected=collected,
                collected_lock=collected_lock,
                message=f"[system] 镜像不存在或无法拉取: {img}",
            )
            return
        except (APIError, DockerException, RequestsConnectionError) as exc:
            _finalize_failure(
                br=br,
                pipeline=pipeline,
                r=r,
                log_key=log_key,
                collected=collected,
                collected_lock=collected_lock,
                message=f"[system] 拉取镜像失败: {exc}",
            )
            return

        try:
            container = client.containers.create(
                image=img,
                command=cmd,
                detach=True,
                stdout=True,
                stderr=True,
                tty=False,
            )
        except ImageNotFound:
            _finalize_failure(
                br=br,
                pipeline=pipeline,
                r=r,
                log_key=log_key,
                collected=collected,
                collected_lock=collected_lock,
                message=f"[system] 本地不存在镜像: {img}（可先 pull 或检查标签）",
            )
            return
        except (APIError, DockerException) as exc:
            _finalize_failure(
                br=br,
                pipeline=pipeline,
                r=r,
                log_key=log_key,
                collected=collected,
                collected_lock=collected_lock,
                message=f"[system] 创建容器失败: {exc}",
            )
            return

        def _pump_logs() -> None:
            nonlocal buf_out, buf_err
            try:
                stream_it = container.logs(stream=True, follow=True, demux=True)
                for parts in stream_it:
                    if not parts:
                        continue
                    out_b, err_b = parts
                    if out_b:
                        buf_out += _decode_chunk(out_b)
                        buf_out = _flush_line_buffer(
                            buf_out,
                            "stdout",
                            r=r,
                            log_key=log_key,
                            collected=collected,
                            lock=collected_lock,
                        )
                    if err_b:
                        buf_err += _decode_chunk(err_b)
                        buf_err = _flush_line_buffer(
                            buf_err,
                            "stderr",
                            r=r,
                            log_key=log_key,
                            collected=collected,
                            lock=collected_lock,
                        )
            except Exception as exc:
                pump_error.append(str(exc))
                logger.exception("docker log pump failed")
            finally:
                for stream, buf in (("stdout", buf_out), ("stderr", buf_err)):
                    rest = buf.rstrip("\n\r")
                    if rest:
                        text = f"[{stream}] {rest}"
                        try:
                            _redis_push_line(r, log_key, text)
                            with collected_lock:
                                collected.append(text)
                        except Exception:
                            pass

        try:
            container.start()
        except (APIError, DockerException) as exc:
            _finalize_failure(
                br=br,
                pipeline=pipeline,
                r=r,
                log_key=log_key,
                collected=collected,
                collected_lock=collected_lock,
                message=f"[system] 启动容器失败: {exc}",
            )
            return

        pump_thread = threading.Thread(target=_pump_logs, daemon=True)
        pump_thread.start()

        deadline = time.monotonic() + max(1, int(timeout_seconds))
        try:
            while time.monotonic() < deadline:
                _maybe_flush_duration()
                try:
                    container.reload()
                except Exception:
                    break
                state = (container.attrs or {}).get("State") or {}
                status = state.get("Status", "")
                if status in ("exited", "dead"):
                    break
                time.sleep(0.2)
            else:
                timed_out = True
                try:
                    container.kill()
                except Exception:
                    pass
                msg = f"[system] 构建超时（>{timeout_seconds}s），已终止容器"
                _redis_push_line(r, log_key, msg)
                with collected_lock:
                    collected.append(msg)
        except Exception as exc:
            timed_out = True
            logger.exception("wait loop error")
            try:
                container.kill()
            except Exception:
                pass
            msg = f"[system] 等待容器结束异常: {exc}"
            try:
                _redis_push_line(r, log_key, msg)
                with collected_lock:
                    collected.append(msg)
            except Exception:
                pass

        pump_thread.join(timeout=120)
        if pump_thread.is_alive():
            wmsg = "[system] 日志泵未在预期时间内结束"
            try:
                _redis_push_line(r, log_key, wmsg)
                with collected_lock:
                    collected.append(wmsg)
            except Exception:
                pass

        if pump_error:
            msg = f"[system] 日志流异常: {pump_error[0]}"
            try:
                _redis_push_line(r, log_key, msg)
                with collected_lock:
                    collected.append(msg)
            except Exception:
                pass

        exit_code = 1
        try:
            container.reload()
            exit_code = int(
                (container.attrs or {}).get("State", {}).get("ExitCode", 1)
            )
        except Exception:
            pass

        if timed_out:
            exit_code = exit_code if exit_code != 0 else 124

        now = timezone.now()
        elapsed = (now - br.start_time).total_seconds()
        br.end_time = now
        br.duration = elapsed
        br.status = (
            BuildRecord.STATUS_SUCCESS
            if exit_code == 0 and not timed_out
            else BuildRecord.STATUS_FAIL
        )
        br.save(update_fields=["status", "end_time", "duration"])

        pipeline.status = (
            Pipeline.STATUS_SUCCESS
            if exit_code == 0 and not timed_out
            else Pipeline.STATUS_FAIL
        )
        pipeline.save(update_fields=["status"])

        with collected_lock:
            lines_copy = list(collected)
        for text in lines_copy:
            try:
                PipelineLog.objects.create(build_record=br, log_text=text)
            except Exception:
                logger.exception("persist pipeline log line failed")

    except Exception:
        logger.exception("run_build_task 未预期异常")
        try:
            br.refresh_from_db()
            if br.status == BuildRecord.STATUS_RUNNING:
                now = timezone.now()
                br.end_time = now
                br.duration = (now - br.start_time).total_seconds()
                br.status = BuildRecord.STATUS_FAIL
                br.save(update_fields=["status", "end_time", "duration"])
                pipeline.refresh_from_db()
                pipeline.status = Pipeline.STATUS_FAIL
                pipeline.save(update_fields=["status"])
        except Exception:
            pass
    finally:
        _force_remove_container(client, container)
        _safe_close_client(client)


def _fail_import_error(build_record_id: int) -> None:
    from project.models import BuildRecord, Pipeline

    try:
        br = BuildRecord.objects.select_related("pipeline").get(pk=build_record_id)
    except BuildRecord.DoesNotExist:
        return
    pipeline = br.pipeline
    now = timezone.now()
    br.end_time = now
    br.duration = (now - br.start_time).total_seconds()
    br.status = BuildRecord.STATUS_FAIL
    br.save(update_fields=["status", "end_time", "duration"])
    pipeline.status = Pipeline.STATUS_FAIL
    pipeline.save(update_fields=["status"])
    logger.error("docker SDK 未安装，无法执行 run_build_task")


def _finalize_failure(
    *,
    br,
    pipeline,
    r,
    log_key: str,
    collected: list[str],
    collected_lock: threading.Lock,
    message: str,
) -> None:
    from project.models import PipelineLog

    try:
        _redis_push_line(r, log_key, message)
    except Exception:
        pass
    with collected_lock:
        collected.append(message)
    now = timezone.now()
    br.end_time = now
    br.duration = (now - br.start_time).total_seconds()
    br.status = BuildRecord.STATUS_FAIL
    br.save(update_fields=["status", "end_time", "duration"])
    pipeline.status = Pipeline.STATUS_FAIL
    pipeline.save(update_fields=["status"])
    with collected_lock:
        lines_copy = list(collected)
    for text in lines_copy:
        try:
            PipelineLog.objects.create(build_record=br, log_text=text)
        except Exception:
            pass


def _safe_close_client(client) -> None:
    if client is None:
        return
    try:
        client.close()
    except Exception:
        pass
