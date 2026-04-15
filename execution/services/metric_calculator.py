from __future__ import annotations

from decimal import Decimal
from typing import Dict, Optional

from django.db.models import Avg, Count, Q
from django.utils import timezone

from defect.models import TestDefect
from execution.models import TestPlan, TestQualityMetric
from testcase.models import ExecutionLog, TestCase


class MetricCalculator:
    """质量指标计算器。"""

    def _dimension(self, project_id: Optional[int]) -> Dict[str, object]:
        return {"project_id": project_id if project_id is not None else "all"}

    def _upsert_metric(
        self,
        *,
        metric_date,
        metric_type: str,
        metric_value: Decimal,
        project_id: Optional[int],
    ):
        dimension = self._dimension(project_id)
        TestQualityMetric.objects.update_or_create(
            metric_date=metric_date,
            metric_type=metric_type,
            dimension=dimension,
            defaults={"metric_value": metric_value},
        )

    def calc_pass_rate(self, project_id: Optional[int], metric_date=None) -> Decimal:
        if metric_date is None:
            metric_date = timezone.localdate()
        qs = ExecutionLog.objects.filter(
            is_deleted=False, create_time__date=metric_date
        )
        if project_id is not None:
            qs = qs.filter(test_case__module__project_id=project_id)
        agg = qs.aggregate(
            total=Count("id"), passed=Count("id", filter=Q(is_passed=True))
        )
        total = int(agg.get("total") or 0)
        passed = int(agg.get("passed") or 0)
        rate = Decimal("0.0")
        if total > 0:
            rate = (Decimal(passed) / Decimal(total)) * Decimal("100")
        rate = rate.quantize(Decimal("0.0001"))
        self._upsert_metric(
            metric_date=metric_date,
            metric_type=TestQualityMetric.METRIC_PASS_RATE,
            metric_value=rate,
            project_id=project_id,
        )
        return rate

    def calc_defect_density(
        self, project_id: Optional[int], metric_date=None
    ) -> Decimal:
        if metric_date is None:
            metric_date = timezone.localdate()
        defects = TestDefect.objects.filter(
            is_deleted=False, create_time__date=metric_date
        )
        cases = TestCase.objects.filter(is_deleted=False)
        if project_id is not None:
            defects = defects.filter(module__project_id=project_id)
            cases = cases.filter(module__project_id=project_id)
        defect_cnt = defects.count()
        case_cnt = cases.count()
        density = Decimal("0.0")
        if case_cnt > 0:
            density = Decimal(defect_cnt) / Decimal(case_cnt)
        density = density.quantize(Decimal("0.0001"))
        self._upsert_metric(
            metric_date=metric_date,
            metric_type=TestQualityMetric.METRIC_DEFECT_DENSITY,
            metric_value=density,
            project_id=project_id,
        )
        return density

    def calc_requirement_coverage(
        self, project_id: Optional[int], metric_date=None
    ) -> Decimal:
        if metric_date is None:
            metric_date = timezone.localdate()
        plans = TestPlan.objects.filter(is_deleted=False, create_time__date=metric_date)
        if project_id is not None:
            plans = plans.filter(version__project_id=project_id)
        rows = plans.values("version_id").annotate(
            req=Avg("req_count"), cov=Avg("coverage_rate")
        )
        total_req = Decimal(sum(int(row["req"] or 0) for row in rows))
        covered_req = Decimal("0.0")
        for row in rows:
            covered_req += (
                Decimal(row["req"] or 0) * Decimal(row["cov"] or 0) / Decimal("100")
            )
        coverage = Decimal("0.0")
        if total_req > 0:
            coverage = (covered_req / total_req) * Decimal("100")
        coverage = coverage.quantize(Decimal("0.0001"))
        self._upsert_metric(
            metric_date=metric_date,
            metric_type=TestQualityMetric.METRIC_REQUIREMENT_COVERAGE,
            metric_value=coverage,
            project_id=project_id,
        )
        return coverage
