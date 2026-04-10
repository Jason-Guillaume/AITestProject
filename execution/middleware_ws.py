"""
WebSocket 连接：支持查询参数 ?token=<DRF Token>，写入 scope["user"]。
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _user_from_token(key: str):
    if not key:
        return AnonymousUser()
    try:
        from rest_framework.authtoken.models import Token

        t = Token.objects.select_related("user").get(key=key)
        return t.user
    except Exception:
        return AnonymousUser()


class TokenAuthMiddleware:
    """ASGI 中间件：在路由前解析 token。"""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            qs = parse_qs(scope.get("query_string", b"").decode())
            token = (qs.get("token") or [None])[0]
            scope["user"] = await _user_from_token(token or "")
        return await self.inner(scope, receive, send)
