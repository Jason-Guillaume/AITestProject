"""RAG：知识库语义检索 + Prompt 组装。"""

from __future__ import annotations

import logging
from django.conf import settings

from assistant.knowledge_rag import KnowledgeSearcher

logger = logging.getLogger(__name__)

_RAG_CONTEXT_TEMPLATE = """

## Knowledge Context (Top-{top_k})
The following are semantically relevant snippets retrieved from the knowledge base. Use them as context and guidance.

{context_block}

## Task Input
- module_name: {module_name}
- requirement:
{requirement}
- api_spec:
{api_spec}

## RAG Rules (mandatory)
1. Prioritize retrieved knowledge context when designing cases.
2. If context conflicts with requirement, prioritize requirement and explain assumptions in case steps/expected results.
3. Output must still strictly follow the JSON schema required by the system prompt.
4. All natural language values in JSON must be Simplified Chinese.
"""


def build_rag_system_prompt(
    base_system: str,
    requirement: str,
    module_name: str | None = None,
    api_spec: str | None = None,
    top_k: int = 5,
) -> str:
    q = (requirement or "").strip()
    if not q:
        return base_system
    try:
        results = KnowledgeSearcher.search_similar(q, top_k=max(1, int(top_k)))
    except Exception as exc:  # pragma: no cover
        logger.warning("RAG: 知识库检索失败，跳过上下文拼接: %s", exc)
        return base_system

    if not results:
        context_block = "（知识库未检索到高相关片段，请依据需求与接口定义生成。）"
    else:
        parts = []
        max_context_chars = max(200, int(getattr(settings, "RAG_MAX_CONTEXT_CHARS", 1200)))
        for i, item in enumerate(results, 1):
            title = item.get("title") or "未命名文档"
            category = item.get("category") or "-"
            score = item.get("score")
            score_text = f"{float(score):.4f}" if score is not None else "-"
            snippet = (item.get("document") or "").strip()
            if len(snippet) > max_context_chars:
                snippet = snippet[:max_context_chars] + "\n...(truncated)"
            parts.append(
                f"[Context {i}] title={title} category={category} score={score_text}\n{snippet}"
            )
        context_block = "\n\n".join(parts)

    api_spec_clip = (api_spec or "").strip()
    if len(api_spec_clip) > 6000:
        api_spec_clip = api_spec_clip[:6000] + "\n...(truncated)"
    return base_system + _RAG_CONTEXT_TEMPLATE.format(
        top_k=max(1, int(top_k)),
        context_block=context_block,
        module_name=(module_name or "").strip() or "未指定",
        requirement=q,
        api_spec=api_spec_clip or "（未提供）",
    )


def is_all_covered_output(raw: str) -> bool:
    t = (raw or "").strip()
    if t == "[ALL_COVERED]":
        return True
    if t.replace("\n", "").replace("\r", "") == "[ALL_COVERED]":
        return True
    return False
