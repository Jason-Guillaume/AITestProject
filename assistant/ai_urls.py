from django.urls import path

from assistant.views import (
    AiGenerateCasesAPIView,
    AiGenerateCasesStreamView,
    AiPhase1PreviewAPIView,
    AiPatchApplyAPIView,
    AiPatchFromExecutionAPIView,
    AiPatchListAPIView,
    AiPatchRollbackAPIView,
    AiSecurityAnalyzeExecutionAPIView,
    AiSecurityGenerateCasesAPIView,
    AiKnowledgeAskAPIView,
    AiSuggestCaseFixAPIView,
    AiTestConnectionAPIView,
    AiVerifyConnectionAPIView,
)

urlpatterns = [
    path("verify-connection/", AiVerifyConnectionAPIView.as_view()),
    path("test-connection/", AiTestConnectionAPIView.as_view()),
    path("phase1-preview/", AiPhase1PreviewAPIView.as_view()),
    path("generate-cases/", AiGenerateCasesAPIView.as_view()),
    path("generate-cases-stream/", AiGenerateCasesStreamView.as_view()),
    path("suggest-case-fix/", AiSuggestCaseFixAPIView.as_view()),
    path("patches/", AiPatchListAPIView.as_view()),
    path("patches/from-execution/", AiPatchFromExecutionAPIView.as_view()),
    path("patches/<int:patch_id>/apply/", AiPatchApplyAPIView.as_view()),
    path("patches/<int:patch_id>/rollback/", AiPatchRollbackAPIView.as_view()),
    path("security/generate-cases/", AiSecurityGenerateCasesAPIView.as_view()),
    path("security/analyze-execution/", AiSecurityAnalyzeExecutionAPIView.as_view()),
    path("knowledge/ask/", AiKnowledgeAskAPIView.as_view()),
]
