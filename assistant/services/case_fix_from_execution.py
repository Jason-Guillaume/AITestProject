"""
基于 ExecutionLog 的失败执行，生成「用例修订建议」提示词与输出解析（不落库）。
"""

from __future__ import annotations

import json
import re
from typing import Any

CASE_FIX_SYSTEM_PROMPT = (
    "你是资深软件测试工程师，擅长分析 API/自动化执行失败原因并给出可操作的用例修订建议。\n"
    "你必须只输出一个 JSON 对象，不要 markdown 代码围栏，不要额外说明文字。\n"
    "JSON 键固定为：\n"
    '  "summary": 字符串（简体中文，2～6 句，概括失败原因与修订方向）\n'
    '  "suggested_steps": 数组，每项为 {"step_desc":"...","expected_result":"..."}，'
    "表示建议的新步骤或对现有步骤的替换草案（可少于原步骤数）。\n"
    '  "risks": 字符串（简体中文，说明模型不确定性或信息不足处）\n'
    "若信息不足，仍须输出三键，suggested_steps 可为空数组，risks 中说明缺什么。"
)


def can_user_access_execution_log(user, log) -> bool:
    """与用例数据范围对齐：项目成员 / 系统与 Django 管理员 / 用例创建者（含无 module 孤儿用例）。"""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True
    if bool(getattr(user, "is_system_admin", False)):
        return True
    tc = getattr(log, "test_case", None)
    if not tc or getattr(tc, "is_deleted", False):
        return False
    mod = getattr(tc, "module", None)
    if mod is None:
        return int(getattr(tc, "creator_id", 0) or 0) == int(getattr(user, "id", 0) or 0)
    proj = getattr(mod, "project", None)
    if not proj or getattr(proj, "is_deleted", False):
        return False
    if proj.members.filter(pk=user.pk, is_deleted=False).exists():
        return True
    return int(getattr(tc, "creator_id", 0) or 0) == int(getattr(user, "id", 0) or 0)


def build_case_fix_user_message(
    *,
    case_name: str,
    test_type: str,
    steps_block: str,
    execution_status: str,
    is_passed: bool,
    request_method: str,
    request_url: str,
    response_status: int | None,
    error_message: str,
    assertion_text: str,
    request_body_snip: str,
    response_body_snip: str,
    extra_hint: str,
) -> str:
    parts = [
        f"【用例名称】{case_name}",
        f"【测试类型】{test_type}",
        f"【当前步骤】\n{steps_block}",
        f"【执行状态】execution_status={execution_status}, is_passed={is_passed}",
        f"【请求】{request_method} {request_url}",
        f"【响应状态码】{response_status if response_status is not None else 'null'}",
        f"【错误信息】\n{error_message or '（无）'}",
        f"【断言结果 JSON 摘要】\n{assertion_text or '[]'}",
        f"【请求体片段】\n{request_body_snip or '（无）'}",
        f"【响应体片段】\n{response_body_snip or '（无）'}",
    ]
    if extra_hint:
        parts.append(f"【用户补充说明】\n{extra_hint}")
    return "\n\n".join(parts)


def parse_case_fix_llm_output(raw_content: str) -> dict[str, Any]:
    t = (raw_content or "").strip()
    if not t:
        raise ValueError("模型返回为空")
    md = re.search(r"\{[\s\S]*\}", t)
    payload = (md.group(0) if md else t).strip()
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("根节点必须为 JSON 对象")
    summary = str(data.get("summary") or "").strip()
    risks = str(data.get("risks") or "").strip()
    raw_steps = data.get("suggested_steps")
    suggested_steps: list[dict[str, str]] = []
    if isinstance(raw_steps, list):
        for it in raw_steps:
            if not isinstance(it, dict):
                continue
            desc = str(it.get("step_desc") or it.get("desc") or "").strip()
            exp = str(it.get("expected_result") or it.get("expected") or "").strip() or "—"
            if desc:
                suggested_steps.append({"step_desc": desc, "expected_result": exp})
    if not summary:
        summary = "（模型未给出 summary）"
    if not risks:
        risks = "请人工核对日志与网络环境；模型可能未见到完整请求/响应。"
    return {
        "summary": summary,
        "suggested_steps": suggested_steps,
        "risks": risks,
    }
