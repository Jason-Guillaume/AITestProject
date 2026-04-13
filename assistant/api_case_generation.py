"""
ApiCasePrompt：结构化输出与 ApiTestCase（api_method/api_url/api_headers/api_body/api_expected_status）映射。
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any, Dict, List, Optional, Union

_ALLOWED_HTTP_METHODS = frozenset(
    {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
)
_MAX_URL_LEN = 2048
_MAX_METHOD_LEN = 16


def _build_curl_from_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    body: Any,
) -> str:
    """
    从请求信息构建 cURL 命令字符串，用于保存 api_source_curl。
    便于后续重新解析或审计追踪。
    """
    parts = ["curl"]

    # 添加请求方法
    if method and method != "GET":
        parts.append(f"-X {method}")

    # 添加请求头
    if headers:
        for k, v in headers.items():
            escaped_v = str(v).replace('"', '\\"')
            parts.append(f'-H "{k}: {escaped_v}"')

    # 添加请求体
    if body:
        if isinstance(body, (dict, list)):
            import json
            body_json = json.dumps(body, ensure_ascii=False)
            escaped_body = body_json.replace('"', '\\"')
            parts.append(f'-d "{escaped_body}"')
        else:
            escaped_body = str(body).replace('"', '\\"')
            parts.append(f'-d "{escaped_body}"')

    # 添加 URL（转义特殊字符）
    escaped_url = str(url).replace('"', '\\"')
    parts.append(f'"{escaped_url}"')

    return " ".join(parts)

ZH_JSON_MANDATE_API = """
══════════════════════════════════════════════════════
【输出形态 · 最高优先级】
只输出「纯 JSON 数组」文本：首字符为 [ ，末字符为 ] ；严禁 Markdown 代码围栏与数组外任何文字。
除 JSON 键名、HTTP 方法字面值、URL 等技术标识外，说明性字符串（如 caseName、steps、expectedResult）须使用简体中文。
本任务仅生成 1 条用例：数组长度必须为 1。
══════════════════════════════════════════════════════
"""

_API_SPEC_BLOCK_STRICT = """
【接口定义 — 已提供原文】
用户已在下方「输入内容」中粘贴 OpenAPI/Swagger/JSON/YAML 或 cURL。你必须严格据此解析：
路径、HTTP 方法、请求头、请求体字段、成功/错误响应；不得编造与 Spec 冲突的 URL 或字段。
若 Spec 中信息缺失，可在 steps 或 assert_logic 中注明依据与假设。
"""

_API_SPEC_BLOCK_INFER = """
【接口定义 — 未提供原文】
用户未粘贴 Spec。请结合「需求描述」与业务语义合理推断 method、url、headers、request_body；
在 steps 或 caseName 中简要说明推断依据（如「按 REST 惯例推断路径为 /api/users」）。
仍须给出可执行的 request_body（无体时 {{}}）与 assert_logic。
"""


def _api_output_example_block() -> str:
    return """
【输出示例 · 单元素数组（字段名须与下列一致）】
[
  {{
    "businessId": "API-1",
    "caseName": "[API-1] 正向-示例",
    "module_name": "用户模块",
    "method": "POST",
    "url": "/api/v1/login",
    "headers": {{
      "Content-Type": "application/json",
      "Authorization": "Bearer {{token}}"
    }},
    "request_body": {{
      "phone": "13800138000",
      "password": "Test@123"
    }},
    "assert_logic": "status == 200 且 msg == 'success' 且 data.token 非空",
    "steps": "1. 按 method/url/headers/request_body 构造请求\\\\n2. 发送并核对 assert_logic",
    "expectedResult": "登录成功并返回 token"
  }}
]

说明：亦兼容额外输出 body（与 request_body 同义）、response_assert（结构化断言）；系统会归一化入库。
不要输出 ```json，不要输出数组外任何字符。
"""


API_CASE_SYSTEM_TEMPLATE = (
    ZH_JSON_MANDATE_API
    + """
你现在是一名资深接口自动化测试专家。

{api_spec_instruction}

任务：解析以下 API 规格（或根据名称与需求推断），并生成 1 条测试用例（JSON 数组内仅含一个对象）。

要求：
- 结构化输出：必须输出 JSON 数组格式。
- 字段要求（该对象顶层须包含）：
  - method：识别为 GET、POST、PUT、DELETE 等标准方法（大写）。
  - url：提取路径；若无则根据业务推断。
  - headers：自动生成必要的 Content-Type 与 Authorization 等占位符。
  - request_body：生成符合字段逻辑的 Mock 数据（例如：手机号须符合 11 位格式）；无请求体时为 {{}}。
  - assert_logic：生成断言逻辑描述，例如：status == 200 且 msg == 'success'。

建议补充（便于用例管理与展示）：caseName（中文，建议带 [API-1] 前缀）、businessId（API-1）、module_name、level、precondition、steps、expectedResult。

【输入内容】
{api_spec_section}

【其它上下文】
测试类型侧重点：{test_type_focus}
当前模块（module_name 宜对齐，中文）：{module_name}
需求描述：
{requirement_description}
"""
    + _api_output_example_block()
)


def build_api_case_system_prompt_from_ctx(ctx: Dict[str, Any]) -> str:
    """ApiCasePrompt：由策略层传入完整 ctx（含 api_spec 是否为空）。"""
    mn = (ctx.get("module_name") or "").strip() or "（未指定模块，从需求推断中文模块名）"
    focus = (ctx.get("test_type_focus") or "").strip()
    spec = (ctx.get("api_spec") or "").strip()
    api_spec_instruction = _API_SPEC_BLOCK_STRICT if spec else _API_SPEC_BLOCK_INFER
    max_embed = 100_000
    if spec:
        api_spec_section = (
            spec
            if len(spec) <= max_embed
            else spec[:max_embed] + "\n…(以下已截断，完整原文同时见用户消息中的【接口定义原文】)"
        )
    else:
        api_spec_section = (
            "（未单独粘贴接口定义：请以用户消息中的「需求描述」与「接口上下文/推断依据」为准解析或推断接口。）"
        )
    return API_CASE_SYSTEM_TEMPLATE.format(
        api_spec_instruction=api_spec_instruction,
        api_spec_section=api_spec_section,
        test_type_focus=focus,
        module_name=mn,
        requirement_description=(ctx.get("requirement") or "").strip(),
    )


# 兼容旧 import
def build_api_case_system_prompt(
    module_name: str,
    requirement: str,
    test_type_focus: str | None = None,
) -> str:
    return build_api_case_system_prompt_from_ctx(
        {
            "module_name": module_name,
            "requirement": requirement,
            "test_type_focus": test_type_focus,
            "api_spec": "",
        }
    )


def _safe_json_dict(val: Any) -> Dict[str, Any]:
    if isinstance(val, dict):
        return dict(val)
    if isinstance(val, str) and val.strip():
        try:
            o = json.loads(val)
            return dict(o) if isinstance(o, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _coerce_headers_for_api_model(val: Any) -> Dict[str, str]:
    """清洗为 ApiTestCase.api_headers 可序列化的 JSON 对象（值为字符串，兼容执行层）。"""
    d = _safe_json_dict(val)
    out: Dict[str, str] = {}
    for k, v in d.items():
        key = str(k).strip()
        if not key:
            continue
        if isinstance(v, (dict, list)):
            out[key] = json.dumps(v, ensure_ascii=False)
        elif v is None:
            out[key] = ""
        elif isinstance(v, bool):
            out[key] = "true" if v else "false"
        else:
            out[key] = str(v)
    return out


def _coerce_body_for_api_model(val: Any) -> Union[Dict[str, Any], List[Any]]:
    """清洗为 ApiTestCase.api_body（JSONField）可用的 dict 或 list。"""
    if val is None:
        return {}
    if isinstance(val, dict):
        return dict(val)
    if isinstance(val, list):
        return list(val)
    if isinstance(val, str):
        t = val.strip()
        if not t:
            return {}
        try:
            o = json.loads(t)
            if isinstance(o, dict):
                return dict(o)
            if isinstance(o, list):
                return list(o)
            return {"_scalar": o}
        except json.JSONDecodeError:
            return {"_legacy_text": t}
    return {"_value": val}


def sanitize_ai_raw_item_for_apitestcase(raw: Any) -> Dict[str, Any]:
    """
    清洗层：将模型输出的单条用例 JSON 规整为与 ApiTestCase 字段一一对应的语义，
    并写入规范键 method / url / headers / body（供后续 enrich 与入库）。
    """
    if not isinstance(raw, dict):
        return {
            "method": "GET",
            "url": "",
            "headers": {},
            "body": {},
        }
    out = dict(raw)
    m = str(out.get("method") or out.get("http_method") or "GET").strip().upper()
    if m not in _ALLOWED_HTTP_METHODS:
        m = "GET"
    out["method"] = m[:_MAX_METHOD_LEN]
    u = str(out.get("url") or out.get("api_url") or out.get("path") or "").strip()
    out["url"] = u[:_MAX_URL_LEN]
    out["headers"] = _coerce_headers_for_api_model(out.get("headers"))
    b = out.get("body")
    if b is None:
        b = out.get("request_body") or out.get("json")
    out["body"] = _coerce_body_for_api_model(b)
    return out


def _assertions_to_summary(assertions: Any) -> str:
    if not isinstance(assertions, list) or not assertions:
        return ""
    lines: List[str] = []
    for a in assertions:
        if not isinstance(a, dict):
            continue
        desc = str(a.get("description_zh") or "").strip()
        kind = str(a.get("kind") or "").strip()
        if kind == "status_code":
            op = a.get("op", "==")
            val = a.get("value", "")
            lines.append(f"状态码 {op} {val}" + (f"（{desc}）" if desc else ""))
        elif kind == "json_path":
            path = a.get("path", "")
            op = a.get("op", "")
            val = a.get("value", "")
            lines.append(f"JSONPath `{path}` {op} {val}" + (f"（{desc}）" if desc else ""))
        elif kind == "body_contains":
            sub = a.get("substring", "")
            lines.append(f"响应体包含 `{sub}`" + (f"（{desc}）" if desc else ""))
        elif kind == "header":
            name = a.get("name", "")
            lines.append(f"响应头 `{name}` 校验" + (f"（{desc}）" if desc else ""))
        elif desc:
            lines.append(desc)
    if not lines:
        return ""
    return "【自动断言】" + "；".join(lines)


def _first_status_code_from_assertions(assertions: Any) -> Optional[int]:
    if not isinstance(assertions, list):
        return None
    for a in assertions:
        if not isinstance(a, dict):
            continue
        if str(a.get("kind") or "").strip() != "status_code":
            continue
        if str(a.get("op") or "") != "==":
            continue
        v = a.get("value")
        try:
            return int(v)
        except (TypeError, ValueError):
            continue
    return None


def _status_from_assert_logic(text: str) -> Optional[int]:
    """从 assert_logic 等自由文本中尽量提取期望 HTTP 状态码。"""
    if not (text or "").strip():
        return None
    m = re.search(
        r"(?:status(?:_code)?|状态码)\s*[=!]=+\s*(\d{3})\b",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    m2 = re.search(r"==\s*(\d{3})\b", text)
    if m2:
        try:
            code = int(m2.group(1))
            if 100 <= code <= 599:
                return code
        except ValueError:
            pass
    return None


def _parse_response_assert(raw_item: Dict[str, Any]) -> tuple[Dict[str, Any], List[Any], str]:
    """返回 (response_assert dict, rules list, logic_text)；兼容 assert_logic 字符串。"""
    al = str(raw_item.get("assert_logic") or raw_item.get("assertLogic") or "").strip()
    ra = raw_item.get("response_assert")
    if isinstance(ra, str):
        logic = ra.strip()
        if al:
            logic = f"{logic}\n{al}".strip() if logic else al
        return {}, [], logic
    if not isinstance(ra, dict):
        return {}, [], al
    rules = ra.get("rules")
    if not isinstance(rules, list):
        rules = []
    logic = str(ra.get("logic_text") or ra.get("logicText") or "").strip()
    if al:
        logic = f"{logic}\n{al}".strip() if logic else al
    return ra, rules, logic


def _ensure_business_prefix(case_name: str, business_id: str, index: int) -> str:
    name = (case_name or "").strip()
    bid = (business_id or "").strip() or f"API-{index + 1}"
    if not re.match(r"^\[API-\d+\]", name):
        if not bid.upper().startswith("API-"):
            bid = f"API-{index + 1}"
        name = f"[{bid}] {name}".strip()
    return name[:255]


def enrich_normalized_case_with_api_fields(
    normalized: Dict[str, Any],
    raw_item: Dict[str, Any],
    index: int,
) -> Dict[str, Any]:
    """
    合并 Api 结构化字段 -> api_method, api_url, api_headers, api_body, api_expected_status；
    先经 sanitize_ai_raw_item_for_apitestcase 清洗，再兼容 request_config 兜底。
    """
    raw_item = sanitize_ai_raw_item_for_apitestcase(raw_item)
    out = dict(normalized)
    business_id = (
        raw_item.get("businessId")
        or raw_item.get("business_id")
        or raw_item.get("case_business_prefix")
        or ""
    )
    business_id = str(business_id).strip() or f"API-{index + 1}"
    out["business_id"] = business_id
    out["case_name"] = _ensure_business_prefix(
        out.get("case_name") or "", business_id, index
    )

    method = str(raw_item.get("method") or "GET").strip().upper() or "GET"
    url = str(raw_item.get("url") or "").strip()[:_MAX_URL_LEN]
    headers = dict(raw_item.get("headers") or {})
    body: Any = raw_item.get("body")
    if not isinstance(body, (dict, list)):
        body = _coerce_body_for_api_model(body)

    # 兼容旧 request_config（清洗后仍缺省时回填）
    req_cfg = _safe_json_dict(
        raw_item.get("request_config") or raw_item.get("requestConfig")
    )
    if req_cfg:
        if not url:
            url = str(req_cfg.get("url") or req_cfg.get("path") or "").strip()[
                :_MAX_URL_LEN
            ]
        if method == "GET" and req_cfg.get("method"):
            method = (
                str(req_cfg.get("method") or "GET").strip().upper() or "GET"
            )[:_MAX_METHOD_LEN]
            if method not in _ALLOWED_HTTP_METHODS:
                method = "GET"
        if not headers:
            headers = _coerce_headers_for_api_model(req_cfg.get("headers"))
        if (not body or body == {}) and (
            req_cfg.get("body") is not None or req_cfg.get("body_positive") is not None
        ):
            body = _coerce_body_for_api_model(
                req_cfg.get("body") if req_cfg.get("body") is not None else req_cfg.get("body_positive")
            )

    ra_dict, rules, logic_text = _parse_response_assert(raw_item)
    if not rules and isinstance(raw_item.get("assertions"), list):
        rules = list(raw_item["assertions"])
    if not logic_text:
        logic_text = str(
            raw_item.get("assertion_logic_text")
            or raw_item.get("assertionLogicText")
            or ""
        ).strip()
    out["response_assert"] = ra_dict if ra_dict else None
    out["assertion_logic_text"] = logic_text
    out["assertions"] = rules

    summary = _assertions_to_summary(rules)
    exp_status = ra_dict.get("expected_status")
    if exp_status is None:
        exp_status = ra_dict.get("status_code")
    try:
        exp_status_int = int(exp_status) if exp_status is not None else None
    except (TypeError, ValueError):
        exp_status_int = _first_status_code_from_assertions(rules)

    if exp_status_int is None:
        exp_status_int = _first_status_code_from_assertions(rules)
    if exp_status_int is None and logic_text:
        exp_status_int = _status_from_assert_logic(logic_text)

    exp = str(out.get("expected_result") or "").strip()
    extra_parts: List[str] = []
    if summary:
        extra_parts.append(summary)
    if logic_text:
        extra_parts.append(f"【断言逻辑】{logic_text}")
    if extra_parts:
        out["expected_result"] = (
            (exp + "\n\n" + "\n".join(extra_parts)).strip() if exp else "\n".join(extra_parts)
        )

    out["api_method"] = method[:_MAX_METHOD_LEN]
    if method not in _ALLOWED_HTTP_METHODS:
        out["api_method"] = "GET"
    out["api_url"] = url
    out["api_headers"] = headers
    out["api_body"] = body if isinstance(body, (dict, list)) else {}
    out["api_source_curl"] = _build_curl_from_request(method, url, headers, body)
    if exp_status_int is not None:
        out["api_expected_status"] = exp_status_int

    out["request_config"] = {
        "method": out["api_method"],
        "url": out["api_url"],
        "headers": out["api_headers"],
        "body": out["api_body"],
    }

    return out


def _is_placeholder_api_url(url: str) -> bool:
    u = (url or "").strip().lower()
    if not u:
        return True
    return "example.com" in u or "example.org" in u


def _is_empty_api_body(body: Any) -> bool:
    if body is None:
        return True
    if isinstance(body, dict):
        return len(body) == 0
    if isinstance(body, list):
        return len(body) == 0
    return False


def _is_empty_api_headers(h: Any) -> bool:
    return not isinstance(h, dict) or len(h) == 0


def _api_case_request_richness(c: Dict[str, Any]) -> int:
    """分数越高越适合作同批回填补全的锚点用例。"""
    score = 0
    u = str(c.get("api_url") or "").strip()
    if u and not _is_placeholder_api_url(u):
        score += 6
    if not _is_empty_api_headers(c.get("api_headers")):
        score += 2
    if not _is_empty_api_body(c.get("api_body")):
        score += 4
    m = str(c.get("api_method") or "GET").strip().upper()
    if m in ("POST", "PUT", "PATCH", "DELETE"):
        score += 1
    return score


def backfill_api_request_fields_in_batch(cases: List[Dict[str, Any]]) -> None:
    """
    同批多条 API 用例时，模型常在首条写全 request，后续只写步骤而省略 body/headers。
    将「本批中请求信息最完整的一条」作为模板，给后续条补全空的 url/headers/body（及必要时 method），
    避免前端执行台大量 `{}`。
    """
    if not cases or len(cases) < 2:
        return
    anchor: Optional[Dict[str, Any]] = None
    best = -1
    for c in cases:
        if not isinstance(c, dict):
            continue
        sc = _api_case_request_richness(c)
        if sc > best:
            best = sc
            anchor = c
    if anchor is None or best <= 0:
        return

    a_url = str(anchor.get("api_url") or "").strip()[:_MAX_URL_LEN]
    a_method = str(anchor.get("api_method") or "GET").strip().upper()
    if a_method not in _ALLOWED_HTTP_METHODS:
        a_method = "GET"
    a_headers = anchor.get("api_headers") if isinstance(anchor.get("api_headers"), dict) else {}
    a_body = anchor.get("api_body")

    for c in cases:
        if c is anchor or not isinstance(c, dict):
            continue
        u = str(c.get("api_url") or "").strip()
        replaced_url = False
        if (not u) or _is_placeholder_api_url(u):
            if a_url:
                c["api_url"] = a_url
                replaced_url = True
        if _is_empty_api_headers(c.get("api_headers")) and a_headers:
            c["api_headers"] = copy.deepcopy(a_headers)
        copied_body = False
        if _is_empty_api_body(c.get("api_body")) and not _is_empty_api_body(a_body):
            c["api_body"] = copy.deepcopy(a_body)
            copied_body = True
        if (replaced_url or copied_body) and a_method in _ALLOWED_HTTP_METHODS:
            c["api_method"] = a_method

        # 补全请求字段后，同步重新生成 curl
        c["api_method"] = c.get("api_method", a_method)
        c["api_url"] = c.get("api_url", a_url)
        c["api_headers"] = c.get("api_headers", a_headers)
        c["api_body"] = c.get("api_body", a_body)
        c["api_source_curl"] = _build_curl_from_request(
            c["api_method"], c["api_url"], c["api_headers"], c["api_body"]
        )
        c["request_config"] = {
            "method": c["api_method"],
            "url": c["api_url"],
            "headers": c["api_headers"],
            "body": c["api_body"],
        }


def renumber_api_business_ids(cases: List[Dict[str, Any]]) -> None:
    for i, c in enumerate(cases):
        if not isinstance(c, dict):
            continue
        new_bid = f"API-{i + 1}"
        old_name = str(c.get("case_name") or "")
        stripped = re.sub(r"^\[API-\d+\]\s*", "", old_name).strip() or old_name.strip()
        c["business_id"] = new_bid
        c["case_name"] = f"[{new_bid}] {stripped}"[:255]
