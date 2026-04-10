"""
不依赖大模型时，由 API 链路确定性生成 k6 JavaScript 脚本。
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List


def _duration_literal(duration: str) -> str:
    d = (duration or "30s").strip()
    if not re.match(r"^\d+[smh]$", d):
        return "30s"
    return d


def _escape_js_string(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def _headers_object(headers: Dict[str, Any]) -> str:
    h = dict(headers or {})
    merged = {"Content-Type": "application/json", **h}
    return json.dumps(merged, ensure_ascii=False)


def _body_argument(body: Any, method: str) -> str:
    m = (method or "GET").upper()
    if m in ("GET", "HEAD", "DELETE", "OPTIONS") or body in (None, {}, []):
        return "null"
    raw = json.dumps(body, ensure_ascii=False)
    return f"JSON.parse({_escape_js_string(raw)})"


def build_k6_script(
    steps: List[Dict[str, Any]],
    vus: int,
    duration: str,
) -> str:
    vus = max(1, min(int(vus or 1), 500))
    dur = _duration_literal(duration)

    lines = [
        "import http from 'k6/http';",
        "import { check, sleep } from 'k6';",
        "",
        f"export const options = {{ vus: {vus}, duration: {_escape_js_string(dur)} }};",
        "",
        "export default function () {",
    ]

    for i, st in enumerate(steps):
        method = (st.get("method") or "GET").upper()
        url_js = _escape_js_string(st.get("url") or "")
        hdr_js = _headers_object(st.get("headers") or {})
        body_js = _body_argument(st.get("body"), method)
        exp = st.get("expected_status")
        check_name = f"step_{i + 1}_ok"

        if method == "GET":
            lines.append(f"  let res{i} = http.get({url_js}, {{ headers: {hdr_js} }});")
        elif method == "POST":
            lines.append(
                f"  let res{i} = http.post({url_js}, {body_js}, {{ headers: {hdr_js} }});"
            )
        elif method == "PUT":
            lines.append(
                f"  let res{i} = http.put({url_js}, {body_js}, {{ headers: {hdr_js} }});"
            )
        elif method == "PATCH":
            lines.append(
                f"  let res{i} = http.patch({url_js}, {body_js}, {{ headers: {hdr_js} }});"
            )
        elif method == "DELETE":
            lines.append(
                f"  let res{i} = http.del({url_js}, null, {{ headers: {hdr_js} }});"
            )
        else:
            lines.append(
                f"  let res{i} = http.request({_escape_js_string(method)}, {url_js}, {body_js}, {{ headers: {hdr_js} }});"
            )

        if exp is not None:
            lines.append(
                f"  check(res{i}, {{ '{check_name}': (r) => r.status === {int(exp)} }});"
            )
        else:
            lines.append(
                f"  check(res{i}, {{ '{check_name}': (r) => r.status >= 200 && r.status < 300 }});"
            )
        lines.append("  sleep(0.2);")

    lines.append("}")
    lines.append("")
    return "\n".join(lines)
