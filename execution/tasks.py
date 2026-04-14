from __future__ import annotations

import uuid

from celery import shared_task
from celery import group
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from execution.engine import APIExecutor
from execution.models import ExecutionTask, ScheduledTask, ScheduledTaskLog
from testcase.models import TestCase
from testcase.services.case_subtypes import get_api_profile_for_execute
from testcase.services.api_execution import run_api_case


@shared_task(
    bind=True,
    name="execution.run_execution_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
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


@shared_task(
    bind=True,
    name="execution.run_scheduled_api_case",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=2,
    soft_time_limit=300,
    time_limit=330,
)
def run_scheduled_api_case(self, *, scheduled_task_id: int, case_id: int, environment_id: int | None) -> dict:
    case = (
        TestCase.objects.filter(pk=case_id, is_deleted=False)
        .select_related("apitestcase")
        .first()
    )
    if not case:
        return {"case_id": case_id, "skipped": True, "reason": "case_not_found"}
    if case.test_type != TestCase.TEST_TYPE_API:
        return {"case_id": case_id, "skipped": True, "reason": f"non_api:{case.test_type}"}
    api_prof = get_api_profile_for_execute(case)
    if api_prof is None:
        return {"case_id": case.id, "skipped": False, "passed": False, "error": "API 用例扩展数据缺失"}
    result = run_api_case(
        case,
        api_prof,
        overrides={"environment_id": environment_id},
        user=None,
        write_legacy_apilog=False,
    )
    return {
        "case_id": case.id,
        "skipped": False,
        "passed": bool(getattr(result.execution_log, "is_passed", False)),
        "message": result.message or "",
        "trace_id": getattr(result.execution_log, "trace_id", None),
    }


@shared_task(
    bind=True,
    name="execution.run_scheduled_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=2,
    soft_time_limit=3600,
    time_limit=3660,
)
def run_scheduled_task(self, scheduled_task_id: int, *, scheduled_task_log_id: int | None = None) -> dict:
    task = ScheduledTask.objects.filter(pk=scheduled_task_id, is_deleted=False).first()
    if not task:
        return {"skipped": True, "reason": "scheduled_task_not_found"}

    log = None
    if scheduled_task_log_id:
        log = ScheduledTaskLog.objects.filter(pk=scheduled_task_log_id).first()

    env_id = task.environment_id
    cases = list(
        task.test_cases.filter(is_deleted=False)
        .only("id", "test_type")
        .values_list("id", "test_type")
    )
    total = len(cases)
    non_api_ids = [cid for cid, tt in cases if tt != TestCase.TEST_TYPE_API]
    api_ids = [cid for cid, tt in cases if tt == TestCase.TEST_TYPE_API]

    detail: Dict[str, Any] = {
        "task_id": task.id,
        "executed_case_ids": [cid for cid, _ in cases],
        "api_errors": [],
        "skipped_non_api_case_ids": non_api_ids,
    }

    api_failed = 0
    if api_ids:
        jobs = group(
            run_scheduled_api_case.s(
                scheduled_task_id=task.id, case_id=cid, environment_id=env_id
            )
            for cid in api_ids
        )
        results = jobs.apply_async().get(disable_sync_subtasks=False)
        for r in results:
            if r.get("skipped"):
                api_failed += 1
                detail["api_errors"].append({"case_id": r.get("case_id"), "error": r.get("reason")})
                continue
            if not r.get("passed"):
                api_failed += 1
                detail["api_errors"].append({"case_id": r.get("case_id"), "error": r.get("message") or r.get("error") or "断言未通过"})

    end_time = timezone.now()
    api_count = len(api_ids)
    skipped_non_api = len(non_api_ids)
    if api_count > 0 and api_failed >= api_count:
        status = ScheduledTaskLog.STATUS_FAILED
        message = f"共 {total} 条用例，API {api_count} 条均未通过或异常"
        if skipped_non_api:
            message += f"，跳过非 API {skipped_non_api} 条"
        last_st = ScheduledTask.LAST_FAILED
    elif api_count > 0 and api_failed > 0:
        status = ScheduledTaskLog.STATUS_PARTIAL
        message = f"共 {total} 条用例，API {api_count} 条（失败 {api_failed}）"
        if skipped_non_api:
            message += f"，跳过非 API {skipped_non_api} 条"
        last_st = ScheduledTask.LAST_PARTIAL
    elif api_count == 0 and skipped_non_api > 0:
        status = ScheduledTaskLog.STATUS_PARTIAL
        message = f"共 {total} 条用例，均为非 API 类型，已跳过 {skipped_non_api} 条"
        last_st = ScheduledTask.LAST_PARTIAL
    else:
        status = ScheduledTaskLog.STATUS_SUCCESS
        message = f"共触发 {total} 条用例（API: {api_count}）"
        last_st = ScheduledTask.LAST_SUCCESS

    if log:
        log.status = status
        log.message = message
        log.detail = detail
        log.end_time = end_time
        log.save(update_fields=["status", "message", "detail", "end_time", "update_time"])

    ScheduledTask.objects.filter(pk=task.pk).update(
        last_run_time=end_time,
        last_status=last_st,
        last_message=message,
    )
    return {"ok": True, "status": status, "message": message}


try:
    from execution import tasks_k6  # noqa: F401  — 注册 k6 压测 Celery 任务
except ImportError:
    pass
