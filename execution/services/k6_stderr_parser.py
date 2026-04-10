"""
解析 k6 周期性输出到 stderr 的汇总行，提取 QPS、P95、错误率等用于 WebSocket 推送。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class K6LiveSample:
    qps: Optional[float] = None
    http_reqs_total: Optional[int] = None
    p95_ms: Optional[float] = None
    error_rate: Optional[float] = None
    raw_http_req_duration_line: Optional[str] = None

    def to_payload(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.qps is not None:
            d["qps"] = self.qps
        if self.http_reqs_total is not None:
            d["http_reqs_total"] = self.http_reqs_total
        if self.p95_ms is not None:
            d["p95_ms"] = self.p95_ms
        if self.error_rate is not None:
            d["error_rate"] = self.error_rate
        return d

    def has_metrics(self) -> bool:
        return bool(self.to_payload())


_RE_HTTP_REQS = re.compile(
    r"http_reqs\s*\.+\s*:\s*(\d+)\s+([\d.]+)/s",
    re.IGNORECASE,
)
_RE_FAILED = re.compile(
    r"http_req_failed\s*\.+\s*:\s*([\d.]+)%",
    re.IGNORECASE,
)
_RE_P95 = re.compile(r"p\(95\)=([^\s]+)", re.IGNORECASE)


def _parse_duration_token(tok: str) -> Optional[float]:
    t = tok.strip().lower()
    if not t:
        return None
    try:
        if t.endswith("ms"):
            return float(t[:-2])
        if t.endswith("s"):
            return float(t[:-1]) * 1000.0
        if t.endswith("m"):
            return float(t[:-1]) * 60_000.0
        return float(t)
    except ValueError:
        return None


def feed_line(state: K6LiveSample, line: str) -> K6LiveSample:
    line = line.rstrip()
    m = _RE_HTTP_REQS.search(line)
    if m:
        try:
            state.http_reqs_total = int(m.group(1))
            state.qps = float(m.group(2))
        except ValueError:
            pass
    m2 = _RE_FAILED.search(line)
    if m2:
        try:
            state.error_rate = float(m2.group(1)) / 100.0
        except ValueError:
            pass
    if "http_req_duration" in line and "p(95)" in line:
        state.raw_http_req_duration_line = line
        m3 = _RE_P95.search(line)
        if m3:
            ms = _parse_duration_token(m3.group(1))
            if ms is not None:
                state.p95_ms = ms
    return state
