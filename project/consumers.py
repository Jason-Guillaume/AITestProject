"""
CI/CD 流水线 WebSocket：构建日志订阅（Channels Group + Redis layer）。
"""

from __future__ import annotations

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


@database_sync_to_async
def _can_subscribe_build_logs(user, build_record_id: int) -> bool:
    """校验用户是否可订阅该次构建的日志（与 REST 侧尽量一致：存在、流水线未删、本人/管理员）。"""
    from project.models import BuildRecord

    if isinstance(user, AnonymousUser) or not getattr(user, "is_authenticated", False):
        return False
    try:
        br = BuildRecord.objects.select_related("pipeline").get(pk=build_record_id)
    except BuildRecord.DoesNotExist:
        return False
    pipeline = br.pipeline
    if getattr(pipeline, "is_deleted", False):
        return False
    if user.is_staff or user.is_superuser or bool(getattr(user, "is_system_admin", False)):
        return True
    creator_id = getattr(pipeline, "creator_id", None)
    if creator_id and creator_id == user.id:
        return True
    return False


class BuildLogConsumer(AsyncWebsocketConsumer):
    """
    订阅单次构建的实时日志流。

    URL: ``/ws/logs/<build_record_id>/?token=<DRF Token>``

    连接后加入 Channels 组 ``build_log_{build_record_id}``（与 Redis channel layer 对应）。
    服务端其它位置通过 ``channel_layer.group_send`` 推送，``type`` 须为 ``send.log``，
    由本类的 ``send_log`` 处理并转发到浏览器。
    """

    group_prefix = "build_log"

    async def connect(self):
        raw = self.scope["url_route"]["kwargs"].get("build_record_id")
        try:
            self.build_record_id = int(raw)
        except (TypeError, ValueError):
            await self.close(code=4400)
            return

        user = self.scope.get("user")
        if isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4401)
            return

        if not await _can_subscribe_build_logs(user, self.build_record_id):
            await self.close(code=4403)
            return

        self.group_name = f"{self.group_prefix}_{self.build_record_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(
            text_data=json.dumps(
                {
                    "type": "status",
                    "phase": "subscribed",
                    "build_record_id": self.build_record_id,
                    "group": self.group_name,
                    "message": "已订阅构建日志",
                },
                ensure_ascii=False,
            )
        )

    async def disconnect(self, code):
        if getattr(self, "group_name", None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_log(self, event):
        """
        接收来自 Group 的消息（``group_send`` 中 ``type`` 为 ``send.log``）。

        约定 ``event`` 字段::

            payload: dict，建议含 ``line`` 或 ``text`` 表示一行日志；也可直接传整包给前端。
        """
        try:
            payload = event.get("payload")
            if isinstance(payload, dict):
                out = {
                    "type": "log",
                    "build_record_id": self.build_record_id,
                    **payload,
                }
            else:
                line = event.get("line") or event.get("text") or event.get("message") or ""
                out = {
                    "type": "log",
                    "build_record_id": self.build_record_id,
                    "line": line,
                }
            await self.send(text_data=json.dumps(out, ensure_ascii=False))
        except Exception:
            logger.exception("BuildLogConsumer.send_log 推送到客户端失败")
