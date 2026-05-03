"""
从 UI / POM 脚本工作空间提取执行后生成的 HTML 报告，归档到 UIPomTestReport。
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from django.core.files.base import ContentFile

if TYPE_CHECKING:
    from assistant.models import UIScriptExecution

logger = logging.getLogger(__name__)

MIN_HTML_BYTES = 200
MAX_HTML_BYTES = 50 * 1024 * 1024
MAX_REPORTS_PER_RUN = 20
MAX_WALK_DEPTH = 8
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
# 路径名含以下片段时优先保留（BeautifulReport 等常见目录）
PRIORITY_SUBSTRINGS = (
    "report",
    "beautiful",
    "summary",
    "result",
    "html",
    "测试报告",
)


def _walk_depth(root: Path, current: Path) -> int:
    try:
        return len(current.relative_to(root).parts)
    except ValueError:
        return 999


def discover_html_report_paths(
    workspace_abs: str,
    since_ts: Optional[float],
    until_ts: Optional[float],
) -> List[str]:
    """
    在工作空间内查找本次执行可能产生的 HTML 报告路径。
    since_ts / until_ts 为文件 mtime 的闭区间（秒级时间戳），可为 None 表示不限制该端。
    """
    root = Path(workspace_abs).resolve()
    if not root.is_dir():
        return []

    found: List[Tuple[str, float, int]] = []  # path, mtime, priority

    for dirpath, dirnames, filenames in os.walk(root):
        cur = Path(dirpath)
        depth = _walk_depth(root, cur)
        if depth > MAX_WALK_DEPTH:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES and not d.startswith(".")]

        for fn in filenames:
            low = fn.lower()
            if not (low.endswith(".html") or low.endswith(".htm")):
                continue
            full = str(Path(dirpath) / fn)
            try:
                st = os.stat(full)
            except OSError:
                continue
            if not (MIN_HTML_BYTES <= st.st_size <= MAX_HTML_BYTES):
                continue
            mt = st.st_mtime
            if since_ts is not None and mt < since_ts - 2:
                continue
            if until_ts is not None and mt > until_ts + 5:
                continue
            lp = full.lower()
            prio = sum(1 for s in PRIORITY_SUBSTRINGS if s in lp)
            found.append((full, mt, prio))

    if not found:
        return []

    found.sort(key=lambda x: (-x[2], -x[1], x[0]))

    seen_inodes: set = set()
    uniq: List[str] = []
    for path, _mt, _prio in found:
        try:
            inode = os.stat(path).st_ino
        except OSError:
            inode = None
        key = (inode, path) if inode is not None else path
        if key in seen_inodes:
            continue
        seen_inodes.add(key)
        uniq.append(path)
        if len(uniq) >= MAX_REPORTS_PER_RUN:
            break
    return uniq


def harvest_ui_pom_reports(execution: UIScriptExecution) -> int:
    """
    将本次执行在工作空间内产生的 HTML 报告复制到 media 并写入 UIPomTestReport。

    Returns:
        新建报告条数。
    """
    from assistant.models import UIPomTestReport

    script = execution.script
    wp = (script.workspace_path or "").strip()
    if not wp:
        return 0
    wp_abs = os.path.abspath(wp)
    if not os.path.isdir(wp_abs):
        logger.warning("harvest_ui_pom_reports: workspace 不存在 %s", wp_abs)
        return 0

    since_ts: Optional[float] = None
    until_ts: Optional[float] = None
    if execution.started_at:
        since_ts = execution.started_at.timestamp() - 120
    if execution.completed_at:
        until_ts = execution.completed_at.timestamp() + 180

    paths = discover_html_report_paths(wp_abs, since_ts, until_ts)
    if not paths and since_ts is not None:
        # 时钟偏差或报告略早于 started_at：放宽下界
        paths = discover_html_report_paths(
            wp_abs, since_ts - 3600, until_ts
        )
    if not paths:
        logger.info(
            "harvest_ui_pom_reports: 未发现 HTML 报告 execution_id=%s workspace=%s",
            execution.execution_id,
            wp_abs,
        )
        return 0

    created = 0
    for idx, src in enumerate(paths):
        rel = os.path.relpath(src, wp_abs).replace("\\", "/")
        base = os.path.basename(src) or f"report_{idx}.html"
        dest_name = f"run_{execution.id}_{idx}_{base}"
        title = f"{script.name} · {base}"
        if len(title) > 250:
            title = title[:247] + "…"

        try:
            with open(src, "rb") as fh:
                raw = fh.read()
        except OSError as e:
            logger.warning("harvest_ui_pom_reports: 读取失败 %s %s", src, e)
            continue

        if len(raw) < MIN_HTML_BYTES:
            continue

        try:
            rep = UIPomTestReport(
                execution=execution,
                script=script,
                title=title,
                source_relative_path=rel[:500],
                file_size=len(raw),
            )
            rep.report_file.save(dest_name, ContentFile(raw), save=True)
            created += 1
        except Exception:
            logger.exception(
                "harvest_ui_pom_reports: 保存失败 execution_id=%s file=%s",
                execution.execution_id,
                src,
            )
    if created:
        logger.info(
            "harvest_ui_pom_reports: 已归档 %s 份报告 execution_id=%s",
            created,
            execution.execution_id,
        )
    return created
