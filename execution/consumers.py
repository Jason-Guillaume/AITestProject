import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


@database_sync_to_async
def _session_exists(run_id: str) -> bool:
    from execution.models import K6LoadTestSession

    return K6LoadTestSession.objects.filter(run_id=run_id, is_deleted=False).exists()


class K6MetricsConsumer(AsyncWebsocketConsumer):
    """
    订阅 k6 压测会话的实时指标：加入 Channels 组 k6_run_<run_id>。
    """

    async def connect(self):
        self.run_id = self.scope["url_route"]["kwargs"]["run_id"]
        user = self.scope.get("user")
        if isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4401)
            return
        if not await _session_exists(self.run_id):
            await self.close(code=4404)
            return
        self.group_name = f"k6_run_{self.run_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(
            text_data=json.dumps(
                {
                    "type": "status",
                    "phase": "subscribed",
                    "run_id": self.run_id,
                    "message": "已订阅实时指标",
                },
                ensure_ascii=False,
            )
        )

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def k6_metrics(self, event):
        payload = event.get("payload") or {}
        try:
            await self.send(text_data=json.dumps(payload, ensure_ascii=False))
        except Exception:
            logger.exception("WebSocket 推送失败")
