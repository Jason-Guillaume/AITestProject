from rest_framework.routers import DefaultRouter

from testcase.views import TestEnvironmentViewSet

router = DefaultRouter()
router.register(r"", TestEnvironmentViewSet, basename="environment")

urlpatterns = router.urls
