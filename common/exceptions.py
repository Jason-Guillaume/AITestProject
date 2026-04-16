"""
自定义异常类
提供业务逻辑中使用的异常类型
"""
from rest_framework.exceptions import APIException
from rest_framework import status


class BusinessException(APIException):
    """
    业务异常基类

    所有业务相关的异常都应该继承此类

    Attributes:
        status_code: HTTP 状态码
        default_detail: 默认错误消息
        default_code: 默认错误代码
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "业务处理失败"
    default_code = "business_error"

    def __init__(self, detail=None, code=None):
        """
        初始化异常

        Args:
            detail: 错误详情
            code: 错误代码
        """
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code

        super().__init__(detail, code)


class ResourceNotFoundException(BusinessException):
    """
    资源不存在异常

    当请求的资源不存在时抛出此异常

    Example:
        >>> raise ResourceNotFoundException("测试用例不存在")
    """
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "资源不存在"
    default_code = "resource_not_found"


class PermissionDeniedException(BusinessException):
    """
    权限不足异常

    当用户没有权限执行某个操作时抛出此异常

    Example:
        >>> raise PermissionDeniedException("您没有权限删除此用例")
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "权限不足"
    default_code = "permission_denied"


class ValidationException(BusinessException):
    """
    数据验证异常

    当数据验证失败时抛出此异常

    Example:
        >>> raise ValidationException("用例名称不能为空")
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "数据验证失败"
    default_code = "validation_error"


class DuplicateException(BusinessException):
    """
    重复数据异常

    当尝试创建重复的数据时抛出此异常

    Example:
        >>> raise DuplicateException("用例名称已存在")
    """
    status_code = status.HTTP_409_CONFLICT
    default_detail = "数据已存在"
    default_code = "duplicate_error"


class OperationFailedException(BusinessException):
    """
    操作失败异常

    当业务操作失败时抛出此异常

    Example:
        >>> raise OperationFailedException("用例执行失败")
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "操作失败"
    default_code = "operation_failed"


class ExternalServiceException(BusinessException):
    """
    外部服务异常

    当调用外部服务失败时抛出此异常

    Example:
        >>> raise ExternalServiceException("AI 服务调用失败")
    """
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "外部服务不可用"
    default_code = "external_service_error"


class RateLimitException(BusinessException):
    """
    限流异常

    当请求超过限流阈值时抛出此异常

    Example:
        >>> raise RateLimitException("请求过于频繁，请稍后再试")
    """
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "请求过于频繁"
    default_code = "rate_limit_exceeded"


class ConfigurationException(BusinessException):
    """
    配置异常

    当系统配置错误时抛出此异常

    Example:
        >>> raise ConfigurationException("AI 模型未配置")
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "系统配置错误"
    default_code = "configuration_error"
