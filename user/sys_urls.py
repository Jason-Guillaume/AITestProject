from django.urls import path

from user.sys_views import (
    AIModelConfigAPIView,
    AIModelConfigDisconnectAPIView,
    AIModelConfigReconnectAPIView,
)

urlpatterns = [
    path("ai-config/", AIModelConfigAPIView.as_view()),
    path("ai-config/disconnect/", AIModelConfigDisconnectAPIView.as_view()),
    path("ai-config/reconnect/", AIModelConfigReconnectAPIView.as_view()),
]
