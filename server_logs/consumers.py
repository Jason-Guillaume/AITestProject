import asyncio
import json
import logging
import queue
import threading
import urllib.parse

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from server_logs.access import remote_log_server_queryset_for_user
from server_logs.audit import log_server_log_event_async
from server_logs.models import ServerLogAuditEvent
from server_logs.ssh_tail import ssh_tail_worker
from server_logs.validators import validate_remote_log_path

logger = logging.getLogger(__name__)


@database_sync_to_async
def _load_server_payload(server_id: int, user):
    row = (
        remote_log_server_queryset_for_user(user)
        .filter(pk=server_id)
        .select_related("organization")
        .first()
    )
    if not row:
        return None
    return {
        "server_id": row.id,
        "host_name": row.name,
        "host": row.host,
        "port": row.port,
        "username": row.username,
        "password": row.get_password(),
        "private_key": row.get_private_key(),
        "server_type": row.server_type,
        "default_log_path": row.default_log_path or "/var/log/syslog",
    }


class LogViewerConsumer(AsyncWebsocketConsumer):
    """
    WebSocket：SSH tail -f（或 Windows Get-Content -Wait）实时推送；
    无输出时由 SSH 通道读超时触发 hb，经本端转为 heartbeat 消息。
    """

    async def connect(self):
        accepted = False
        try:
            user = self.scope.get("user")
            if isinstance(user, AnonymousUser) or not user.is_authenticated:
                await self.close(code=4401)
                return

            try:
                self.server_id = int(self.scope["url_route"]["kwargs"]["server_id"])
            except (TypeError, ValueError):
                await self.close(code=4400)
                return

            qs = urllib.parse.parse_qs(
                (self.scope.get("query_string") or b"").decode(errors="replace")
            )
            raw_path = (qs.get("path") or [""])[0].strip()
            try:
                raw_path = urllib.parse.unquote(raw_path)
            except Exception:
                pass

            payload = await _load_server_payload(self.server_id, user)
            if not payload:
                await self.close(code=4404)
                return

            self.log_path = raw_path or payload["default_log_path"]
            path_err = validate_remote_log_path(self.log_path, payload["server_type"])
            await self.accept()
            accepted = True
            if path_err:
                await log_server_log_event_async(
                    user=user,
                    action=ServerLogAuditEvent.Action.WS_CONNECT,
                    remote_server_id=self.server_id,
                    meta={"path": self.log_path, "accepted": False, "reason": path_err},
                    scope=self.scope,
                )
                await self.send(
                    text_data=json.dumps(
                        {"type": "error", "message": path_err},
                        ensure_ascii=False,
                    )
                )
                await self.close(code=4400)
                return

            self._stop = threading.Event()
            self._q: queue.Queue = queue.Queue(maxsize=8000)
            self._thread = threading.Thread(
                target=ssh_tail_worker,
                kwargs={
                    "server_id": payload["server_id"],
                    "host_name": payload["host_name"],
                    "host": payload["host"],
                    "port": payload["port"],
                    "username": payload["username"],
                    "password": payload["password"],
                    "private_key_text": payload["private_key"],
                    "server_type": payload["server_type"],
                    "log_path": self.log_path,
                    "out_queue": self._q,
                    "stop_event": self._stop,
                    # WebSocket 实时查看：优先快速失败，避免长时间无回包
                    "connect_timeout": 10.0,
                },
                daemon=True,
                name=f"ssh-tail-{self.server_id}",
            )

            await self.send(
                text_data=json.dumps(
                    {
                        "type": "status",
                        "phase": "connected",
                        "path": self.log_path,
                        "message": "已连接，正在打开远程日志流",
                    },
                    ensure_ascii=False,
                )
            )
            await log_server_log_event_async(
                user=user,
                action=ServerLogAuditEvent.Action.WS_CONNECT,
                remote_server_id=self.server_id,
                meta={"path": self.log_path, "accepted": True},
                scope=self.scope,
            )
            self._thread.start()
            self._pump_task = asyncio.create_task(self._pump_queue())
        except Exception:
            logger.exception("server-logs websocket connect failed")
            try:
                if not accepted:
                    await self.accept()
            except Exception:
                pass
            try:
                await self.send(
                    text_data=json.dumps(
                        {"type": "error", "message": "服务器内部错误（500），请查看后端运行日志定位原因"},
                        ensure_ascii=False,
                    )
                )
            except Exception:
                pass
            try:
                await self.close(code=1011)
            except Exception:
                pass
            return

    async def disconnect(self, code):
        if hasattr(self, "_stop"):
            self._stop.set()
        if hasattr(self, "_pump_task"):
            self._pump_task.cancel()
            try:
                await self._pump_task
            except asyncio.CancelledError:
                pass
        if hasattr(self, "_thread") and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        user = self.scope.get("user")
        if user and user.is_authenticated and hasattr(self, "server_id"):
            try:
                await log_server_log_event_async(
                    user=user,
                    action=ServerLogAuditEvent.Action.WS_DISCONNECT,
                    remote_server_id=self.server_id,
                    meta={"close_code": int(code) if code is not None else None},
                    scope=self.scope,
                )
            except Exception:
                logger.exception("audit disconnect failed")

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            msg = json.loads(text_data)
        except json.JSONDecodeError:
            return
        mtype = msg.get("type")
        user = self.scope.get("user")
        if mtype == "ping":
            await self.send(
                text_data=json.dumps({"type": "pong", "ts": msg.get("ts")}, ensure_ascii=False)
            )
        elif mtype == "stop" and hasattr(self, "_stop"):
            self._stop.set()
            await self.send(
                text_data=json.dumps(
                    {"type": "status", "phase": "stopping", "message": "正在停止远程 tail"},
                    ensure_ascii=False,
                )
            )
            if user and user.is_authenticated and hasattr(self, "server_id"):
                try:
                    await log_server_log_event_async(
                        user=user,
                        action=ServerLogAuditEvent.Action.WS_STOP,
                        remote_server_id=self.server_id,
                        scope=self.scope,
                    )
                except Exception:
                    logger.exception("audit stop failed")

    async def _pump_queue(self):
        loop = asyncio.get_running_loop()

        def _get_item():
            try:
                return self._q.get(timeout=0.4)
            except queue.Empty:
                return None

        try:
            while True:
                try:
                    item = await loop.run_in_executor(None, _get_item)
                except Exception:
                    logger.exception("queue read failed")
                    break
                if item is None:
                    continue
                kind, payload = item

                if kind == "line":
                    await self.send(
                        text_data=json.dumps(
                            {"type": "log", "line": payload},
                            ensure_ascii=False,
                        )
                    )
                elif kind == "hb":
                    await self.send(
                        text_data=json.dumps({"type": "heartbeat"}, ensure_ascii=False)
                    )
                elif kind == "error":
                    await self.send(
                        text_data=json.dumps(
                            {"type": "error", "message": payload},
                            ensure_ascii=False,
                        )
                    )
                    # 错误后尽快关闭连接，避免前端“挂住”以及 dev reload 残留任务
                    try:
                        if hasattr(self, "_stop"):
                            self._stop.set()
                    except Exception:
                        pass
                    try:
                        await self.close(code=1011)
                    except Exception:
                        pass
                    break
                elif kind == "done":
                    # SSH tail 线程已结束：主动通知并关闭连接，避免在 dev server reload 时残留任务
                    # 导致 daphne 报 "took too long to shut down"。
                    try:
                        await self.send(
                            text_data=json.dumps(
                                {
                                    "type": "status",
                                    "phase": "done",
                                    "message": "远程日志流已结束",
                                },
                                ensure_ascii=False,
                            )
                        )
                    except Exception:
                        pass
                    try:
                        await self.close(code=1000)
                    except Exception:
                        pass
                    break
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("LogViewerConsumer pump failed")
