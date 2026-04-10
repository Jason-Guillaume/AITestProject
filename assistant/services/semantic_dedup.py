from __future__ import annotations

import math
from typing import Any

from django.conf import settings

from assistant.embeddings_zhipu import embed_batch

# 语义去重阈值：相似度 >= 阈值视为重复
AI_CASE_SEMANTIC_DUP_THRESHOLD = float(
    getattr(settings, "AI_CASE_SEMANTIC_DUP_THRESHOLD", 0.85)
)


def _build_case_semantic_text(case_item: dict[str, Any]) -> str:
    """
    组装用于向量化的文本：
    - 标题（case_name/title/name）
    - 步骤（steps）
    """
    title = str(
        case_item.get("case_name")
        or case_item.get("title")
        or case_item.get("name")
        or ""
    ).strip()
    steps = str(case_item.get("steps") or "").strip()
    return f"标题：{title}\n步骤：{steps}".strip()


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    余弦相似度，返回 [0,1]（异常输入时降级 0.0）。
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b):
        dot += a * b
        norm_a += a * a
        norm_b += b * b
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def semantic_deduplicate_cases(
    generated_cases: list[dict[str, Any]],
    existing_cases: list[dict[str, Any]],
    *,
    api_key: str,
    base_url: str,
    threshold: float | None = None,
) -> list[dict[str, Any]]:
    """
    对新生成用例做“与库内已存在用例”的语义去重。
    规则：若新用例与任一已存在用例的最高相似度 >= threshold，则剔除。
    """
    if not generated_cases:
        return []
    if not existing_cases:
        return generated_cases
    th = (
        AI_CASE_SEMANTIC_DUP_THRESHOLD
        if threshold is None
        else max(0.0, min(1.0, float(threshold)))
    )

    generated_texts = [_build_case_semantic_text(x) for x in generated_cases]
    existing_texts = [_build_case_semantic_text(x) for x in existing_cases]

    generated_vectors = embed_batch(generated_texts, api_key=api_key, base_url=base_url)
    existing_vectors = embed_batch(existing_texts, api_key=api_key, base_url=base_url)

    # 若向量服务不可用/调用失败，降级返回原结果，避免影响主流程可用性
    if not existing_vectors or all(v is None for v in existing_vectors):
        return generated_cases

    kept: list[dict[str, Any]] = []
    for idx, item in enumerate(generated_cases):
        gv = generated_vectors[idx] if idx < len(generated_vectors) else None
        if not gv:
            kept.append(item)
            continue
        max_sim = 0.0
        for ev in existing_vectors:
            if not ev:
                continue
            sim = cosine_similarity(gv, ev)
            if sim > max_sim:
                max_sim = sim
        if max_sim < th:
            kept.append(item)
    return kept
