"""
基于日志上下文生成「缺陷工单草稿」结构化 JSON（供 Celery / REST 异步任务使用）。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_JSON_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE | re.MULTILINE)


def _strip_code_fences(raw: str) -> str:
    s = (raw or "").strip()
    s = _JSON_FENCE.sub("", s).strip()
    return s


def analyze_log_ticket_draft(
    *,
    anchor_text: str,
    context_lines: list[str],
    server_name: str | None,
    time_window_seconds: int,
    api_key_override: str = "",
    api_base_override: str = "",
    model_override: str = "",
) -> tuple[dict[str, Any] | None, str | None]:
    """
    调用大模型输出严格 JSON；成功返回 (dict, None)，失败返回 (None, error)。
    """
    try:
        from assistant.views import (
            OPENAI_SDK_AVAILABLE,
            APIConnectionError,
            APIError,
            APITimeoutError,
            AuthenticationError,
            OpenAI,
            _get_active_ai_model_credentials,
            _normalize_openai_sdk_base_url,
            _resolve_openai_target,
            ZHIPU_DEFAULT_API_BASE,
        )
    except Exception as e:  # pragma: no cover
        logger.exception("import assistant.views failed")
        return None, f"AI 模块加载失败：{e}"

    if not OPENAI_SDK_AVAILABLE:
        return None, "未安装 openai SDK，请执行 pip install openai 后重试。"

    key = (api_key_override or "").strip()
    base = (api_base_override or "").strip()
    model = (model_override or "").strip()
    if not key:
        k2, b2, m2 = _get_active_ai_model_credentials()
        key = k2 or ""
        base = base or (b2 or "")
        model = model or (m2 or "")
    if not key:
        return None, "未配置 AI：请在系统管理保存模型配置，或在请求中传入 api_key。"

    model, base = _resolve_openai_target(model or "glm-4.7-flash", base or ZHIPU_DEFAULT_API_BASE)
    base = _normalize_openai_sdk_base_url(base, model).rstrip("/")

    ctx = "\n".join([ln for ln in (context_lines or []) if (ln or "").strip()])
    head = (
        f"主机：{server_name}\n时间窗口：前后 {int(time_window_seconds)} 秒\n"
        if server_name
        else f"时间窗口：前后 {int(time_window_seconds)} 秒\n"
    )
    combined = (
        head
        + "\n【上下文日志】\n"
        + (ctx if ctx else "(无上下文)")
        + "\n\n【用户选中 / 锚点片段】\n"
        + ((anchor_text or "").strip() or "(空)")
    )

    schema_hint = """只输出一个 JSON 对象，不要 Markdown，不要代码块。字段要求：
{
  "title": "string, 缺陷标题，<=80字",
  "severity": 1-4 整数，含义 1致命 2严重 3一般 4建议",
  "priority": 1-3 整数，含义 1高 2中 3低",
  "summary_markdown": "string, 现象与影响，Markdown",
  "reproduction_steps": ["string", "..."],
  "environment_notes": "string, 可选，运行环境与版本线索"
}"""

    system = (
        "你是测试与运维联合专家，需要根据日志生成「缺陷单草稿」。"
        "严禁编造日志中不存在的信息；不确定的内容写入 environment_notes 并标明不确定。"
        + schema_hint
    )
    user_content = "请根据以下日志材料生成工单草稿 JSON：\n\n```text\n" + combined.strip() + "\n```"

    try:
        client = OpenAI(api_key=key, base_url=base, timeout=120.0)
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            max_tokens=4096,
            temperature=0.15,
        )
        choice = completion.choices[0].message
        text = (getattr(choice, "content", None) or "").strip()
        if not text:
            return None, "模型未返回有效内容。"
        cleaned = _strip_code_fences(text)
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            return None, "模型输出不是 JSON 对象。"
        err = _validate_ticket_draft(data)
        if err:
            return None, err
        return data, None
    except json.JSONDecodeError as e:
        return None, f"JSON 解析失败：{e}"
    except AuthenticationError as e:
        return None, f"鉴权失败：{e}"
    except APITimeoutError:
        return None, "调用模型超时，请稍后重试。"
    except APIConnectionError as e:
        return None, f"无法连接模型服务：{e}"
    except APIError as e:
        return None, getattr(e, "message", None) or str(e)
    except Exception as e:
        logger.exception("analyze_log_ticket_draft failed")
        return None, str(e)


def _validate_ticket_draft(data: dict[str, Any]) -> str | None:
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        return "草稿缺少有效 title。"
    sev = data.get("severity")
    pri = data.get("priority")
    try:
        sev_i = int(sev)
        pri_i = int(pri)
    except (TypeError, ValueError):
        return "severity / priority 必须为整数。"
    if sev_i not in (1, 2, 3, 4) or pri_i not in (1, 2, 3):
        return "severity 须在 1-4，priority 须在 1-3。"
    sm = data.get("summary_markdown")
    if not isinstance(sm, str):
        return "summary_markdown 必须为字符串。"
    steps = data.get("reproduction_steps")
    if steps is not None and not isinstance(steps, list):
        return "reproduction_steps 必须为字符串数组。"
    data["title"] = title.strip()[:200]
    data["severity"] = sev_i
    data["priority"] = pri_i
    if isinstance(steps, list):
        data["reproduction_steps"] = [str(x).strip() for x in steps if str(x).strip()][:30]
    env = data.get("environment_notes")
    if env is not None and not isinstance(env, str):
        return "environment_notes 必须为字符串。"
    return None
