"""
测试用例语义向量：ChromaDB（本地持久化）+ 智谱 embedding-3。
"""

from __future__ import annotations

import logging
import os
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

_COLLECTION = "aitesta_test_cases"
_ID_PREFIX = "case_"

_chroma_client = None
_collection = None

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    CHROMADB_AVAILABLE = True
except ImportError:  # pragma: no cover
    CHROMADB_AVAILABLE = False
    chromadb = None  # type: ignore
    ChromaSettings = None  # type: ignore


def _chroma_path() -> str:
    root = getattr(settings, "BASE_DIR", os.getcwd())
    path = os.path.join(root, "data", "chroma")
    os.makedirs(path, exist_ok=True)
    return path


def get_collection():
    """懒加载 Chroma collection；不可用时返回 None。"""
    global _chroma_client, _collection
    if not CHROMADB_AVAILABLE:
        return None
    if _collection is not None:
        return _collection
    try:
        _chroma_client = chromadb.PersistentClient(
            path=_chroma_path(),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _chroma_client.get_or_create_collection(
            name=_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    except Exception as e:  # pragma: no cover
        logger.exception("ChromaDB 初始化失败: %s", e)
        _collection = None
    return _collection


def _doc_id(case_id: int) -> str:
    return f"{_ID_PREFIX}{int(case_id)}"


def build_testcase_embed_text(case) -> str:
    """用例名称 + 步骤描述（用于嵌入）。"""
    from testcase.models import TestCase

    if not isinstance(case, TestCase):
        return ""
    parts = [f"用例名称：{case.case_name or ''}".strip()]
    parts.append(f"等级：{case.level or ''}")
    if getattr(case, "test_type", None) == "api":
        try:
            a = case.apitestcase
            parts.append(
                f"API：{(a.api_method or 'GET').strip()} {(a.api_url or '').strip()}".strip()
            )
        except Exception:
            pass
    try:
        steps = case.steps.all().order_by("step_number")
        for s in steps:
            line = f"步骤{s.step_number}：{(s.step_desc or '').strip()}"
            if (s.expected_result or "").strip():
                line += f" 预期：{s.expected_result.strip()}"
            parts.append(line)
    except Exception:
        pass
    return "\n".join(p for p in parts if p).strip()


def index_test_case(case_id: int) -> bool:
    """写入或更新单条用例向量；软删除或无效用例则删除向量。"""
    col = get_collection()
    if col is None:
        return False
    from testcase.models import TestCase

    try:
        tc = (
            TestCase.objects.filter(pk=case_id, is_deleted=False)
            .select_related("module", "apitestcase")
            .first()
        )
    except Exception as e:
        logger.warning("index_test_case load %s: %s", case_id, e)
        return False

    did = _doc_id(case_id)
    if tc is None or not tc.is_valid:
        try:
            col.delete(ids=[did])
        except Exception:
            pass
        return True

    text = build_testcase_embed_text(tc)
    if not text:
        try:
            col.delete(ids=[did])
        except Exception:
            pass
        return True

    mid = tc.module_id
    if mid is None:
        try:
            col.delete(ids=[did])
        except Exception:
            pass
        return True

    meta: dict[str, Any] = {
        "case_id": int(tc.id),
        "module_id": str(int(mid)),
    }
    try:
        from assistant.embeddings_zhipu import embed_single

        vec = embed_single(text)
        if not vec:
            logger.warning("嵌入为空，跳过 case_id=%s", case_id)
            return False
        col.upsert(
            ids=[did],
            embeddings=[vec],
            documents=[text[:8000]],
            metadatas=[meta],
        )
        return True
    except Exception as e:
        logger.exception("index_test_case upsert %s: %s", case_id, e)
        return False


def delete_test_case_embedding(case_id: int) -> None:
    col = get_collection()
    if col is None:
        return
    try:
        col.delete(ids=[_doc_id(case_id)])
    except Exception:
        pass


def search_similar_by_module(
    query_embedding: list[float],
    module_id: int,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    在同一 module_id 下检索最相似文档。
    返回 [{"case_id", "document", "distance"}, ...]
    """
    col = get_collection()
    if col is None or not query_embedding:
        return []
    try:
        res = col.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"module_id": str(int(module_id))},
            include=["documents", "distances", "metadatas"],
        )
    except Exception as e:
        logger.warning("Chroma query failed: %s", e)
        return []

    out: list[dict[str, Any]] = []
    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    for i, _sid in enumerate(ids):
        meta = metas[i] if i < len(metas) else {}
        cid = meta.get("case_id") if isinstance(meta, dict) else None
        try:
            cid = int(cid) if cid is not None else None
        except (TypeError, ValueError):
            cid = None
        out.append(
            {
                "case_id": cid,
                "document": docs[i] if i < len(docs) else "",
                "distance": dists[i] if i < len(dists) else None,
            }
        )
    return out
