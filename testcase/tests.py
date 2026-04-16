from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase as DjangoTestCase
from rest_framework.test import APIClient

from project.models import TestProject
from testcase.models import (
    TEST_CASE_TYPE_FUNCTIONAL,
    ExecutionLog,
    TestCase as TestCaseModel,
    TestCaseStep,
    TestModule,
)
from testcase.services.variable_runtime import (
    VariableExtractor,
    VariableResolver,
    suggest_extractions,
)


class VariableRuntimeTests(SimpleTestCase):
    def test_extract_from_body_jsonpath(self):
        extractor = VariableExtractor()
        response_data = {
            "body": {"data": {"token": "abc123"}},
            "headers": {"Content-Type": "application/json"},
        }
        rules = [{"var_name": "my_token", "source": "body", "rule": "$.data.token"}]
        result = extractor.extract(response_data, rules)
        self.assertEqual(result, {"my_token": "abc123"})

    def test_extract_from_header_case_insensitive(self):
        extractor = VariableExtractor()
        response_data = {
            "body": {},
            "headers": {"Content-Type": "application/json"},
        }
        rules = [{"var_name": "ctype", "source": "header", "rule": "content-type"}]
        result = extractor.extract(response_data, rules)
        self.assertEqual(result, {"ctype": "application/json"})

    def test_extract_invalid_rule_returns_none(self):
        extractor = VariableExtractor(keep_none_on_error=True)
        response_data = {"body": {"a": 1}, "headers": {}}
        rules = [{"var_name": "x", "source": "body", "expression": "$.missing.path"}]
        result = extractor.extract(response_data, rules)
        self.assertEqual(result, {"x": None})

    def test_extract_support_expression_key(self):
        extractor = VariableExtractor()
        response_data = {"body": {"data": {"token": "abc123"}}, "headers": {}}
        rules = [
            {"var_name": "my_token", "source": "body", "expression": "$.data.token"}
        ]
        result = extractor.extract(response_data, rules)
        self.assertEqual(result, {"my_token": "abc123"})

    def test_variable_resolver_resolve_nested(self):
        resolver = VariableResolver(missing_policy="keep")
        payload = {
            "url": "/api/orders/${order_id}",
            "headers": {"Authorization": "Bearer ${token}"},
            "body": {"user": "${user_name}", "note": "hello"},
            "list": ["${token}", 1],
        }
        variables = {"order_id": 1001, "token": "abc123", "user_name": "alice"}
        result = resolver.resolve(payload, variables)
        self.assertEqual(result["url"], "/api/orders/1001")
        self.assertEqual(result["headers"]["Authorization"], "Bearer abc123")
        self.assertEqual(result["body"]["user"], "alice")
        self.assertEqual(result["list"][0], "abc123")

    def test_suggest_extractions_keyword_and_value_features(self):
        data = {
            "data": {
                "token": "abcdefghijklmnopqrstuvwxyz123456",
                "requestId": "550e8400-e29b-41d4-a716-446655440000",
                "orderNo": "ORD202604090001",
            },
            "code": 200,
            "msg": "ok",
            "status": True,
        }
        suggestions = suggest_extractions(data)
        paths = {x["json_path"] for x in suggestions}
        self.assertIn("$.data.token", paths)
        self.assertIn("$.data.requestId", paths)
        self.assertIn("$.data.orderNo", paths)
        self.assertNotIn("$.code", paths)
        self.assertNotIn("$.msg", paths)
        self.assertNotIn("$.status", paths)


User = get_user_model()


class ApplyAiSuggestedStepsApiTests(DjangoTestCase):
    """POST /api/testcase/cases/<id>/apply-ai-suggested-steps/ 权限与替换步骤行为。"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="apply_ai_steps_u1",
            password="pass-apply-ai-1",
            real_name="Apply Steps User",
        )
        self.project = TestProject.objects.create(
            project_name="ProjApplySteps",
            creator=self.user,
        )
        self.project.members.add(self.user)
        self.module = TestModule.objects.create(
            project=self.project,
            name="RootMod",
            test_type=TEST_CASE_TYPE_FUNCTIONAL,
        )
        self.case = TestCaseModel.objects.create(
            module=self.module,
            case_name="Case Apply AI",
            test_type=TEST_CASE_TYPE_FUNCTIONAL,
            creator=self.user,
            updater=self.user,
        )
        self.old_step = TestCaseStep.objects.create(
            testcase=self.case,
            step_number=1,
            step_desc="旧步骤",
            expected_result="旧预期",
            creator=self.user,
            updater=self.user,
        )
        self.log = ExecutionLog.objects.create(
            test_case=self.case,
            request_url="http://example.com/api",
            request_method="GET",
            is_passed=False,
            execution_status=ExecutionLog.ExecutionStatus.ASSERTION_FAILED,
            creator=self.user,
            updater=self.user,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _url(self, case_id: int | None = None) -> str:
        cid = case_id if case_id is not None else self.case.id
        return f"/api/testcase/cases/{cid}/apply-ai-suggested-steps/"

    def test_requires_confirm_replace_all_boolean_true(self):
        r = self.client.post(
            self._url(),
            {
                "execution_log_id": self.log.id,
                "suggested_steps": [{"step_desc": "n1", "expected_result": "e1"}],
                "confirm_replace_all": False,
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        data = r.json()
        self.assertFalse(data.get("success", True))

    def test_rejects_passed_execution_log(self):
        self.log.is_passed = True
        self.log.save(update_fields=["is_passed"])
        r = self.client.post(
            self._url(),
            {
                "execution_log_id": self.log.id,
                "confirm_replace_all": True,
                "suggested_steps": [{"step_desc": "n1"}],
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_rejects_log_not_belonging_to_case(self):
        other = TestCaseModel.objects.create(
            module=self.module,
            case_name="Other",
            test_type=TEST_CASE_TYPE_FUNCTIONAL,
            creator=self.user,
            updater=self.user,
        )
        r = self.client.post(
            self._url(other.id),
            {
                "execution_log_id": self.log.id,
                "confirm_replace_all": True,
                "suggested_steps": [{"step_desc": "n1"}],
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_replaces_steps_happy_path(self):
        r = self.client.post(
            self._url(),
            {
                "execution_log_id": self.log.id,
                "confirm_replace_all": True,
                "suggested_steps": [
                    {"step_desc": "新步骤一", "expected_result": "预期甲"},
                    {"step_desc": "新步骤二", "expected_result": "—"},
                ],
            },
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("success"))
        self.assertEqual(body.get("steps_count"), 2)
        self.old_step.refresh_from_db()
        self.assertTrue(self.old_step.is_deleted)
        active = list(
            TestCaseStep.objects.filter(testcase=self.case, is_deleted=False).order_by(
                "step_number"
            )
        )
        self.assertEqual(len(active), 2)
        self.assertEqual(active[0].step_desc, "新步骤一")
        self.assertEqual(active[0].expected_result, "预期甲")
        self.assertEqual(active[1].step_number, 2)
        self.assertEqual(active[1].step_desc, "新步骤二")
