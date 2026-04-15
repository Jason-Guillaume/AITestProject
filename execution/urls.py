# project/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path

from execution.views import *
from execution.views_k6 import K6LoadTestSessionViewSet

# 1. 实例化路由器
router = DefaultRouter()

# 2. 注册视图集
# 参数1: URL前缀 (如 projects)
# 参数2: 对应的 ViewSet
router.register(r"plans", TestPlanViewSet)
router.register(r"reports", TestReportViewSet)
router.register(r"tasks", PerfTaskViewSet)
router.register(r"scheduled-tasks", ScheduledTaskViewSet)
router.register(r"scheduled-task-logs", ScheduledTaskLogViewSet)
router.register(r"k6-sessions", K6LoadTestSessionViewSet)

# 3. 暴露路由
urlpatterns = router.urls + [
    path(
        "dashboard/stream/",
        DashboardStreamView.as_view(),
        name="dashboard-stream",
    ),
    path(
        "dashboard/summary/",
        DashboardSummaryAPIView.as_view(),
        name="dashboard-summary",
    ),
    path(
        "dashboard/quality/",
        QualityDashboardView.as_view(),
        name="dashboard-quality",
    ),
]
