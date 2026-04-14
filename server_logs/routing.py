from django.urls import re_path

from server_logs import consumers

websocket_urlpatterns = [
    re_path(
        r"^ws/server-logs/(?P<server_id>[0-9]+)/$",
        consumers.LogViewerConsumer.as_asgi(),
    ),
]
