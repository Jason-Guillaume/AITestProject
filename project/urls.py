# project/urls.py
from rest_framework.routers import DefaultRouter
from project.views import TestProjectViewSet, TestTaskViewSet, ReleasePlanViewSet

# 1. 实例化路由器
router = DefaultRouter()

# 2. 注册视图集
# 参数1: URL前缀 (如 projects)
# 参数2: 对应的 ViewSet
router.register(r"projects", TestProjectViewSet)
router.register(r"tasks", TestTaskViewSet)
router.register(r"releases", ReleasePlanViewSet)

# 3. 暴露路由
urlpatterns = router.urls
