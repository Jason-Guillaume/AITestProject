from django.urls import path, include
from rest_framework.routers import DefaultRouter

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
from assistant.ui_automation_views import UiAutomationGenerateAPIView
from assistant.ui_element_views import (
    UIModuleViewSet,
    UIPageViewSet,
    UIPageElementViewSet,
    UITestCaseViewSet,
    UIActionStepViewSet
)

# 创建路由器用于UI元素库的ViewSet
router = DefaultRouter()
router.register(r'ui-modules', UIModuleViewSet, basename='ui-module')
router.register(r'ui-pages', UIPageViewSet, basename='ui-page')
router.register(r'ui-elements', UIPageElementViewSet, basename='ui-element')
router.register(r'ui-test-cases', UITestCaseViewSet, basename='ui-test-case')
router.register(r'ui-action-steps', UIActionStepViewSet, basename='ui-action-step')

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
    path("ui-automation/generate/", UiAutomationGenerateAPIView.as_view()),
    # UI元素库路由
    path("", include(router.urls)),
]
