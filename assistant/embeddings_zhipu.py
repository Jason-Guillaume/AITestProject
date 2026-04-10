"""
智谱 OpenAI 兼容 Embedding：model embedding-3
"""

from __future__ import annotations

import logging
from typing import Sequence

logger = logging.getLogger(__name__)

ZHIPU_EMBEDDING_MODEL = "embedding-3"

try:
    from openai import OpenAI

    OPENAI_EMBED_AVAILABLE = True
except ImportError:  # pragma: no cover
    OPENAI_EMBED_AVAILABLE = False
    OpenAI = None  # type: ignore


def embed_single(
    text: str,
    api_key: str,
    base_url: str,
) -> list[float] | None:
    """单条文本量化为向量；失败返回 None。"""
    t = (text or "").strip()
    if not t or not OPENAI_EMBED_AVAILABLE or not api_key:
        return None
    base = (base_url or "").rstrip("/")
    try:
        client = OpenAI(api_key=api_key, base_url=base, timeout=60.0)
        r = client.embeddings.create(model=ZHIPU_EMBEDDING_MODEL, input=t[:8000])
        data = r.data[0].embedding
        return list(data) if data is not None else None
    except Exception as e:
        logger.warning("embed_single failed: %s", e)
        return None


def embed_batch(
    texts: Sequence[str],
    api_key: str,
    base_url: str,
) -> list[list[float] | None]:
    out: list[list[float] | None] = []
    for t in texts:
        out.append(embed_single(t, api_key, base_url))
    return out
