"""
AI 生成用例：Prompt 上下文分发（核心规则 test_type == 'api' → 接口专业模板 → ApiTestCase）。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

# 与业务侧命名对齐，便于日志与调试
API_CASE_PROMPT_TEMPLATE = "API_CASE_PROMPT_TEMPLATE"
FUNCTIONAL_CASE_PROMPT_TEMPLATE = "FUNCTIONAL_CASE_PROMPT_TEMPLATE"


@dataclass(frozen=True)
class AiPromptContext:
    """一次生成请求的 Prompt 解析结果（模板选择 + 用户侧 input_data + 目标模型语义）。"""

    use_api_prompt: bool
    model_target: str
    input_data: str
    system_prompt: str
    template_key: str


@dataclass(frozen=True)
class AiGenerationDispatch:
    """策略分发器输出：同步/流式生成统一取 system / user / 是否做 Api 字段 enrich。"""

    system_prompt: str
    user_message: str
    should_enrich_api: bool
    prompt_context: AiPromptContext


def get_ai_prompt_context(
    test_type: str,
    *,
    api_spec: Optional[str] = None,
    case_name: str = "",
    requirement: str = "",
    module_name: str = "",
    test_type_focus: str = "",
) -> AiPromptContext:
    """
    核心判断：只要是 API 类型，就启用接口专业模板（ApiCasePrompt），目标语义为 ApiTestCase。
    否则使用功能/通用模板（StandardCasePrompt），目标语义为 TestCase。

    - API + 有 api_spec：input_data 为 Spec 原文（由外层用户消息再附全文）。
    - API + 无 api_spec：input_data 为「根据名称预测接口」类提示，供用户消息补充段使用。
    - 非 API：input_data 优先 api_spec，否则需求描述（供扩展或日志）。
    """
    use_api_prompt = str(test_type or "").strip() == "api"
    spec = (api_spec or "").strip()
    cn = (case_name or "").strip()

    if use_api_prompt:
        input_data = spec if spec else f"根据名称预测接口: {cn or '（结合需求描述推断各接口）'}"
        ctx = {
            "module_name": module_name,
            "requirement": requirement,
            "test_type_focus": test_type_focus,
            "api_spec": spec,
        }
        from assistant.api_case_generation import build_api_case_system_prompt_from_ctx

        system_prompt = build_api_case_system_prompt_from_ctx(ctx)
        return AiPromptContext(
            use_api_prompt=True,
            model_target="ApiTestCase",
            input_data=input_data,
            system_prompt=system_prompt,
            template_key=API_CASE_PROMPT_TEMPLATE,
        )

    import assistant.views as v

    system_prompt = v._build_ai_generate_system_prompt(
        module_name,
        requirement,
        test_type_focus,
    )
    input_data = spec if spec else (requirement or "").strip()
    return AiPromptContext(
        use_api_prompt=False,
        model_target="TestCase",
        input_data=input_data,
        system_prompt=system_prompt,
        template_key=FUNCTIONAL_CASE_PROMPT_TEMPLATE,
    )


def get_ai_prompt_context_from_request_ctx(ctx: Dict[str, Any]) -> AiPromptContext:
    """从 views 侧组装好的 ctx 字典生成 AiPromptContext。"""
    return get_ai_prompt_context(
        str(ctx.get("test_type") or "functional"),
        api_spec=ctx.get("api_spec"),
        case_name=str(ctx.get("case_name") or ""),
        requirement=str(ctx.get("requirement") or ""),
        module_name=str(ctx.get("module_name") or ""),
        test_type_focus=str(ctx.get("test_type_focus") or ""),
    )


def build_system_prompt_for_generate(ctx: Dict[str, Any]) -> str:
    """兼容旧入口：等价于 get_ai_prompt_context_from_request_ctx(ctx).system_prompt。"""
    return get_ai_prompt_context_from_request_ctx(ctx).system_prompt


def build_user_message_for_generate(ctx: Dict[str, Any]) -> str:
    """
    用户消息：需求 + 可选完整 api_spec；
    API 且无 Spec 时追加 input_data 段，强化「按名称/需求推断接口」。
    """
    pc = get_ai_prompt_context_from_request_ctx(ctx)
    parts = [
        "请严格按系统提示：只输出 JSON 数组，且所有说明性字符串取值必须为简体中文。\n"
        "用户需求（再次强调）：\n\n"
        + (ctx.get("requirement") or "").strip()
    ]
    spec = (ctx.get("api_spec") or "").strip()
    if spec:
        max_spec = 100000
        body = spec if len(spec) <= max_spec else spec[:max_spec] + "\n…(以下已截断)"
        parts.append("\n\n【接口定义原文】\n" + body)
    elif pc.use_api_prompt and pc.input_data:
        parts.append("\n\n【接口上下文 / 推断依据】\n" + pc.input_data)
    return "".join(parts)


def validate_spec(text: str) -> Tuple[bool, Optional[str]]:
    """
    调用 AI 前校验用户粘贴的接口定义。
    合法：空（跳过）、JSON 对象/数组、可识别的 cURL、常见 OpenAPI YAML 片段。
    返回 (True, None) 或 (False, 错误说明)。
    """
    t = (text or "").strip()
    if not t:
        return True, None
    try:
        json.loads(t)
        return True, None
    except json.JSONDecodeError:
        pass
    if re.search(r"(?is)\bcurl\s+", t) and re.search(r"https?://[^\s\"']+", t):
        return True, None
    tl = t.lower()
    if "openapi:" in tl or "swagger:" in tl or "swagger " in tl:
        return True, None
    if re.search(r"(?m)^\s*paths\s*:", t):
        return True, None
    if re.search(r"-X\s+[A-Z]{3,7}\b", t) and re.search(r"https?://", t):
        return True, None
    return (
        False,
        "接口定义格式无法识别：请粘贴合法 JSON（OpenAPI JSON）、含 openapi:/paths: 的 YAML 片段，或完整 cURL 命令。",
    )


def should_apply_api_case_enrichment(ctx: Dict[str, Any]) -> bool:
    """是否对归一化结果做 ApiTestCase 字段回填。"""
    return str(ctx.get("test_type") or "").strip() == "api"


def apply_test_type_domain_strategy(base_system_prompt: str, ctx: Dict[str, Any]) -> str:
    """
    在 RAG 外层包装之前，按 test_type 注入「领域专家」补充段（策略模式）。
    与 ctx['context_data'] 联动：安全场景可强调 OWASP；性能/UI 等可追加侧重点。
    """
    tt = str(ctx.get("test_type") or "functional").strip()
    cd = ctx.get("context_data")
    if not isinstance(cd, dict):
        cd = {}

    blocks: list[str] = []
    if tt == "security":
        blocks.append(
            "【安全测试 · 领域指令】你是一位资深安全测试专家，请重点关注 OWASP Top 10 "
            "及相关风险（如注入、失效访问控制、敏感数据暴露、XSS、不安全设计、安全配置错误、"
            "日志与监控不足等）。用例须覆盖威胁入口、攻击路径、验证方式与修复建议要点；"
            "输出格式仍须遵守系统提示中的纯 JSON 数组约束，正文为简体中文。"
        )
        vuln = cd.get("vulnerability_types")
        if isinstance(vuln, (list, tuple)) and vuln:
            labs = ", ".join(str(x).strip() for x in vuln if str(x).strip())
            if labs:
                blocks.append("【用户指定漏洞关注点】" + labs)
        scope = (cd.get("scan_scope") or "").strip()
        if scope:
            blocks.append("【扫描/测试范围（用户补充）】\n" + scope)
    elif tt == "performance":
        blocks.append(
            "【性能测试 · 领域指令】请明确并发、负载模型、响应时间（RT）与吞吐目标，"
            "以及数据准备、监控指标与通过准则；用例步骤与预期须可执行、可度量，简体中文。"
        )
        pm = (cd.get("performance_metrics") or "").strip()
        if pm:
            blocks.append("【性能指标与约束（用户补充）】\n" + pm)
    elif tt == "ui-automation":
        blocks.append(
            "【UI 自动化 · 领域指令】请重视稳定定位策略、页面状态流转、显式等待与断言、"
            "数据驱动与异常恢复；步骤须可映射到自动化脚本，简体中文。"
        )
        loc = (cd.get("ui_locators") or "").strip()
        if loc:
            blocks.append("【页面元素/定位参考（用户补充）】\n" + loc)
    elif tt == "functional":
        blocks.append(
            "【功能测试 · 领域指令】请覆盖业务流程、前置与数据、界面与接口侧表现，"
            "正向/边界/异常场景兼顾，简体中文。"
        )
        bf = (cd.get("business_flow") or cd.get("preconditions") or "").strip()
        if bf:
            blocks.append("【业务流程/前置条件（用户补充）】\n" + bf)

    if not blocks:
        return base_system_prompt
    return base_system_prompt + "\n\n" + "\n".join(blocks)


def dispatch_ai_generation(ctx: Dict[str, Any]) -> AiGenerationDispatch:
    """
    策略分发器：根据 ctx.test_type 选择 API 专用 Prompt 或功能步骤 Prompt，
    并组装用户消息（含 Spec 全文或推断段）。RAG 仍由 views 在 system 外包一层。
    """
    pc = get_ai_prompt_context_from_request_ctx(ctx)
    return AiGenerationDispatch(
        system_prompt=pc.system_prompt,
        user_message=build_user_message_for_generate(ctx),
        should_enrich_api=should_apply_api_case_enrichment(ctx),
        prompt_context=pc,
    )
