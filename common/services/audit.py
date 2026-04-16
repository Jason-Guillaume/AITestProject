from __future__ import annotations

from typing import Any, Dict, Optional

from django.db import models

from common.models import AuditEvent

_SENSITIVE_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
    "authorization",
    "cookie",
    "set-cookie",
}


def _truncate(v: Any, max_len: int = 2000) -> Any:
    if v is None:
        return None
    if isinstance(v, str):
        if len(v) <= max_len:
            return v
        return v[:max_len] + f"...(truncated,total={len(v)})"
    return v


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            key = str(k).lower()
            if key in _SENSITIVE_KEYS:
                out[k] = "***"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(obj, list):
        return [_redact(x) for x in obj[:200]]
    return _truncate(obj)


def _model_payload(instance: models.Model) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for f in instance._meta.get_fields():
        if not hasattr(f, "attname"):
            continue
        name = getattr(f, "attname", None)
        if not name:
            continue
        if name in ("id", "pk"):
            continue
        # 跳过反向关系 / M2M
        if getattr(f, "many_to_many", False) or getattr(f, "one_to_many", False):
            continue
        try:
            payload[name] = getattr(instance, name)
        except Exception:
            continue
    return _redact(payload)


def record_audit_event(
    *,
    action: str,
    actor,
    instance: Optional[models.Model],
    request=None,
    before: Any = None,
    after: Any = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    写入审计事件（失败不应影响主业务）。
    """

    try:
        obj_app = ""
        obj_model = ""
        obj_id = ""
        obj_repr = ""
        if instance is not None:
            meta = instance._meta
            obj_app = getattr(meta, "app_label", "") or ""
            obj_model = getattr(meta, "model_name", "") or ""
            try:
                obj_id = str(getattr(instance, "pk", "") or "")
            except Exception:
                obj_id = ""
            try:
                obj_repr = str(instance)[:255]
            except Exception:
                obj_repr = ""

        path = ""
        ua = ""
        ip = ""
        if request is not None:
            try:
                path = str(getattr(request, "path", "") or "")[:512]
            except Exception:
                path = ""
            try:
                ua = str(request.META.get("HTTP_USER_AGENT", "") or "")[:512]
            except Exception:
                ua = ""
            try:
                ip = str(
                    request.META.get("HTTP_X_FORWARDED_FOR", "")
                    or request.META.get("REMOTE_ADDR", "")
                    or ""
                )[:64]
            except Exception:
                ip = ""

        if before is None and instance is not None:
            before = _model_payload(instance)
        elif isinstance(before, models.Model):
            before = _model_payload(before)

        if after is None and instance is not None:
            after = _model_payload(instance)
        elif isinstance(after, models.Model):
            after = _model_payload(after)

        AuditEvent.objects.create(
            action=action,
            object_app=obj_app,
            object_model=obj_model,
            object_id=obj_id,
            object_repr=obj_repr,
            request_path=path,
            ip=ip,
            user_agent=ua,
            before=_redact(before) if before is not None else None,
            after=_redact(after) if after is not None else None,
            extra=extra or {},
            creator=actor if (actor and getattr(actor, "is_authenticated", False)) else None,
            updater=actor if (actor and getattr(actor, "is_authenticated", False)) else None,
        )
    except Exception:
        # 审计不能影响业务路径
        return


def record_export_audit(
    *,
    actor,
    instance: Optional[models.Model],
    request=None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    统一“导出”审计入口（CSV/报表下载等）。
    """

    record_audit_event(
        action=AuditEvent.ACTION_EXPORT,
        actor=actor,
        instance=instance,
        request=request,
        extra=extra or {},
    )


def record_execute_audit(
    *,
    actor,
    instance: Optional[models.Model],
    request=None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    统一“执行”审计入口（跑批/任务触发/异步入队等）。
    """

    record_audit_event(
        action=AuditEvent.ACTION_EXECUTE,
        actor=actor,
        instance=instance,
        request=request,
        extra=extra or {},
    )

