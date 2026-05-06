"""WebSocket 路由：CI/CD 流水线等。"""

from django.urls import re_path

from project import consumers

websocket_urlpatterns = [
    re_path(
        r"^ws/logs/(?P<build_record_id>[0-9]+)/$",
        consumers.BuildLogConsumer.as_asgi(),
    ),
]
