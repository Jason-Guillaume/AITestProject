"""
AI 导入前 API 草稿静态预检（与 ai-import-precheck 单行语义一致，供 HTTP 与 ai-import strict 复用）。
"""

from __future__ import annotations

import json
import re
from typing import Any

from testcase.services.api_execution import (
    case_api_headers_to_dict,
    load_environment_runtime_variables,
    normalize_api_body,
    resolve_url_with_environment,
    validate_before_request,
)
from testcase.services.variable_runtime import VariableResolver

_VAR_PAT = re.compile(r"\$\{[^}]+\}")


def _find_unresolved_vars(obj: Any) -> list[str]:
    try:
        text = json.dumps(obj, ensure_ascii=False)
    except Exception:
        text = str(obj)
    return sorted(set(_VAR_PAT.findall(text or "")))[:50]


def precheck_api_draft_item(
    item: dict, overrides: dict | None
) -> dict[str, Any]:
    """
    对单条草稿 item 做 URL 拼接、变量替换与合法性校验（不发 HTTP）。

    :param item: 含 api_url / api_method / api_headers / api_body 等
    :param overrides: environment_id、variables（或 runtime_variables）
    :return: ok, error, unresolved_vars, request
    """
    overrides = overrides if isinstance(overrides, dict) else {}
    if not isinstance(item, dict):
        return {
            "ok": False,
            "error": "item 必须为对象",
            "unresolved_vars": [],
            "request": {},
        }

    env_id = overrides.get("environment_id")
    try:
        env_id = int(env_id) if env_id is not None else None
    except (TypeError, ValueError):
        env_id = None

    runtime_vars = overrides.get("variables") or overrides.get("runtime_variables")
    if not isinstance(runtime_vars, dict):
        runtime_vars = {}
    env_runtime_vars = load_environment_runtime_variables(env_id)
    merged_vars = {**env_runtime_vars, **runtime_vars}
    resolver = VariableResolver(missing_policy="keep")

    url = str(item.get("api_url") or item.get("url") or "").strip()
    method = (
        str(item.get("api_method") or item.get("method") or "GET").strip().upper()[:16]
        or "GET"
    )
    headers = case_api_headers_to_dict(item.get("api_headers"))
    body = normalize_api_body(item.get("api_body"))
    if env_id:
        url = resolve_url_with_environment(url, env_id)
    final_url = resolver.resolve(url, merged_vars)
    final_headers = resolver.resolve(headers, merged_vars)
    final_body = resolver.resolve(body, merged_vars)
    req = {
        "method": method,
        "url": final_url,
        "headers": final_headers,
        "body": final_body,
        "environment_id": env_id,
    }
    err = validate_before_request(final_url, method)
    unresolved = _find_unresolved_vars(req)
    ok = (not err) and (not unresolved)
    return {
        "ok": ok,
        "error": err or "",
        "unresolved_vars": unresolved,
        "request": req,
    }
