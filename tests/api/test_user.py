from __future__ import annotations

from datetime import datetime

import pytest

from ._helpers import assert_status, url

pytestmark = [pytest.mark.full]


def test_user_login_happy_path(api_client, user_credentials):
    resp = api_client.post(url(api_client, "/user/login/"), json=user_credentials, timeout=20)
    assert_status(resp, (200,))
    body = resp.json()
    assert (body.get("data") or {}).get("token")


@pytest.mark.smoke
def test_user_login_invalid_password(api_client, user_credentials):
    resp = api_client.post(
        url(api_client, "/user/login/"),
        json={"username": user_credentials["username"], "password": "wrong-password"},
        timeout=20,
    )
    assert_status(resp, (400,))


@pytest.mark.smoke
def test_user_profile_patch_boundary_and_invalid(authed_client):
    ok_resp = authed_client.patch(
        url(authed_client, "/user/me/profile/"),
        json={"phone_number": "", "real_name": f"API Tester {datetime.utcnow().timestamp()}"},
        timeout=20,
    )
    assert_status(ok_resp, (200,))

    bad_resp = authed_client.patch(
        url(authed_client, "/user/me/profile/"),
        json={"phone_number": "1" * 256},
        timeout=20,
    )
    assert_status(bad_resp, (200, 400))

