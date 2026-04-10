# user/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CaptchaAPIView,
    UserRegisterAPIView,
    UserLoginAPIView,
    CurrentUserAPIView,
    UserViewSet,
    OrganizationViewSet,
    SystemMessageSettingViewSet,
    RoleViewSet,
    ChangePasswordAPIView,
    UserProfileAPIView,
    UserMyPendingSensitiveStatusAPIView,
    UserSensitiveChangeRequestAPIView,
    SystemMessageListAPIView,
    SystemMessageMarkReadAPIView,
    AdminUserChangeRequestListAPIView,
    AdminUserChangeRequestDecisionAPIView,
)

# 1. 实例化路由器，专门用来注册 ViewSet
router = DefaultRouter()
router.register(r'users', UserViewSet)  # 注册用户增删改查接口
router.register(r'orgs', OrganizationViewSet)
router.register(r'message-settings', SystemMessageSettingViewSet)
router.register(r'roles', RoleViewSet)

# 2. 将普通 APIView 的路由与 Router 的路由合并
urlpatterns = [
    path('captcha/', CaptchaAPIView.as_view(), name='captcha'),
    path('register/', UserRegisterAPIView.as_view(), name='register'),
    path('login/', UserLoginAPIView.as_view(), name='login'),
    path('me/', CurrentUserAPIView.as_view(), name='current-user'),
    path('me/profile/', UserProfileAPIView.as_view(), name='user-profile'),
    path('me/change-requests-status/', UserMyPendingSensitiveStatusAPIView.as_view(), name='user-change-requests-status'),
    path('me/sensitive-change/', UserSensitiveChangeRequestAPIView.as_view(), name='user-sensitive-change'),
    path('system-messages/', SystemMessageListAPIView.as_view(), name='system-messages'),
    path('system-messages/<int:pk>/read/', SystemMessageMarkReadAPIView.as_view(), name='system-message-mark-read'),
    path('admin/change-requests/', AdminUserChangeRequestListAPIView.as_view(), name='admin-change-requests'),
    path('admin/change-requests/<int:pk>/decision/', AdminUserChangeRequestDecisionAPIView.as_view(), name='admin-change-request-decision'),
    path('change-password/', ChangePasswordAPIView.as_view(), name='change-password'),

    # 将 router 自动生成的接口全部挂载到当前路径下
    path('', include(router.urls)),
]