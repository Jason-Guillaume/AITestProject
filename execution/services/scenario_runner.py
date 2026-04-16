from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Tuple

from django.db import transaction
from django.utils import timezone

from execution.models import (
    ApiScenario,
    ApiScenarioRun,
    ApiScenarioStep,
    ApiScenarioStepRun,
)
from testcase.models import TestCase
from testcase.services.api_execution import run_api_case
from testcase.services.case_subtypes import get_api_profile_for_execute


def _merge_step_overrides(
    *,
    scenario: ApiScenario,
    run: ApiScenarioRun,
    step: ApiScenarioStep,
    runtime_vars: Dict[str, Any],
) -> Dict[str, Any]:
    """
    组装给 run_api_case() 的 overrides：
    - 合并场景环境 / run 环境 / step 覆盖
    - 注入 variables 与 extraction_rules（提取规则：step 默认 + step_overrides 覆盖）
    """

    overrides = dict(step.step_overrides or {})

    if overrides.get("environment_id") is None:
        env_id = run.environment_id
        if not env_id and getattr(scenario, "environment_id", None):
            env_id = scenario.environment_id
        if env_id:
            overrides["environment_id"] = env_id

    overrides["variables"] = runtime_vars or {}
    if overrides.get("extraction_rules") is None and overrides.get("variable_extractions") is None:
        overrides["extraction_rules"] = list(step.extraction_rules or [])
    return overrides


def _resolve_failure_strategy(scenario: ApiScenario, step: ApiScenarioStep) -> str:
    st = (step.failure_strategy or "").strip().lower()
    if st in (ApiScenario.STRATEGY_ABORT, ApiScenario.STRATEGY_CONTINUE):
        return st
    return (scenario.failure_strategy or ApiScenario.STRATEGY_ABORT).strip().lower()


def run_api_scenario(
    *,
    run_id: int,
    runtime_overrides: Dict[str, Any] | None = None,
) -> Tuple[ApiScenarioRun, Dict[str, Any]]:
    """
    同步执行一次 API 场景（给 Celery task 调用）。
    返回 (run, summary_dict)。
    """

    t0 = time.perf_counter()
    runtime_overrides = runtime_overrides or {}

    with transaction.atomic():
        run = ApiScenarioRun.objects.select_for_update().select_related("scenario").get(
            pk=run_id
        )
        scenario = run.scenario
        if run.status in (ApiScenarioRun.STATUS_RUNNING, ApiScenarioRun.STATUS_SUCCESS):
            return run, {"skipped": True, "reason": "already_running_or_done"}
        run.status = ApiScenarioRun.STATUS_RUNNING
        run.started_at = timezone.now()
        if not run.trace_id:
            run.trace_id = str(uuid.uuid4())
        run.save(update_fields=["status", "started_at", "trace_id", "update_time"])

    scenario = ApiScenario.objects.get(pk=run.scenario_id)
    steps = list(
        ApiScenarioStep.objects.filter(scenario=scenario, is_deleted=False)
        .select_related("test_case")
        .order_by("order", "id")
    )

    runtime_vars: Dict[str, Any] = {}
    runtime_vars.update(scenario.default_variables or {})
    runtime_vars.update(run.initial_variables or {})
    runtime_vars.update(runtime_overrides.get("variables") or {})

    total = 0
    passed = 0
    failed = 0
    skipped = 0
    step_results = []
    fatal_error = ""

    for step in steps:
        if not step.is_enabled or step.is_deleted:
            skipped += 1
            continue
        total += 1

        strategy = _resolve_failure_strategy(scenario, step)

        case: TestCase = step.test_case
        if case.is_deleted:
            failed += 1
            ApiScenarioStepRun.objects.create(
                run_id=run.id,
                step_id=step.id,
                order=step.order,
                test_case_id=int(case.id),
                status=ApiScenarioStepRun.STATUS_FAILED,
                passed=False,
                message="用例已删除",
            )
            if strategy == ApiScenario.STRATEGY_ABORT:
                fatal_error = "用例已删除，已中止"
                break
            continue

        if case.test_type != TestCase.TEST_TYPE_API:
            skipped += 1
            ApiScenarioStepRun.objects.create(
                run_id=run.id,
                step_id=step.id,
                order=step.order,
                test_case_id=int(case.id),
                status=ApiScenarioStepRun.STATUS_SKIPPED,
                passed=False,
                message=f"非 API 用例已跳过: {case.test_type}",
            )
            continue

        api_prof = get_api_profile_for_execute(case)
        if api_prof is None:
            failed += 1
            ApiScenarioStepRun.objects.create(
                run_id=run.id,
                step_id=step.id,
                order=step.order,
                test_case_id=int(case.id),
                status=ApiScenarioStepRun.STATUS_FAILED,
                passed=False,
                message="API 用例扩展数据缺失",
            )
            if strategy == ApiScenario.STRATEGY_ABORT:
                fatal_error = "API 用例扩展数据缺失，已中止"
                break
            continue

        overrides = _merge_step_overrides(
            scenario=scenario, run=run, step=step, runtime_vars=runtime_vars
        )
        try:
            result = run_api_case(
                case,
                api_prof,
                overrides=overrides,
                user=None,
                write_legacy_apilog=False,
            )
        except Exception as exc:
            failed += 1
            ApiScenarioStepRun.objects.create(
                run_id=run.id,
                step_id=step.id,
                order=step.order,
                test_case_id=int(case.id),
                status=ApiScenarioStepRun.STATUS_FAILED,
                passed=False,
                message=f"执行异常: {str(exc)[:200]}",
            )
            if strategy == ApiScenario.STRATEGY_ABORT:
                fatal_error = f"执行异常，已中止: {str(exc)[:200]}"
                break
            continue

        ex_log = result.execution_log
        extracted = result.extracted_variables or {}
        if extracted:
            runtime_vars.update({k: v for k, v in extracted.items() if v is not None})

        step_passed = bool(getattr(ex_log, "is_passed", False))
        if step_passed:
            passed += 1
            st_status = ApiScenarioStepRun.STATUS_COMPLETED
        else:
            failed += 1
            st_status = ApiScenarioStepRun.STATUS_FAILED

        ApiScenarioStepRun.objects.create(
            run_id=run.id,
            step_id=step.id,
            order=step.order,
            test_case_id=int(case.id),
            execution_log_id=int(ex_log.id),
            status=st_status,
            passed=step_passed,
            extracted_variables=extracted,
            message=(result.message or "")[:255],
        )
        step_results.append(
            {
                "step_id": int(step.id),
                "case_id": int(case.id),
                "execution_log_id": int(ex_log.id),
                "passed": step_passed,
            }
        )

        if (not step_passed) and strategy == ApiScenario.STRATEGY_ABORT:
            fatal_error = "断言未通过，已中止"
            break

    duration_ms = int((time.perf_counter() - t0) * 1000)
    finished_at = timezone.now()
    if fatal_error:
        status = ApiScenarioRun.STATUS_FAILED
    elif failed > 0 and passed > 0:
        status = ApiScenarioRun.STATUS_PARTIAL
    elif failed > 0 and passed == 0 and total > 0:
        status = ApiScenarioRun.STATUS_FAILED
    else:
        status = ApiScenarioRun.STATUS_SUCCESS

    summary = {
        "total_steps": total,
        "passed_steps": passed,
        "failed_steps": failed,
        "skipped_steps": skipped,
        "step_results": step_results,
        "failure_reason": fatal_error,
    }

    ApiScenarioRun.objects.filter(pk=run.id).update(
        status=status,
        finished_at=finished_at,
        duration_ms=duration_ms,
        final_variables=runtime_vars,
        summary=summary,
        error_message=fatal_error,
    )
    run.refresh_from_db()
    return run, summary

