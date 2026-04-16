from __future__ import annotations

import os

import pytest

from ._helpers import assert_status, url

pytestmark = [pytest.mark.full]


@pytest.mark.smoke
def test_ai_endpoints_invalid_and_optional_happy(authed_client):
    for path in ["/ai/verify-connection/", "/ai/test-connection/"]:
        resp = authed_client.post(url(authed_client, path), json={}, timeout=30)
        assert_status(resp, (400, 200))

    gen_bad = authed_client.post(url(authed_client, "/ai/generate-cases/"), json={}, timeout=30)
    assert_status(gen_bad, (400,))

    stream_bad = authed_client.post(url(authed_client, "/ai/generate-cases-stream/"), json={}, timeout=30)
    assert_status(stream_bad, (400,))

    ai_key = os.getenv("TEST_AI_API_KEY", "").strip()
    if ai_key:
        happy = authed_client.post(
            url(authed_client, "/ai/verify-connection/"),
            json={"api_key": ai_key},
            timeout=60,
        )
        assert_status(happy, (200,))


@pytest.mark.smoke
def test_assistant_raw_llm_endpoint_invalid_input(authed_client):
    resp = authed_client.post(
        url(authed_client, "/assistant/llm/test-connection/"),
        json={"model": "glm-4.7-flash"},
        timeout=20,
    )
    assert_status(resp, (200,))

