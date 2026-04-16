from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from jsonpath_ng import parse
from jsonpath_ng.exceptions import JsonPathParserError


def _jsonpath_values(body: Any, path: str) -> Tuple[bool, List[Any], str]:
    if not path:
        return False, [], "JSONPath 不能为空"
    try:
        expr = parse(path)
    except JsonPathParserError:
        return False, [], f"JSONPath 解析失败: {path}"
    except Exception:
        return False, [], f"JSONPath 解析异常: {path}"

    try:
        matches = expr.find(body)
    except Exception as exc:
        return False, [], f"JSONPath 执行异常: {str(exc)[:200]}"
    if not matches:
        return True, [], "未命中"
    return True, [m.value for m in matches], "命中"


def _get_header(headers: Dict[str, Any], key: str) -> Any:
    if not isinstance(headers, dict):
        return None
    if key in headers:
        return headers.get(key)
    low = str(key or "").lower()
    for k, v in headers.items():
        if str(k).lower() == low:
            return v
    return None


def evaluate_assertions(
    *,
    response_status: int | None,
    response_text: str,
    response_json: Any,
    response_headers: Dict[str, Any],
    duration_ms: int | None,
    expected_status: int | None,
    expected_substring: str,
    custom_assertions: List[Dict[str, Any]] | None,
    transport_error: str | None = None,
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    断言 DSL：
    - 支持内置基础断言：状态码、body_contains（来自 expected_substring）
    - 支持 custom_assertions 列表：
      - jsonpath_exists: {type, path}
      - jsonpath_equals: {type, path, expected}
      - jsonpath_regex:  {type, path, pattern}
      - header_equals:   {type, key, expected}
      - response_time_lt_ms: {type, max_ms}
    """

    results: List[Dict[str, Any]] = []
    ok_all = True

    if transport_error:
        results.append(
            {"name": "transport", "type": "transport", "passed": False, "detail": transport_error}
        )
        return results, False

    # 1) 基础断言：HTTP 状态码
    if response_status is None:
        results.append(
            {
                "name": "http_status",
                "type": "http_status",
                "passed": False,
                "detail": "无响应状态码（请求异常）",
            }
        )
        return results, False

    if expected_status is not None:
        passed = response_status == int(expected_status)
        results.append(
            {
                "name": "http_status",
                "type": "http_status",
                "passed": passed,
                "detail": f"实际 {response_status}，期望 {expected_status}",
            }
        )
        ok_all = ok_all and passed
    else:
        passed = 200 <= int(response_status) < 300
        results.append(
            {
                "name": "http_status_2xx",
                "type": "http_status_2xx",
                "passed": passed,
                "detail": f"实际 {response_status}，期望 2xx",
            }
        )
        ok_all = ok_all and passed

    # 2) 基础断言：响应体包含预期子串（兼容旧 expected_result）
    expected_substring = (expected_substring or "").strip()
    if expected_substring:
        passed = expected_substring in (response_text or "")
        results.append(
            {
                "name": "body_contains",
                "type": "body_contains",
                "passed": passed,
                "detail": "响应体包含预期子串"
                if passed
                else f"响应体未包含: {expected_substring[:200]}",
            }
        )
        ok_all = ok_all and passed

    # 3) 扩展断言
    for idx, a in enumerate(custom_assertions or []):
        if not isinstance(a, dict):
            results.append(
                {
                    "name": f"assertion_{idx}",
                    "type": "invalid",
                    "passed": False,
                    "detail": "断言配置必须为对象",
                }
            )
            ok_all = False
            continue

        typ = str(a.get("type") or "").strip()
        name = str(a.get("name") or typ or f"assertion_{idx}").strip() or f"assertion_{idx}"

        if typ == "jsonpath_exists":
            path = str(a.get("path") or a.get("jsonpath") or "").strip()
            ok, values, msg = _jsonpath_values(response_json, path)
            passed = ok and len(values) > 0
            results.append(
                {
                    "name": name,
                    "type": typ,
                    "passed": passed,
                    "detail": f"{msg}: {path}",
                }
            )
            ok_all = ok_all and passed
            continue

        if typ == "jsonpath_equals":
            path = str(a.get("path") or a.get("jsonpath") or "").strip()
            expected = a.get("expected")
            ok, values, msg = _jsonpath_values(response_json, path)
            actual = values[0] if values else None
            passed = ok and len(values) > 0 and actual == expected
            results.append(
                {
                    "name": name,
                    "type": typ,
                    "passed": passed,
                    "detail": f"{msg}: {path} 实际={actual} 期望={expected}",
                }
            )
            ok_all = ok_all and passed
            continue

        if typ == "jsonpath_regex":
            path = str(a.get("path") or a.get("jsonpath") or "").strip()
            pattern = str(a.get("pattern") or "").strip()
            ok, values, msg = _jsonpath_values(response_json, path)
            actual = values[0] if values else None
            try:
                matched = bool(re.search(pattern, str(actual or ""))) if pattern else False
            except re.error:
                matched = False
                msg = f"{msg}; 正则非法"
            passed = ok and len(values) > 0 and matched
            results.append(
                {
                    "name": name,
                    "type": typ,
                    "passed": passed,
                    "detail": f"{msg}: {path} pattern={pattern}",
                }
            )
            ok_all = ok_all and passed
            continue

        if typ == "header_equals":
            key = str(a.get("key") or "").strip()
            expected = a.get("expected")
            actual = _get_header(response_headers or {}, key)
            passed = key != "" and actual == expected
            results.append(
                {
                    "name": name,
                    "type": typ,
                    "passed": passed,
                    "detail": f"Header[{key}] 实际={actual} 期望={expected}",
                }
            )
            ok_all = ok_all and passed
            continue

        if typ == "response_time_lt_ms":
            max_ms = a.get("max_ms")
            try:
                max_ms_i = int(max_ms)
            except (TypeError, ValueError):
                max_ms_i = None
            if duration_ms is None or max_ms_i is None:
                passed = False
                detail = "duration 或 max_ms 非法"
            else:
                passed = int(duration_ms) < int(max_ms_i)
                detail = f"耗时 {duration_ms}ms < {max_ms_i}ms"
            results.append(
                {"name": name, "type": typ, "passed": passed, "detail": detail}
            )
            ok_all = ok_all and passed
            continue

        results.append(
            {
                "name": name,
                "type": typ or "unknown",
                "passed": False,
                "detail": f"不支持的断言类型: {typ}",
            }
        )
        ok_all = False

    return results, ok_all

