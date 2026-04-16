from __future__ import annotations

import uuid
from typing import Any, Dict

from celery import shared_task
from celery import group
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from execution.engine import APIExecutor
from execution.models import ExecutionTask, ScheduledTask, ScheduledTaskLog, TestReport
from project.models import ReleasePlanTestCase
from testcase.models import TestCase
from testcase.services.case_subtypes import get_api_profile_for_execute
from testcase.services.api_execution import run_api_case
from execution.services.scenario_runner import run_api_scenario


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
        task.error_message = (
            "环境健康检查失败，任务已取消"
            if err_text.startswith("ENV_UNHEALTHY:")
            else err_text
        )
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
def run_scheduled_api_case(
    self, *, scheduled_task_id: int, case_id: int, environment_id: int | None
) -> dict:
    case = (
        TestCase.objects.filter(pk=case_id, is_deleted=False)
        .select_related("apitestcase")
        .first()
    )
    if not case:
        return {"case_id": case_id, "skipped": True, "reason": "case_not_found"}
    if case.test_type != TestCase.TEST_TYPE_API:
        return {
            "case_id": case_id,
            "skipped": True,
            "reason": f"non_api:{case.test_type}",
        }
    api_prof = get_api_profile_for_execute(case)
    if api_prof is None:
        return {
            "case_id": case.id,
            "skipped": False,
            "passed": False,
            "error": "API 用例扩展数据缺失",
        }
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
    name="execution.run_report_api_case",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=1,
    soft_time_limit=300,
    time_limit=330,
)
def run_report_api_case(
    self, *, report_id: int, case_id: int, environment_id: int | None
) -> dict:
    """
    执行“测试报告关联的 API 用例”单条任务：
    - 产出 testcase.ExecutionLog（run_api_case 内落库）
    - 返回 passed / execution_log_id / trace_id 供汇总
    """
    case = (
        TestCase.objects.filter(pk=case_id, is_deleted=False)
        .select_related("apitestcase")
        .first()
    )
    if not case:
        return {"case_id": case_id, "skipped": True, "reason": "case_not_found"}
    if case.test_type != TestCase.TEST_TYPE_API:
        return {
            "case_id": case_id,
            "skipped": True,
            "reason": f"non_api:{case.test_type}",
        }
    api_prof = get_api_profile_for_execute(case)
    if api_prof is None:
        return {
            "case_id": case.id,
            "skipped": False,
            "passed": False,
            "error": "API 用例扩展数据缺失",
        }
    result = run_api_case(
        case,
        api_prof,
        overrides={"environment_id": environment_id},
        user=None,
        write_legacy_apilog=False,
    )
    ex = getattr(result, "execution_log", None)
    return {
        "case_id": case.id,
        "skipped": False,
        "passed": bool(getattr(ex, "is_passed", False)),
        "execution_log_id": int(getattr(ex, "id", 0) or 0) or None,
        "message": result.message or "",
        "trace_id": getattr(ex, "trace_id", None),
    }


@shared_task(
    bind=True,
    name="execution.run_test_report_execute",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=1,
    soft_time_limit=3600,
    time_limit=3660,
)
def run_test_report_execute(
    self, report_id: int, *, environment_id: int | None = None
) -> dict:
    """
    执行测试报告：
    - 按 report.plan.version(ReleasePlan) 关联的用例集进行执行（仅 API 类型）
    - 汇总通过率/缺陷数，并回写 TestReport 的 trace_id / execution_log_id / request/response 快照摘要
    """
    report = (
        TestReport.objects.filter(pk=int(report_id), is_deleted=False)
        .select_related("plan__version", "plan", "project")
        .first()
    )
    if not report:
        return {"skipped": True, "reason": "report_not_found", "report_id": report_id}

    plan = getattr(report, "plan", None)
    rp = getattr(plan, "version", None) if plan else None
    if not rp:
        return {
            "skipped": True,
            "reason": "plan_or_release_missing",
            "report_id": int(report.id),
        }

    rel = (
        ReleasePlanTestCase.objects.filter(release_plan_id=rp.id, is_deleted=False)
        .values_list("test_case_id", flat=True)
    )
    case_ids = [int(x) for x in list(rel) if int(x or 0) > 0]
    if not case_ids:
        return {"skipped": True, "reason": "no_cases", "report_id": int(report.id)}

    api_ids = list(
        TestCase.objects.filter(
            is_deleted=False,
            id__in=case_ids,
            test_type=TestCase.TEST_TYPE_API,
        )
        .order_by("id")
        .values_list("id", flat=True)
    )
    api_ids = [int(x) for x in api_ids]
    if not api_ids:
        return {
            "skipped": True,
            "reason": "no_api_cases",
            "report_id": int(report.id),
        }

    trace_id = self.request.id or ""
    if not trace_id:
        trace_id = str(uuid.uuid4())

    jobs = group(
        run_report_api_case.s(
            report_id=int(report.id), case_id=int(cid), environment_id=environment_id
        )
        for cid in api_ids
    )
    results = jobs.apply_async().get(disable_sync_subtasks=False)

    passed = 0
    failed = 0
    details = []
    last_ex_log_id = None
    last_req = None
    last_resp = None
    for r in results:
        if r.get("skipped"):
            failed += 1
            details.append(
                {
                    "case_id": r.get("case_id"),
                    "passed": False,
                    "error": r.get("reason"),
                }
            )
            continue
        ok = bool(r.get("passed"))
        if ok:
            passed += 1
        else:
            failed += 1
        ex_id = r.get("execution_log_id")
        if ex_id:
            last_ex_log_id = int(ex_id)
        details.append(
            {
                "case_id": r.get("case_id"),
                "passed": ok,
                "execution_log_id": ex_id,
                "message": r.get("message") or "",
            }
        )

    total = len(api_ids)
    pass_rate = round((passed / total) * 100, 2) if total > 0 else 0

    if last_ex_log_id:
        try:
            from testcase.models import ExecutionLog

            ex = (
                ExecutionLog.objects.filter(pk=last_ex_log_id)
                .only("request_payload", "response_payload")
                .first()
            )
            if ex:
                last_req = ex.request_payload
                last_resp = ex.response_payload
        except Exception:
            last_req = None
            last_resp = None

    with transaction.atomic():
        TestReport.objects.filter(pk=report.id).update(
            trace_id=str(trace_id)[:36],
            execution_log_id=last_ex_log_id,
            request_payload=last_req,
            response_payload={
                "summary": {
                    "total_api": total,
                    "passed": passed,
                    "failed": failed,
                    "pass_rate": pass_rate,
                },
                "details": details[:2000],
                "last_response_payload": last_resp,
            },
            pass_rate=pass_rate,
            defect_count=int(failed),
            environment=getattr(plan, "environment", report.environment),
            req_count=int(getattr(plan, "req_count", report.req_count) or 0),
            case_count=int(getattr(plan, "case_count", report.case_count) or 0),
            coverage_rate=getattr(plan, "coverage_rate", report.coverage_rate),
            start_time=timezone.now(),
            end_time=timezone.now(),
            update_time=timezone.now(),
        )

    return {
        "skipped": False,
        "report_id": int(report.id),
        "trace_id": str(trace_id)[:36],
        "total_api": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "execution_log_id": last_ex_log_id,
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
def run_scheduled_task(
    self, scheduled_task_id: int, *, scheduled_task_log_id: int | None = None
) -> dict:
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
                detail["api_errors"].append(
                    {"case_id": r.get("case_id"), "error": r.get("reason")}
                )
                continue
            if not r.get("passed"):
                api_failed += 1
                detail["api_errors"].append(
                    {
                        "case_id": r.get("case_id"),
                        "error": r.get("message") or r.get("error") or "断言未通过",
                    }
                )

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
        log.save(
            update_fields=["status", "message", "detail", "end_time", "update_time"]
        )

    ScheduledTask.objects.filter(pk=task.pk).update(
        last_run_time=end_time,
        last_status=last_st,
        last_message=message,
    )
    return {"ok": True, "status": status, "message": message}


@shared_task(
    bind=True,
    name="execution.run_api_scenario_run",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=2,
    soft_time_limit=3600,
    time_limit=3660,
)
def run_api_scenario_run(self, scenario_run_id: int, *, overrides: dict | None = None) -> dict:
    """
    异步执行一次 API 场景运行（按步骤顺序执行 TestCase，贯穿变量上下文）。
    """

    run, summary = run_api_scenario(run_id=int(scenario_run_id), runtime_overrides=overrides or {})
    return {
        "ok": True,
        "run_id": int(run.id),
        "scenario_id": int(run.scenario_id),
        "status": run.status,
        "trace_id": run.trace_id,
        "summary": summary,
    }


try:
    from execution import tasks_k6  # noqa: F401  — 注册 k6 压测 Celery 任务
except ImportError:
    pass
