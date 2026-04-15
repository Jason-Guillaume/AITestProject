"""
从业务库中按顺序收集 API 测试用例，供 k6 脚本生成（模板或 AI）。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from testcase.models import TEST_CASE_TYPE_API, ApiTestCase, TestCase


def resolve_request_url(api_url: str, target_base_url: str) -> str:
    u = (api_url or "").strip()
    if u.startswith("http://") or u.startswith("https://"):
        return u
    b = (target_base_url or "").strip().rstrip("/")
    if not b:
        return u
    path = u if u.startswith("/") else f"/{u}"
    return f"{b}{path}"


def collect_api_chain(
    case_ids: List[int], target_base_url: str = ""
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    按 case_ids 顺序返回 API 步骤描述列表。
    若存在非 API 用例或缺失 ID，返回 (list, error_message)。
    """
    if not case_ids:
        return [], "test_case_ids 不能为空"

    qs = TestCase.objects.filter(id__in=case_ids, is_deleted=False).select_related(
        "apitestcase"
    )
    by_id = {c.id: c for c in qs}
    ordered: List[TestCase] = []
    missing = []
    for cid in case_ids:
        c = by_id.get(cid)
        if not c:
            missing.append(cid)
            continue
        if c.test_type != TEST_CASE_TYPE_API:
            return [], f"用例 {cid} 不是 API 类型，无法用于 k6 链路"
        ordered.append(c)

    if missing:
        return [], f"以下用例不存在或已删除: {missing}"

    steps: List[Dict[str, Any]] = []
    for c in ordered:
        ap = ApiTestCase.objects.filter(pk=c.pk).first()
        if not ap:
            return [], f"用例 {c.id} 缺少 API 子表数据"

        url = resolve_request_url(ap.api_url, target_base_url)
        if not url.startswith("http://") and not url.startswith("https://"):
            return [], (
                f"用例 {c.id} 的 URL 为相对路径但未提供 target_base_url，"
                "请在请求中填写目标 Base URL"
            )

        steps.append(
            {
                "case_id": c.id,
                "case_name": c.case_name,
                "method": (ap.api_method or "GET").upper(),
                "url": url,
                "headers": ap.api_headers if isinstance(ap.api_headers, dict) else {},
                "body": ap.api_body if ap.api_body is not None else {},
                "expected_status": ap.api_expected_status,
            }
        )

    return steps, None


def chain_to_prompt_json(steps: List[Dict[str, Any]]) -> str:
    return json.dumps(steps, ensure_ascii=False, indent=2)
