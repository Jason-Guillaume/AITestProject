from __future__ import annotations

import os
import socket
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.db import connections

from testcase.models import EnvironmentHealthCheck


class HealthChecker:
    """任务执行前环境健康检查工具。"""

    def _record(
        self,
        *,
        check_type: str,
        status: str,
        response_time_ms: int,
        target: str = "",
        error_log: str = "",
        dimension: Optional[Dict[str, Any]] = None,
    ) -> EnvironmentHealthCheck:
        return EnvironmentHealthCheck.objects.create(
            check_type=check_type,
            status=status,
            response_time_ms=max(int(response_time_ms), 0),
            target=target or "",
            error_log=(error_log or "")[:4000],
            dimension=dimension or {},
        )

    def check_db(self, config: Optional[Dict[str, Any]] = None, *, dimension=None) -> Dict[str, Any]:
        start = time.perf_counter()
        target = "default-db"
        try:
            if config:
                host = str(config.get("host", "127.0.0.1"))
                port = int(config.get("port", 3306))
                target = f"{host}:{port}"
                with socket.create_connection((host, port), timeout=3):
                    pass
            else:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            elapsed = int((time.perf_counter() - start) * 1000)
            self._record(
                check_type=EnvironmentHealthCheck.CHECK_DB,
                status=EnvironmentHealthCheck.STATUS_HEALTHY,
                response_time_ms=elapsed,
                target=target,
                dimension=dimension,
            )
            return {"ok": True, "check_type": "db", "response_time_ms": elapsed}
        except Exception as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            self._record(
                check_type=EnvironmentHealthCheck.CHECK_DB,
                status=EnvironmentHealthCheck.STATUS_UNHEALTHY,
                response_time_ms=elapsed,
                target=target,
                error_log=str(exc),
                dimension=dimension,
            )
            return {"ok": False, "check_type": "db", "response_time_ms": elapsed, "error": str(exc)}

    def check_api(self, url: str, *, dimension=None) -> Dict[str, Any]:
        start = time.perf_counter()
        target = url or ""
        try:
            if not url:
                raise ValueError("缺少 API URL")
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise ValueError("API URL 非法")
            resp = requests.head(url, timeout=5, allow_redirects=True)
            elapsed = int((time.perf_counter() - start) * 1000)
            ok = 200 <= resp.status_code < 400
            self._record(
                check_type=EnvironmentHealthCheck.CHECK_API,
                status=EnvironmentHealthCheck.STATUS_HEALTHY if ok else EnvironmentHealthCheck.STATUS_UNHEALTHY,
                response_time_ms=elapsed,
                target=target,
                error_log="" if ok else f"status_code={resp.status_code}",
                dimension=dimension,
            )
            return {
                "ok": ok,
                "check_type": "api",
                "response_time_ms": elapsed,
                "status_code": resp.status_code,
            }
        except Exception as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            self._record(
                check_type=EnvironmentHealthCheck.CHECK_API,
                status=EnvironmentHealthCheck.STATUS_UNHEALTHY,
                response_time_ms=elapsed,
                target=target,
                error_log=str(exc),
                dimension=dimension,
            )
            return {"ok": False, "check_type": "api", "response_time_ms": elapsed, "error": str(exc)}

    def check_redis(self, *, dimension=None) -> Dict[str, Any]:
        start = time.perf_counter()
        host = os.environ.get("REDIS_HOST", "127.0.0.1")
        port = int(os.environ.get("REDIS_PORT", "6379"))
        target = f"{host}:{port}"
        try:
            with socket.create_connection((host, port), timeout=2):
                pass
            elapsed = int((time.perf_counter() - start) * 1000)
            self._record(
                check_type=EnvironmentHealthCheck.CHECK_REDIS,
                status=EnvironmentHealthCheck.STATUS_HEALTHY,
                response_time_ms=elapsed,
                target=target,
                dimension=dimension,
            )
            return {"ok": True, "check_type": "redis", "response_time_ms": elapsed}
        except Exception as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            self._record(
                check_type=EnvironmentHealthCheck.CHECK_REDIS,
                status=EnvironmentHealthCheck.STATUS_UNHEALTHY,
                response_time_ms=elapsed,
                target=target,
                error_log=str(exc),
                dimension=dimension,
            )
            return {"ok": False, "check_type": "redis", "response_time_ms": elapsed, "error": str(exc)}

    def check_before_task(
        self,
        *,
        api_url: str,
        db_config: Optional[Dict[str, Any]] = None,
        dimension: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        results = [
            self.check_db(db_config, dimension=dimension),
            self.check_api(api_url, dimension=dimension),
            self.check_redis(dimension=dimension),
        ]
        unhealthy = [x for x in results if not x.get("ok")]
        return {"ok": len(unhealthy) == 0, "results": results, "unhealthy": unhealthy}

    def send_alert_email(self, *, task_name: str, summary: Dict[str, Any]):
        admins = [x.strip() for x in (getattr(settings, "USER_CENTER_ADMIN_EMAIL", "") or "").split(",") if x.strip()]
        if not admins:
            admins = [email for _, email in (getattr(settings, "ADMINS", []) or []) if email]
        if not admins:
            return
        subject = f"[AITest] 环境健康检查告警 - {task_name}"
        unhealthy_lines = []
        for item in summary.get("unhealthy", []):
            unhealthy_lines.append(
                f"- {item.get('check_type')}: {item.get('error') or item.get('status_code')}"
            )
        body = "任务执行前健康检查失败，任务已取消。\n\n" + "\n".join(unhealthy_lines)
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "webmaster@localhost"),
            recipient_list=admins,
            fail_silently=True,
        )
