"""
接口关联变量能力：
1) VariableExtractor: 从响应 body/header 提取变量
2) VariableResolver: 将 ${var_name} 占位符替换到后续请求
"""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Tuple

from jsonpath_ng import parse
from jsonpath_ng.exceptions import JsonPathParserError


class VariableExtractor:
    """
    提取规则格式:
    [
      {"var_name": "my_token", "source": "body", "expression": "$.data.token"},
      {"var_name": "content_type", "source": "header", "expression": "Content-Type"},
    ]
    """

    def __init__(self, keep_none_on_error: bool = True):
        self.keep_none_on_error = keep_none_on_error

    def extract(
        self, response_data: Dict[str, Any], extraction_rules: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        :param response_data: {"body": {...}, "headers": {...}}
        :param extraction_rules: 变量提取规则列表
        :return: 提取结果字典（提取失败时按配置写入 None）
        """
        out: Dict[str, Any] = {}

        body = response_data.get("body", {})
        headers = response_data.get("headers", {})
        if not isinstance(headers, dict):
            headers = {}

        for idx, item in enumerate(extraction_rules or []):
            var_name = (item.get("var_name") or "").strip()
            source = (item.get("source") or "").strip().lower()
            expression = (
                item.get("expression") or item.get("rule") or ""  # 兼容旧字段名
            ).strip()

            if not var_name or not source or not expression:
                self._on_error(
                    out,
                    var_name,
                    f"规则不完整（index={idx}），需包含 var_name/source/expression",
                )
                continue

            if source == "body":
                value = self._extract_from_body(body, expression)
                if value is None:
                    self._on_error(
                        out, var_name, f"JSONPath 未命中或表达式非法：{expression}"
                    )
                else:
                    out[var_name] = value
                continue

            if source == "header":
                value = self._extract_from_header(headers, expression)
                if value is None:
                    self._on_error(out, var_name, f"Header 未命中：{expression}")
                else:
                    out[var_name] = value
                continue

            self._on_error(out, var_name, f"不支持的 source：{source}")

        return out

    def _extract_from_body(self, body: Any, jsonpath_expr: str) -> Any:
        try:
            expr = parse(jsonpath_expr)
        except JsonPathParserError:
            return None
        except Exception:
            return None

        try:
            matches = expr.find(body)
        except Exception:
            return None

        if not matches:
            return None
        values = [m.value for m in matches]
        return values[0] if len(values) == 1 else values

    def _extract_from_header(self, headers: Dict[str, Any], key: str) -> Any:
        if key in headers:
            return headers[key]
        lower_map = {str(k).lower(): v for k, v in headers.items()}
        return lower_map.get(key.lower())

    def _on_error(self, out: Dict[str, Any], var_name: str, _msg: str) -> None:
        # 如需接日志系统，可在此接入 logger.warning(_msg)
        if self.keep_none_on_error and var_name:
            out[var_name] = None


_VAR_PATTERN = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
_UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}$"
)
_KEYWORD_HINTS = ("token", "auth", "sid", "id", "uuid", "orderno", "code", "sn")
_COMMON_STATUS_FILTERS = (
    ("code", 200),
    ("msg", "ok"),
    ("status", True),
)


def suggest_extractions(json_data: Any) -> List[Dict[str, str]]:
    """
    根据 JSON 内容自动建议可提取变量。

    返回格式:
    [
      {"field_name": "token", "json_path": "$.data.token", "reason": "键名命中关键词 token"},
      ...
    ]
    """
    suggestions: List[Dict[str, str]] = []
    seen_paths = set()

    def walk(node: Any, path: str, key_name: str = "") -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                next_path = f"{path}.{k}" if path != "$" else f"$.{k}"
                walk(v, next_path, str(k))
            return
        if isinstance(node, list):
            for idx, v in enumerate(node):
                next_path = f"{path}[{idx}]"
                walk(v, next_path, key_name)
            return

        matched, reason = _match_business_signal(key_name, node)
        if not matched:
            return
        if _should_filter_common_status(key_name, node):
            return
        if path in seen_paths:
            return

        seen_paths.add(path)
        # 生成可直接用于 VariableExtractor 的规则草案
        var_name = (
            _to_var_name(key_name)
            or _to_var_name(path.replace("$.", ""))
            or "extracted_var"
        )
        suggestions.append(
            {
                "field_name": key_name,
                "json_path": path,
                "reason": reason,
                "var_name": var_name,
                "source": "body",
                "expression": path,
            }
        )

    walk(json_data, "$")
    return suggestions


def _match_business_signal(key_name: str, value: Any) -> Tuple[bool, str]:
    key_lower = (key_name or "").lower()
    for kw in _KEYWORD_HINTS:
        if kw in key_lower:
            return True, f"键名命中关键词 {kw}"

    if isinstance(value, str):
        v = value.strip()
        if len(v) > 20:
            return True, "值长度大于 20，疑似令牌/会话标识"
        if _UUID_PATTERN.match(v):
            return True, "值匹配 UUID 格式"
    return False, ""


def _should_filter_common_status(key_name: str, value: Any) -> bool:
    key_lower = (key_name or "").lower()
    for k, expected in _COMMON_STATUS_FILTERS:
        if key_lower == k and value == expected:
            return True
    return False


def _to_var_name(name: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z_]+", "_", str(name or ""))
    s = re.sub(r"_+", "_", s).strip("_").lower()
    if not s:
        return ""
    if s[0].isdigit():
        s = f"v_{s}"
    return s


class VariableResolver:
    """
    将数据结构中的 ${var_name} 替换为变量池中的值。
    - 支持 str/dict/list 递归替换
    - missing_policy:
      - "keep": 保留原占位符
      - "empty": 用空串替换
      - "error": 抛出 KeyError
    """

    def __init__(self, missing_policy: str = "keep"):
        if missing_policy not in {"keep", "empty", "error"}:
            raise ValueError("missing_policy 仅支持 keep/empty/error")
        self.missing_policy = missing_policy

    def resolve(self, payload: Any, variables: Dict[str, Any]) -> Any:
        safe_vars = variables or {}
        return self._resolve_any(copy.deepcopy(payload), safe_vars)

    def _resolve_any(self, val: Any, variables: Dict[str, Any]) -> Any:
        if isinstance(val, str):
            return self._resolve_str(val, variables)
        if isinstance(val, dict):
            return {k: self._resolve_any(v, variables) for k, v in val.items()}
        if isinstance(val, list):
            return [self._resolve_any(v, variables) for v in val]
        return val

    def _resolve_str(self, text: str, variables: Dict[str, Any]) -> str:
        def repl(match: re.Match) -> str:
            name = match.group(1)
            if name in variables and variables[name] is not None:
                v = variables[name]
                return v if isinstance(v, str) else str(v)
            if self.missing_policy == "empty":
                return ""
            if self.missing_policy == "error":
                raise KeyError(f"变量未定义: {name}")
            return match.group(0)

        return _VAR_PATTERN.sub(repl, text)
