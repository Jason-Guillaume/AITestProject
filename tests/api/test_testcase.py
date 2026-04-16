from __future__ import annotations

import pytest

from ._helpers import assert_status, url

pytestmark = [pytest.mark.full]


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
        "/testcase/approaches/",
    ]:
        resp = authed_client.get(url(authed_client, path), timeout=20)
        assert_status(resp, (200,))

    mod_detail = authed_client.get(url(authed_client, f"/testcase/modules/{module_id}/"), timeout=20)
    assert_status(mod_detail, (200,))
    case_detail = authed_client.get(url(authed_client, f"/testcase/cases/{case_id}/"), timeout=20)
    assert_status(case_detail, (200,))
    step_detail = authed_client.get(url(authed_client, f"/testcase/steps/{step_id}/"), timeout=20)
    assert_status(step_detail, (200,))
    design_detail = authed_client.get(url(authed_client, f"/testcase/designs/{design_id}/"), timeout=20)
    assert_status(design_detail, (200,))
    approach_detail = authed_client.get(url(authed_client, f"/testcase/approaches/{approach_id}/"), timeout=20)
    assert_status(approach_detail, (200,))


@pytest.mark.regression
def test_testcase_case_invalid_inputs(authed_client, seed_objects):
    bad_query = authed_client.get(url(authed_client, "/testcase/cases/?project=abc"), timeout=20)
    assert_status(bad_query, (200,))

    bad_method = authed_client.post(
        url(authed_client, f"/testcase/cases/{seed_objects['case_id']}/execute-api/"),
        json={},
        timeout=30,
    )
    assert_status(bad_method, (200, 400))

    invalid_payload = authed_client.post(
        url(authed_client, "/testcase/cases/"),
        json={"case_name": "", "module": "invalid"},
        timeout=20,
    )
    assert_status(invalid_payload, (400,))


@pytest.mark.smoke
@pytest.mark.regression
def test_testcase_batch_actions_and_boundary(authed_client, seed_objects):
    case_id = seed_objects["case_id"]
    execute_ok = authed_client.post(
        url(authed_client, "/testcase/cases/batch-execute/"),
        json={"ids": [case_id]},
        timeout=20,
    )
    assert_status(execute_ok, (200,))

    execute_bad = authed_client.post(
        url(authed_client, "/testcase/cases/batch-execute/"),
        json={"ids": ["bad"]},
        timeout=20,
    )
    assert_status(execute_bad, (400,))

    delete_ok = authed_client.post(
        url(authed_client, "/testcase/cases/batch-delete/"),
        json={"ids": [case_id]},
        timeout=20,
    )
    assert_status(delete_ok, (200,))


@pytest.mark.regression
def test_approach_custom_actions(authed_client, seed_objects):
    approach_id = seed_objects["approach_id"]
    list_img = authed_client.get(url(authed_client, f"/testcase/approaches/{approach_id}/images/"), timeout=20)
    assert_status(list_img, (200,))

    upload_bad = authed_client.post(
        url(authed_client, f"/testcase/approaches/{approach_id}/images/upload/"),
        json={},
        timeout=20,
    )
    assert_status(upload_bad, (400,))


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
    resp = authed_client.post(url(authed_client, "/testcase/suggest-extractions/"), json=payload, timeout=20)
    assert_status(resp, (200,))
    body = resp.json()
    suggestions = body.get("suggestions") or []
    paths = {x.get("json_path") for x in suggestions if isinstance(x, dict)}
    assert "$.data.token" in paths
    assert "$.data.requestId" in paths
    assert "$.code" not in paths

