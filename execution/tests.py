from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from defect.models import TestDefect
from execution.engine import APIExecutor
from execution.models import ExecutionTask, TestPlan, TestQualityMetric
from execution.services.health_checker import HealthChecker
from execution.services.metric_calculator import MetricCalculator
from execution.tasks import run_execution_task
from execution.views import QualityDashboardView
from project.models import ReleasePlan, TestProject
from testcase.models import (
    EnvironmentHealthCheck,
    ExecutionLog,
    TestCase as BizTestCase,
    TestModule,
)
from user.models import User


class MetricCalculatorTestCase(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.calculator = MetricCalculator()
        self.user = User.objects.create_user(
            username="metric_u",
            password="123456",
            real_name="Metric User",
        )
        self.project = TestProject.objects.create(
            project_name="P-Metric",
            description="metric test project",
            project_status=1,
            progress=10,
        )
        self.project.members.add(self.user)
        self.release = ReleasePlan.objects.create(
            project=self.project,
            release_name="R-Metric",
            version_no="v1.0.0",
            release_date=timezone.now() + timedelta(days=1),
            status=1,
        )
        self.module = TestModule.objects.create(
            project=self.project,
            name="M-API",
            test_type="api",
        )

    def _create_case(self, name: str):
        return BizTestCase.objects.create(
            module=self.module,
            case_name=name,
            test_type=BizTestCase.TEST_TYPE_API,
            level="P1",
        )

    def test_calc_pass_rate_by_execution_log(self):
        case = self._create_case("case-pass-rate")
        ExecutionLog.objects.create(
            test_case=case,
            request_url="https://example.com/a",
            request_method="GET",
            request_headers={},
            request_body_text="",
            response_status_code=200,
            response_headers={},
            response_body_text="ok",
            duration_ms=10,
            execution_status=ExecutionLog.ExecutionStatus.SUCCESS,
            assertion_results=[],
            is_passed=True,
        )
        ExecutionLog.objects.create(
            test_case=case,
            request_url="https://example.com/b",
            request_method="GET",
            request_headers={},
            request_body_text="",
            response_status_code=500,
            response_headers={},
            response_body_text="err",
            duration_ms=12,
            execution_status=ExecutionLog.ExecutionStatus.ASSERTION_FAILED,
            assertion_results=[],
            is_passed=False,
        )

        rate = self.calculator.calc_pass_rate(self.project.id, self.today)
        self.assertEqual(rate, Decimal("50.0000"))

        row = TestQualityMetric.objects.get(
            metric_date=self.today,
            metric_type=TestQualityMetric.METRIC_PASS_RATE,
            dimension={"project_id": self.project.id},
        )
        self.assertEqual(row.metric_value, Decimal("50.0000"))

    def test_calc_defect_density(self):
        case1 = self._create_case("case-density-1")
        case2 = self._create_case("case-density-2")
        self.assertIsNotNone(case1.id)
        self.assertIsNotNone(case2.id)
        TestDefect.objects.create(
            defect_no="D-001",
            defect_name="defect-1",
            release_version=self.release,
            severity=2,
            priority=2,
            status=1,
            handler=self.user,
            module=self.module,
            defect_content="c1",
        )

        density = self.calculator.calc_defect_density(self.project.id, self.today)
        self.assertEqual(density, Decimal("0.5000"))  # 1 / 2

        row = TestQualityMetric.objects.get(
            metric_date=self.today,
            metric_type=TestQualityMetric.METRIC_DEFECT_DENSITY,
            dimension={"project_id": self.project.id},
        )
        self.assertEqual(row.metric_value, Decimal("0.5000"))

    def test_calc_requirement_coverage(self):
        TestPlan.objects.create(
            plan_name="plan-a",
            version=self.release,
            environment="test",
            req_count=10,
            case_count=20,
            coverage_rate=Decimal("60.00"),
            pass_rate=Decimal("80.00"),
            defect_count=1,
        )
        TestPlan.objects.create(
            plan_name="plan-b",
            version=self.release,
            environment="test",
            req_count=10,
            case_count=25,
            coverage_rate=Decimal("80.00"),
            pass_rate=Decimal("90.00"),
            defect_count=0,
        )

        # 同版本去重后：req=avg(10,10)=10, cov=avg(60,80)=70 => 覆盖率 70%
        coverage = self.calculator.calc_requirement_coverage(
            self.project.id, self.today
        )
        self.assertEqual(coverage, Decimal("70.0000"))

        row = TestQualityMetric.objects.get(
            metric_date=self.today,
            metric_type=TestQualityMetric.METRIC_REQUIREMENT_COVERAGE,
            dimension={"project_id": self.project.id},
        )
        self.assertEqual(row.metric_value, Decimal("70.0000"))


class QualityDashboardViewTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.today = timezone.localdate()
        self.user = User.objects.create_user(
            username="quality_view_u",
            password="123456",
            real_name="Quality View User",
        )
        self.project = TestProject.objects.create(
            project_name="P-View",
            description="quality view project",
            project_status=1,
            progress=10,
        )
        self.project.members.add(self.user)
        self.release = ReleasePlan.objects.create(
            project=self.project,
            release_name="R-View",
            version_no="v2.0.0",
            release_date=timezone.now() + timedelta(days=1),
            status=1,
        )
        self.module = TestModule.objects.create(
            project=self.project,
            name="M-View",
            test_type="api",
        )
        self.case = BizTestCase.objects.create(
            module=self.module,
            case_name="case-view",
            test_type=BizTestCase.TEST_TYPE_API,
            level="P1",
        )
        ExecutionLog.objects.create(
            test_case=self.case,
            request_url="https://example.com/ok",
            request_method="GET",
            request_headers={},
            request_body_text="",
            response_status_code=200,
            response_headers={},
            response_body_text="ok",
            duration_ms=8,
            execution_status=ExecutionLog.ExecutionStatus.SUCCESS,
            assertion_results=[],
            is_passed=True,
        )
        TestDefect.objects.create(
            defect_no="DV-001",
            defect_name="defect-view",
            release_version=self.release,
            severity=2,
            priority=2,
            status=1,
            handler=self.user,
            module=self.module,
            defect_content="view defect",
        )
        TestPlan.objects.create(
            plan_name="plan-view",
            version=self.release,
            environment="test",
            req_count=12,
            case_count=30,
            coverage_rate=Decimal("75.00"),
            pass_rate=Decimal("88.00"),
            defect_count=1,
        )

    def test_quality_dashboard_view_returns_30d_trend_structure(self):
        request = self.factory.get("/api/execution/dashboard/quality/")
        force_authenticate(request, user=self.user)
        response = QualityDashboardView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        data = response.data

        self.assertIn("filters", data)
        self.assertEqual(data["filters"]["time_range"], "30d")
        self.assertIn("trendChart", data)
        self.assertIn("series", data["trendChart"])
        self.assertEqual(len(data["trendChart"]["series"]), 3)
        self.assertGreaterEqual(len(data["trendChart"]["xAxis"]), 30)
        self.assertIn("latestMetrics", data)
        self.assertIn("raw", data)
        self.assertIn("pass_rate", data["raw"])
        self.assertEqual(
            len(data["raw"]["pass_rate"]["points"]), len(data["trendChart"]["xAxis"])
        )

    def test_quality_dashboard_view_supports_project_filter(self):
        request = self.factory.get(
            "/api/execution/dashboard/quality/",
            {"project_id": str(self.project.id)},
        )
        force_authenticate(request, user=self.user)
        response = QualityDashboardView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["filters"]["project_id"], self.project.id)

    def test_quality_dashboard_view_invalid_project_id(self):
        request = self.factory.get(
            "/api/execution/dashboard/quality/",
            {"project_id": "not-int"},
        )
        force_authenticate(request, user=self.user)
        response = QualityDashboardView.as_view()(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("project_id", str(response.data))


class EnvironmentHealthCheckWorkflowTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="health_u",
            password="123456",
            real_name="Health User",
        )
        self.project = TestProject.objects.create(
            project_name="P-Health",
            description="health project",
            project_status=1,
            progress=10,
        )
        self.project.members.add(self.user)
        self.module = TestModule.objects.create(
            project=self.project,
            name="M-Health",
            test_type="api",
        )
        self.exec_task = ExecutionTask.objects.create(
            task_name="health-check-task",
            method="GET",
            url="https://example.com/health",
            timeout_seconds=5,
        )

    @patch("execution.services.health_checker.requests.head")
    @patch("execution.services.health_checker.socket.create_connection")
    def test_health_checker_records_checks(self, mock_conn, mock_head):
        class _Resp:
            status_code = 200

        mock_head.return_value = _Resp()
        checker = HealthChecker()
        summary = checker.check_before_task(
            api_url="https://example.com/health",
            dimension={"project_id": self.project.id},
        )
        self.assertTrue(summary["ok"])
        # db + api + redis 三种记录都应写入
        self.assertGreaterEqual(
            EnvironmentHealthCheck.objects.filter(is_deleted=False).count(),
            3,
        )
        self.assertTrue(
            EnvironmentHealthCheck.objects.filter(
                check_type=EnvironmentHealthCheck.CHECK_API,
                status=EnvironmentHealthCheck.STATUS_HEALTHY,
            ).exists()
        )

    @patch("execution.services.health_checker.requests.head")
    @patch("execution.services.health_checker.socket.create_connection")
    def test_health_checker_unhealthy_api_status(self, mock_conn, mock_head):
        class _Resp:
            status_code = 503

        mock_head.return_value = _Resp()
        checker = HealthChecker()
        result = checker.check_api(
            "https://example.com/health", dimension={"scene": "ut"}
        )
        self.assertFalse(result["ok"])
        row = EnvironmentHealthCheck.objects.filter(
            check_type=EnvironmentHealthCheck.CHECK_API
        ).first()
        self.assertIsNotNone(row)
        self.assertEqual(row.status, EnvironmentHealthCheck.STATUS_UNHEALTHY)

    @patch("execution.services.health_checker.connections")
    def test_health_checker_db_default_connection_failure(self, mock_connections):
        mock_connections.__getitem__.return_value.cursor.side_effect = Exception(
            "db down"
        )
        checker = HealthChecker()
        result = checker.check_db(None, dimension={"scene": "ut"})
        self.assertFalse(result["ok"])
        row = EnvironmentHealthCheck.objects.filter(
            check_type=EnvironmentHealthCheck.CHECK_DB
        ).first()
        self.assertIsNotNone(row)
        self.assertEqual(row.status, EnvironmentHealthCheck.STATUS_UNHEALTHY)
        self.assertIn("db down", row.error_log)

    @patch("execution.engine.HealthChecker")
    def test_api_executor_raises_when_unhealthy_and_alerts(self, mock_checker_cls):
        checker_inst = mock_checker_cls.return_value
        checker_inst.check_before_task.return_value = {
            "ok": False,
            "unhealthy": [{"check_type": "db", "error": "connect timeout"}],
        }
        executor = APIExecutor()
        with self.assertRaises(RuntimeError):
            executor.execute(self.exec_task)
        checker_inst.send_alert_email.assert_called_once()

    @patch("execution.tasks.APIExecutor.execute")
    def test_run_execution_task_cancelled_when_env_unhealthy(self, mock_execute):
        mock_execute.side_effect = RuntimeError("ENV_UNHEALTHY: db down")
        result = run_execution_task.run(self.exec_task.id)
        self.exec_task.refresh_from_db()
        self.assertEqual(self.exec_task.status, ExecutionTask.STATUS_FAILED)
        self.assertIn("任务已取消", self.exec_task.error_message)
        self.assertTrue(self.exec_task.report.get("cancelled"))
        self.assertTrue(result.get("cancelled"))
