"""
从 Elasticsearch 拉取锚点附近的日志上下文，供同步诊断与异步工单草稿复用。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def fetch_es_context_for_anchor(
    *,
    server_id: int,
    anchor_text: str,
    anchor_ts: int | None,
    window_seconds: int,
    limit: int,
) -> tuple[list[str], dict[str, Any]]:
    """
    返回 (context_lines, meta)。

    meta 含：backend（es / fallback_no_anchor / fallback_es_error）、context_count、
    可选 es_error、resolved_ts。
    """
    context_lines: list[str] = []
    meta: dict[str, Any] = {"backend": "es", "context_count": 0}
    used_backend = "es"

    try:
        from server_logs.es_client import get_elasticsearch_client, get_server_logs_es_index

        es = get_elasticsearch_client()
        idx = get_server_logs_es_index()
    except Exception as e:
        meta["backend"] = "fallback_es_error"
        meta["es_error"] = str(e)[:300]
        meta["context_count"] = 0
        return context_lines, meta

    resolved_ts: int | None = int(anchor_ts) if anchor_ts is not None else None
    try:
        if resolved_ts is None:
            must = [{"term": {"server_id": server_id}}, {"match": {"message": {"query": anchor_text}}}]
            body = {"size": 1, "query": {"bool": {"must": must}}, "sort": [{"timestamp": {"order": "desc"}}]}
            r = es.search(index=idx, body=body)
            hits = (r.get("hits") or {}).get("hits") or []
            if hits:
                src = hits[0].get("_source") or {}
                if src.get("timestamp") is not None:
                    resolved_ts = int(src.get("timestamp"))

        if resolved_ts is not None:
            gte = resolved_ts - window_seconds * 1000
            lte = resolved_ts + window_seconds * 1000
            must = [
                {"term": {"server_id": server_id}},
                {"range": {"timestamp": {"gte": gte, "lte": lte}}},
            ]
            body = {
                "size": min(int(limit), 500),
                "query": {"bool": {"must": must}},
                "sort": [{"timestamp": {"order": "asc"}}],
            }
            r = es.search(index=idx, body=body)
            hits = (r.get("hits") or {}).get("hits") or []
            for h in hits:
                src = h.get("_source") or {}
                msg = (src.get("message") or "").rstrip("\n")
                ts = src.get("timestamp")
                if msg:
                    context_lines.append(f"[{ts}] {msg}")
        else:
            used_backend = "fallback_no_anchor"
    except Exception as e:
        used_backend = "fallback_es_error"
        meta["es_error"] = str(e)[:300]
        logger.debug("fetch_es_context_for_anchor failed: %s", meta["es_error"])

    meta["backend"] = used_backend
    meta["context_count"] = len(context_lines)
    meta["resolved_ts"] = resolved_ts
    return context_lines, meta
