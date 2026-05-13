"""
智谱 OpenAI 兼容 Embedding：model embedding-3
"""

from __future__ import annotations

import hashlib
import logging
from typing import Sequence

from django.core.cache import cache

logger = logging.getLogger(__name__)

ZHIPU_EMBEDDING_MODEL = "embedding-3"
_EMBED_CACHE_TTL = 86400

try:
    from openai import OpenAI

    OPENAI_EMBED_AVAILABLE = True
except ImportError:  # pragma: no cover
    OPENAI_EMBED_AVAILABLE = False
    OpenAI = None  # type: ignore


def _cache_key(text: str) -> str:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"embed:{ZHIPU_EMBEDDING_MODEL}:{h}"


def embed_single(
    text: str,
    api_key: str,
    base_url: str,
) -> list[float] | None:
    t = (text or "").strip()
    if not t or not OPENAI_EMBED_AVAILABLE or not api_key:
        return None

    ck = _cache_key(t)
    try:
        cached = cache.get(ck)
        if cached is not None:
            return cached
    except Exception:
        pass

    base = (base_url or "").rstrip("/")
    try:
        client = OpenAI(api_key=api_key, base_url=base, timeout=60.0)
        r = client.embeddings.create(model=ZHIPU_EMBEDDING_MODEL, input=t[:8000])
        data = r.data[0].embedding
        vec = list(data) if data is not None else None
        if vec is not None:
            try:
                cache.set(ck, vec, _EMBED_CACHE_TTL)
            except Exception:
                pass
        return vec
    except Exception as e:
        logger.warning("embed_single failed: %s", e)
        return None


def embed_batch(
    texts: Sequence[str],
    api_key: str,
    base_url: str,
) -> list[list[float] | None]:
    uncached: list[tuple[int, str]] = []
    results: list[list[float] | None] = [None] * len(texts)

    for i, t in enumerate(texts):
        stripped = (t or "").strip()
        if not stripped:
            results[i] = None
            continue
        ck = _cache_key(stripped)
        try:
            cached = cache.get(ck)
            if cached is not None:
                results[i] = cached
                continue
        except Exception:
            pass
        uncached.append((i, stripped))

    if uncached and OPENAI_EMBED_AVAILABLE and api_key:
        base = (base_url or "").rstrip("/")
        batch_size = 20
        for start in range(0, len(uncached), batch_size):
            chunk = uncached[start : start + batch_size]
            inputs = [t for _, t in chunk]
            try:
                client = OpenAI(api_key=api_key, base_url=base, timeout=120.0)
                r = client.embeddings.create(
                    model=ZHIPU_EMBEDDING_MODEL,
                    input=[t[:8000] for t in inputs],
                )
                for j, item in enumerate(r.data):
                    vec = list(item.embedding) if item.embedding is not None else None
                    orig_idx = chunk[j][0]
                    results[orig_idx] = vec
                    if vec is not None:
                        try:
                            cache.set(_cache_key(inputs[j]), vec, _EMBED_CACHE_TTL)
                        except Exception:
                            pass
            except Exception as e:
                logger.warning("embed_batch chunk failed: %s", e)
                for orig_idx, _ in chunk:
                    if results[orig_idx] is None:
                        results[orig_idx] = None

    return results
