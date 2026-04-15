from __future__ import annotations

import json
from typing import Any

from django.conf import settings

AI_CASE_BATCH_MIN_COUNT = max(1, int(getattr(settings, "AI_CASE_BATCH_MIN_COUNT", 5)))


def build_batch_generation_prompt(
    *,
    module_name: str,
    requirement: str,
    test_type_focus: str,
    existing_titles: list[str],
    min_count: int | None = None,
) -> str:
    """
    构建一次性批量生成多条测试用例的 Prompt。
    """
    cnt = AI_CASE_BATCH_MIN_COUNT if min_count is None else max(1, int(min_count))
    existing_block = "\n".join(
        f"- {x}" for x in existing_titles[:120] if str(x).strip()
    )
    if not existing_block:
        existing_block = "- （当前模块暂无历史用例）"

    return f"""
你是资深软件测试工程师。请基于需求生成测试用例。

【硬性要求】
1) 一次性输出不少于 {cnt} 条用例。
2) 必须覆盖：正向、逆向（异常）与边界场景。
3) 严格输出合法 JSON Array，且只输出 JSON 本体，不要 Markdown、不要解释文字。
4) 严禁生成与“已有用例标题”语义重复的测试意图。

【JSON Schema】
每条须带 module_name（简体中文，与下方【当前模块】一致或为其合理子域），便于导入时落库到正确模块。
[
  {{
    "title": "用例标题",
    "type": "正向/逆向/边界",
    "steps": "（兼容字段）操作步骤文本，可选",
    "expected": "预期结果",
    "steps_list": [
      {{"step_desc": "步骤描述（简体中文、可直接落库）", "expected_result": "该步骤预期（可选）"}}
    ],
    "module_name": "与【当前模块】一致的中文模块名"
  }}
]

【测试类型侧重点】
{test_type_focus}

【当前模块】
{module_name}

【需求描述】
{requirement}

【已有用例标题（避免重复）】
{existing_block}
""".strip()


def parse_batch_json_array(raw_text: str) -> list[dict[str, Any]]:
    """
    容错解析模型输出：
    - 支持纯数组
    - 支持 {"cases": [...]} / {"data":[...]}
    """
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("模型返回为空")

    # 去除常见 markdown fence
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    data = json.loads(text)
    if isinstance(data, list):
        arr = data
    elif isinstance(data, dict):
        arr = data.get("cases") or data.get("data") or data.get("items")
    else:
        arr = None
    if not isinstance(arr, list):
        raise ValueError("模型输出不是 JSON 数组")
    return [x for x in arr if isinstance(x, dict)]


def normalize_batch_case_item(item: dict[str, Any], index: int) -> dict[str, Any]:
    """
    将批量 JSON 用例归一化为系统通用用例字段。
    须保留 module_name：下游 _normalize_generated_case 依赖该字段写入预览与导入。
    """
    name = str(
        item.get("title") or item.get("caseName") or item.get("name") or ""
    ).strip()
    if not name:
        name = f"AI生成用例-{index + 1}"
    case_type = str(item.get("type") or "").strip()
    steps = str(item.get("steps") or "").strip()
    steps_list = item.get("steps_list") or item.get("stepsList")
    if steps_list is None and isinstance(item.get("steps"), list):
        steps_list = item.get("steps")
    if isinstance(steps_list, list):
        norm_steps_list = []
        for it in steps_list:
            if not isinstance(it, dict):
                continue
            desc = str(
                it.get("step_desc") or it.get("desc") or it.get("action") or ""
            ).strip()
            if not desc:
                continue
            exp2 = str(it.get("expected_result") or it.get("expected") or "").strip()
            norm_steps_list.append(
                {
                    "step_desc": desc[:4000],
                    "expected_result": exp2[:2000],
                }
            )
        steps_list = norm_steps_list
        if not steps and norm_steps_list:
            steps = "\n".join(
                f"{i+1}. {x['step_desc']}" for i, x in enumerate(norm_steps_list)
            )
    expected = str(item.get("expected") or item.get("expectedResult") or "").strip()
    level_raw = str(item.get("level") or "").strip().upper()
    level = level_raw if level_raw in ("P0", "P1", "P2", "P3") else "P2"
    mod = str(
        item.get("module_name")
        or item.get("moduleName")
        or item.get("belonging_module")
        or item.get("所属模块")
        or ""
    ).strip()[:100]
    pre = str(item.get("precondition") or item.get("pre_condition") or "").strip()

    return {
        "case_name": name[:255],
        "level": level,
        "precondition": pre,
        "steps": steps,
        "steps_list": steps_list if isinstance(steps_list, list) else None,
        "expected_result": expected,
        "case_type": case_type,
        "module_name": mod,
    }
