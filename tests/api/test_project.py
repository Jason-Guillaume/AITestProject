from __future__ import annotations

from datetime import datetime

import pytest

from ._helpers import assert_status, url

pytestmark = [pytest.mark.full]


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
    create_resp = authed_client.post(url(authed_client, "/project/projects/"), json=payload, timeout=20)
    assert_status(create_resp, (200, 201))
    project_id = create_resp.json()["id"]

    list_resp = authed_client.get(url(authed_client, "/project/projects/"), timeout=20)
    assert_status(list_resp, (200,))

    update_resp = authed_client.patch(
        url(authed_client, f"/project/projects/{project_id}/"),
        json={"progress": 99},
        timeout=20,
    )
    assert_status(update_resp, (200,))

    invalid_resp = authed_client.post(
        url(authed_client, "/project/projects/"),
        json={"project_name": "", "project_status": 999, "progress": 999},
        timeout=20,
    )
    assert_status(invalid_resp, (400,))

    delete_resp = authed_client.delete(url(authed_client, f"/project/projects/{project_id}/"), timeout=20)
    assert_status(delete_resp, (204,))


@pytest.mark.regression
def test_release_filter_boundary(authed_client, seed_objects):
    ok = authed_client.get(
        url(authed_client, f"/project/releases/?project={seed_objects['project_id']}"),
        timeout=20,
    )
    assert_status(ok, (200,))
    bad = authed_client.get(url(authed_client, "/project/releases/?project=not-a-number"), timeout=20)
    assert_status(bad, (200,))


@pytest.mark.regression
def test_release_risk_brief(authed_client, seed_objects):
    rid = seed_objects["release_id"]
    resp = authed_client.get(url(authed_client, f"/project/releases/{rid}/risk-brief/?days=7"), timeout=20)
    assert_status(resp, (200,))
    data = resp.json()
    assert data.get("release", {}).get("id") == rid
    assert "coverage" in data and "defects" in data and "executions" in data
    assert isinstance(data.get("markdown"), str) and data["markdown"]

