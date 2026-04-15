"""
由日志 AI 工单草稿在后台创建 TestDefect（与 defect.views.perform_create 编号规则对齐）。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django.db import transaction

if TYPE_CHECKING:
    from defect.models import TestDefect
    from server_logs.models import LogAutoTicketJob as LogAutoTicketJobType

logger = logging.getLogger(__name__)

# 仅当调用方传入对应关键字参数时，才覆盖任务上已保存的缺陷关联字段。
_MISSING = object()


def _clamp_severity(v: Any) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        return 3
    return max(1, min(4, n))


def _clamp_priority(v: Any) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        return 2
    return max(1, min(3, n))


def _build_defect_content(draft: dict[str, Any]) -> str:
    parts: list[str] = []
    sm = (draft.get("summary_markdown") or "").strip()
    if sm:
        parts.append("## 摘要\n\n" + sm)
    steps = draft.get("reproduction_steps") or []
    if isinstance(steps, list) and steps:
        lines = "\n".join(
            f"{i + 1}. {s}"
            for i, s in enumerate(str(x).strip() for x in steps if str(x).strip())
        )
        parts.append("## 复现 / 验证步骤\n\n" + lines)
    env = (draft.get("environment_notes") or "").strip()
    if env:
        parts.append("## 环境说明\n\n" + env)
    parts.append("\n---\n*由服务器日志「AI 工单草稿」异步生成。*")
    return "\n\n".join(parts).strip()


def create_test_defect_from_auto_ticket(
    job: "LogAutoTicketJobType",
    draft: dict[str, Any],
    *,
    defect_handler: Any = _MISSING,
    defect_release_version: Any = _MISSING,
    defect_module: Any = _MISSING,
) -> tuple["TestDefect | None", str | None]:
    """
    使用任务上保存的处理人 / 版本 / 模块偏好创建缺陷；处理人未指定则默认任务发起人。

    传入 ``defect_handler=…`` 等关键字参数时，覆盖任务表中的对应字段（用于 REST 补建）。

    返回 (实例, None) 或 (None, 错误信息)。
    """
    from defect.models import TestDefect

    if not isinstance(draft, dict):
        return None, "草稿数据无效。"

    title = (draft.get("title") or "").strip() or "日志异常（AI 草稿）"
    title = title[:255]

    if defect_handler is _MISSING:
        handler = getattr(job, "defect_handler", None) or job.user
    else:
        handler = defect_handler or job.user
    if handler is None:
        return None, "无法确定缺陷处理人。"

    if defect_release_version is _MISSING:
        release_version = getattr(job, "defect_release_version", None)
    else:
        release_version = defect_release_version

    if defect_module is _MISSING:
        module = getattr(job, "defect_module", None)
    else:
        module = defect_module

    try:
        with transaction.atomic():
            last = TestDefect.objects.order_by("-id").first()
            next_id = 1 if not last else (last.id + 1)
            defect_no = f"DEF-{next_id:05d}"

            obj = TestDefect.objects.create(
                defect_no=defect_no,
                defect_name=title,
                release_version=release_version,
                severity=_clamp_severity(draft.get("severity")),
                priority=_clamp_priority(draft.get("priority")),
                status=1,
                handler=handler,
                module=module,
                defect_content=_build_defect_content(draft),
                creator=job.user,
                updater=job.user,
            )
            return obj, None
    except Exception as e:
        logger.exception(
            "create_test_defect_from_auto_ticket failed job_id=%s",
            getattr(job, "pk", None),
        )
        return None, str(e)[:2000]
