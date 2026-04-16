"""
全局异常处理中间件
统一处理应用中的所有异常
"""
import logging
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.exceptions import APIException
from rest_framework import status
from common.exceptions import BusinessException

logger = logging.getLogger(__name__)


class GlobalExceptionMiddleware:
    """
    全局异常处理中间件

    捕获并统一处理应用中的所有异常，返回标准化的错误响应

    Example:
        在 settings.py 中添加:
        MIDDLEWARE = [
            ...
            'common.middleware.exception_middleware.GlobalExceptionMiddleware',
        ]
    """

    def __init__(self, get_response):
        """
        初始化中间件

        Args:
            get_response: Django 的 get_response 函数
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        处理请求

        Args:
            request: HTTP 请求对象

        Returns:
            HTTP 响应对象
        """
        try:
            response = self.get_response(request)
            return response
        except Exception as exc:
            return self.handle_exception(exc, request)

    def handle_exception(self, exc, request):
        """
        处理异常

        Args:
            exc: 异常对象
            request: HTTP 请求对象

        Returns:
            JSON 响应对象
        """
        # 业务异常
        if isinstance(exc, BusinessException):
            return self._handle_business_exception(exc, request)

        # DRF API 异常
        if isinstance(exc, APIException):
            return self._handle_api_exception(exc, request)

        # 其他未知异常
        return self._handle_unknown_exception(exc, request)

    def _handle_business_exception(self, exc, request):
        """
        处理业务异常

        Args:
            exc: 业务异常对象
            request: HTTP 请求对象

        Returns:
            JSON 响应对象
        """
        logger.warning(
            f"业务异常: {exc.detail} | "
            f"路径: {request.path} | "
            f"用户: {getattr(request.user, 'username', 'anonymous')}"
        )

        return JsonResponse({
            "code": exc.status_code,
            "message": str(exc.detail),
            "data": None,
            "timestamp": timezone.now().isoformat()
        }, status=exc.status_code)

    def _handle_api_exception(self, exc, request):
        """
        处理 DRF API 异常

        Args:
            exc: API 异常对象
            request: HTTP 请求对象

        Returns:
            JSON 响应对象
        """
        logger.warning(
            f"API 异常: {exc.detail} | "
            f"路径: {request.path} | "
            f"用户: {getattr(request.user, 'username', 'anonymous')}"
        )

        return JsonResponse({
            "code": exc.status_code,
            "message": str(exc.detail),
            "data": None,
            "timestamp": timezone.now().isoformat()
        }, status=exc.status_code)

    def _handle_unknown_exception(self, exc, request):
        """
        处理未知异常

        Args:
            exc: 异常对象
            request: HTTP 请求对象

        Returns:
            JSON 响应对象
        """
        logger.exception(
            f"未处理的异常: {str(exc)} | "
            f"路径: {request.path} | "
            f"用户: {getattr(request.user, 'username', 'anonymous')}"
        )

        return JsonResponse({
            "code": 500,
            "message": "服务器内部错误",
            "data": None,
            "timestamp": timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
