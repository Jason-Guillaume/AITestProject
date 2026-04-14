"""
日志片段 AI 诊断：复用平台 AIModelConfig，或请求体临时传入 api_key / api_base_url。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

def analyze_log_markdown_with_context(
    *,
    anchor_text: str,
    context_lines: list[str],
    server_name: str | None = None,
    time_window_seconds: int = 300,
    api_key_override: str = "",
    api_base_override: str = "",
    model_override: str = "",
) -> tuple[str | None, str | None]:
    """
    检索增强诊断：将 ES 上下文（前后窗口）与用户选中片段一起喂给模型，减少“断章取义”。

    返回 (markdown, error_message)。成功时 error 为 None。
    """
    ctx = "\n".join([ln for ln in (context_lines or []) if (ln or "").strip()])
    anchor = (anchor_text or "").strip()
    head = f"主机：{server_name}\n窗口：前后 {int(time_window_seconds)} 秒\n" if server_name else f"窗口：前后 {int(time_window_seconds)} 秒\n"
    combined = (
        head
        + "\n【上下文日志（按时间顺序）】\n"
        + (ctx if ctx else "(无上下文命中)")
        + "\n\n【用户选中片段】\n"
        + (anchor if anchor else "(空)")
    )
    return analyze_log_markdown(
        combined,
        api_key_override=api_key_override,
        api_base_override=api_base_override,
        model_override=model_override,
    )


def analyze_log_markdown(
    log_text: str,
    *,
    api_key_override: str = "",
    api_base_override: str = "",
    model_override: str = "",
) -> tuple[str | None, str | None]:
    """
    返回 (markdown, error_message)。成功时 error 为 None。
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

    system = (
        "你是一名资深测试开发专家，擅长从应用与系统日志中定位缺陷、性能与配置问题。"
        "请用简体中文撰写分析报告，使用 Markdown（含分级标题、列表、加粗关键词）。"
        "依次给出：现象摘要、可能根因、验证步骤、修复或缓解建议；不要编造日志中未出现的事实。"
    )
    user_content = "以下为用户选中的日志片段，请分析：\n\n```text\n" + log_text.strip() + "\n```"

    try:
        client = OpenAI(api_key=key, base_url=base, timeout=90.0)
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            max_tokens=4096,
            temperature=0.2,
        )
        choice = completion.choices[0].message
        text = (getattr(choice, "content", None) or "").strip()
        if not text:
            return None, "模型未返回有效内容。"
        return text, None
    except AuthenticationError as e:
        return None, f"鉴权失败：{e}"
    except APITimeoutError:
        return None, "调用模型超时，请稍后重试。"
    except APIConnectionError as e:
        return None, f"无法连接模型服务：{e}"
    except APIError as e:
        return None, getattr(e, "message", None) or str(e)
    except Exception as e:
        logger.exception("analyze_log_markdown failed")
        return None, str(e)
