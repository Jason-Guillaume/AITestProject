from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.cache import cache


def _now_ms() -> int:
    return int(time.time() * 1000)


def _safe_str(x: Any, max_len: int = 512) -> str:
    s = str(x or "")
    s = s.replace("\n", " ").replace("\r", " ").strip()
    if len(s) > max_len:
        s = s[: max_len - 1] + "…"
    return s


def _redact_meta(meta: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(meta or {})
    for k in list(out.keys()):
        lk = str(k).lower()
        if "password" in lk or "private_key" in lk or "api_key" in lk or "token" in lk:
            out[k] = "[redacted]"
    return out


def _int_setting(name: str, default: int) -> int:
    try:
        return int(getattr(settings, name, default))
    except Exception:
        return default


@dataclass(frozen=True)
class AiGuardLimits:
    daily_requests: int
    max_concurrency: int
    concurrency_ttl_seconds: int


def get_ai_guard_limits() -> AiGuardLimits:
    return AiGuardLimits(
        daily_requests=max(0, _int_setting("AI_GUARD_DAILY_REQUESTS", 0)),
        max_concurrency=max(0, _int_setting("AI_GUARD_MAX_CONCURRENCY", 2)),
        concurrency_ttl_seconds=max(
            10, _int_setting("AI_GUARD_CONCURRENCY_TTL_SECONDS", 180)
        ),
    )


def _daily_quota_key(user_id: int, yyyymmdd: str) -> str:
    return f"ai:quota:{yyyymmdd}:u:{int(user_id)}"


def _concurrency_key(user_id: int) -> str:
    return f"ai:concurrency:u:{int(user_id)}"


def _scope_daily_quota_key(scope: str, scope_id: int, yyyymmdd: str) -> str:
    return f"ai:quota:{yyyymmdd}:{scope}:{int(scope_id)}"


def _scope_concurrency_key(scope: str, scope_id: int) -> str:
    return f"ai:concurrency:{scope}:{int(scope_id)}"


@dataclass(frozen=True)
class AiScopePolicy:
    scope: str  # "u" | "p" | "o"
    scope_id: int
    daily_requests: int
    max_concurrency: int
    concurrency_ttl_seconds: int


def _action_allowed(allowed_actions: list[str] | None, action: str) -> bool:
    arr = list(allowed_actions or [])
    if not arr:
        return True
    return action in arr


def resolve_effective_scope_policy(
    *,
    user_id: int,
    project_id: int | None,
    org_id: int | None,
    action: str,
) -> AiScopePolicy | None:
    """
    优先级：user > project > org。
    - 未配置/未启用则返回 None（表示不额外限制）
    - allowed_actions 为空表示对全部 action 生效
    """
    try:
        from user.models import AiQuotaPolicy
    except Exception:
        return None

    uid = int(user_id or 0)
    pid = int(project_id or 0) if project_id else 0
    oid = int(org_id or 0) if org_id else 0
    a = str(action or "").strip()
    if uid <= 0 or not a:
        return None

    cache_key = f"ai:policy:resolve:u:{uid}:p:{pid}:o:{oid}:a:{a}"
    cached = cache.get(cache_key)
    if isinstance(cached, dict):
        try:
            return AiScopePolicy(**cached)  # type: ignore[arg-type]
        except Exception:
            pass
    if cached is False:
        return None

    qs = AiQuotaPolicy.objects.filter(is_deleted=False, is_enabled=True)

    # 1) user override
    row = qs.filter(scope_type=AiQuotaPolicy.SCOPE_USER, user_id=uid).order_by("-id").first()
    if row and _action_allowed(getattr(row, "allowed_actions", None), a):
        pol = AiScopePolicy(
            scope="u",
            scope_id=uid,
            daily_requests=int(getattr(row, "daily_requests", 0) or 0),
            max_concurrency=int(getattr(row, "max_concurrency", 0) or 0),
            concurrency_ttl_seconds=int(getattr(row, "concurrency_ttl_seconds", 180) or 180),
        )
        cache.set(cache_key, pol.__dict__, timeout=30)
        return pol

    # 2) project
    if pid > 0:
        row = qs.filter(scope_type=AiQuotaPolicy.SCOPE_PROJECT, project_id=pid).order_by("-id").first()
        if row and _action_allowed(getattr(row, "allowed_actions", None), a):
            pol = AiScopePolicy(
                scope="p",
                scope_id=pid,
                daily_requests=int(getattr(row, "daily_requests", 0) or 0),
                max_concurrency=int(getattr(row, "max_concurrency", 0) or 0),
                concurrency_ttl_seconds=int(getattr(row, "concurrency_ttl_seconds", 180) or 180),
            )
            cache.set(cache_key, pol.__dict__, timeout=30)
            return pol

    # 3) org
    if oid > 0:
        row = qs.filter(scope_type=AiQuotaPolicy.SCOPE_ORG, org_id=oid).order_by("-id").first()
        if row and _action_allowed(getattr(row, "allowed_actions", None), a):
            pol = AiScopePolicy(
                scope="o",
                scope_id=oid,
                daily_requests=int(getattr(row, "daily_requests", 0) or 0),
                max_concurrency=int(getattr(row, "max_concurrency", 0) or 0),
                concurrency_ttl_seconds=int(getattr(row, "concurrency_ttl_seconds", 180) or 180),
            )
            cache.set(cache_key, pol.__dict__, timeout=30)
            return pol

    cache.set(cache_key, False, timeout=30)
    return None


def check_and_increment_daily_quota_for_scope(
    *, scope: str, scope_id: int, yyyymmdd: str, limit: int
) -> tuple[bool, int, int]:
    """
    返回 (allowed, used_after, limit).
    limit==0 表示不启用配额。
    """
    lim = int(limit or 0)
    if lim <= 0:
        return True, 0, 0
    key = _scope_daily_quota_key(scope, int(scope_id), yyyymmdd)
    try:
        used = cache.incr(key, 1)
    except ValueError:
        cache.add(key, 0, timeout=60 * 60 * 24 + 60)
        used = cache.incr(key, 1)
    if used > lim:
        return False, used, lim
    return True, used, lim


def acquire_ai_concurrency_slot_for_scope(
    *, scope: str, scope_id: int, max_concurrency: int, ttl_seconds: int
) -> tuple[bool, int, int]:
    """
    返回 (acquired, current_after, max_concurrency).
    max==0 表示不限制（不建议）。
    """
    max_c = int(max_concurrency or 0)
    if max_c <= 0:
        return True, 0, 0
    ttl = max(10, int(ttl_seconds or 180))
    key = _scope_concurrency_key(scope, int(scope_id))
    try:
        cur = cache.incr(key, 1)
    except ValueError:
        cache.add(key, 0, timeout=ttl)
        cur = cache.incr(key, 1)
    cache.expire(key, ttl)  # type: ignore[attr-defined]
    if cur > max_c:
        try:
            cache.decr(key, 1)
        except Exception:
            pass
        return False, cur, max_c
    return True, cur, max_c


def release_ai_concurrency_slot_for_scope(*, scope: str, scope_id: int) -> None:
    key = _scope_concurrency_key(scope, int(scope_id))
    try:
        cache.decr(key, 1)
    except Exception:
        return


def check_and_increment_daily_quota(
    *, user_id: int, yyyymmdd: str
) -> tuple[bool, int, int]:
    """
    返回 (allowed, used_after, limit).
    limit==0 表示不启用配额。
    """
    limits = get_ai_guard_limits()
    limit = int(limits.daily_requests)
    if limit <= 0:
        return True, 0, 0
    key = _daily_quota_key(user_id, yyyymmdd)
    try:
        used = cache.incr(key, 1)
    except ValueError:
        cache.add(key, 0, timeout=60 * 60 * 24 + 60)
        used = cache.incr(key, 1)
    if used > limit:
        return False, used, limit
    return True, used, limit


def acquire_ai_concurrency_slot(*, user_id: int) -> tuple[bool, int, int]:
    """
    返回 (acquired, current_after, max_concurrency).
    max==0 表示不限制（不建议）。
    """
    limits = get_ai_guard_limits()
    max_c = int(limits.max_concurrency)
    if max_c <= 0:
        return True, 0, 0
    key = _concurrency_key(user_id)
    ttl = int(limits.concurrency_ttl_seconds)
    try:
        cur = cache.incr(key, 1)
    except ValueError:
        cache.add(key, 0, timeout=ttl)
        cur = cache.incr(key, 1)
    cache.expire(key, ttl)  # type: ignore[attr-defined]
    if cur > max_c:
        # 释放本次占用
        try:
            cache.decr(key, 1)
        except Exception:
            pass
        return False, cur, max_c
    return True, cur, max_c


def release_ai_concurrency_slot(*, user_id: int) -> None:
    key = _concurrency_key(user_id)
    try:
        cache.decr(key, 1)
    except Exception:
        return


def write_ai_usage_event(
    *,
    user,
    action: str,
    endpoint: str = "",
    success: bool,
    status_code: int,
    model_used: str = "",
    test_type: str = "",
    module_id: int | None = None,
    streamed: bool = False,
    all_covered: bool = False,
    latency_ms: int = 0,
    prompt_chars: int = 0,
    output_chars: int = 0,
    cases_count: int = 0,
    error_code: str = "",
    error_message: str = "",
    meta: dict[str, Any] | None = None,
) -> None:
    from assistant.models import AiUsageEvent

    safe_meta = _redact_meta(meta)
    try:
        AiUsageEvent.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            action=action,
            endpoint=(endpoint or "")[:128],
            success=bool(success),
            status_code=int(status_code or 0),
            error_code=(error_code or "")[:64],
            error_message=_safe_str(error_message, 512),
            model_used=(model_used or "")[:128],
            test_type=(test_type or "")[:32],
            module_id=module_id,
            streamed=bool(streamed),
            all_covered=bool(all_covered),
            latency_ms=max(0, int(latency_ms or 0)),
            prompt_chars=max(0, int(prompt_chars or 0)),
            output_chars=max(0, int(output_chars or 0)),
            cases_count=max(0, int(cases_count or 0)),
            meta=safe_meta,
        )
    except Exception:
        # 审计写入失败不应影响主流程
        return
