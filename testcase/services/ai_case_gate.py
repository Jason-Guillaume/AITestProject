from __future__ import annotations

from typing import Any, Dict, List, Tuple


def validate_and_normalize_ai_api_case(item: Dict[str, Any]) -> Tuple[Dict[str, Any] | None, str | None]:
    """
    AI/导入生成用例门禁：避免落库不可执行/不安全的定义。

    输出： (normalized_payload, error)
    normalized_payload fields:
    - case_name
    - api_url
    - api_method
    - api_headers (dict)
    - api_body (dict|list)
    - api_expected_status (int|None)
    """

    if not isinstance(item, dict):
        return None, "item 必须为对象"

    case_name = str(item.get("case_name") or "").strip() or "未命名接口"
    case_name = case_name[:255]

    api_url = str(item.get("api_url") or "").strip()
    if not api_url:
        return None, "api_url 不能为空"
    api_url = api_url[:2048]

    api_method = str(item.get("api_method") or "GET").strip().upper()
    if api_method not in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}:
        return None, f"不支持的 api_method: {api_method}"

    headers = item.get("api_headers")
    if headers is None:
        headers = {}
    if not isinstance(headers, dict):
        return None, "api_headers 必须为对象"

    body = item.get("api_body")
    if body is None:
        body = {}
    if not isinstance(body, (dict, list)):
        return None, "api_body 必须为对象或数组"

    exp = item.get("api_expected_status")
    if exp is not None and exp != "":
        try:
            exp = int(exp)
        except (TypeError, ValueError):
            exp = None
    else:
        exp = None

    # 简单安全门禁：禁止把明显的凭据字段写入 headers 明文（建议改用环境变量/鉴权配置）
    for k in list(headers.keys()):
        kl = str(k).lower()
        if kl in {"authorization", "cookie", "set-cookie", "x-api-key"}:
            # 允许占位符（变量替换），禁止直接长 token
            v = headers.get(k)
            if isinstance(v, str) and ("${" not in v) and len(v.strip()) > 16:
                return None, f"敏感请求头请使用环境鉴权或变量占位符: {k}"

    return (
        {
            "case_name": case_name,
            "api_url": api_url,
            "api_method": api_method[:16],
            "api_headers": headers,
            "api_body": body,
            "api_expected_status": exp,
        },
        None,
    )


def gate_ai_api_cases(items: List[Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    ok: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    for idx, it in enumerate(items or []):
        if not isinstance(it, dict):
            errors.append({"index": idx, "error": "item 非对象"})
            continue
        norm, err = validate_and_normalize_ai_api_case(it)
        if err:
            errors.append({"index": idx, "error": err, "raw": {k: it.get(k) for k in ("case_name", "api_url", "api_method")}})
            continue
        ok.append(norm)
    return ok, errors

