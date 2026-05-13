import logging
from django.utils import timezone
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from common.exceptions import BusinessException

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    if isinstance(exc, BusinessException):
        logger.warning(
            "业务异常: %s | 路径: %s",
            exc.detail,
            context.get("request").path if context.get("request") else "",
        )
        return Response(
            {
                "code": exc.status_code,
                "message": str(exc.detail),
                "data": None,
                "timestamp": timezone.now().isoformat(),
            },
            status=exc.status_code,
        )

    response = exception_handler(exc, context)

    if response is not None:
        detail = response.data
        message = ""
        if isinstance(detail, dict):
            message = detail.get("detail", str(detail))
            if isinstance(message, list):
                message = "; ".join(str(x) for x in message)
        elif isinstance(detail, list):
            message = "; ".join(str(x) for x in detail)
        elif isinstance(detail, str):
            message = detail
        else:
            message = str(detail)

        logger.warning(
            "API 异常: %s | 路径: %s | 状态码: %s",
            message,
            context.get("request").path if context.get("request") else "",
            response.status_code,
        )

        response.data = {
            "code": response.status_code,
            "message": message,
            "data": None,
            "timestamp": timezone.now().isoformat(),
        }
    else:
        logger.exception(
            "未处理的异常: %s | 路径: %s",
            str(exc),
            context.get("request").path if context.get("request") else "",
        )
        response = Response(
            {
                "code": 500,
                "message": "服务器内部错误",
                "data": None,
                "timestamp": timezone.now().isoformat(),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
