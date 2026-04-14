"""
审计写入：同步函数供 REST 使用；异步包装供 Channels consumer 使用。
"""

from __future__ import annotations

import logging
from typing import Any

from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


def client_ip_from_request(request) -> str:
    if not request:
        return ""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return str(xff).split(",")[0].strip()[:64]
    return (request.META.get("REMOTE_ADDR") or "")[:64]


def client_ip_from_scope(scope: dict) -> str:
    if not scope:
        return ""
    client = scope.get("client")
    if isinstance(client, (list, tuple)) and client:
        return str(client[0] or "")[:64]
    return ""


def log_server_log_event(
    user,
    action: str,
    *,
    remote_server=None,
    remote_server_id: int | None = None,
    organization=None,
    meta: dict[str, Any] | None = None,
    request=None,
    client_ip: str = "",
    scope: dict | None = None,
) -> None:
    from server_logs.models import RemoteLogServer, ServerLogAuditEvent

    rs = remote_server
    if rs is None and remote_server_id is not None:
        rs = RemoteLogServer.objects.filter(pk=remote_server_id).first()

    ip = (client_ip or "").strip()
    if not ip and request is not None:
        ip = client_ip_from_request(request)
    if not ip and scope is not None:
        ip = client_ip_from_scope(scope)

    org = organization
    if org is None and rs is not None:
        org = getattr(rs, "organization", None)

    safe_meta = dict(meta or {})
    for k in list(safe_meta.keys()):
        lk = k.lower()
        if "password" in lk or "private_key" in lk or "api_key" in lk:
            safe_meta[k] = "[redacted]"

    try:
        ServerLogAuditEvent.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            action=action,
            remote_log_server=rs,
            organization=org if org is not None else None,
            meta=safe_meta,
            client_ip=ip,
        )
    except Exception:
        logger.exception("log_server_log_event failed action=%s", action)


@database_sync_to_async
def log_server_log_event_async(**kwargs):
    log_server_log_event(**kwargs)
