"""
统一 API 响应格式
提供标准化的 API 响应结构
"""
from typing import Any, Optional
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone


class ApiResponse:
    """
    统一 API 响应格式

    所有 API 接口都应该使用此类返回响应，确保响应格式的一致性

    响应格式:
    {
        "code": 200,
        "message": "操作成功",
        "data": {...},
        "timestamp": "2026-04-27T10:00:00Z"
    }

    Example:
        >>> return ApiResponse.success(data={'id': 1, 'name': 'test'})
        >>> return ApiResponse.error('参数错误', code=400)
    """

    @staticmethod
    def success(
        data: Any = None,
        message: str = "操作成功",
        code: int = 200,
        status_code: int = status.HTTP_200_OK
    ) -> Response:
        """
        成功响应

        Args:
            data: 响应数据
            message: 响应消息
            code: 业务状态码
            status_code: HTTP 状态码

        Returns:
            Response 对象
        """
        return Response({
            "code": code,
            "message": message,
            "data": data,
            "timestamp": timezone.now().isoformat()
        }, status=status_code)

    @staticmethod
    def error(
        message: str,
        code: int = 400,
        data: Any = None,
        status_code: Optional[int] = None
    ) -> Response:
        """
        错误响应

        Args:
            message: 错误消息
            code: 业务状态码
            data: 额外的错误信息
            status_code: HTTP 状态码，如果为 None 则使用 code

        Returns:
            Response 对象
        """
        if status_code is None:
            status_code = code

        return Response({
            "code": code,
            "message": message,
            "data": data,
            "timestamp": timezone.now().isoformat()
        }, status=status_code)

    @staticmethod
    def paginated(
        results: list,
        total: int,
        page: int,
        page_size: int,
        message: str = "查询成功"
    ) -> Response:
        """
        分页响应

        Args:
            results: 结果列表
            total: 总数
            page: 当前页码
            page_size: 每页大小
            message: 响应消息

        Returns:
            Response 对象
        """
        return Response({
            "code": 200,
            "message": message,
            "data": {
                "results": results,
                "pagination": {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0
                }
            },
            "timestamp": timezone.now().isoformat()
        })

    @staticmethod
    def created(data: Any = None, message: str = "创建成功") -> Response:
        """
        创建成功响应

        Args:
            data: 响应数据
            message: 响应消息

        Returns:
            Response 对象
        """
        return ApiResponse.success(
            data=data,
            message=message,
            status_code=status.HTTP_201_CREATED
        )

    @staticmethod
    def no_content(message: str = "操作成功") -> Response:
        """
        无内容响应（通常用于删除操作）

        Args:
            message: 响应消息

        Returns:
            Response 对象
        """
        return Response({
            "code": 200,
            "message": message,
            "data": None,
            "timestamp": timezone.now().isoformat()
        }, status=status.HTTP_200_OK)

    @staticmethod
    def bad_request(message: str = "请求参数错误", data: Any = None) -> Response:
        """
        错误请求响应

        Args:
            message: 错误消息
            data: 额外的错误信息

        Returns:
            Response 对象
        """
        return ApiResponse.error(
            message=message,
            code=400,
            data=data,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    @staticmethod
    def unauthorized(message: str = "未认证") -> Response:
        """
        未认证响应

        Args:
            message: 错误消息

        Returns:
            Response 对象
        """
        return ApiResponse.error(
            message=message,
            code=401,
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    @staticmethod
    def forbidden(message: str = "权限不足") -> Response:
        """
        权限不足响应

        Args:
            message: 错误消息

        Returns:
            Response 对象
        """
        return ApiResponse.error(
            message=message,
            code=403,
            status_code=status.HTTP_403_FORBIDDEN
        )

    @staticmethod
    def not_found(message: str = "资源不存在") -> Response:
        """
        资源不存在响应

        Args:
            message: 错误消息

        Returns:
            Response 对象
        """
        return ApiResponse.error(
            message=message,
            code=404,
            status_code=status.HTTP_404_NOT_FOUND
        )

    @staticmethod
    def server_error(message: str = "服务器内部错误") -> Response:
        """
        服务器错误响应

        Args:
            message: 错误消息

        Returns:
            Response 对象
        """
        return ApiResponse.error(
            message=message,
            code=500,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
