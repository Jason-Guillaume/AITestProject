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
