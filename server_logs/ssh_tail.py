"""
阻塞式 SSH tail：供 Channels consumer 在线程中运行。
使用 Paramiko exec_command + channel 超时，便于在无输出时配合心跳。
"""

from __future__ import annotations

import logging
import queue
import shlex
import socket
import threading
import time
from io import StringIO
from typing import Any

from server_logs.es_client import get_server_logs_es_index

logger = logging.getLogger(__name__)

_es_client = None
_es_ingest_q: "queue.Queue[dict]" | None = None
_es_ingest_thread: threading.Thread | None = None
_celery_bulk_lock = threading.Lock()
_celery_bulk_buf: list[dict] = []
_celery_bulk_last_flush = 0.0
_celery_bulk_max_docs = 200
_celery_bulk_max_wait_s = 1.0


def _init_es_client():
    """初始化 Elasticsearch 客户端（配置见 Django settings / 环境变量）。"""
    global _es_client
    if _es_client is not None:
        return _es_client
    try:
        from server_logs.es_client import get_elasticsearch_client
    except Exception as e:  # pragma: no cover
        logger.warning("Elasticsearch client factory unavailable: %s", e)
        _es_client = False  # type: ignore[assignment]
        return _es_client

    try:
        _es_client = get_elasticsearch_client()
        _ensure_es_index_template(_es_client, get_server_logs_es_index())
    except Exception as e:
        logger.warning("Elasticsearch init failed: %s", e)
        _es_client = False  # type: ignore[assignment]
    return _es_client


def _ensure_es_index_template(es, alias: str) -> None:
    """
    为日志索引创建/更新模板，确保字段类型稳定（alias 为写别名，如 server-logs）：
    - server_id: integer（term 过滤）
    - host_name: keyword（聚合/精确过滤）
    - message: text（全文检索）
    - timestamp: date（毫秒时间戳，排序/范围查询）

    注意：任何异常都应吞掉，不能影响实时推送。
    """
    try:
        # 1) ILM policy：3 天后删除；索引超过 500MB 自动 rollover
        #    任意失败都吞掉，避免影响实时推送。
        ilm_name = f"{alias}-ilm"
        try:
            es.ilm.put_lifecycle(
                name=ilm_name,
                body={
                    "policy": {
                        "phases": {
                            "hot": {
                                "actions": {
                                    "rollover": {
                                        "max_primary_shard_size": "500mb",
                                    }
                                }
                            },
                            "delete": {
                                "min_age": "3d",
                                "actions": {"delete": {}},
                            },
                        }
                    }
                },
            )
        except Exception as e:
            logger.debug("ensure es ilm policy failed: %s", str(e)[:200])

        template_name = f"{alias}-template"
        body = {
            "index_patterns": [f"{alias}-*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "index.lifecycle.name": ilm_name,
                    "index.lifecycle.rollover_alias": alias,
                },
                "mappings": {
                    "dynamic": True,
                    "properties": {
                        "server_id": {"type": "integer"},
                        "host_name": {"type": "keyword", "ignore_above": 256},
                        "message": {"type": "text"},
                        "timestamp": {"type": "date", "format": "epoch_millis"},
                    },
                },
            },
        }
        # ES 8/9 Python client: indices.put_index_template
        es.indices.put_index_template(name=template_name, body=body)
        # 2) 初始化 rollover：创建首个物理索引，并设置别名为写索引
        first_physical = f"{alias}-000001"
        try:
            if not es.indices.exists(index=first_physical):
                es.indices.create(
                    index=first_physical,
                    aliases={alias: {"is_write_index": True}},
                )
        except Exception as e:
            logger.debug("ensure rollover index failed: %s", str(e)[:200])
    except Exception as e:
        logger.debug("ensure es index template failed: %s", str(e)[:200])


def _ensure_es_ingest_worker() -> None:
    """启动后台 ES 写入线程（失败不影响实时推送）。"""
    global _es_ingest_q, _es_ingest_thread
    if (
        _es_ingest_q is not None
        and _es_ingest_thread is not None
        and _es_ingest_thread.is_alive()
    ):
        return
    _es_ingest_q = queue.Queue(maxsize=50000)

    def _worker():
        es = _init_es_client()
        if not es or es is False:  # type: ignore[truthy-bool]
            # ES 不可用时直接丢弃（避免阻塞实时推送线程）
            while True:
                try:
                    _es_ingest_q.get(timeout=2.0)  # type: ignore[union-attr]
                except Exception:
                    continue
        while True:
            try:
                doc = _es_ingest_q.get(timeout=1.0)  # type: ignore[union-attr]
            except queue.Empty:
                continue
            try:
                es.index(index=get_server_logs_es_index(), document=doc)
            except Exception as e:
                # 只记录 debug，避免噪音；关键是不能阻塞/中断实时流
                logger.debug("es index failed: %s", str(e)[:200])

    _es_ingest_thread = threading.Thread(
        target=_worker, name="server-logs-es-ingest", daemon=True
    )
    _es_ingest_thread.start()


def _flush_docs_to_local_es_queue(docs: list[dict]) -> None:
    """Celery 投递失败时的兜底：把一批文档塞回本地 ES 写入线程队列。"""
    if not docs:
        return
    _ensure_es_ingest_worker()
    if _es_ingest_q is None:
        return
    for d in docs:
        try:
            _es_ingest_q.put_nowait(d)
        except queue.Full:
            logger.debug("es ingest queue full during celery fallback, dropping doc")


def _enqueue_es_doc(doc: dict) -> None:
    """非阻塞入队（队列满则丢弃）。"""
    try:
        # 优先走 Celery：Django/ASGI 只投递任务，worker 负责写 ES
        try:
            from server_logs.tasks import index_server_log_docs_bulk  # type: ignore

            now = time.time()
            to_send: list[dict] | None = None
            with _celery_bulk_lock:
                _celery_bulk_buf.append(doc)
                global _celery_bulk_last_flush
                if _celery_bulk_last_flush <= 0:
                    _celery_bulk_last_flush = now
                if (
                    len(_celery_bulk_buf) >= _celery_bulk_max_docs
                    or (now - _celery_bulk_last_flush) >= _celery_bulk_max_wait_s
                ):
                    to_send = _celery_bulk_buf[:]
                    _celery_bulk_buf.clear()
                    _celery_bulk_last_flush = now
            if to_send:
                try:
                    index_server_log_docs_bulk.delay(to_send)  # type: ignore[attr-defined]
                except Exception:
                    # broker/worker 不可用时：不要把这批日志丢掉
                    _flush_docs_to_local_es_queue(to_send)
            return
        except Exception:
            # Celery 未运行/投递失败时，降级为本地后台线程写 ES（仍不影响实时推送）
            pass

        _ensure_es_ingest_worker()
        if _es_ingest_q is None:
            return
        _es_ingest_q.put_nowait(doc)
    except queue.Full:
        logger.debug("es ingest queue full, dropping one doc")
    except Exception:
        # 不影响实时推送
        return


def _import_paramiko():
    """延迟导入：避免未安装 paramiko 时整个 ASGI 无法加载。"""
    try:
        import paramiko
    except ImportError as e:
        raise RuntimeError(
            "未安装 paramiko，服务器日志 SSH 不可用。请在当前解释器执行: pip install paramiko"
        ) from e
    return paramiko


def _emit_queue(
    out_queue: queue.Queue, item: tuple, *, prefer_drop: bool = False
) -> None:
    """prefer_drop：队列满时丢弃该条（用于日志行），避免阻塞 SSH 读线程。"""
    if not prefer_drop:
        try:
            out_queue.put(item, timeout=5.0)
        except queue.Full:
            logger.warning(
                "server_logs queue full, dropping critical message kind=%s", item[0]
            )
        return
    try:
        out_queue.put_nowait(item)
    except queue.Full:
        logger.debug("server_logs queue full, dropping one log line")


def _load_private_key(text: str) -> Any:
    if not (text or "").strip():
        return None
    paramiko = _import_paramiko()
    bio = StringIO(text.strip())
    for cls in (
        paramiko.RSAKey,
        paramiko.Ed25519Key,
        paramiko.ECDSAKey,
    ):
        try:
            bio.seek(0)
            return cls.from_private_key(bio)
        except Exception:
            continue
    return None


def _build_remote_command(server_type: str, log_path: str) -> str:
    st = (server_type or "linux").lower()
    if st == "windows":
        ps = (log_path or "C:\\\\Windows\\\\Temp\\\\app.log").replace("'", "''")
        return (
            "powershell.exe -NoProfile -Command "
            f"\"Get-Content -LiteralPath '{ps}' -Tail 200 -Wait -Encoding UTF8\""
        )
    path_q = shlex.quote(log_path or "/var/log/messages")
    return f"tail -n 200 -f {path_q}"


def ssh_tail_worker(
    *,
    server_id: int,
    host_name: str,
    host: str,
    port: int,
    username: str,
    password: str,
    private_key_text: str,
    server_type: str,
    log_path: str,
    out_queue: queue.Queue,
    stop_event: threading.Event,
    recv_timeout: float = 8.0,
    connect_timeout: float = 20.0,
) -> None:
    """
    在独立线程中运行：将 (\"line\", str) 或 (\"error\", str) 或 (\"hb\", None) 放入队列，结束时放 (\"done\", None)。
    """
    try:
        paramiko = _import_paramiko()
    except RuntimeError as e:
        _emit_queue(out_queue, ("error", str(e)))
        _emit_queue(out_queue, ("done", None))
        return

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        pkey = _load_private_key(private_key_text)
        pwd = (password or "").strip() or None
        if not pwd and not pkey:
            _emit_queue(
                out_queue,
                (
                    "error",
                    "没有可用的 SSH 密码或私钥（解密后为空）。请检查主机配置是否已保存、"
                    "或 Fernet 密钥是否与加密时一致。",
                ),
            )
            return
        client.connect(
            hostname=host,
            port=int(port or 22),
            username=username,
            password=pwd,
            pkey=pkey,
            look_for_keys=False,
            allow_agent=False,
            timeout=float(connect_timeout or 20.0),
            banner_timeout=float(connect_timeout or 20.0),
            auth_timeout=float(connect_timeout or 20.0),
        )
        cmd = _build_remote_command(server_type, log_path)
        _stdin, stdout, stderr = client.exec_command(cmd, get_pty=False)
        chan = stdout.channel
        chan.settimeout(recv_timeout)

        buf = b""
        while not stop_event.is_set():
            try:
                chunk = chan.recv(65536)
            except socket.timeout:
                _emit_queue(out_queue, ("hb", None), prefer_drop=True)
                continue
            if not chunk:
                break
            buf += chunk
            while True:
                idx = buf.find(b"\n")
                if idx < 0:
                    break
                line = buf[:idx]
                buf = buf[idx + 1 :]
                msg = line.decode("utf-8", errors="replace").rstrip("\r")
                _emit_queue(out_queue, ("line", msg), prefer_drop=True)
                # 异步写入 ES（失败/堵塞不影响实时推送）
                _enqueue_es_doc(
                    {
                        "server_id": int(server_id),
                        "host_name": (host_name or "")[:128],
                        "message": msg,
                        "timestamp": int(time.time() * 1000),
                    }
                )
        try:
            err_raw = (stderr.read() or b"").strip()
            if err_raw:
                err_txt = err_raw.decode("utf-8", errors="replace")[:1200]
                _emit_queue(
                    out_queue,
                    (
                        "error",
                        _friendly_tail_error(server_type, log_path, err_txt),
                    ),
                )
            elif chan.exit_status_ready():
                es = chan.recv_exit_status()
                if es != 0:
                    _emit_queue(
                        out_queue,
                        (
                            "error",
                            f"远程 tail 进程已结束，退出码 {es}（请确认日志路径存在且有读权限）",
                        ),
                    )
        except Exception:
            pass
    except paramiko.AuthenticationException as e:
        _emit_queue(
            out_queue,
            (
                "error",
                f"SSH 认证失败：请核对用户名、密码或私钥；若禁止 root 密码登录请改用密钥。详情：{e}",
            ),
        )
    except (paramiko.SSHException, OSError, socket.error, TimeoutError) as e:
        _emit_queue(
            out_queue,
            (
                "error",
                f"无法连接 {host}:{port}（SSH 由运行 Django/ASGI 的机器发起，请确认该机器到目标 IP 网络互通、"
                f"防火墙放行 22 端口且 sshd 已启动）。详情：{e}",
            ),
        )
    except Exception as e:
        _emit_queue(out_queue, ("error", str(e)))
        logger.exception("ssh_tail_worker failed")
    finally:
        try:
            client.close()
        except Exception:
            pass
        _emit_queue(out_queue, ("done", None))


def _friendly_tail_error(server_type: str, log_path: str, err_text: str) -> str:
    """
    把常见的 tail/Get-Content 错误转换成更可读的提示，避免用户只能看到生硬的 stderr。
    注意：这里只做文本增强，不改变实际执行逻辑。
    """
    et = (err_text or "").strip()
    st = (server_type or "linux").lower()
    lp = log_path or ""
    low = et.lower()

    if st != "windows":
        if "no such file or directory" in low or "cannot open" in low:
            return (
                f"远程日志文件不存在或路径不正确：{lp}\n"
                "常见日志路径示例（按发行版可能不同）：\n"
                "- /var/log/messages（CentOS/RHEL 等）\n"
                "- /var/log/syslog（Ubuntu/Debian 等）\n"
                "- /var/log/auth.log（认证相关）\n"
                '你可以先在目标机执行：ls -lh /var/log | grep -E "messages|syslog|auth"，'
                "确认实际文件名后再填入上方“远程日志文件路径”。\n"
                f"原始错误：{et}"
            )
        if "permission denied" in low:
            return (
                f"远程日志文件无读取权限：{lp}\n"
                "请确认该用户具备读取权限（例如加入 adm 组、或用 sudo/提升权限），并确保日志文件可被读取。\n"
                f"原始错误：{et}"
            )

    # Windows
    if st == "windows":
        if (
            "cannot find path" in low
            or "cannot find the path" in low
            or "does not exist" in low
        ):
            return (
                f"远程日志文件不存在或路径不正确：{lp}\n"
                "请确认文件路径正确（建议用绝对路径），并确认运行 SSH 的账号有读取权限。\n"
                f"原始错误：{et}"
            )
        if "access is denied" in low:
            return (
                f"远程日志文件无读取权限：{lp}\n"
                "请确认运行 SSH 的账号拥有读取权限。\n"
                f"原始错误：{et}"
            )

    return f"远程命令错误：{et}"
