from __future__ import annotations

import logging
import os
import re
import hashlib
from typing import Any, Dict, List

from django.conf import settings

from assistant.models import KnowledgeArticle

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "aitest_knowledge_articles"
_DOC_PREFIX = "ka_"
_chroma_client = None
_collection = None

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from chromadb.utils.embedding_functions import (
        DefaultEmbeddingFunction,
        SentenceTransformerEmbeddingFunction,
    )

    CHROMADB_AVAILABLE = True
except ImportError:  # pragma: no cover
    CHROMADB_AVAILABLE = False
    chromadb = None  # type: ignore
    ChromaSettings = None  # type: ignore
    DefaultEmbeddingFunction = None  # type: ignore
    SentenceTransformerEmbeddingFunction = None  # type: ignore


def _chroma_path() -> str:
    base_dir = getattr(settings, "BASE_DIR", os.getcwd())
    path = os.path.join(base_dir, "data", "chroma")
    os.makedirs(path, exist_ok=True)
    return path


def _build_embedding_function():
    """
    默认使用离线哈希嵌入，避免网络受限时模型下载失败。
    可通过 KNOWLEDGE_EMBED_MODE 切换：
    - hash（默认，完全离线）
    - chroma（Chroma 默认嵌入，可能触发模型下载）
    - sentence（sentence-transformers）
    """
    mode = (os.environ.get("KNOWLEDGE_EMBED_MODE", "hash") or "hash").strip().lower()
    if mode == "hash":
        class _HashEmbeddingFunction:
            def name(self) -> str:
                return "default"

            def __call__(self, input):
                texts = input if isinstance(input, list) else [input]
                out = []
                for t in texts:
                    raw = (t or "").encode("utf-8", errors="ignore")
                    # 128 维离线向量：sha256 循环扩展
                    vals = []
                    seed = raw or b"empty"
                    while len(vals) < 128:
                        seed = hashlib.sha256(seed).digest()
                        vals.extend([(b / 255.0) * 2.0 - 1.0 for b in seed])
                    out.append(vals[:128])
                return out

        return _HashEmbeddingFunction()
    if mode == "chroma":
        return DefaultEmbeddingFunction()
    model_name = os.environ.get("KNOWLEDGE_EMBED_MODEL", "all-MiniLM-L6-v2")
    try:
        return SentenceTransformerEmbeddingFunction(model_name=model_name)
    except Exception as exc:  # pragma: no cover
        logger.warning("SentenceTransformerEmbeddingFunction 初始化失败，回退默认嵌入: %s", exc)
        return DefaultEmbeddingFunction()


def get_collection():
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
            name=_COLLECTION_NAME,
            embedding_function=_build_embedding_function(),
            metadata={"hnsw:space": "cosine"},
        )
    except Exception as exc:  # pragma: no cover
        logger.exception("Knowledge Chroma collection 初始化失败: %s", exc)
        _collection = None
    return _collection


def _doc_id(article_id: int, chunk_index: int | None = None) -> str:
    if chunk_index is None:
        return f"{_DOC_PREFIX}{int(article_id)}"
    return f"{_DOC_PREFIX}{int(article_id)}_{int(chunk_index)}"


def _build_article_text(article: KnowledgeArticle) -> str:
    tags = article.tags if isinstance(article.tags, list) else []
    tags_text = ", ".join(str(t) for t in tags if str(t).strip())
    lines = [
        f"标题：{article.title or ''}",
        f"分类：{article.category or ''}",
        f"标签：{tags_text}",
        "正文：",
        article.markdown_content or "",
    ]
    return "\n".join(lines).strip()


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> List[str]:
    """
    优先使用 LangChain TextSplitter；不可用时回退字符窗口切分。
    """
    source = (text or "").strip()
    if not source:
        return []
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
        )
        docs = splitter.split_text(source)
        out = [x.strip() for x in docs if (x or "").strip()]
        if out:
            return out
    except Exception:
        pass
    if len(source) <= chunk_size:
        return [source]
    chunks: List[str] = []
    start = 0
    step = max(chunk_size - overlap, 1)
    total = len(source)
    while start < total:
        end = min(start + chunk_size, total)
        part = source[start:end].strip()
        if part:
            chunks.append(part)
        if end >= total:
            break
        start += step
    return chunks


class KnowledgeIndexer:
    """知识库向量索引器。"""

    @classmethod
    def index_article(cls, article_id: int) -> bool:
        col = get_collection()
        if col is None:
            return False
        article = KnowledgeArticle.objects.filter(pk=article_id, is_deleted=False).first()
        cls.delete_article(article_id)
        if article is None:
            return True
        doc_text = _build_article_text(article)
        chunks = _chunk_text(doc_text)
        if not chunks:
            return True
        metadata = {
            "article_id": int(article.id),
            "title": article.title or "",
            "category": article.category or "",
            "tags": ",".join(
                [str(t) for t in (article.tags if isinstance(article.tags, list) else [])]
            ),
        }
        try:
            ids = [_doc_id(article.id, i) for i, _ in enumerate(chunks)]
            metadatas = [{**metadata, "chunk_index": i} for i, _ in enumerate(chunks)]
            col.upsert(
                ids=ids,
                documents=[x[:12000] for x in chunks],
                metadatas=metadatas,
            )
            return True
        except Exception as exc:  # pragma: no cover
            logger.exception("KnowledgeIndexer upsert 失败: article_id=%s err=%s", article_id, exc)
            return False

    @classmethod
    def delete_article(cls, article_id: int):
        col = get_collection()
        if col is None:
            return
        try:
            col.delete(where={"article_id": int(article_id)})
        except Exception:
            pass

    @classmethod
    def reindex_all(cls) -> Dict[str, int]:
        total = 0
        success = 0
        for item in KnowledgeArticle.objects.filter(is_deleted=False).values_list("id", flat=True):
            total += 1
            if cls.index_article(int(item)):
                success += 1
        return {"total": total, "success": success, "failed": total - success}


class KnowledgeSearcher:
    """知识库语义搜索。"""

    @classmethod
    def _keyword_fallback_search(
        cls,
        query_text: str,
        top_k: int = 5,
        *,
        category: str | None = None,
        tag: str | None = None,
    ) -> List[Dict[str, Any]]:
        """
        向量检索不可用时回退关键词检索，避免接口 500 或空结果不可用。
        """
        q = (query_text or "").strip()
        if not q:
            return []
        tokens = [t for t in re.split(r"\s+", q) if t]
        if not tokens:
            tokens = [q]

        qs = KnowledgeArticle.objects.filter(is_deleted=False)
        if category:
            qs = qs.filter(category=str(category))
        if tag:
            qs = qs.filter(tags__contains=[str(tag)])

        ranked: List[Dict[str, Any]] = []
        for art in qs.order_by("-create_time")[:300]:
            text = f"{art.title or ''}\n{art.markdown_content or ''}".lower()
            tags = art.tags if isinstance(art.tags, list) else []
            tags_text = " ".join(str(x).lower() for x in tags)
            hit = 0
            for tk in tokens:
                k = tk.lower()
                if k and (k in text or k in tags_text):
                    hit += 1
            if hit <= 0:
                continue
            score = round(hit / max(len(tokens), 1), 4)
            ranked.append(
                {
                    "article_id": int(art.id),
                    "title": art.title or "",
                    "category": art.category or "",
                    "tags": tags,
                    "distance": None,
                    "score": score,
                    "document": _build_article_text(art)[:12000],
                    "retrieve_mode": "keyword_fallback",
                }
            )
        ranked.sort(
            key=lambda x: (
                float(x.get("score") or 0.0),
                int(x.get("article_id") or 0),
            ),
            reverse=True,
        )
        return ranked[: max(int(top_k), 1)]

    @classmethod
    def search_similar(
        cls,
        query_text: str,
        top_k: int = 5,
        *,
        category: str | None = None,
        tag: str | None = None,
        min_score: float | None = None,
    ) -> List[Dict[str, Any]]:
        col = get_collection()
        if col is None:
            logger.warning("KnowledgeSearcher 向量检索不可用，回退关键词检索")
            return cls._keyword_fallback_search(
                query_text,
                top_k=top_k,
                category=category,
                tag=tag,
            )
        q = (query_text or "").strip()
        if not q:
            return []
        try:
            where = None
            if category:
                where = {"category": str(category)}
            res = col.query(
                query_texts=[q],
                n_results=max(int(top_k), 1),
                where=where,
                include=["documents", "distances", "metadatas"],
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("KnowledgeSearcher query failed: %s", exc)
            return cls._keyword_fallback_search(
                query_text,
                top_k=top_k,
                category=category,
                tag=tag,
            )
        docs = (res.get("documents") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        out: List[Dict[str, Any]] = []
        best_by_article: Dict[int, Dict[str, Any]] = {}
        for i, md in enumerate(metas):
            meta = md if isinstance(md, dict) else {}
            title = meta.get("title", "")
            category = meta.get("category", "")
            tags = [x for x in str(meta.get("tags", "")).split(",") if x]
            dist = dists[i] if i < len(dists) else None
            score = (1.0 - float(dist)) if dist is not None else None
            item = {
                "article_id": int(meta.get("article_id")) if meta.get("article_id") else None,
                "title": title,
                "category": category,
                "tags": tags,
                "distance": dist,
                "score": score,
                "document": docs[i] if i < len(docs) else "",
            }
            if tag and tag not in tags:
                continue
            if min_score is not None and score is not None and score < float(min_score):
                continue
            article_id = item["article_id"]
            if article_id is None:
                continue
            row = {
                "article_id": article_id,
                "title": item["title"],
                "category": item["category"],
                "tags": item["tags"],
                "distance": item["distance"],
                "score": item["score"],
                "document": item["document"],
                "retrieve_mode": "semantic",
            }
            old = best_by_article.get(article_id)
            old_score = float(old.get("score") or -1) if old else -1
            new_score = float(row.get("score") or -1)
            if old is None or new_score > old_score:
                best_by_article[article_id] = row
        out = sorted(
            best_by_article.values(),
            key=lambda x: float(x.get("score") or 0.0),
            reverse=True,
        )[: max(int(top_k), 1)]
        if not out:
            # 语义检索结果为空时，回退关键词检索提升可用性。
            return cls._keyword_fallback_search(
                query_text,
                top_k=top_k,
                category=category,
                tag=tag,
            )
        return out
