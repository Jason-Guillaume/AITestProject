from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


try:
    from celery import shared_task

    try:
        from celery.exceptions import MaxRetriesExceededError
    except Exception:  # pragma: no cover
        class MaxRetriesExceededError(Exception):
            pass

    _CELERY_AVAILABLE = True
except Exception:  # pragma: no cover
    shared_task = None  # type: ignore
    MaxRetriesExceededError = Exception  # type: ignore
    _CELERY_AVAILABLE = False


def _es_client():
    from server_logs.es_client import get_elasticsearch_client

    return get_elasticsearch_client()


if _CELERY_AVAILABLE:

    @shared_task(bind=True, autoretry_for=(), retry_backoff=False, retry_jitter=False)  # type: ignore[misc]
    def index_server_log_doc(self, doc: dict) -> None:
        """
        将单条日志写入 Elasticsearch（由 Celery worker 执行）。

        约束：写入失败不得抛出导致 worker 崩溃；若 ES 暂不可用，由平台运维自行处理重试策略。
        """
        try:
            from server_logs.es_client import get_server_logs_es_index

            es = _es_client()
            es.index(index=get_server_logs_es_index(), document=doc)
        except Exception as e:
            logger.debug("celery es index failed: %s", str(e)[:200])

    @shared_task(
        bind=True,
        autoretry_for=(Exception,),
        retry_backoff=True,
        retry_backoff_max=60,
        retry_jitter=True,
        max_retries=4,
    )  # type: ignore[misc]
    def index_server_log_docs_bulk(self, docs: list[dict]) -> None:
        """
        批量写入 Elasticsearch（bulk），用于降低 broker/worker 开销。

        - docs 为空时直接返回
        - ES/网络抖动：自动重试（指数退避 + jitter）
        - 超过重试次数：记录 warning（不抛异常，避免无限重试风暴）
        """
        if not docs:
            return
        try:
            from elasticsearch.helpers import bulk  # type: ignore

            from server_logs.es_client import get_server_logs_es_index

            es = _es_client()
            idx = get_server_logs_es_index()
            actions = [{"_index": idx, "_source": d} for d in docs if isinstance(d, dict) and d]
            if not actions:
                return
            # raise_on_error=True：任何单条失败会抛 BulkIndexError，便于触发 Celery 重试
            bulk(es, actions, raise_on_error=True, raise_on_exception=True, request_timeout=15)
        except Exception as e:
            try:
                raise self.retry(exc=e)  # type: ignore[misc]
            except MaxRetriesExceededError:
                logger.warning(
                    "celery es bulk index gave up after retries: docs=%s err=%s",
                    len(docs or []),
                    str(e)[:300],
                )

    @shared_task(bind=True, max_retries=2, default_retry_delay=5)  # type: ignore[misc]
    def run_log_auto_ticket_job(
        self,
        job_id: int,
        *,
        api_key: str = "",
        api_base_url: str = "",
        model: str = "",
    ) -> None:
        """
        后台生成「缺陷工单草稿」：复用 ES 上下文 + 结构化 JSON 模型输出。
        """
        from django.db import transaction

        from server_logs.ai_ticket import analyze_log_ticket_draft
        from server_logs.audit import log_server_log_event
        from server_logs.defect_create import create_test_defect_from_auto_ticket
        from server_logs.log_context import fetch_es_context_for_anchor
        from server_logs.models import LogAutoTicketJob, LogAutoTicketJobStatus, ServerLogAuditEvent

        job = (
            LogAutoTicketJob.objects.select_related(
                "remote_log_server",
                "user",
                "defect_handler",
                "defect_release_version",
                "defect_module",
            )
            .filter(pk=job_id)
            .first()
        )
        if not job:
            logger.warning("run_log_auto_ticket_job: missing job_id=%s", job_id)
            return

        srv = job.remote_log_server
        try:
            with transaction.atomic():
                locked = (
                    LogAutoTicketJob.objects.select_for_update()
                    .filter(pk=job_id, status=LogAutoTicketJobStatus.PENDING)
                    .first()
                )
                if not locked:
                    return
                locked.status = LogAutoTicketJobStatus.PROCESSING
                locked.save(update_fields=["status", "updated_at"])
        except Exception as e:
            logger.exception("run_log_auto_ticket_job lock failed job_id=%s", job_id)
            try:
                raise self.retry(exc=e)  # type: ignore[misc]
            except MaxRetriesExceededError:
                LogAutoTicketJob.objects.filter(pk=job_id).update(
                    status=LogAutoTicketJobStatus.FAILED,
                    error_message=str(e)[:2000],
                )
            return

        server_id = srv.id
        anchor_ts = int(job.anchor_ts) if job.anchor_ts is not None else None
        context_lines, ctx_meta = fetch_es_context_for_anchor(
            server_id=server_id,
            anchor_text=job.anchor_text,
            anchor_ts=anchor_ts,
            window_seconds=int(job.window_seconds),
            limit=int(job.es_limit),
        )

        draft, err = analyze_log_ticket_draft(
            anchor_text=job.anchor_text,
            context_lines=context_lines,
            server_name=getattr(srv, "name", None),
            time_window_seconds=int(job.window_seconds),
            api_key_override=api_key or "",
            api_base_override=api_base_url or "",
            model_override=model or "",
        )

        meta: dict[str, object] = {"es": ctx_meta, "context_line_count": len(context_lines)}
        u = job.user
        if err:
            LogAutoTicketJob.objects.filter(pk=job_id).update(
                status=LogAutoTicketJobStatus.FAILED,
                error_message=err[:4000],
                meta=meta,
            )
            if u and getattr(u, "is_authenticated", False):
                log_server_log_event(
                    u,
                    ServerLogAuditEvent.Action.AUTO_TICKET,
                    meta={"job_id": job_id, "success": False, "error": err[:500]},
                    remote_server=srv,
                    client_ip="celery",
                )
            return

        created_defect_pk: int | None = None
        if getattr(job, "create_defect_requested", False) and draft:
            d_obj, derr = create_test_defect_from_auto_ticket(job, draft)
            if d_obj:
                meta["defect_create"] = {
                    "success": True,
                    "defect_id": d_obj.id,
                    "defect_no": d_obj.defect_no,
                }
                created_defect_pk = d_obj.id
            else:
                meta["defect_create"] = {"success": False, "error": (derr or "")[:800]}
        else:
            meta["defect_create"] = {"skipped": True}

        LogAutoTicketJob.objects.filter(pk=job_id).update(
            status=LogAutoTicketJobStatus.SUCCESS,
            draft=draft,
            meta=meta,
            error_message="",
            created_defect_id=created_defect_pk,
        )
        if u and getattr(u, "is_authenticated", False):
            log_server_log_event(
                u,
                ServerLogAuditEvent.Action.AUTO_TICKET,
                meta={
                    "job_id": job_id,
                    "success": True,
                    "title": (draft or {}).get("title", "")[:120],
                    "severity": (draft or {}).get("severity"),
                    "defect_id": created_defect_pk,
                },
                remote_server=srv,
                client_ip="celery",
            )

