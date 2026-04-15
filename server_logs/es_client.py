"""
Elasticsearch 客户端：统一从 Django settings / 环境变量读取，避免多处硬编码。
"""

from __future__ import annotations

from typing import Any


def get_server_logs_es_index() -> str:
    from django.conf import settings

    v = getattr(settings, "SERVER_LOGS_ES_INDEX", "server-logs")
    s = str(v or "").strip()
    return s or "server-logs"


def get_elasticsearch_client():
    from django.conf import settings
    from elasticsearch import Elasticsearch

    url = str(
        getattr(settings, "ELASTICSEARCH_URL", "http://localhost:9200") or ""
    ).strip()
    if not url:
        url = "http://localhost:9200"
    user = str(getattr(settings, "ELASTICSEARCH_USER", "") or "").strip()
    password = getattr(settings, "ELASTICSEARCH_PASSWORD", None)
    if password is not None and not isinstance(password, str):
        password = str(password)
    password = (password or "").strip()
    verify = bool(getattr(settings, "ELASTICSEARCH_VERIFY_CERTS", False))
    # 服务器日志模块的 ES 访问属于“可选增强能力”，必须快速失败，避免阻塞页面其它操作。
    timeout = int(getattr(settings, "ELASTICSEARCH_REQUEST_TIMEOUT", 2) or 2)

    kwargs: dict[str, Any] = {
        "verify_certs": verify,
        "request_timeout": timeout,
        # 快速失败：ES 不可用时不要重试拖慢请求
        "max_retries": 0,
        "retry_on_timeout": False,
    }
    if password:
        kwargs["basic_auth"] = (user or "elastic", password)
    return Elasticsearch(url, **kwargs)
