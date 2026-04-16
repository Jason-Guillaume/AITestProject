from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SecurityFinding:
    rule_id: str
    severity: str  # low/medium/high
    title: str
    description: str
    method: str = "GET"
    url: str = ""
    payload: dict | list | str | None = None
    tags: list[str] | None = None

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "suggested_request": {
                "method": self.method,
                "url": self.url,
                "body": self.payload,
            },
            "tags": self.tags or [],
        }


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
        return json.loads(t)


def _iter_openapi_ops(spec: dict) -> list[dict]:
    paths = spec.get("paths") or {}
    if not isinstance(paths, dict):
        return []
    ops: list[dict] = []
    for p, methods in paths.items():
        if not isinstance(p, str) or not isinstance(methods, dict):
            continue
        for m, op in methods.items():
            mm = str(m or "").lower()
            if mm not in ("get", "post", "put", "delete", "patch"):
                continue
            if not isinstance(op, dict):
                continue
            ops.append({"path": p, "method": mm.upper(), "op": op})
    return ops


def generate_security_findings_from_openapi(
    *,
    openapi_spec_text: str,
    base_url: str = "",
    scopes: Optional[list[str]] = None,
    max_findings: int = 50,
) -> list[dict]:
    """
    规则优先的安全用例生成：
    - 不依赖大模型
    - 输出为 findings（可解释、可复现、可审计）
    """
    spec_any = _safe_load_yaml_or_json(openapi_spec_text)
    if not isinstance(spec_any, dict):
        raise ValueError("openapi_spec 必须为 JSON/YAML 对象")
    scopes = [str(s).strip().lower() for s in (scopes or []) if str(s).strip()]
    allow_all = not scopes

    ops = _iter_openapi_ops(spec_any)
    if not ops:
        raise ValueError("openapi_spec 未发现 paths 下的可用接口")

    findings: list[SecurityFinding] = []

    def full_url(p: str) -> str:
        b = (base_url or "").strip().rstrip("/")
        if not b:
            return p
        if p.startswith("/"):
            return f"{b}{p}"
        return f"{b}/{p}"

    # R-001: IDOR/越权：路径含 /{id} 或常见 id 参数
    if allow_all or "idor" in scopes or "authz" in scopes:
        for it in ops:
            path = it["path"]
            if re.search(r"\{[^}]*id[^}]*\}", path, flags=re.I) or re.search(
                r"/\d+($|/)", path
            ):
                findings.append(
                    SecurityFinding(
                        rule_id="R-001-IDOR",
                        severity="high",
                        title="越权/IDOR 检查（对象级权限）",
                        description=(
                            "对包含对象 ID 的资源接口，验证普通用户不能读取/修改他人对象。"
                            "建议准备两套用户与资源 ID，分别执行并比较返回码与数据差异。"
                        ),
                        method=it["method"],
                        url=full_url(path),
                        tags=["idor", "authz"],
                    )
                )

    # R-002: 注入：query 参数或 body 字段可疑（name=*, q=*, filter/sort）
    if allow_all or "injection" in scopes:
        needles = ["search", "query", "q", "filter", "sort", "order", "where", "sql"]
        for it in ops:
            op = it["op"]
            params = op.get("parameters") or []
            hit = False
            if isinstance(params, list):
                for p in params[:50]:
                    if not isinstance(p, dict):
                        continue
                    name = str(p.get("name") or "").lower()
                    if any(n in name for n in needles):
                        hit = True
                        break
            if hit:
                findings.append(
                    SecurityFinding(
                        rule_id="R-002-INJECTION",
                        severity="high",
                        title="注入类风险检查（SQL/表达式/过滤条件）",
                        description=(
                            "对 search/filter/sort 等参数进行注入测试："
                            "如 '\" or 1=1 --'、'${jndi:ldap://...}'、'../../' 等，观察是否报错泄露或绕过。"
                        ),
                        method=it["method"],
                        url=full_url(it["path"]),
                        payload=None,
                        tags=["injection"],
                    )
                )

    # R-003: 敏感信息：返回字段可能含 password/token/secret
    if allow_all or "sensitive" in scopes:
        findings.append(
            SecurityFinding(
                rule_id="R-003-SENSITIVE-DATA",
                severity="medium",
                title="敏感信息泄露检查（响应字段/日志）",
                description=(
                    "检查响应体与错误信息中是否包含 password/token/secret/key 等敏感字段明文；"
                    "并确认审计/日志输出已脱敏。"
                ),
                method="GET",
                url="（对关键列表/详情接口执行）",
                tags=["sensitive", "privacy"],
            )
        )

    # R-004: 认证缺失：spec 未声明 security（启发式）
    if allow_all or "authn" in scopes:
        has_security = bool(spec_any.get("security")) or bool(
            (spec_any.get("components") or {}).get("securitySchemes")
        )
        if not has_security:
            findings.append(
                SecurityFinding(
                    rule_id="R-004-AUTH-MISSING",
                    severity="high",
                    title="认证声明缺失（OpenAPI 未声明 security）",
                    description=(
                        "OpenAPI 未声明 securitySchemes/security，可能导致调用方误以为接口无需鉴权。"
                        "建议补齐鉴权声明并对匿名请求做 401/403 验证。"
                    ),
                    method="GET",
                    url="（全局）",
                    tags=["authn"],
                )
            )

    out = [f.to_dict() for f in findings[: max(1, min(int(max_findings or 50), 200))]]
    return out


_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}")
_IDCARD_RE = re.compile(r"\\b\\d{17}[0-9Xx]\\b")
_TOKEN_LIKE_RE = re.compile(r"\\b(?:eyJ[a-zA-Z0-9_-]{10,}|[A-Za-z0-9_-]{32,})\\b")


def analyze_execution_log_security(
    *,
    response_status: int | None,
    response_text: str,
    response_headers: dict | None,
) -> list[dict]:
    """
    针对单条执行结果做轻量安全信号分析（不等价于渗透，仅用于“早期预警”）。
    """
    txt = (response_text or "")[:20000]
    headers = response_headers if isinstance(response_headers, dict) else {}
    findings: list[SecurityFinding] = []

    if response_status is not None and int(response_status) >= 500:
        findings.append(
            SecurityFinding(
                rule_id="E-500-ERROR-LEAK",
                severity="medium",
                title="疑似内部错误（500）",
                description="服务端返回 5xx，需检查是否暴露堆栈/SQL/敏感配置；并确认错误信息已对外收敛。",
                tags=["error", "leak"],
            )
        )

    if "set-cookie" in {str(k).lower() for k in headers.keys()}:
        ck = str(headers.get("set-cookie") or "")
        if "httponly" not in ck.lower() or "secure" not in ck.lower():
            findings.append(
                SecurityFinding(
                    rule_id="H-COOKIE-FLAGS",
                    severity="low",
                    title="Cookie 安全属性检查",
                    description="Set-Cookie 可能缺少 HttpOnly/Secure/SameSite 等属性，建议对登录态 Cookie 配置安全属性。",
                    tags=["cookie"],
                )
            )

    if _EMAIL_RE.search(txt) or _IDCARD_RE.search(txt):
        findings.append(
            SecurityFinding(
                rule_id="D-PII-LEAK",
                severity="high",
                title="疑似 PII 泄露（邮箱/身份证）",
                description="响应体中出现邮箱或身份证号模式字符串，需确认是否符合脱敏/最小返回原则。",
                tags=["pii", "privacy"],
            )
        )

    if _TOKEN_LIKE_RE.search(txt) and ("token" in txt.lower() or "authorization" in txt.lower()):
        findings.append(
            SecurityFinding(
                rule_id="D-TOKEN-LEAK",
                severity="high",
                title="疑似 Token 泄露",
                description="响应体中出现疑似 token 字符串，需确认是否应返回、是否已做脱敏，以及是否会被日志/审计记录明文持久化。",
                tags=["token", "leak"],
            )
        )

    return [f.to_dict() for f in findings]

