"""
基础可达性/鉴权冒烟（pytest + requests）。

- public endpoints: 不应要求登录（非 401/403）
- protected endpoints: 应要求登录（401/403）
- wrong method: 401/403/405
"""

from __future__ import annotations

import pytest

from ._helpers import url

pytestmark = [pytest.mark.full]

PUBLIC_ENDPOINTS = [
    ("GET", "/user/captcha/"),
    ("POST", "/user/register/"),
    ("POST", "/user/login/"),
]

AUTH_ENDPOINTS = [
    ("GET", "/user/me/"),
    ("PATCH", "/user/me/profile/"),
    ("POST", "/user/change-password/"),
    ("GET", "/user/system-messages/"),
    ("GET", "/sys/ai-config/"),
    ("POST", "/ai/verify-connection/"),
    ("POST", "/ai/test-connection/"),
    ("POST", "/ai/generate-cases/"),
    ("POST", "/ai/generate-cases-stream/"),
    ("POST", "/ai/suggest-case-fix/"),
    ("POST", "/testcase/cases/1/apply-ai-suggested-steps/"),
    ("GET", "/assistant/llm/test-connection/"),
    ("GET", "/project/projects/"),
    ("GET", "/project/releases/"),
    ("GET", "/project/releases/0/risk-brief/"),
    ("GET", "/project/tasks/"),
    ("GET", "/testcase/modules/"),
    ("GET", "/testcase/cases/"),
    ("GET", "/testcase/steps/"),
    ("GET", "/testcase/designs/"),
    ("GET", "/testcase/approaches/"),
    ("GET", "/execution/plans/"),
    ("GET", "/execution/reports/"),
    ("POST", "/execution/plans/batch-delete/"),
    ("POST", "/execution/plans/batch-update/"),
    ("POST", "/execution/plans/batch-copy/"),
    ("POST", "/execution/reports/batch-delete/"),
    ("POST", "/execution/reports/batch-update/"),
    ("POST", "/execution/reports/batch-copy/"),
    ("GET", "/execution/tasks/"),
    ("GET", "/execution/dashboard/summary/"),
    ("GET", "/execution/dashboard/quality/"),
    ("GET", "/perf/tasks/"),
    ("POST", "/perf/tasks/batch-delete/"),
    ("POST", "/perf/tasks/batch-update/"),
    ("POST", "/perf/tasks/batch-copy/"),
    ("GET", "/defect/defects/"),
    ("POST", "/execution/scheduled-tasks/batch-delete/"),
    ("POST", "/execution/scheduled-tasks/batch-update/"),
    ("POST", "/execution/scheduled-tasks/batch-copy/"),
    ("POST", "/execution/scheduled-task-logs/batch-delete/"),
    ("POST", "/execution/scheduled-task-logs/batch-delete-by-filter/"),
    ("POST", "/perf/k6-sessions/batch-delete/"),
    ("POST", "/perf/k6-sessions/batch-copy/"),
    ("GET", "/perf/k6-sessions/"),
]


@pytest.mark.parametrize("method,path", PUBLIC_ENDPOINTS)
def test_public_endpoints_accessible_without_token(api_client, method, path):
    req = getattr(api_client, method.lower())
    payload = {}
    if path.endswith("/register/"):
        # 缺少验证码是预期非法输入，目标是验证“非 401/403 且可返回业务错误”
        payload = {"username": "u_invalid_for_smoke", "password": "123456"}
    if path.endswith("/login/"):
        payload = {"username": "invalid", "password": "invalid"}
    resp = req(url(api_client, path), json=payload or None, timeout=20)
    assert resp.status_code not in (401, 403), f"{method} {path} 不应要求登录"


@pytest.mark.parametrize("method,path", AUTH_ENDPOINTS)
def test_protected_endpoints_require_auth(api_client, method, path):
    req = getattr(api_client, method.lower())
    resp = req(url(api_client, path), json={}, timeout=20)
    assert resp.status_code in (401, 403), f"{method} {path} 预期需要鉴权"


@pytest.mark.parametrize(
    "path,wrong_method",
    [
        ("/user/login/", "get"),
        ("/ai/generate-cases/", "get"),
        ("/execution/dashboard/summary/", "post"),
        ("/change-requests/1/approve/", "get"),
    ],
)
def test_method_not_allowed_or_auth(path, wrong_method, api_client):
    req = getattr(api_client, wrong_method)
    resp = req(url(api_client, path), timeout=20)
    assert resp.status_code in (401, 403, 405)

