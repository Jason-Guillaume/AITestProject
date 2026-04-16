"""
发布计划只读风险简报：聚合关联用例、测试计划、缺陷与近期 API 执行日志（无大模型）。
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from defect.models import TestDefect
from execution.models import TestPlan
from project.models import ReleasePlan, ReleasePlanTestCase
from testcase.models import ExecutionLog


def _never_executed_case_ids_in_window(case_ids: list[int], *, since) -> list[int]:
    """
    返回在时间窗口内从未产生 ExecutionLog 的用例 id。
    注意：ExecutionLog 是按 test_case_id 关联。
    """

    if not case_ids:
        return []
    executed_ids = set(
        ExecutionLog.objects.filter(
            is_deleted=False,
            test_case_id__in=case_ids,
            create_time__gte=since,
        )
        .values_list("test_case_id", flat=True)
        .distinct()
    )
    return [cid for cid in case_ids if cid not in executed_ids]


def build_release_risk_brief(
    release: ReleasePlan, *, execution_days: int = 7
) -> dict[str, object]:
    execution_days = max(1, min(int(execution_days), 90))
    since = timezone.now() - timedelta(days=execution_days)
    rid = release.id

    link_qs = ReleasePlanTestCase.objects.filter(
        release_plan_id=rid, is_deleted=False
    )
    linked_case_count = link_qs.count()
    case_ids = list(link_qs.values_list("test_case_id", flat=True))

    plan_qs = TestPlan.objects.filter(version_id=rid, is_deleted=False)
    plans_total = plan_qs.count()
    plan_buckets = {"not_started": 0, "in_progress": 0, "completed": 0}
    for row in plan_qs.values("plan_status").annotate(c=Count("id")):
        ps = row["plan_status"]
        if ps == 1:
            plan_buckets["not_started"] = int(row["c"])
        elif ps == 2:
            plan_buckets["in_progress"] = int(row["c"])
        elif ps == 3:
            plan_buckets["completed"] = int(row["c"])

    def_qs = TestDefect.objects.filter(release_version_id=rid, is_deleted=False)
    defects_total = def_qs.count()
    defects_open = def_qs.filter(status__in=(1, 2)).count()
    by_severity: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0}
    for row in def_qs.values("severity").annotate(c=Count("id")):
        sev = int(row["severity"] or 3)
        if sev in by_severity:
            by_severity[sev] = int(row["c"])
    by_status: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0}
    for row in def_qs.values("status").annotate(c=Count("id")):
        st = int(row["status"] or 1)
        if st in by_status:
            by_status[st] = int(row["c"])

    exec_qs = ExecutionLog.objects.filter(
        is_deleted=False,
        create_time__gte=since,
    )
    if case_ids:
        exec_qs = exec_qs.filter(test_case_id__in=case_ids)
    else:
        exec_qs = exec_qs.none()
    exec_total = exec_qs.count()
    exec_passed = exec_qs.filter(is_passed=True).count()
    exec_failed = max(0, exec_total - exec_passed)
    never_executed_ids = _never_executed_case_ids_in_window(case_ids, since=since)
    never_executed_count = len(never_executed_ids)

    project_name = ""
    proj = getattr(release, "project", None)
    if proj is not None:
        project_name = str(getattr(proj, "project_name", "") or "")

    release_info = {
        "id": release.id,
        "release_name": release.release_name,
        "version_no": release.version_no,
        "status": release.status,
        "project_id": release.project_id,
        "project_name": project_name,
    }

    coverage = {
        "linked_cases": linked_case_count,
        "test_plans": {
            "total": plans_total,
            **plan_buckets,
        },
    }

    defects_block = {
        "total": defects_total,
        "open_not_closed": defects_open,
        "by_severity": {str(k): v for k, v in by_severity.items()},
        "by_status": {str(k): v for k, v in by_status.items()},
    }

    executions = {
        "window_days": execution_days,
        "since": since.isoformat(),
        "total_runs": exec_total,
        "passed": exec_passed,
        "failed": exec_failed,
        "never_executed_cases": never_executed_count,
    }

    md_lines = [
        f"## 发布风险简报 · {release.version_no}",
        "",
        f"- **发布名称**：{release.release_name}",
        f"- **所属项目**：{project_name or '—'}",
        f"- **关联用例数**：{linked_case_count}",
        f"- **测试计划**：共 {plans_total} 个（未开始 {plan_buckets['not_started']} / 进行中 {plan_buckets['in_progress']} / 已完成 {plan_buckets['completed']}）",
        f"- **关联缺陷**：共 {defects_total} 条，未关闭（新缺陷/处理中）**{defects_open}** 条",
        f"- **近 {execution_days} 天 API 执行**（仅统计本版本关联用例）：共 {exec_total} 次，通过 {exec_passed}，未通过 {exec_failed}",
        f"- **近 {execution_days} 天从未执行用例**：{never_executed_count}",
        "",
        "> 说明：数据来自 ORM 聚合，不含大模型推断；执行日志依赖用例已产生 `ExecutionLog`。",
    ]
    markdown = "\n".join(md_lines)

    return {
        "release": release_info,
        "coverage": coverage,
        "defects": defects_block,
        "executions": executions,
        "never_executed_case_ids": never_executed_ids[:2000],
        "markdown": markdown,
    }
