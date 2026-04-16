from __future__ import annotations


def url(client, path: str) -> str:
    return f"{client.base_url}{path}"


def assert_status(resp, expected: tuple[int, ...]):
    assert resp.status_code in expected, f"status={resp.status_code}, body={resp.text}"

