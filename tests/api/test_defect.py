from __future__ import annotations

import pytest

from ._helpers import assert_status, url

pytestmark = [pytest.mark.full]


@pytest.mark.regression
def test_defect_endpoints_happy_and_invalid(authed_client, seed_objects):
    defect_id = seed_objects["defect_id"]
    list_resp = authed_client.get(url(authed_client, "/defect/defects/"), timeout=20)
    assert_status(list_resp, (200,))

    detail_resp = authed_client.get(url(authed_client, f"/defect/defects/{defect_id}/"), timeout=20)
    assert_status(detail_resp, (200,))

    filter_bad = authed_client.get(
        url(authed_client, "/defect/defects/?severity=abc&status=xyz"),
        timeout=20,
    )
    assert_status(filter_bad, (200,))

    create_bad = authed_client.post(
        url(authed_client, "/defect/defects/"),
        json={"defect_name": "", "severity": 99, "priority": 99, "status": 99},
        timeout=20,
    )
    assert_status(create_bad, (400,))

