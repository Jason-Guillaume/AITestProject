# project/urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter
from testcase.views import *

# 1. 实例化路由器
router = DefaultRouter()

# 2. 注册视图集
# 参数1: URL前缀 (如 projects)
# 参数2: 对应的 ViewSet
router.register(r'cases', TestCaseViewSet)
router.register(r'modules', TestModuleViewSet)
router.register(r'environments', TestEnvironmentViewSet)
router.register(r'environment-variables', EnvironmentVariableViewSet)
router.register(r"approaches", TestApproachViewSet)
router.register(r'steps', TestCaseStepViewSet)
router.register(r'designs', TestDesignViewSet)

# 3. 暴露路由（含 AI 数据增强与 Swagger/cURL 导入）
urlpatterns = [
    path("ai-fill-test-data/", AiFillTestDataAPIView.as_view()),
    path("suggest-extractions/", SuggestExtractionsAPIView.as_view()),
    path("import-api-spec/", ApiImportFromSpecAPIView.as_view()),
] + router.urls