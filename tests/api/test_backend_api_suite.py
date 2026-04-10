"""
后端 API 自动化测试套件（pytest + requests）。

覆盖目标：
1) 全量路由可达性（含鉴权）
2) Happy Path（有效参数）
3) 边界/非法输入（参数类型、必填缺失、错误 method）
"""

from __future__ import annotations

import os
from datetime import datetime

import pytest

pytestmark = [pytest.mark.full]


def _url(client, path: str) -> str:
    return f"{client.base_url}{path}"


def _assert_status(resp, expected: tuple[int, ...]):
    assert resp.status_code in expected, f"status={resp.status_code}, body={resp.text}"


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
    ("GET", "/assistant/llm/test-connection/"),
    ("GET", "/project/projects/"),
    ("GET", "/project/releases/"),
    ("GET", "/project/tasks/"),
    ("GET", "/testcase/modules/"),
    ("GET", "/testcase/cases/"),
    ("GET", "/testcase/steps/"),
    ("GET", "/testcase/designs/"),
    ("GET", "/testcase/approachs/"),
    ("GET", "/execution/plans/"),
    ("GET", "/execution/reports/"),
    ("GET", "/execution/tasks/"),
    ("GET", "/execution/dashboard/summary/"),
    ("GET", "/execution/dashboard/quality/"),
    ("GET", "/perf/tasks/"),
    ("GET", "/defect/defects/"),
]


@pytest.mark.parametrize("method,path", PUBLIC_ENDPOINTS)
def test_public_endpoints_accessible_without_token(api_client, method, path):
    req = getattr(api_client, method.lower())
    payload = {}
    if path.endswith("/register/"):
        # 缺少验证码是预期非法输入，目标是验证“非 401/403 且可返回业务错误”
        payload = {"username": f"u_{datetime.utcnow().timestamp()}", "password": "123456"}
    if path.endswith("/login/"):
        payload = {"username": "invalid", "password": "invalid"}
    resp = req(_url(api_client, path), json=payload or None, timeout=20)
    assert resp.status_code not in (401, 403), f"{method} {path} 不应要求登录"


@pytest.mark.parametrize("method,path", AUTH_ENDPOINTS)
def test_protected_endpoints_require_auth(api_client, method, path):
    req = getattr(api_client, method.lower())
    resp = req(_url(api_client, path), json={}, timeout=20)
    assert resp.status_code in (401, 403), f"{method} {path} 预期需要鉴权"


def test_user_login_happy_path(api_client, user_credentials):
    resp = api_client.post(
        _url(api_client, "/user/login/"),
        json=user_credentials,
        timeout=20,
    )
    _assert_status(resp, (200,))
    body = resp.json()
    assert (body.get("data") or {}).get("token")


@pytest.mark.smoke
def test_user_login_invalid_password(api_client, user_credentials):
    resp = api_client.post(
        _url(api_client, "/user/login/"),
        json={"username": user_credentials["username"], "password": "wrong-password"},
        timeout=20,
    )
    _assert_status(resp, (400,))


@pytest.mark.smoke
def test_user_profile_patch_boundary_and_invalid(authed_client):
    # 边界：手机号为空可接受
    ok_resp = authed_client.patch(
        _url(authed_client, "/user/me/profile/"),
        json={"phone_number": "", "real_name": "API Tester"},
        timeout=20,
    )
    _assert_status(ok_resp, (200,))

    # 非法：超长手机号（后端若未限制会返回 200，此处接受 200/400，并检查不应 500）
    bad_resp = authed_client.patch(
        _url(authed_client, "/user/me/profile/"),
        json={"phone_number": "1" * 256},
        timeout=20,
    )
    _assert_status(bad_resp, (200, 400))


@pytest.mark.regression
def test_sys_ai_config_endpoints(admin_client):
    get_resp = admin_client.get(_url(admin_client, "/sys/ai-config/"), timeout=20)
    _assert_status(get_resp, (200,))

    put_resp = admin_client.put(
        _url(admin_client, "/sys/ai-config/"),
        json={"model_type": "glm-4.7-flash", "api_key": "dummy-key", "base_url": ""},
        timeout=20,
    )
    _assert_status(put_resp, (200,))

    disconnect_resp = admin_client.post(_url(admin_client, "/sys/ai-config/disconnect/"), json={}, timeout=20)
    _assert_status(disconnect_resp, (200,))

    reconnect_resp = admin_client.post(_url(admin_client, "/sys/ai-config/reconnect/"), json={}, timeout=20)
    _assert_status(reconnect_resp, (200,))


@pytest.mark.smoke
@pytest.mark.regression
def test_project_crud_and_invalid(authed_client, user_context):
    uid = user_context["user_id"]
    payload = {
        "project_name": f"proj-{datetime.utcnow().timestamp()}",
        "project_status": 1,
        "progress": 1,
        "members": [uid],
    }
    create_resp = authed_client.post(_url(authed_client, "/project/projects/"), json=payload, timeout=20)
    _assert_status(create_resp, (200, 201))
    project_id = create_resp.json()["id"]

    list_resp = authed_client.get(_url(authed_client, "/project/projects/"), timeout=20)
    _assert_status(list_resp, (200,))

    update_resp = authed_client.patch(
        _url(authed_client, f"/project/projects/{project_id}/"),
        json={"progress": 99},
        timeout=20,
    )
    _assert_status(update_resp, (200,))

    invalid_resp = authed_client.post(
        _url(authed_client, "/project/projects/"),
        json={"project_name": "", "project_status": 999, "progress": 999},
        timeout=20,
    )
    _assert_status(invalid_resp, (400,))

    delete_resp = authed_client.delete(_url(authed_client, f"/project/projects/{project_id}/"), timeout=20)
    _assert_status(delete_resp, (204,))


@pytest.mark.regression
def test_release_filter_boundary(authed_client, seed_objects):
    ok = authed_client.get(
        _url(authed_client, f"/project/releases/?project={seed_objects['project_id']}"),
        timeout=20,
    )
    _assert_status(ok, (200,))
    bad = authed_client.get(_url(authed_client, "/project/releases/?project=not-a-number"), timeout=20)
    _assert_status(bad, (200,))


@pytest.mark.regression
def test_testcase_module_case_step_design_approach_happy_paths(authed_client, seed_objects):
    module_id = seed_objects["module_id"]
    case_id = seed_objects["case_id"]
    step_id = seed_objects["step_id"]
    design_id = seed_objects["design_id"]
    approach_id = seed_objects["approach_id"]

    for path in [
        "/testcase/modules/",
        "/testcase/cases/",
        "/testcase/steps/",
        "/testcase/designs/",
        "/testcase/approachs/",
    ]:
        resp = authed_client.get(_url(authed_client, path), timeout=20)
        _assert_status(resp, (200,))

    mod_detail = authed_client.get(_url(authed_client, f"/testcase/modules/{module_id}/"), timeout=20)
    _assert_status(mod_detail, (200,))
    case_detail = authed_client.get(_url(authed_client, f"/testcase/cases/{case_id}/"), timeout=20)
    _assert_status(case_detail, (200,))
    step_detail = authed_client.get(_url(authed_client, f"/testcase/steps/{step_id}/"), timeout=20)
    _assert_status(step_detail, (200,))
    design_detail = authed_client.get(_url(authed_client, f"/testcase/designs/{design_id}/"), timeout=20)
    _assert_status(design_detail, (200,))
    approach_detail = authed_client.get(_url(authed_client, f"/testcase/approachs/{approach_id}/"), timeout=20)
    _assert_status(approach_detail, (200,))


@pytest.mark.regression
def test_testcase_case_invalid_inputs(authed_client, seed_objects):
    bad_query = authed_client.get(_url(authed_client, "/testcase/cases/?project=abc"), timeout=20)
    _assert_status(bad_query, (200,))

    bad_method = authed_client.post(
        _url(authed_client, f"/testcase/cases/{seed_objects['case_id']}/execute-api/"),
        json={},
        timeout=30,
    )
    _assert_status(bad_method, (200, 400))

    invalid_payload = authed_client.post(
        _url(authed_client, "/testcase/cases/"),
        json={"case_name": "", "module": "invalid"},
        timeout=20,
    )
    _assert_status(invalid_payload, (400,))


@pytest.mark.smoke
@pytest.mark.regression
def test_testcase_batch_actions_and_boundary(authed_client, seed_objects):
    case_id = seed_objects["case_id"]
    execute_ok = authed_client.post(
        _url(authed_client, "/testcase/cases/batch-execute/"),
        json={"ids": [case_id]},
        timeout=20,
    )
    _assert_status(execute_ok, (200,))

    execute_bad = authed_client.post(
        _url(authed_client, "/testcase/cases/batch-execute/"),
        json={"ids": ["bad"]},
        timeout=20,
    )
    _assert_status(execute_bad, (400,))

    delete_ok = authed_client.post(
        _url(authed_client, "/testcase/cases/batch-delete/"),
        json={"ids": [case_id]},
        timeout=20,
    )
    _assert_status(delete_ok, (200,))


@pytest.mark.regression
def test_approach_custom_actions(authed_client, seed_objects):
    approach_id = seed_objects["approach_id"]
    list_img = authed_client.get(
        _url(authed_client, f"/testcase/approachs/{approach_id}/images/"),
        timeout=20,
    )
    _assert_status(list_img, (200,))

    # 非法上传：无文件
    upload_bad = authed_client.post(
        _url(authed_client, f"/testcase/approachs/{approach_id}/images/upload/"),
        json={},
        timeout=20,
    )
    _assert_status(upload_bad, (400,))


@pytest.mark.regression
def test_suggest_extractions_api(authed_client):
    payload = {
        "json_data": {
            "code": 200,
            "msg": "ok",
            "status": True,
            "data": {
                "token": "abcdefghijklmnopqrstuvwxyz123456",
                "requestId": "550e8400-e29b-41d4-a716-446655440000",
            },
        }
    }
    resp = authed_client.post(
        _url(authed_client, "/testcase/suggest-extractions/"),
        json=payload,
        timeout=20,
    )
    _assert_status(resp, (200,))
    body = resp.json()
    suggestions = body.get("suggestions") or []
    paths = {x.get("json_path") for x in suggestions if isinstance(x, dict)}
    assert "$.data.token" in paths
    assert "$.data.requestId" in paths
    assert "$.code" not in paths
    token_item = next(
        (x for x in suggestions if isinstance(x, dict) and x.get("json_path") == "$.data.token"),
        None,
    )
    assert token_item is not None
    assert token_item.get("source") == "body"
    assert token_item.get("expression") == "$.data.token"
    assert token_item.get("var_name")


@pytest.mark.regression
def test_execution_endpoints_happy_and_invalid(authed_client, seed_objects):
    plan_id = seed_objects["plan_id"]
    report_id = seed_objects["report_id"]
    perf_task_id = seed_objects["perf_task_id"]

    for path in ["/execution/plans/", "/execution/reports/", "/execution/tasks/", "/perf/tasks/"]:
        resp = authed_client.get(_url(authed_client, path), timeout=20)
        _assert_status(resp, (200,))

    plan_detail = authed_client.get(_url(authed_client, f"/execution/plans/{plan_id}/"), timeout=20)
    _assert_status(plan_detail, (200,))
    report_detail = authed_client.get(_url(authed_client, f"/execution/reports/{report_id}/"), timeout=20)
    _assert_status(report_detail, (200,))
    perf_detail = authed_client.get(_url(authed_client, f"/execution/tasks/{perf_task_id}/"), timeout=20)
    _assert_status(perf_detail, (200,))

    run_ok = authed_client.post(_url(authed_client, f"/execution/tasks/{perf_task_id}/run/"), json={}, timeout=20)
    _assert_status(run_ok, (200, 400))

    invalid_perf = authed_client.post(
        _url(authed_client, "/execution/tasks/"),
        json={"task_name": "", "scenario": "invalid", "concurrency": -1, "duration": "oops"},
        timeout=20,
    )
    _assert_status(invalid_perf, (400,))

    dashboard = authed_client.get(_url(authed_client, "/execution/dashboard/summary/"), timeout=20)
    _assert_status(dashboard, (200,))

    quality = authed_client.get(_url(authed_client, "/execution/dashboard/quality/"), timeout=20)
    _assert_status(quality, (200,))
    quality_body = quality.json()
    assert "trendChart" in quality_body
    trend = quality_body["trendChart"]
    assert isinstance(trend.get("xAxis"), list)
    assert isinstance(trend.get("series"), list)
    assert len(trend.get("series") or []) >= 3
    # 最近 30 天趋势，至少应返回 30 个 x 轴点位
    assert len(trend.get("xAxis") or []) >= 30
    assert "latestMetrics" in quality_body
    assert "raw" in quality_body


@pytest.mark.regression
def test_defect_endpoints_happy_and_invalid(authed_client, seed_objects):
    defect_id = seed_objects["defect_id"]
    list_resp = authed_client.get(_url(authed_client, "/defect/defects/"), timeout=20)
    _assert_status(list_resp, (200,))

    detail_resp = authed_client.get(_url(authed_client, f"/defect/defects/{defect_id}/"), timeout=20)
    _assert_status(detail_resp, (200,))

    filter_bad = authed_client.get(
        _url(authed_client, "/defect/defects/?severity=abc&status=xyz"),
        timeout=20,
    )
    _assert_status(filter_bad, (200,))

    create_bad = authed_client.post(
        _url(authed_client, "/defect/defects/"),
        json={"defect_name": "", "severity": 99, "priority": 99, "status": 99},
        timeout=20,
    )
    _assert_status(create_bad, (400,))


@pytest.mark.smoke
def test_ai_endpoints_invalid_and_optional_happy(authed_client):
    # invalid: 缺少 API key
    for path in ["/ai/verify-connection/", "/ai/test-connection/"]:
        resp = authed_client.post(_url(authed_client, path), json={}, timeout=30)
        _assert_status(resp, (400, 200))

    gen_bad = authed_client.post(_url(authed_client, "/ai/generate-cases/"), json={}, timeout=30)
    _assert_status(gen_bad, (400,))

    stream_bad = authed_client.post(_url(authed_client, "/ai/generate-cases-stream/"), json={}, timeout=30)
    _assert_status(stream_bad, (400,))

    # 可选 happy path：仅当显式提供可用 key 时执行
    ai_key = os.getenv("TEST_AI_API_KEY", "").strip()
    if ai_key:
        happy = authed_client.post(
            _url(authed_client, "/ai/verify-connection/"),
            json={"api_key": ai_key},
            timeout=60,
        )
        _assert_status(happy, (200,))


@pytest.mark.smoke
def test_assistant_raw_llm_endpoint_invalid_input(authed_client):
    resp = authed_client.post(
        _url(authed_client, "/assistant/llm/test-connection/"),
        json={"model": "glm-4.7-flash"},
        timeout=20,
    )
    _assert_status(resp, (200,))


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
    resp = req(_url(api_client, path), timeout=20)
    assert resp.status_code in (401, 403, 405)
