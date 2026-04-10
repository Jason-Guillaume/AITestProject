from django.urls import re_path

from execution import consumers

websocket_urlpatterns = [
    re_path(
        r"^ws/k6/(?P<run_id>[0-9a-fA-F-]{36})/$",
        consumers.K6MetricsConsumer.as_asgi(),
    ),
]
