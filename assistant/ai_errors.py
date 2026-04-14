"""
Map OpenAI Python SDK exceptions to DRF ``Response`` payloads used by assistant views.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from rest_framework.response import Response

try:
    from openai import (
        APIConnectionError,
        APIError,
        APITimeoutError,
        AuthenticationError,
    )

    _OPENAI_SDK_ERROR_TYPES = (
        AuthenticationError,
        APITimeoutError,
        APIConnectionError,
        APIError,
    )
except ImportError:  # pragma: no cover
    _OPENAI_SDK_ERROR_TYPES = ()

logger = logging.getLogger(__name__)


def resolve_ai_test_connection_openai_error(
    exc: BaseException,
    *,
    request,
    model: str,
    api_base_url: str,
    err_body: Callable[..., Response],
) -> Response | None:
    """Return a DRF response for OpenAI SDK errors in ``AiTestConnectionAPIView``, else ``None``."""
    if not _OPENAI_SDK_ERROR_TYPES or not isinstance(exc, _OPENAI_SDK_ERROR_TYPES):
        return None
    user_id = getattr(request.user, "id", None)
    if isinstance(exc, AuthenticationError):
        logger.exception(
            "AI test connection auth failed. user_id=%s model=%s base_url=%s",
            user_id,
            model,
            api_base_url,
        )
        return err_body(f"鉴权失败，请检查 API Key：{exc}")
    if isinstance(exc, APITimeoutError):
        logger.exception(
            "AI test connection timeout. user_id=%s model=%s base_url=%s",
            user_id,
            model,
            api_base_url,
        )
        return err_body("连接上游超时，请检查网络或代理后重试。", status_code=504)
    if isinstance(exc, APIConnectionError):
        logger.exception(
            "AI test connection upstream unreachable. user_id=%s model=%s base_url=%s",
            user_id,
            model,
            api_base_url,
        )
        return err_body(f"无法连接模型服务：{exc}", status_code=502)
    if isinstance(exc, APIError):
        logger.exception(
            "AI test connection API error. user_id=%s model=%s base_url=%s",
            user_id,
            model,
            api_base_url,
        )
        raw_msg = getattr(exc, "message", None) or str(exc)
        lower_msg = str(raw_msg).lower()
        status_code = getattr(exc, "status_code", None)
        if (
            status_code == 404
            or "no any schema route found" in lower_msg
            or "schema route" in lower_msg
        ):
            return err_body(
                "上游返回 404：API 地址可能不正确。讯飞 MaaS 请使用 base_url 根路径 "
                "`https://maas-coding-api.cn-huabei-1.xf-yun.com/v2`（不要手填 /chat/completions）。",
                status_code=502,
            )
        return err_body(raw_msg, status_code=502)
    return None


def resolve_ai_verify_connection_openai_error(
    exc: BaseException,
    *,
    request,
    model: str,
    base_url: str,
    fail: Callable[..., Response],
) -> Response | None:
    """Return a DRF response for OpenAI SDK errors in ``AiVerifyConnectionAPIView``, else ``None``."""
    if not _OPENAI_SDK_ERROR_TYPES or not isinstance(exc, _OPENAI_SDK_ERROR_TYPES):
        return None
    user_id = getattr(request.user, "id", None)
    if isinstance(exc, AuthenticationError):
        logger.exception(
            "AI verify connection auth failed. user_id=%s model=%s base_url=%s",
            user_id,
            model,
            base_url,
        )
        return fail(f"API Key 无效或未授权：{exc}")
    if isinstance(exc, APITimeoutError):
        logger.exception(
            "AI verify connection timeout. user_id=%s model=%s base_url=%s",
            user_id,
            model,
            base_url,
        )
        return fail("请求智谱接口超时，请检查网络或稍后重试。", status_code=504)
    if isinstance(exc, APIConnectionError):
        logger.exception(
            "AI verify connection upstream unreachable. user_id=%s model=%s base_url=%s",
            user_id,
            model,
            base_url,
        )
        return fail(f"无法连接智谱服务：{exc}", status_code=502)
    if isinstance(exc, APIError):
        logger.exception(
            "AI verify connection API error. user_id=%s model=%s base_url=%s",
            user_id,
            model,
            base_url,
        )
        return fail(getattr(exc, "message", None) or str(exc), status_code=502)
    return None


def resolve_ai_generate_cases_outer_openai_error(
    exc: BaseException,
    *,
    request,
    model_used: str,
    api_base_url: str,
    module_id: Any,
    fail: Callable[..., Response],
) -> Response | None:
    """
    OpenAI SDK errors for the outer ``try`` of ``AiGenerateCasesAPIView.post``
    (not including errors swallowed by the inner phase-2 ``except Exception``).
    """
    if not _OPENAI_SDK_ERROR_TYPES or not isinstance(exc, _OPENAI_SDK_ERROR_TYPES):
        return None
    user_id = getattr(request.user, "id", None)
    if isinstance(exc, AuthenticationError):
        logger.exception(
            "AI generate cases auth failed. user_id=%s model=%s base_url=%s module_id=%s",
            user_id,
            model_used,
            api_base_url,
            module_id,
        )
        return fail(f"API Key 无效：{exc}", status_code=401, code="AUTH_ERROR")
    if isinstance(exc, APITimeoutError):
        logger.exception(
            "AI generate cases timeout. user_id=%s model=%s base_url=%s module_id=%s",
            user_id,
            model_used,
            api_base_url,
            module_id,
        )
        return fail("调用智谱接口超时，请稍后重试。", status_code=504, code="UPSTREAM_TIMEOUT")
    if isinstance(exc, APIConnectionError):
        logger.exception(
            "AI generate cases upstream unreachable. user_id=%s model=%s base_url=%s module_id=%s",
            user_id,
            model_used,
            api_base_url,
            module_id,
        )
        return fail(f"无法连接模型服务：{exc}", status_code=502, code="UPSTREAM_UNREACHABLE")
    if isinstance(exc, APIError):
        logger.exception(
            "AI generate cases API error. user_id=%s model=%s base_url=%s module_id=%s",
            user_id,
            model_used,
            api_base_url,
            module_id,
        )
        return fail(
            getattr(exc, "message", None) or str(exc),
            status_code=502,
            code="UPSTREAM_API_ERROR",
        )
    return None
