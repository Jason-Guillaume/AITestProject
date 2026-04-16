from __future__ import annotations

import pytest

from ._helpers import assert_status, url

pytestmark = [pytest.mark.full]


@pytest.mark.regression
def test_sys_ai_config_endpoints(admin_client):
    get_resp = admin_client.get(url(admin_client, "/sys/ai-config/"), timeout=20)
    assert_status(get_resp, (200,))

    put_resp = admin_client.put(
        url(admin_client, "/sys/ai-config/"),
        json={"model_type": "glm-4.7-flash", "api_key": "dummy-key", "base_url": ""},
        timeout=20,
    )
    assert_status(put_resp, (200,))

    disconnect_resp = admin_client.post(url(admin_client, "/sys/ai-config/disconnect/"), json={}, timeout=20)
    assert_status(disconnect_resp, (200,))

    reconnect_resp = admin_client.post(url(admin_client, "/sys/ai-config/reconnect/"), json={}, timeout=20)
    assert_status(reconnect_resp, (200,))

