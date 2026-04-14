from django.urls import path

from assistant.views import (
    AiGenerateCasesAPIView,
    AiGenerateCasesStreamView,
    AiPhase1PreviewAPIView,
    AiTestConnectionAPIView,
    AiVerifyConnectionAPIView,
)

urlpatterns = [
    path("verify-connection/", AiVerifyConnectionAPIView.as_view()),
    path("test-connection/", AiTestConnectionAPIView.as_view()),
    path("phase1-preview/", AiPhase1PreviewAPIView.as_view()),
    path("generate-cases/", AiGenerateCasesAPIView.as_view()),
    path("generate-cases-stream/", AiGenerateCasesStreamView.as_view()),
]
