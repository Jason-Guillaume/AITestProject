"""
ASGI config for AITestProduct project.

HTTP 由 Django 处理；WebSocket 由 Channels 路由到 execution 应用（k6 实时指标）。
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AITestProduct.settings")

django_asgi_app = get_asgi_application()

from execution.middleware_ws import TokenAuthMiddleware  # noqa: E402
from execution.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": TokenAuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
