from django.test import SimpleTestCase

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
