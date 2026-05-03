"""UI 脚本（WebUI 工作台）REST API 集成测试：依赖已启动后端与 TEST_API_* 环境变量。"""
from __future__ import annotations

import io
import uuid

import pytest

from ._helpers import assert_status, url

pytestmark = [pytest.mark.full]


def _multipart_post(authed_client, path: str, *, data: dict, files: dict, timeout: int = 60):
    """去掉 Session 默认的 application/json，以便正确发送 multipart。"""
    h = {k: v for k, v in authed_client.headers.items() if k.lower() != "content-type"}
    return authed_client.post(url(authed_client, path), data=data, files=files, headers=h, timeout=timeout)


def _list_results(body):
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        return body.get("results") or body.get("data") or []
    return []


@pytest.mark.regression
def test_ui_scripts_list_requires_auth(api_client):
    r = api_client.get(url(api_client, "/assistant/ui-scripts/"), timeout=20)
    assert_status(r, (401, 403))


@pytest.mark.smoke
def test_ui_scripts_full_flow(authed_client):
    nonce = uuid.uuid4().hex[:8]
    name = f"api-ui-{nonce}"
    py_bytes = b'print("api-test")\n'
    files = {"file_path": (f"api_test_{nonce}.py", io.BytesIO(py_bytes), "application/octet-stream")}
    form = {
        "name": name,
        "script_type": "LINEAR",
        "language": "PYTHON",
        "framework": "AUTO",
    }
    create = _multipart_post(authed_client, "/assistant/ui-scripts/", data=form, files=files, timeout=90)
    assert_status(create, (201,))
    created = create.json()
    sid = created.get("id")
    assert sid, created

    lst = authed_client.get(url(authed_client, "/assistant/ui-scripts/"), timeout=30)
    assert_status(lst, (200,))
    rows = _list_results(lst.json())
    assert any((r.get("id") if isinstance(r, dict) else None) == sid for r in rows), lst.text

    patch = authed_client.patch(
        url(authed_client, f"/assistant/ui-scripts/{sid}/"),
        json={"name": f"{name}-renamed"},
        timeout=30,
    )
    assert_status(patch, (200,))
    assert patch.json().get("name") == f"{name}-renamed"

    ws = authed_client.get(url(authed_client, f"/assistant/ui-scripts/{sid}/workspace_info/"), timeout=30)
    assert_status(ws, (200,))
    assert "workspace_path" in ws.json() or "files" in ws.json()

    fld = authed_client.get(url(authed_client, "/assistant/ui-scripts/folders/"), timeout=30)
    assert_status(fld, (200,))

    # 须在启用状态下触发执行（异步 202）
    exe = authed_client.post(
        url(authed_client, "/assistant/ui-script-executions/execute/"),
        json={"script_id": sid, "browser": "chrome", "headless": True, "parallel": 1},
        timeout=30,
    )
    assert_status(exe, (202,))
    assert exe.json().get("execution_id")

    toggle = authed_client.post(url(authed_client, f"/assistant/ui-scripts/{sid}/toggle_active/"), timeout=30)
    assert_status(toggle, (200,))
    assert "is_active" in toggle.json()

    delete = authed_client.delete(url(authed_client, f"/assistant/ui-scripts/{sid}/"), timeout=30)
    assert_status(delete, (204,))

    trash = authed_client.get(url(authed_client, "/assistant/ui-scripts/trash/"), timeout=30)
    assert_status(trash, (200,))
    tj = trash.json()
    trows = tj.get("results") if isinstance(tj, dict) else []
    assert any((r.get("id") if isinstance(r, dict) else None) == sid for r in trows), trash.text

    restore = authed_client.post(url(authed_client, f"/assistant/ui-scripts/{sid}/restore/"), timeout=30)
    assert_status(restore, (200,))

    delete2 = authed_client.delete(url(authed_client, f"/assistant/ui-scripts/{sid}/"), timeout=30)
    assert_status(delete2, (204,))

    purge = authed_client.post(url(authed_client, f"/assistant/ui-scripts/{sid}/permanent_delete/"), timeout=60)
    assert_status(purge, (200,))


@pytest.mark.regression
def test_ui_scripts_create_validation(authed_client):
    bad = authed_client.post(
        url(authed_client, "/assistant/ui-scripts/"),
        json={"name": "", "script_type": "LINEAR", "language": "PYTHON"},
        timeout=30,
    )
    assert_status(bad, (400,))
