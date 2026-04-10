from __future__ import annotations

import uuid

from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from execution.engine import APIExecutor
from execution.models import ExecutionTask


@shared_task(
    bind=True,
    name="execution.run_execution_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    soft_time_limit=60,
    time_limit=75,
)
def run_execution_task(self, execution_task_id: int) -> dict:
    """
    异步执行单个 API 测试任务，并将执行结果写回 ExecutionTask。
    """
    lock_key = f"execution_task_lock:{execution_task_id}"
    lock_token = str(uuid.uuid4())
    trace_id = self.request.id or lock_token
    got_lock = cache.add(lock_key, lock_token, timeout=180)
    if not got_lock:
        return {"skipped": True, "reason": "任务正在执行中"}

    with transaction.atomic():
        task = ExecutionTask.objects.select_for_update().get(
            pk=execution_task_id, is_deleted=False
        )
        if task.status == ExecutionTask.STATUS_RUNNING:
            cache.delete(lock_key)
            return {"skipped": True, "reason": "任务已在运行态"}
        task.status = ExecutionTask.STATUS_RUNNING
        task.started_at = timezone.now()
        task.finished_at = None
        task.duration_ms = None
        task.error_message = ""
        task.celery_task_id = self.request.id or ""
        task.save(
            update_fields=[
                "status",
                "started_at",
                "finished_at",
                "duration_ms",
                "error_message",
                "celery_task_id",
                "update_time",
            ]
        )

    executor = APIExecutor()
    try:
        report = executor.execute(task)
    except Exception as exc:
        err_text = str(exc)
        task.status = ExecutionTask.STATUS_FAILED
        task.finished_at = timezone.now()
        task.error_message = "环境健康检查失败，任务已取消" if err_text.startswith("ENV_UNHEALTHY:") else err_text
        task.report = {
            "passed": False,
            "trace_id": trace_id,
            "cancelled": err_text.startswith("ENV_UNHEALTHY:"),
            "error": err_text,
        }
        task.save(
            update_fields=[
                "status",
                "finished_at",
                "error_message",
                "report",
                "update_time",
            ]
        )
        if err_text.startswith("ENV_UNHEALTHY:"):
            return task.report
        raise self.retry(exc=exc)
    finally:
        cache.delete(lock_key)

    task.duration_ms = report.get("duration_ms")
    task.finished_at = timezone.now()
    report["trace_id"] = trace_id
    task.report = report
    task.status = (
        ExecutionTask.STATUS_COMPLETED
        if report.get("passed")
        else ExecutionTask.STATUS_FAILED
    )
    if not report.get("passed"):
        task.error_message = "断言未通过"
    task.save(
        update_fields=[
            "status",
            "finished_at",
            "duration_ms",
            "report",
            "error_message",
            "update_time",
        ]
    )
    return report


try:
    from execution import tasks_k6  # noqa: F401  — 注册 k6 压测 Celery 任务
except ImportError:
    pass
