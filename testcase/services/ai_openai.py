"""
测试域 LLM 调用：复用 assistant 中的 OpenAI 兼容配置解析。
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple, Union

_JSON_FENCE = re.compile(r"^```(?:json)?\s*", re.IGNORECASE)
_JSON_FENCE_END = re.compile(r"\s*```\s*$", re.DOTALL)


def strip_json_fence(text: str) -> str:
    t = (text or "").strip()
    t = _JSON_FENCE.sub("", t)
    t = _JSON_FENCE_END.sub("", t)
    return t.strip()


def parse_llm_json(text: str) -> Union[Dict[str, Any], List[Any]]:
    raw = strip_json_fence(text)
    return json.loads(raw)


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.2,
) -> Tuple[Optional[str], Optional[str]]:
    """
    返回 (assistant_text, error_message)。error 非空表示失败。
    """
    try:
        import assistant.views as av
    except Exception as exc:  # pragma: no cover
        return None, f"加载 AI 模块失败: {exc}"

    if not av.OPENAI_SDK_AVAILABLE or av.OpenAI is None:
        return None, av._openai_missing_response_json()

    key = (api_key or "").strip()
    b = (base_url or "").strip()
    m = (model or "").strip()

    if key:
        from assistant.views import ZHIPU_DEFAULT_API_BASE

        b = b or ZHIPU_DEFAULT_API_BASE
        m = m or av.AI_GENERATE_MODEL
    else:
        key, b, m = av._get_active_ai_model_credentials()
        if not key:
            return None, (
                "未配置大模型：请在「系统 → AI 配置」连接模型，或在请求中传入 api_key"
            )
    m, b = av._resolve_openai_target(m, b)
    b = av._normalize_openai_sdk_base_url(b, m)

    client = av.OpenAI(api_key=key, base_url=b)
    try:
        completion = client.chat.completions.create(
            model=m,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except Exception as exc:
        return None, str(exc)

    text = ""
    try:
        ch0 = completion.choices[0]
        text = (ch0.message.content or "").strip()
    except (AttributeError, IndexError, TypeError):
        text = ""
    if not text:
        return None, "模型返回为空"
    return text, None


def ai_fill_test_data(
    fields_spec: List[Dict[str, Any]],
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    根据字段描述生成合法测试数据（如 phone → 手机号）。
    fields_spec: [{"name":"phone","type":"string","description":"可选"}]
    """
    if not isinstance(fields_spec, list) or not fields_spec:
        return None, "fields 须为非空数组"

    system = (
        "你是测试数据生成器。根据用户给出的字段结构，生成一条用于接口测试的示例数据。"
        "必须输出且仅输出一个 JSON 对象（不要 Markdown），键与字段 name 一致，"
        "值为符合语义与类型的真实样例（中国大陆手机号 11 位、邮箱合法格式等）。"
    )
    user = json.dumps(
        {"fields": fields_spec},
        ensure_ascii=False,
    )
    text, err = chat_completion(system, user, api_key=api_key, base_url=base_url, model=model)
    if err:
        return None, err
    try:
        data = parse_llm_json(text)
    except json.JSONDecodeError as exc:
        return None, f"模型输出非合法 JSON: {exc}; raw={text[:500]}"
    if not isinstance(data, dict):
        return None, "模型应返回 JSON 对象"
    return data, None


def ai_import_api_cases(
    source_type: str,
    content: str,
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    从 Swagger JSON 或 cURL 文本解析出多条 API 用例定义。
    每条: case_name, api_url, api_method, api_headers(对象), api_body(对象或空), api_expected_status(可选)
    """
    st = (source_type or "").strip().lower()
    if st not in ("swagger", "curl", "openapi"):
        return None, "source_type 须为 swagger / openapi / curl"
    raw = (content or "").strip()
    if not raw:
        return None, "content 不能为空"

    system = (
        "你是 API 测试专家。用户会提供 OpenAPI/Swagger JSON 或一段 cURL 命令文本。"
        "请解析其中包含的接口，输出且仅输出一个 JSON 数组（不要 Markdown）。"
        "数组元素为对象，字段："
        "case_name(简体中文短名), api_url(完整 URL 或含 path，若只有 path 保留 path), "
        "api_method(大写), api_headers(对象，可空), api_body(对象或数组，无则 {}), "
        "api_expected_status(数字，可省略)。"
        "忽略与 HTTP 调用无关的元数据；cURL 请还原方法与 URL、头与 body。"
    )
    preview = raw if len(raw) < 120_000 else raw[:120_000] + "\n…(truncated)"
    user = f"来源类型: {st}\n\n{preview}"
    text, err = chat_completion(
        system,
        user,
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_tokens=4096,
        temperature=0.1,
    )
    if err:
        return None, err
    try:
        data = parse_llm_json(text)
    except json.JSONDecodeError as exc:
        return None, f"模型输出非合法 JSON: {exc}; raw={text[:800]}"
    if not isinstance(data, list):
        return None, "模型应返回 JSON 数组"
    return data, None
