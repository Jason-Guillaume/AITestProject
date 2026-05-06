"""
资产中心 (Asset Hub) 与执行中心共用的数据装配：以 UIScriptUpload 为登记基线，并扫描工作区物理文件（Shadow Sync）。

执行中心树使用的项目列表与 list 接口一致；本模块在此基础上展开工作区文件行。
"""
from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

OVERVIEW_NODE_ID = "__asset_overview__"
TEXT_LIKE_EXT = {".py", ".json", ".jar", ".yaml", ".yml", ".xml", ".properties"}


def _norm_rel(p: str) -> str:
    if not p:
        return ""
    return p.replace("\\", "/").strip().lstrip("/")


def _list_workspace_files(workspace_path: str) -> List[str]:
    if not workspace_path or not os.path.isdir(workspace_path):
        return []
    out: List[str] = []
    try:
        for root, _dirs, filenames in os.walk(workspace_path):
            for filename in filenames:
                full = os.path.join(root, filename)
                rel = os.path.relpath(full, workspace_path)
                out.append(rel.replace("\\", "/"))
    except OSError as e:
        logger.warning("工作区扫描失败: %s", e)
    return out


def _sync_state_for_file(
    rel_norm: str, entry_point: Optional[str]
) -> str:
    en = _norm_rel(entry_point or "")
    if en and _norm_rel(rel_norm) == en:
        return "registered"
    ext = os.path.splitext(rel_norm)[1].lower()
    if ext in TEXT_LIKE_EXT or ext == "":
        return "pending_init"
    return "pending_init"


def build_asset_hub_overview(platform: str) -> Dict[str, Any]:
    """
    构建资产中心一次加载所需：Module 树 + 全量行（含物理目录多出的待初始化项）。

    platform: web | mobile | api
    当前实现：web 使用 UIScriptUpload + 工作区扫描；mobile/api 返回仅占位结构（后续接入）。
    """
    from assistant.models import UIScriptUpload

    plat = (platform or "web").lower()
    tree: List[Dict[str, Any]] = [
        {
            "id": OVERVIEW_NODE_ID,
            "label": "全部脚本 (总览)",
            "children": [],
        }
    ]
    rows: List[Dict[str, Any]] = []

    if plat == "mobile":
        return {"platform": plat, "tree": tree, "rows": [], "scanned_projects": 0}
    if plat == "api":
        return {"platform": plat, "tree": tree, "rows": [], "scanned_projects": 0}

    qs = (
        UIScriptUpload.objects.filter(is_deleted=False)
        .order_by("-updated_at")
    )
    scanned = 0
    for script in qs:
        scanned += 1
        proj_id = f"proj-{script.id}"
        tree.append(
            {
                "id": proj_id,
                "label": script.name,
                "children": [],
            }
        )

        if script.workspace_path and os.path.isdir(script.workspace_path):
            files = _list_workspace_files(script.workspace_path)
            seen: set[str] = set()
            for rel in sorted(files):
                rel_norm = rel.replace("\\", "/")
                if rel_norm in seen:
                    continue
                seen.add(rel_norm)
                st = _sync_state_for_file(rel_norm, script.entry_point)
                rows.append(
                    {
                        "id": f"file-{script.id}-{_safe_id_segment(rel_norm)}",
                        "backendId": script.id,
                        "moduleId": proj_id,
                        "moduleLabel": script.name,
                        "name": os.path.basename(rel_norm) or rel_norm,
                        "relPath": rel_norm,
                        "owner": "",
                        "lastSuccessRate": 0,
                        "environment": (script.folder or "/") or "/",
                        "platform": "web",
                        "lastResult": "unknown",
                        "isActive": bool(script.is_active),
                        "syncState": st,
                        "techStack": script.language or "PYTHON",
                        "architecture": script.script_type or "LINEAR",
                    }
                )
        else:
            # 无工作区：仍以 DB 登记展示一条入口占位，避免「脚本消失」
            ep = script.entry_point or f"{script.name}"
            rows.append(
                {
                    "id": f"db-{script.id}-entry",
                    "backendId": script.id,
                    "moduleId": proj_id,
                    "moduleLabel": script.name,
                    "name": os.path.basename(ep) or script.name,
                    "relPath": _norm_rel(ep) or ep,
                    "owner": "",
                    "lastSuccessRate": 0,
                    "environment": (script.folder or "/") or "/",
                    "platform": "web",
                    "lastResult": "unknown",
                    "isActive": bool(script.is_active),
                    "syncState": "registered",
                    "techStack": script.language or "PYTHON",
                    "architecture": script.script_type or "LINEAR",
                }
            )

    return {
        "platform": plat,
        "tree": tree,
        "rows": rows,
        "scanned_projects": scanned,
    }


def _safe_id_segment(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__").replace(" ", "_")[:180]


def sync_asset_hub_shadow(platform: str) -> Dict[str, Any]:
    """
    一键同步：当前与 build 一致的全量重扫；后续可在此写回 DB、补登记等。
    """
    payload = build_asset_hub_overview(platform)
    payload["sync"] = True
    payload["message"] = "已重新扫描物理目录并与数据库条目合并"
    return payload
