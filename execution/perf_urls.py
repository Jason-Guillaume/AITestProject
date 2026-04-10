from rest_framework.routers import DefaultRouter

from execution.views import PerfTaskViewSet
from execution.views_k6 import K6LoadTestSessionViewSet

router = DefaultRouter()
router.register(r"tasks", PerfTaskViewSet, basename="perf-task")
router.register(r"k6-sessions", K6LoadTestSessionViewSet, basename="k6-session")

urlpatterns = router.urls
