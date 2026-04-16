from __future__ import annotations

import base64
from typing import Any, Dict, Tuple

from testcase.models import TestEnvironment


class AuthConfigError(ValueError):
    pass


def _get_var(variables: Dict[str, Any], name: str) -> Any:
    if not name:
        return None
    return (variables or {}).get(name)


def inject_environment_auth(
    *,
    headers: Dict[str, Any],
    body: Any,
    variables: Dict[str, Any],
    environment_id: int | None,
) -> Tuple[Dict[str, Any], Any]:
    """
    将环境鉴权配置注入到 headers/body。

    支持的 auth_config.type：
    - bearer:  {type, token_var="token", header="Authorization", prefix="Bearer "}
    - api_key: {type, header="X-API-Key", value, value_var}
    - basic:   {type, username, password, username_var, password_var, header="Authorization"}
    - cookie:  {type, cookie, cookie_var, header="Cookie"}
    """

    if not environment_id:
        return headers, body
    env = TestEnvironment.objects.filter(pk=environment_id, is_deleted=False).only(
        "id", "auth_config"
    ).first()
    if not env:
        return headers, body

    cfg = env.auth_config if isinstance(env.auth_config, dict) else {}
    typ = str(cfg.get("type") or "").strip().lower()
    if not typ:
        return headers, body

    out_headers = dict(headers or {})

    if typ == "bearer":
        token_var = str(cfg.get("token_var") or "token").strip()
        token = cfg.get("token")
        if token is None:
            token = _get_var(variables or {}, token_var)
        token = (str(token).strip() if token is not None else "")
        if not token:
            return out_headers, body
        header = str(cfg.get("header") or "Authorization").strip() or "Authorization"
        prefix = str(cfg.get("prefix") or "Bearer ")
        out_headers[header] = f"{prefix}{token}"
        return out_headers, body

    if typ == "api_key":
        header = str(cfg.get("header") or "X-API-Key").strip() or "X-API-Key"
        value = cfg.get("value")
        if value is None:
            value = _get_var(variables or {}, str(cfg.get("value_var") or "").strip())
        value = (str(value).strip() if value is not None else "")
        if not value:
            return out_headers, body
        out_headers[header] = value
        return out_headers, body

    if typ == "basic":
        username = cfg.get("username")
        if username is None:
            username = _get_var(variables or {}, str(cfg.get("username_var") or "").strip())
        password = cfg.get("password")
        if password is None:
            password = _get_var(variables or {}, str(cfg.get("password_var") or "").strip())
        username = str(username or "")
        password = str(password or "")
        if not username and not password:
            return out_headers, body
        raw = f"{username}:{password}".encode("utf-8")
        token = base64.b64encode(raw).decode("ascii")
        header = str(cfg.get("header") or "Authorization").strip() or "Authorization"
        out_headers[header] = f"Basic {token}"
        return out_headers, body

    if typ == "cookie":
        header = str(cfg.get("header") or "Cookie").strip() or "Cookie"
        cookie = cfg.get("cookie")
        if cookie is None:
            cookie = _get_var(variables or {}, str(cfg.get("cookie_var") or "").strip())
        cookie = (str(cookie).strip() if cookie is not None else "")
        if not cookie:
            return out_headers, body
        out_headers[header] = cookie
        return out_headers, body

    raise AuthConfigError(f"Unsupported auth_config.type: {typ}")

