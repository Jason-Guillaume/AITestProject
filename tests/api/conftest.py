import os
import uuid
from datetime import datetime, timedelta

import pytest
import requests


def _must_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        pytest.skip(f"缺少环境变量 {name}，跳过 API 集成测试")
    return value


@pytest.fixture(scope="session")
def api_base_url() -> str:
    # 这套 tests/api 为“对已运行后端的集成测试”，必须显式提供 base_url
    return _must_env("TEST_API_BASE_URL").rstrip("/")


@pytest.fixture(scope="session")
def user_credentials():
    return {
        "username": _must_env("TEST_API_USERNAME"),
        "password": _must_env("TEST_API_PASSWORD"),
    }


@pytest.fixture(scope="session")
def admin_credentials(user_credentials):
    username = os.getenv("TEST_API_ADMIN_USERNAME", "").strip()
    password = os.getenv("TEST_API_ADMIN_PASSWORD", "").strip()
    if username and password:
        return {"username": username, "password": password}
    return user_credentials


@pytest.fixture(scope="session")
def api_client(api_base_url):
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.base_url = api_base_url
    return session


def _login(
    session: requests.Session, base_url: str, username: str, password: str
) -> str:
    resp = session.post(
        f"{base_url}/user/login/",
        json={"username": username, "password": password},
        timeout=20,
    )
    assert resp.status_code == 200, f"登录失败: {resp.status_code}, {resp.text}"
    body = resp.json()
    token = (body.get("data") or {}).get("token")
    assert token, f"登录响应缺少 token: {body}"
    return token


@pytest.fixture(scope="session")
def user_token(api_client, api_base_url, user_credentials) -> str:
    return _login(
        api_client,
        api_base_url,
        user_credentials["username"],
        user_credentials["password"],
    )


@pytest.fixture(scope="session")
def admin_token(api_client, api_base_url, admin_credentials) -> str:
    return _login(
        api_client,
        api_base_url,
        admin_credentials["username"],
        admin_credentials["password"],
    )


@pytest.fixture()
def authed_client(api_client, user_token):
    session = requests.Session()
    session.headers.update(
        {
            "Content-Type": "application/json",
            "Authorization": f"Token {user_token}",
        }
    )
    session.base_url = api_client.base_url
    return session


@pytest.fixture()
def admin_client(api_client, admin_token):
    session = requests.Session()
    session.headers.update(
        {
            "Content-Type": "application/json",
            "Authorization": f"Token {admin_token}",
        }
    )
    session.base_url = api_client.base_url
    return session


@pytest.fixture()
def user_context(authed_client):
    resp = authed_client.get(f"{authed_client.base_url}/user/me/", timeout=20)
    assert resp.status_code == 200, resp.text
    data = (resp.json() or {}).get("data") or {}
    user_id = data.get("user_id")
    assert user_id, f"/user/me/ 未返回 user_id: {resp.text}"
    return {"user_id": user_id}


@pytest.fixture()
def seed_objects(authed_client, user_context):
    u = user_context["user_id"]
    nonce = uuid.uuid4().hex[:8]

    project_payload = {
        "project_name": f"api-test-project-{nonce}",
        "description": "pytest api automation",
        "project_status": 1,
        "progress": 10,
        "members": [u],
    }
    project_resp = authed_client.post(
        f"{authed_client.base_url}/project/projects/",
        json=project_payload,
        timeout=20,
    )
    assert project_resp.status_code in (200, 201), project_resp.text
    project_id = project_resp.json()["id"]

    release_payload = {
        "project": project_id,
        "release_name": f"release-{nonce}",
        "version_no": f"v-{nonce}",
        "release_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "status": 1,
    }
    release_resp = authed_client.post(
        f"{authed_client.base_url}/project/releases/",
        json=release_payload,
        timeout=20,
    )
    assert release_resp.status_code in (200, 201), release_resp.text
    release_id = release_resp.json()["id"]

    module_payload = {
        "project": project_id,
        "name": f"module-{nonce}",
        "test_type": "api",
    }
    module_resp = authed_client.post(
        f"{authed_client.base_url}/testcase/modules/",
        json=module_payload,
        timeout=20,
    )
    assert module_resp.status_code in (200, 201), module_resp.text
    module_id = module_resp.json()["id"]

    case_payload = {
        "module": module_id,
        "case_name": f"case-{nonce}",
        "test_type": "api",
        "level": "P1",
        "api_url": "https://httpbin.org/get",
        "api_method": "GET",
        "api_headers": {"Accept": "application/json"},
    }
    case_resp = authed_client.post(
        f"{authed_client.base_url}/testcase/cases/",
        json=case_payload,
        timeout=20,
    )
    assert case_resp.status_code in (200, 201), case_resp.text
    case_id = case_resp.json()["id"]

    step_payload = {
        "testcase": case_id,
        "step_number": 1,
        "step_desc": "发送 GET 请求",
        "expected_result": "返回 200",
    }
    step_resp = authed_client.post(
        f"{authed_client.base_url}/testcase/steps/",
        json=step_payload,
        timeout=20,
    )
    assert step_resp.status_code in (200, 201), step_resp.text
    step_id = step_resp.json()["id"]

    design_payload = {
        "design_name": f"design-{nonce}",
        "req_count": 1,
        "point_count": 1,
        "case_count": 1,
    }
    design_resp = authed_client.post(
        f"{authed_client.base_url}/testcase/designs/",
        json=design_payload,
        timeout=20,
    )
    assert design_resp.status_code in (200, 201), design_resp.text
    design_id = design_resp.json()["id"]

    approach_payload = {
        "scheme_name": f"approach-{nonce}",
        "version": "1.0",
        "test_category": 2,
    }
    approach_resp = authed_client.post(
        f"{authed_client.base_url}/testcase/approaches/",
        json=approach_payload,
        timeout=20,
    )
    assert approach_resp.status_code in (200, 201), approach_resp.text
    approach_id = approach_resp.json()["id"]

    task_payload = {
        "task_title": f"task-{nonce}",
        "task_desc": "task desc",
        "status": 1,
        "assignee": u,
    }
    task_resp = authed_client.post(
        f"{authed_client.base_url}/project/tasks/",
        json=task_payload,
        timeout=20,
    )
    assert task_resp.status_code in (200, 201), task_resp.text
    task_id = task_resp.json()["id"]

    plan_payload = {
        "plan_name": f"plan-{nonce}",
        "version": release_id,
        "environment": "test",
        "req_count": 1,
        "case_count": 1,
        "testers": [u],
    }
    plan_resp = authed_client.post(
        f"{authed_client.base_url}/execution/plans/",
        json=plan_payload,
        timeout=20,
    )
    assert plan_resp.status_code in (200, 201), plan_resp.text
    plan_id = plan_resp.json()["id"]

    now = datetime.utcnow()
    report_payload = {
        "plan": plan_id,
        "report_name": f"report-{nonce}",
        "create_method": 1,
        "environment": "test",
        "start_time": (now - timedelta(hours=1)).isoformat(),
        "end_time": now.isoformat(),
    }
    report_resp = authed_client.post(
        f"{authed_client.base_url}/execution/reports/",
        json=report_payload,
        timeout=20,
    )
    assert report_resp.status_code in (200, 201), report_resp.text
    report_id = report_resp.json()["id"]

    perf_payload = {
        "task_name": f"perf-{nonce}",
        "scenario": "jmeter",
        "concurrency": 10,
        "duration": "10m",
    }
    perf_resp = authed_client.post(
        f"{authed_client.base_url}/execution/tasks/",
        json=perf_payload,
        timeout=20,
    )
    assert perf_resp.status_code in (200, 201), perf_resp.text
    perf_task_id = perf_resp.json()["task_id"]

    defect_payload = {
        "defect_name": f"defect-{nonce}",
        "release_version": release_id,
        "severity": 2,
        "priority": 2,
        "status": 1,
        "handler": u,
        "module": module_id,
        "defect_content": "content",
    }
    defect_resp = authed_client.post(
        f"{authed_client.base_url}/defect/defects/",
        json=defect_payload,
        timeout=20,
    )
    assert defect_resp.status_code in (200, 201), defect_resp.text
    defect_id = defect_resp.json()["id"]

    return {
        "project_id": project_id,
        "release_id": release_id,
        "module_id": module_id,
        "case_id": case_id,
        "step_id": step_id,
        "design_id": design_id,
        "approach_id": approach_id,
        "task_id": task_id,
        "plan_id": plan_id,
        "report_id": report_id,
        "perf_task_id": perf_task_id,
        "defect_id": defect_id,
    }
