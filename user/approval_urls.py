"""独立挂载到 /api/change-requests/ 的审批路由。"""

from django.urls import path

from user.views import AdminChangeRequestApproveAPIView, AdminChangeRequestRejectAPIView

urlpatterns = [
    path("<int:pk>/approve/", AdminChangeRequestApproveAPIView.as_view()),
    path("<int:pk>/reject/", AdminChangeRequestRejectAPIView.as_view()),
]
