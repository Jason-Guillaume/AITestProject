from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple


def _safe_load_yaml_or_json(text: str) -> Any:
    t = (text or "").strip()
    if not t:
        return None
    if t[0] in ("{", "["):
        return json.loads(t)
    try:
        import yaml  # type: ignore

        return yaml.safe_load(t)
    except Exception:
        # 兜底：按 JSON 再试一次
        return json.loads(t)


def _pick_first_server_base(spec: dict) -> str:
    servers = spec.get("servers")
    if isinstance(servers, list) and servers:
        u = (servers[0] or {}).get("url")
        if isinstance(u, str) and u.strip():
            return u.strip().rstrip("/")
    return ""


def _iter_openapi_ops(spec: dict) -> List[dict]:
    paths = spec.get("paths") or {}
    if not isinstance(paths, dict):
        return []
    ops: List[dict] = []
    for p, methods in paths.items():
        if not isinstance(p, str) or not isinstance(methods, dict):
            continue
        for m, op in methods.items():
            mm = str(m or "").lower()
            if mm not in ("get", "post", "put", "delete", "patch", "head", "options"):
                continue
            if not isinstance(op, dict):
                continue
            ops.append({"path": p, "method": mm.upper(), "op": op})
    return ops


def _guess_is_login(path: str, op: dict) -> bool:
    blob = f"{path} {op.get('operationId','')} {op.get('summary','')} {op.get('description','')}".lower()
    needles = ["login", "signin", "sign-in", "auth", "token", "oauth", "session"]
    return any(n in blob for n in needles)


def _request_body_template(op: dict) -> Dict[str, Any]:
    rb = op.get("requestBody") or {}
    if not isinstance(rb, dict):
        return {}
    content = rb.get("content") or {}
    if not isinstance(content, dict):
        return {}
    app_json = content.get("application/json") or content.get("application/*+json") or {}
    if not isinstance(app_json, dict):
        return {}
    schema = app_json.get("schema") or {}
    if not isinstance(schema, dict):
        return {}
    props = schema.get("properties") or {}
    if not isinstance(props, dict):
        return {}
    out: Dict[str, Any] = {}
    for i, k in enumerate(list(props.keys())[:10]):
        out[str(k)] = f"${{{k}}}"
        if i >= 9:
            break
    return out


def _expected_status(op: dict) -> int | None:
    responses = op.get("responses") or {}
    if not isinstance(responses, dict):
        return None
    # 优先 200/201/204
    for k in ("200", "201", "204"):
        if k in responses:
            try:
                return int(k)
            except Exception:
                return None
    # 兜底：任取一个 2xx
    for k in responses.keys():
        s = str(k)
        if s.isdigit() and 200 <= int(s) < 300:
            return int(s)
    return None


def _detect_bearer_auth(spec: dict) -> bool:
    comps = spec.get("components") or {}
    if isinstance(comps, dict):
        sec = comps.get("securitySchemes") or {}
        if isinstance(sec, dict):
            for _, v in sec.items():
                if not isinstance(v, dict):
                    continue
                if str(v.get("type") or "").lower() == "http" and str(
                    v.get("scheme") or ""
                ).lower() == "bearer":
                    return True
    # global security
    sec2 = spec.get("security")
    return bool(sec2)


def build_scenario_draft_from_openapi(
    *,
    openapi_spec_text: str,
    base_url: str = "",
    scenario_name: str = "",
    max_steps: int = 30,
) -> Dict[str, Any]:
    spec_any = _safe_load_yaml_or_json(openapi_spec_text)
    if not isinstance(spec_any, dict):
        raise ValueError("openapi_spec 必须为 JSON/YAML 对象")

    base = (base_url or "").strip().rstrip("/") or _pick_first_server_base(spec_any)
    ops = _iter_openapi_ops(spec_any)
    if not ops:
        raise ValueError("openapi_spec 未发现 paths 下的可用接口")

    # 让登录/鉴权类接口尽量排前
    ops.sort(key=lambda x: (0 if _guess_is_login(x["path"], x["op"]) else 1, x["path"]))
    ops = ops[: max(1, min(int(max_steps or 30), 100))]

    use_bearer = _detect_bearer_auth(spec_any)
    default_vars: Dict[str, Any] = {}
    if use_bearer:
        default_vars["token"] = ""

    steps: List[dict] = []
    for idx, it in enumerate(ops, start=1):
        path = it["path"]
        method = it["method"]
        op = it["op"]
        title = str(op.get("summary") or op.get("operationId") or "").strip()
        if not title:
            title = f"{method} {path}"

        url = f"{base}{path}" if base and path.startswith("/") else (f"{base}/{path}".rstrip("/") if base and not path.startswith("/") else path)
        headers: Dict[str, Any] = {}
        body = _request_body_template(op)
        if body and method in ("POST", "PUT", "PATCH"):
            headers["Content-Type"] = "application/json"
        if use_bearer:
            headers.setdefault("Authorization", "Bearer ${token}")

        expected = _expected_status(op)
        steps.append(
            {
                "order": idx,
                "name": title[:255],
                "request": {
                    "method": method,
                    "url": url[:2048],
                    "headers": headers,
                    "body": body,
                    "expected_status": expected,
                },
                # 对“登录/取 token”接口给一个默认提取规则（启发式）
                "extraction_rules": (
                    [
                        {"var_name": "token", "source": "body", "expression": "$.data.token"},
                        {"var_name": "token", "source": "body", "expression": "$.token"},
                    ]
                    if use_bearer and _guess_is_login(path, op)
                    else []
                ),
            }
        )

    name = (scenario_name or "").strip()
    if not name:
        name = f"OpenAPI 场景草稿（{len(steps)} 步）"
    return {"scenario": {"name": name[:255], "default_variables": default_vars}, "steps": steps}


_CURL_METHOD_RE = re.compile(r"\s-X\s+([A-Za-z]+)\s")
_CURL_URL_RE = re.compile(r"curl\s+(?:-s\s+)?(?:-k\s+)?(?P<url>https?://[^\s'\"\\]+|/[^\\s'\"\\]+)")
_CURL_HEADER_RE = re.compile(r"-H\\s+'([^']+)'|-H\\s+\"([^\"]+)\"")
_CURL_DATA_RE = re.compile(r"--data-raw\\s+'([\\s\\S]*?)'|--data\\s+'([\\s\\S]*?)'|-d\\s+'([\\s\\S]*?)'")


def build_scenario_draft_from_curl_list(
    *,
    curl_list: List[str],
    scenario_name: str = "",
    max_steps: int = 30,
) -> Dict[str, Any]:
    if not isinstance(curl_list, list) or not curl_list:
        raise ValueError("curl_list 必须为非空数组")
    steps: List[dict] = []
    for idx, raw in enumerate(curl_list[: max(1, min(int(max_steps or 30), 100))], start=1):
        s = str(raw or "").strip()
        if not s:
            continue
        m = _CURL_METHOD_RE.search(s)
        method = (m.group(1) if m else "GET").upper()
        um = _CURL_URL_RE.search(s)
        url = (um.group("url") if um else "").strip()
        if not url:
            continue
        headers: Dict[str, Any] = {}
        for hm in _CURL_HEADER_RE.finditer(s):
            hv = hm.group(1) or hm.group(2) or ""
            if ":" in hv:
                k, v = hv.split(":", 1)
                headers[k.strip()] = v.strip()
        body: Any = {}
        dm = _CURL_DATA_RE.search(s)
        if dm:
            data = dm.group(1) or dm.group(2) or dm.group(3) or ""
            data = data.strip()
            if data:
                try:
                    body = json.loads(data)
                except Exception:
                    body = {"raw": data[:4000]}
        name = f"{method} {url}"
        steps.append(
            {
                "order": idx,
                "name": name[:255],
                "request": {
                    "method": method,
                    "url": url[:2048],
                    "headers": headers,
                    "body": body,
                    "expected_status": None,
                },
                "extraction_rules": [],
            }
        )
    if not steps:
        raise ValueError("curl_list 无有效 curl")
    name = (scenario_name or "").strip() or f"cURL 场景草稿（{len(steps)} 步）"
    return {"scenario": {"name": name[:255], "default_variables": {}}, "steps": steps}

