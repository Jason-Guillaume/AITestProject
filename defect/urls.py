# project/urls.py
from rest_framework.routers import DefaultRouter
from defect.views import *
from django.urls import path

# 1. 实例化路由器
router = DefaultRouter()

# 2. 注册视图集
# 参数1: URL前缀 (如 projects)
# 参数2: 对应的 ViewSet
router.register(r"defects", TestDefectViewSet)

# 3. 暴露路由
urlpatterns = router.urls
urlpatterns += [
    path("defects/from-execution/", DefectFromExecutionAPIView.as_view()),
    path(
        "defects/from-security-finding/",
        DefectFromSecurityFindingAPIView.as_view(),
    ),
]
