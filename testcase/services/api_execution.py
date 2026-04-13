"""
API 用例执行：合并用例与实时覆盖参数、发起 HTTP、落库 ExecutionLog / ApiTestLog。
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from django.db.models import F

from testcase.models import (
    ApiTestCase,
    ApiTestLog,
    EnvironmentVariable,
    ExecutionLog,
    TestCase,
    TestEnvironment,
)
from testcase.services.variable_runtime import VariableExtractor, VariableResolver

_ALLOWED_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})
_LOG_BODY_MAX = 200_000


def truncate_log_text(s: Any, max_len: int = _LOG_BODY_MAX) -> str:
    if s is None:
        return ""
    t = str(s)
    if len(t) <= max_len:
        return t
    return t[:max_len] + f"\n…(truncated, total {len(t)} chars)"


def case_api_headers_to_dict(raw: Any) -> Dict[str, str]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        out: Dict[str, str] = {}
        for k, v in raw.items():
            if k is None:
                continue
            key = str(k).strip()
            if not key:
                continue
            # 跳过 None 值，避免将 None 转为字符串 "None"
            if v is None:
                continue
            out[key] = v if isinstance(v, str) else str(v)
        return out
    if isinstance(raw, str):
        t = raw.strip()
        if not t:
            return {}
        parsed = json.loads(t)
        if not isinstance(parsed, dict):
            raise ValueError("请求头需为 JSON 对象")
        out = {}
        for k, v in parsed.items():
            if k is None:
                continue
            key = str(k).strip()
            if not key:
                continue
            # 跳过 None 值，避免将 None 转为字符串 "None"
            if v is None:
                continue
            out[key] = v if isinstance(v, str) else str(v)
        return out
    return {}


def normalize_api_body(body: Any) -> Any:
    """统一为 dict / list / None（空表示无 body）。"""
    if body is None:
        return None
    if isinstance(body, (dict, list)):
        if isinstance(body, dict) and body == {}:
            return None
        return body
    if isinstance(body, str):
        t = body.strip()
        if not t:
            return None
        try:
            v = json.loads(t)
            if isinstance(v, (dict, list)):
                return v
            return {"_legacy_scalar": v}
        except json.JSONDecodeError:
            return {"_legacy_text": t}
    return {"_legacy_scalar": body}


def body_to_log_text(body: Any) -> str:
    if body is None:
        return ""
    if isinstance(body, (dict, list)):
        return truncate_log_text(json.dumps(body, ensure_ascii=False))
    return truncate_log_text(body)


def resolve_url_with_environment(url: str, environment_id: Optional[int]) -> str:
    """
    若提供已登记环境 ID，则将非绝对 URL（相对路径）与该环境的 base_url 拼接。
    已是 http(s) 完整地址时保持不变。
    注意：变量替换在调用方 resolver.resolve 中进行，此处不处理 ${var}。
    """
    u = (url or "").strip()
    if not environment_id:
        return u
    env = TestEnvironment.objects.filter(pk=environment_id, is_deleted=False).first()
    if not env:
        return u
    base = (env.base_url or "").strip().rstrip("/")
    if not base:
        return u
    if not u:
        return base
    low = u.lower()
    if low.startswith("http://") or low.startswith("https://"):
        return u
    if u.startswith("/"):
        return f"{base}{u}"
    return f"{base}/{u}"


def merge_execute_params(
    api_prof: ApiTestCase, overrides: Optional[Dict[str, Any]]
) -> Tuple[str, str, Dict[str, str], Any, Optional[int], Optional[int]]:
    o = overrides or {}
    env_raw = o.get("environment_id")
    env_id: Optional[int] = None
    if env_raw is not None:
        try:
            env_id = int(env_raw)
        except (TypeError, ValueError):
            env_id = None
    url = (o.get("url") or o.get("api_url") or api_prof.api_url or "").strip()
    if env_id:
        url = resolve_url_with_environment(url, env_id)
    method = (
        (o.get("method") or o.get("api_method") or api_prof.api_method or "GET")
        .strip()
        .upper()
        or "GET"
    )
    if o.get("headers") is not None or o.get("api_headers") is not None:
        raw_h = o.get("headers")
        if raw_h is None:
            raw_h = o.get("api_headers")
        headers = case_api_headers_to_dict(raw_h)
    else:
        headers = case_api_headers_to_dict(api_prof.api_headers)
    if o.get("body") is not None or o.get("api_body") is not None:
        body = o.get("body")
        if body is None:
            body = o.get("api_body")
    else:
        body = api_prof.api_body
    body = normalize_api_body(body)
    exp = o.get("expected_status")
    if exp is None:
        exp = o.get("api_expected_status")
    if exp is None:
        exp = api_prof.api_expected_status
    if exp is not None:
        try:
            exp = int(exp)
        except (TypeError, ValueError):
            exp = api_prof.api_expected_status
    return url, method, headers, body, exp, env_id


def load_environment_runtime_variables(environment_id: Optional[int]) -> Dict[str, Any]:
    """读取当前环境下的变量池（含敏感变量解密值），用于 ${var} 运行时替换。"""
    if not environment_id:
        return {}
    rows = EnvironmentVariable.objects.filter(
        environment_id=environment_id,
        is_deleted=False,
    ).order_by("id")
    out: Dict[str, Any] = {}
    for row in rows:
        key = str(getattr(row, "key", "") or "").strip()
        if not key:
            continue
        try:
            value = row.get_decrypted_value() if getattr(row, "is_secret", False) else (row.value or "")
        except Exception:
            value = row.value or ""
        out[key] = value
    return out


def build_requests_kwargs(
    method: str, url: str, headers: Dict[str, str], body: Any
) -> Dict[str, Any]:
    req: Dict[str, Any] = {"method": method, "url": url, "headers": headers, "timeout": 30}
    if method in ("GET", "HEAD") or body is None:
        return req
    ct = str(
        headers.get("Content-Type") or headers.get("content-type") or ""
    ).lower()
    if "application/json" in ct or isinstance(body, (dict, list)):
        if isinstance(body, str):
            try:
                req["json"] = json.loads(body)
            except json.JSONDecodeError:
                req["data"] = body.encode("utf-8")
        else:
            req["json"] = body
    else:
        if isinstance(body, (dict, list)):
            req["data"] = json.dumps(body, ensure_ascii=False).encode("utf-8")
        else:
            req["data"] = str(body).encode("utf-8")
    return req


def collect_assertions(
    response: Optional[requests.Response],
    expected_status: Optional[int],
    expected_substring: str,
    error_text: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], bool]:
    results: List[Dict[str, Any]] = []
    if error_text:
        results.append(
            {
                "name": "transport",
                "passed": False,
                "detail": truncate_log_text(error_text, 2000),
            }
        )
        return results, False
    assert response is not None
    code = response.status_code
    if expected_status is not None:
        ok_code = code == int(expected_status)
        results.append(
            {
                "name": "http_status",
                "passed": ok_code,
                "detail": f"实际 {code}，期望 {expected_status}",
            }
        )
    else:
        ok_code = 200 <= code < 300
        results.append(
            {
                "name": "http_status_2xx",
                "passed": ok_code,
                "detail": f"实际 {code}，期望 2xx",
            }
        )
    ok = ok_code
    if expected_substring:
        text = response.text or ""
        sub_ok = expected_substring in text
        results.append(
            {
                "name": "body_contains",
                "passed": sub_ok,
                "detail": (
                    "响应体包含预期子串"
                    if sub_ok
                    else f"响应体未包含: {truncate_log_text(expected_substring, 200)}"
                ),
            }
        )
        ok = ok and sub_ok
    return results, ok


def response_headers_to_dict(resp: requests.Response) -> Dict[str, str]:
    """将响应头转换为字符串字典，跳过 None 值。"""
    out: Dict[str, str] = {}
    for k, v in resp.headers.items():
        if k is None:
            continue
        if v is None:
            continue
        out[str(k)] = str(v)
    return out


def build_request_payload(
    url: str, method: str, headers: Dict[str, str], body: Any
) -> Dict[str, Any]:
    """执行时真实请求 JSON 快照（可安全写入 JSONField）。"""
    safe_body: Any = body
    if body is not None:
        try:
            json.dumps(body, ensure_ascii=False)
        except (TypeError, ValueError):
            safe_body = str(body)
    # 过滤掉 headers 中的 None 值，确保 JSON 可序列化
    safe_headers = {k: v for k, v in headers.items() if v is not None}
    return {
        "method": method,
        "url": url,
        "headers": safe_headers,
        "body": safe_body,
    }


def build_response_payload_from_error(
    *,
    error: str = "",
    status_code: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None,
    body_text: str = "",
) -> Dict[str, Any]:
    # 过滤掉 headers 中的 None 值，确保 JSON 可序列化
    safe_headers = {k: v for k, v in (headers or {}).items() if v is not None}
    return {
        "status_code": status_code,
        "headers": safe_headers,
        "body_raw": truncate_log_text(body_text),
        "error": truncate_log_text(error, 4000) if error else "",
    }


def build_response_payload_from_response(resp: requests.Response) -> Dict[str, Any]:
    """服务端返回原始数据摘要：含 body_raw，JSON 响应时额外解析 body_json。"""
    text = resp.text or ""
    truncated = text
    if len(truncated) > _LOG_BODY_MAX:
        truncated = (
            truncated[:_LOG_BODY_MAX]
            + f"\n…(truncated, total {len(text)} chars)"
        )
    out: Dict[str, Any] = {
        "status_code": resp.status_code,
        "headers": response_headers_to_dict(resp),
        "body_raw": truncated,
    }
    ct = (resp.headers.get("Content-Type") or "").lower()
    if "application/json" in ct and truncated.strip():
        try:
            out["body_json"] = json.loads(truncated)
        except json.JSONDecodeError:
            pass
    return out


@dataclass
class RunApiResult:
    execution_log: ExecutionLog
    api_test_log: Optional[ApiTestLog] = None
    message: str = ""
    extracted_variables: Dict[str, Any] = field(default_factory=dict)


def prepare_runtime_variable_context(
    overrides: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """
    从 overrides 读取运行时变量上下文：
    - variables / runtime_variables: 变量池
    - extraction_rules / variable_extractions: 提取规则
    """
    o = overrides or {}
    variables = o.get("variables")
    if variables is None:
        variables = o.get("runtime_variables")
    if not isinstance(variables, dict):
        variables = {}

    rules = o.get("extraction_rules")
    if rules is None:
        rules = o.get("variable_extractions")
    if not isinstance(rules, list):
        rules = []

    return variables, rules


def validate_before_request(url: str, method: str) -> Optional[str]:
    if not url.strip():
        return "请填写 API 地址"
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return "API 地址必须是合法的 http/https URL"
    if method not in _ALLOWED_METHODS:
        return f"不支持的 HTTP 方法：{method}"
    return None


def run_api_case(
    case: TestCase,
    api_prof: ApiTestCase,
    *,
    overrides: Optional[Dict[str, Any]] = None,
    user: Any = None,
    write_legacy_apilog: bool = True,
) -> RunApiResult:
    """
    执行 API 用例并写入 ExecutionLog；可选同步写入 ApiTestLog。
    """
    url, method, headers, body, expected_status, env_id = merge_execute_params(api_prof, overrides)
    runtime_vars, extraction_rules = prepare_runtime_variable_context(overrides)
    env_runtime_vars = load_environment_runtime_variables(env_id)
    merged_runtime_vars = {**env_runtime_vars, **(runtime_vars or {})}
    resolver = VariableResolver(missing_policy="keep")
    extractor = VariableExtractor(keep_none_on_error=True)

    # 执行前变量替换：支持 URL / Header / Body 中的 ${var_name}
    url = resolver.resolve(url, merged_runtime_vars)
    headers = resolver.resolve(headers, merged_runtime_vars)
    body = resolver.resolve(body, merged_runtime_vars)
    trace_id = str(uuid.uuid4())
    request_payload_snapshot = build_request_payload(url, method, headers, body)
    err = validate_before_request(url, method)
    body_log = body_to_log_text(body)
    base_log_user: Dict[str, Any] = {}
    if user is not None and getattr(user, "is_authenticated", False):
        base_log_user["creator"] = user
        base_log_user["updater"] = user

    step = (
        case.steps.filter(is_deleted=False).order_by("step_number").first()
    )
    expected_sub = (step.expected_result or "").strip() if step else ""

    if err:
        resp_payload = build_response_payload_from_error(error=err)
        extracted_vars: Dict[str, Any] = {}
        if extraction_rules:
            extracted_vars = extractor.extract(
                {"body": {}, "headers": {}}, extraction_rules
            )
            resp_payload["extracted_variables"] = extracted_vars
        log_ex = ExecutionLog.objects.create(
            test_case=case,
            request_url=url or "",
            request_method=method,
            request_headers=headers,
            request_body_text=body_log,
            response_status_code=None,
            response_headers={},
            response_body_text="",
            duration_ms=0,
            execution_status=ExecutionLog.ExecutionStatus.REQUEST_ERROR,
            assertion_results=[
                {"name": "validation", "passed": False, "detail": err}
            ],
            is_passed=False,
            error_message=err,
            trace_id=trace_id,
            request_payload=request_payload_snapshot,
            response_payload=resp_payload,
            **base_log_user,
        )
        legacy = None
        if write_legacy_apilog:
            legacy = ApiTestLog.objects.create(
                test_case=case,
                request_url=url or "",
                request_method=method,
                request_headers=headers,
                request_body=body_log,
                response_status_code=None,
                response_body=err,
                response_time_ms=0,
                is_passed=False,
                **base_log_user,
            )
        TestCase.objects.filter(pk=case.pk).update(exec_count=F("exec_count") + 1)
        return RunApiResult(log_ex, legacy, err, extracted_vars)

    req_kwargs = build_requests_kwargs(method, url, headers, body)
    t0 = time.perf_counter()
    try:
        resp = requests.request(**req_kwargs)
    except requests.RequestException as exc:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        err_text = str(exc)
        assertions, _ = collect_assertions(
            None, expected_status, expected_sub, error_text=err_text
        )
        resp_payload = build_response_payload_from_error(error=err_text)
        extracted_vars: Dict[str, Any] = {}
        if extraction_rules:
            extracted_vars = extractor.extract(
                {"body": {}, "headers": {}}, extraction_rules
            )
            resp_payload["extracted_variables"] = extracted_vars
        log_ex = ExecutionLog.objects.create(
            test_case=case,
            request_url=url,
            request_method=method,
            request_headers=headers,
            request_body_text=body_log,
            response_status_code=None,
            response_headers={},
            response_body_text=truncate_log_text(err_text),
            duration_ms=elapsed_ms,
            execution_status=ExecutionLog.ExecutionStatus.REQUEST_ERROR,
            assertion_results=assertions,
            is_passed=False,
            error_message=truncate_log_text(err_text, 4000),
            trace_id=trace_id,
            request_payload=request_payload_snapshot,
            response_payload=resp_payload,
            **base_log_user,
        )
        legacy = None
        if write_legacy_apilog:
            legacy = ApiTestLog.objects.create(
                test_case=case,
                request_url=url,
                request_method=method,
                request_headers=headers,
                request_body=body_log,
                response_status_code=None,
                response_body=truncate_log_text(err_text),
                response_time_ms=elapsed_ms,
                is_passed=False,
                **base_log_user,
            )
        TestCase.objects.filter(pk=case.pk).update(exec_count=F("exec_count") + 1)
        return RunApiResult(
            log_ex, legacy, "请求失败（网络或超时）", extracted_vars
        )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    assertions, passed = collect_assertions(
        resp, expected_status, expected_sub, error_text=None
    )
    ex_status = (
        ExecutionLog.ExecutionStatus.SUCCESS
        if passed
        else ExecutionLog.ExecutionStatus.ASSERTION_FAILED
    )
    resp_headers = response_headers_to_dict(resp)
    resp_payload = build_response_payload_from_response(resp)
    extracted_vars: Dict[str, Any] = {}
    if extraction_rules:
        response_data = {
            "body": resp_payload.get("body_json")
            if "body_json" in resp_payload
            else (resp.text or ""),
            "headers": resp_headers,
        }
        extracted_vars = extractor.extract(response_data, extraction_rules)
        resp_payload["extracted_variables"] = extracted_vars
    log_ex = ExecutionLog.objects.create(
        test_case=case,
        request_url=url,
        request_method=method,
        request_headers=headers,
        request_body_text=body_log,
        response_status_code=resp.status_code,
        response_headers=resp_headers,
        response_body_text=truncate_log_text(resp.text),
        duration_ms=elapsed_ms,
        execution_status=ex_status,
        assertion_results=assertions,
        is_passed=passed,
        error_message="",
        trace_id=trace_id,
        request_payload=request_payload_snapshot,
        response_payload=resp_payload,
        **base_log_user,
    )
    legacy = None
    if write_legacy_apilog:
        legacy = ApiTestLog.objects.create(
            test_case=case,
            request_url=url,
            request_method=method,
            request_headers=headers,
            request_body=body_log,
            response_status_code=resp.status_code,
            response_body=truncate_log_text(resp.text),
            response_time_ms=elapsed_ms,
            is_passed=passed,
            **base_log_user,
        )
    TestCase.objects.filter(pk=case.pk).update(exec_count=F("exec_count") + 1)
    msg = "通过" if passed else "未通过断言（状态码或预期结果）"
    return RunApiResult(log_ex, legacy, msg, extracted_vars)


def preview_resolved_request(
    api_prof: ApiTestCase,
    *,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    仅预览执行前的最终请求（不发请求）：
    - 合并环境 base_url
    - 注入环境变量 + 运行时变量
    - 替换 URL/Headers/Body 中的 ${var}
    """
    url, method, headers, body, expected_status, env_id = merge_execute_params(api_prof, overrides)
    runtime_vars, _ = prepare_runtime_variable_context(overrides)
    env_runtime_vars = load_environment_runtime_variables(env_id)
    merged_runtime_vars = {**env_runtime_vars, **(runtime_vars or {})}

    resolver = VariableResolver(missing_policy="keep")
    final_url = resolver.resolve(url, merged_runtime_vars)
    final_headers = resolver.resolve(headers, merged_runtime_vars)
    final_body = resolver.resolve(body, merged_runtime_vars)

    return {
        "request": {
            "method": method,
            "url": final_url,
            "headers": final_headers,
            "body": final_body,
            "expected_status": expected_status,
            "environment_id": env_id,
        },
        "variables": {
            "environment_count": len(env_runtime_vars),
            "runtime_count": len(runtime_vars or {}),
            "merged_count": len(merged_runtime_vars),
            "keys": sorted(list(merged_runtime_vars.keys()))[:100],
        },
    }
