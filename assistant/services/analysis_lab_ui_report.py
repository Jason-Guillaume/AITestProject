"""
Analysis Lab 深度报告：基于 UIScriptExecution + 工作区截图 + 遥测日志聚合。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")
SKIP_DIR_NAMES = frozenset(
    {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".pytest_cache",
        "allure-results",
        ".idea",
        ".mypy_cache",
    }
)
MAX_WALK_DEPTH = 10
MAX_IMAGES = 24


def _walk_depth(root: Path, current: Path) -> int:
    try:
        return len(current.relative_to(root).parts)
    except ValueError:
        return 999


def discover_workspace_images(
    workspace_abs: str,
    since_ts: Optional[float],
    until_ts: Optional[float],
) -> List[Tuple[str, float]]:
    """
    返回 (绝对路径, mtime) 列表，按 mtime 升序（步骤时间线）。
    """
    root = Path(workspace_abs).resolve()
    if not root.is_dir():
        return []

    found: List[Tuple[str, float]] = []

    for dirpath, dirnames, filenames in os.walk(str(root)):
        cur = Path(dirpath)
        depth = _walk_depth(root, cur)
        if depth > MAX_WALK_DEPTH:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES and not d.startswith(".")]

        for fn in filenames:
            low = fn.lower()
            if not low.endswith(IMAGE_EXT):
                continue
            full = str((cur / fn).resolve())
            try:
                if not str(Path(full).resolve()).startswith(str(root)):
                    continue
            except OSError:
                continue
            try:
                st = os.stat(full)
            except OSError:
                continue
            mt = st.st_mtime
            if since_ts is not None and mt < since_ts - 5:
                continue
            if until_ts is not None and mt > until_ts + 10:
                continue
            found.append((full, mt))

    found.sort(key=lambda x: x[1])
    return found[:MAX_IMAGES]


def workspace_relpath(workspace_abs: str, file_abs: str) -> str:
    root = Path(workspace_abs).resolve()
    target = Path(file_abs).resolve()
    rel = os.path.relpath(str(target), str(root))
    return rel.replace("\\", "/")


def resolve_safe_workspace_file(workspace_abs: str, relpath: str) -> Optional[str]:
    """relpath 使用 POSIX 风格相对路径；解析失败或越界则返回 None。"""
    if not workspace_abs or not relpath:
        return None
    raw = str(relpath).strip().replace("\\", "/")
    if raw.startswith("/") or ".." in Path(raw).parts:
        return None
    root = Path(workspace_abs).resolve()
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    low = candidate.suffix.lower()
    if low not in IMAGE_EXT:
        return None
    return str(candidate)


def build_stack_trace(error_message: str, logs: List[Dict[str, Any]], max_chars: int = 8000) -> str:
    parts: List[str] = []
    em = (error_message or "").strip()
    if em:
        parts.append(em)

    stderr_lines: List[str] = []
    for entry in logs or []:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("type") or "") != "stderr":
            continue
        msg = str(entry.get("message") or "").rstrip()
        if msg:
            stderr_lines.append(msg)

    if stderr_lines:
        parts.append("\n--- stderr (telemetry, 最近 50 条) ---\n")
        parts.append("\n".join(stderr_lines[-50:]))

    text = "\n".join(parts).strip()
    if len(text) > max_chars:
        return text[: max_chars - 20] + "\n…(truncated)"
    return text or "（暂无错误堆栈：执行成功或未写入 stderr）"


def depth_report_payload(
    *,
    execution: Any,
    logs: List[Dict[str, Any]],
    api_reports_id: int,
) -> Dict[str, Any]:
    from assistant.models import UIScriptExecution

    st = str(getattr(execution, "status", "") or "")
    if st in (UIScriptExecution.STATUS_PENDING, UIScriptExecution.STATUS_RUNNING):
        report_status = "generating"
    else:
        report_status = "ready"

    script = getattr(execution, "script", None)
    wp = (getattr(script, "workspace_path", None) or "").strip()
    workspace_abs = os.path.abspath(wp) if wp else ""

    since_ts: Optional[float] = None
    until_ts: Optional[float] = None
    if execution.started_at:
        since_ts = execution.started_at.timestamp() - 120
    if execution.completed_at:
        until_ts = execution.completed_at.timestamp() + 180

    images: List[Tuple[str, float]] = []
    if workspace_abs and os.path.isdir(workspace_abs):
        images = discover_workspace_images(workspace_abs, since_ts, until_ts)
        if not images and since_ts is not None:
            images = discover_workspace_images(workspace_abs, since_ts - 3600, until_ts)

    stack_trace = build_stack_trace(getattr(execution, "error_message", "") or "", logs)

    steps: List[Dict[str, Any]] = []
    step_status = "success" if st == UIScriptExecution.STATUS_SUCCESS else ("failed" if st in (UIScriptExecution.STATUS_FAILED, UIScriptExecution.STATUS_TIMEOUT) else "warning")

    if images and workspace_abs:
        for i, (abs_path, _mt) in enumerate(images, start=1):
            rel = workspace_relpath(workspace_abs, abs_path)
            title = Path(abs_path).name
            steps.append(
                {
                    "id": str(i),
                    "order": i,
                    "title": title,
                    "status": "success",
                    "relpath": rel,
                    "screenshot_url": None,
                    "subtitle": rel,
                }
            )

    if not steps:
        steps.append(
            {
                "id": "1",
                "order": 1,
                "title": "执行遥测摘要",
                "status": step_status if st != UIScriptExecution.STATUS_CANCELLED else "warning",
                "screenshot_url": None,
                "subtitle": getattr(script, "name", "") or "",
            }
        )

    return {
        "report_id": str(api_reports_id),
        "status": report_status,
        "execution": {
            "id": execution.id,
            "execution_id": execution.execution_id,
            "status": execution.status,
            "return_code": execution.return_code,
            "script_name": getattr(script, "name", "") if script else "",
            "error_message": (execution.error_message or "")[:2000],
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        },
        "steps": steps,
        "stack_trace": stack_trace,
        "video_url": None,
    }
