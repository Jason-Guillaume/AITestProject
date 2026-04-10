from __future__ import annotations

import json
import time
from typing import Any, Dict
from urllib.parse import urlparse

import requests

from execution.models import ExecutionTask
from execution.services.health_checker import HealthChecker

_ALLOWED_METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
_MAX_BODY_LOG = 20000
_SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key"}
_SENSITIVE_BODY_KEYS = {"password", "token", "secret", "access_token", "refresh_token"}


class APIExecutor:
    """API 执行器：负责请求发送、基础断言与耗时统计。"""

    _session = requests.Session()

    def execute(self, task: ExecutionTask) -> Dict[str, Any]:
        dimension = {
            "execution_task_id": task.id,
            "task_name": task.task_name,
        }
        checker = HealthChecker()
        summary = checker.check_before_task(api_url=task.url, dimension=dimension)
        if not summary.get("ok"):
            checker.send_alert_email(task_name=task.task_name, summary=summary)
            raise RuntimeError(f"ENV_UNHEALTHY: {summary.get('unhealthy')}")

        method = (task.method or "GET").strip().upper()
        if method not in _ALLOWED_METHODS:
            raise ValueError(f"不支持的 HTTP 方法: {method}")
        if not task.url:
            raise ValueError("请求 URL 不能为空")
        parsed = urlparse(task.url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("请求 URL 必须是合法的 http/https 地址")

        request_payload = self._build_request_payload(task, method)
        start = time.perf_counter()
        response = self._session.request(**request_payload)
        duration_ms = int((time.perf_counter() - start) * 1000)

        assertion_result = self._build_assertion_result(task, response)
        passed = all(item["passed"] for item in assertion_result.values())
        sanitized_req_headers = self._sanitize_headers(task.headers or {})
        sanitized_body = self._sanitize_body(task.body)

        return {
            "passed": passed,
            "duration_ms": duration_ms,
            "request": {
                "method": method,
                "url": task.url,
                "headers": sanitized_req_headers,
                "body": sanitized_body,
                "timeout_seconds": task.timeout_seconds,
            },
            "response": {
                "status_code": response.status_code,
                "headers": self._sanitize_headers(dict(response.headers)),
                "body_text": self._truncate_text(response.text or ""),
            },
            "assertions": assertion_result,
        }

    def _build_request_payload(self, task: ExecutionTask, method: str) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "method": method,
            "url": task.url,
            "headers": task.headers or {},
            "timeout": task.timeout_seconds or 30,
        }
        if method in {"GET", "HEAD"}:
            return payload

        body = task.body
        if body is None:
            return payload

        if isinstance(body, (dict, list)):
            payload["json"] = body
            return payload

        if isinstance(body, str):
            try:
                payload["json"] = json.loads(body)
            except json.JSONDecodeError:
                payload["data"] = body.encode("utf-8")
            return payload

        payload["data"] = str(body).encode("utf-8")
        return payload

    def _truncate_text(self, text: str) -> str:
        if len(text) <= _MAX_BODY_LOG:
            return text
        return text[:_MAX_BODY_LOG] + f"\n...(truncated, total={len(text)})"

    def _sanitize_headers(self, headers: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, value in headers.items():
            if key is None:
                continue
            k = str(key)
            if k.lower() in _SENSITIVE_HEADERS:
                out[k] = "***"
            else:
                out[k] = value
        return out

    def _sanitize_body(self, body: Any):
        if isinstance(body, dict):
            out: Dict[str, Any] = {}
            for key, value in body.items():
                if str(key).lower() in _SENSITIVE_BODY_KEYS:
                    out[key] = "***"
                elif isinstance(value, dict):
                    out[key] = self._sanitize_body(value)
                else:
                    out[key] = value
            return out
        if isinstance(body, list):
            return [self._sanitize_body(v) for v in body]
        if isinstance(body, str):
            return self._truncate_text(body)
        return body

    def _build_assertion_result(
        self, task: ExecutionTask, response: requests.Response
    ) -> Dict[str, Dict[str, Any]]:
        status_expected = task.expected_status
        status_passed = (
            response.status_code == int(status_expected)
            if status_expected is not None
            else 200 <= response.status_code < 300
        )
        status_detail = (
            f"实际 {response.status_code}，期望 {status_expected}"
            if status_expected is not None
            else f"实际 {response.status_code}，期望 2xx"
        )

        expected_fragment = (task.expected_body_contains or "").strip()
        if expected_fragment:
            contains_passed = expected_fragment in (response.text or "")
            contains_detail = (
                "响应体包含预期片段"
                if contains_passed
                else f"响应体未包含: {expected_fragment}"
            )
        else:
            contains_passed = True
            contains_detail = "未配置 body 包含断言，默认通过"

        return {
            "status_code": {"passed": status_passed, "detail": status_detail},
            "body_contains": {"passed": contains_passed, "detail": contains_detail},
        }
