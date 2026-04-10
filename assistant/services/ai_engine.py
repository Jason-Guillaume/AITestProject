"""
AI 用例生成：领域策略与 System Prompt 模板池（与 views / RAG 解耦，便于扩展）。
"""

from __future__ import annotations

import json
from typing import Any, Dict

# 可按 test_type 扩展；长文本为领域「专家人设 + 输出约束」
PROMPT_TEMPLATES: Dict[str, str] = {
    "functional": (
        "【功能测试策略】聚焦用户旅程、业务规则与数据一致性；"
        "用例须可执行、可判定，步骤与预期全部为简体中文。"
    ),
    "api": (
        "【接口测试策略】围绕契约、状态码、请求/响应体、鉴权与幂等；"
        "技术字面量（URL/方法）可保留拉丁字符，说明性文字须为简体中文。"
    ),
    "performance": (
        "【性能测试策略】明确负载模型、并发、持续时间、SLA（RT/吞吐/错误率）；"
        "步骤须可转化为压测脚本或监控核对清单。"
    ),
    "security": (
        "【安全测试策略 · 攻击者视角】你以攻击者思维设计验证用例："
        "识别入口、构造恶意输入、观察系统反馈与信息泄露；"
        "每条用例须体现可复现的攻击路径与验证点。"
        "输出仍为单一 JSON 数组；键名使用 camelCase，字符串值为简体中文。"
        "\n【安全用例对象字段要求】除通用字段外，每条对象尽量包含："
        "attackVector（攻击向量）、testSteps（测试步骤）、payloadExample（示例 Payload 或请求片段）、"
        "expectedDefense（预期防御/修复要点）、riskLevel（高|中|低）。"
        "若无法拆分，可将 attackVector/testSteps/payloadExample 合并写入 steps 字段，"
        "将 expectedDefense 写入 expectedResult。"
    ),
    "ui-automation": (
        "【UI 自动化策略】优先 Page Object 思想：定位符稳定、步骤可映射为 Playwright 或 Selenium；"
        "在 steps 或单独字段 automationSnippet 中给出简短代码片段（TypeScript/Java 均可），"
        "并说明等待条件与断言；自然语言说明须为简体中文。"
    ),
}


def build_engine_addon(ctx: Dict[str, Any]) -> str:
    """
    根据 test_type 与 ext_config 追加到 domain strategy 之后的引擎层说明。
    """
    tt = str(ctx.get("test_type") or "functional").strip()
    base = (PROMPT_TEMPLATES.get(tt) or "").strip()
    ext = ctx.get("ext_config")
    if not isinstance(ext, dict):
        ext = {}

    extras: list[str] = []
    if tt == "security":
        vecs = ext.get("sec_vectors")
        if isinstance(vecs, (list, tuple)) and vecs:
            extras.append("【用户勾选漏洞向量】" + "、".join(str(x) for x in vecs if str(x).strip()))
        rl = (ext.get("risk_level") or "").strip()
        if rl:
            extras.append("【用户指定风险等级偏好】" + rl)
        ss = (ext.get("scan_scope") or "").strip()
        if ss:
            extras.append("【扫描/范围补充】\n" + ss)
    elif tt == "ui-automation" and (ext.get("ui_elements") or "").strip():
        extras.append("【页面/DOM 参考】\n" + str(ext.get("ui_elements")).strip()[:8000])
    elif tt == "performance":
        pt = ext.get("perf_targets")
        if isinstance(pt, dict) and pt:
            try:
                extras.append("【性能目标 JSON】\n" + json.dumps(pt, ensure_ascii=False)[:8000])
            except (TypeError, ValueError):
                pass

    parts = [p for p in (base, "\n".join(extras)) if p]
    return "\n\n".join(parts) if parts else ""
