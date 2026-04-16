from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import MagicMock, patch
from io import StringIO
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from rest_framework.test import APIClient

from assistant.ai_generate_strategies import (
    build_system_prompt_for_generate,
    build_user_message_for_generate,
    dispatch_ai_generation,
    get_ai_prompt_context,
    validate_spec,
)
from assistant.api_case_generation import (
    enrich_normalized_case_with_api_fields,
    renumber_api_business_ids,
    sanitize_ai_raw_item_for_apitestcase,
)
from assistant.services.case_batch_generation import (
    build_batch_generation_prompt,
    parse_batch_json_array,
    normalize_batch_case_item,
)
from assistant.services.semantic_dedup import (
    cosine_similarity,
    semantic_deduplicate_cases,
)
from assistant.views import (
    IFLYTEK_MAAS_MODEL_TYPE,
    IFLYTEK_MAAS_CHAT_COMPLETIONS,
    IFLYTEK_MAAS_OPENAI_BASE,
    _get_active_ai_model_credentials,
    _prepare_ai_generate_context,
    _resolve_openai_target,
)
from user.models import AIModelConfig, Organization
from project.models import TestProject
from testcase.models import TestModule
from assistant.models import GeneratedTestArtifact, KnowledgeArticle, KnowledgeDocument, AiPatch
from testcase.models import (
    TEST_CASE_TYPE_FUNCTIONAL,
    ExecutionLog,
    TestCase as TestCaseModel,
    TestCaseStep,
)


class IflytekMaasRoutingTests(TestCase):
    def test_resolve_openai_target_for_iflytek(self):
        custom_base = "https://should-be-ignored.example.com/v1"
        model, base = _resolve_openai_target(
            IFLYTEK_MAAS_MODEL_TYPE,
            custom_base,
        )
        self.assertEqual(model, IFLYTEK_MAAS_MODEL_TYPE)
        self.assertEqual(base, custom_base)

    def test_get_active_ai_model_credentials_keep_custom_iflytek_base(self):
        custom_base = "https://wrong.example.com/v1"
        AIModelConfig.objects.create(
            model_type=IFLYTEK_MAAS_MODEL_TYPE,
            api_key="sk-test",
            base_url=custom_base,
            is_connected=True,
        )
        api_key, base_url, model = _get_active_ai_model_credentials()
        self.assertEqual(api_key, "sk-test")
        self.assertEqual(base_url, custom_base)
        self.assertEqual(model, IFLYTEK_MAAS_MODEL_TYPE)

    def test_prepare_context_keep_custom_iflytek_base_when_api_key_provided(self):
        custom_base = "https://not-used.example.com/v1"

        class DummyRequest:
            data = {
                "requirement": "生成登录测试用例",
                "api_key": "sk-live",
                "model": IFLYTEK_MAAS_MODEL_TYPE,
                "api_base_url": custom_base,
            }

        ctx, err = _prepare_ai_generate_context(DummyRequest())
        self.assertIsNone(err)
        self.assertEqual(ctx["api_key"], "sk-live")
        self.assertEqual(ctx["api_base_url"], custom_base)
        self.assertEqual(ctx["model_used"], IFLYTEK_MAAS_MODEL_TYPE)

    def test_prepare_context_api_spec_only_sets_default_requirement(self):
        class DummyRequest:
            data = {
                "api_spec": '{"openapi":"3.0.0","paths":{"/users":{"post":{}}}}',
                "testType": "functional",
                "api_key": "sk-test",
                "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
            }

        ctx, err = _prepare_ai_generate_context(DummyRequest())
        self.assertIsNone(err)
        self.assertTrue(ctx.get("api_spec"))
        self.assertTrue(ctx.get("requirement"))
        self.assertEqual(ctx.get("test_type"), "functional")

    def test_prepare_context_rejects_invalid_spec_when_api_type(self):
        class DummyRequest:
            data = {
                "api_spec": "这不是 json 也不是 curl",
                "testType": "api",
                "api_key": "sk-test",
                "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
            }

        ctx, err = _prepare_ai_generate_context(DummyRequest())
        self.assertIsNotNone(err)
        self.assertIsNone(ctx)

    def test_validate_spec_json_and_curl(self):
        ok, e = validate_spec('{"a":1}')
        self.assertTrue(ok)
        self.assertIsNone(e)
        ok, e = validate_spec("")
        self.assertTrue(ok)
        ok, e = validate_spec("curl -X POST https://x.com/a -d '{}' ")
        self.assertTrue(ok)

    def test_get_ai_prompt_context_matches_spec(self):
        pc = get_ai_prompt_context(
            "api",
            api_spec='{"openapi":"3.0.0"}',
            requirement="r",
            module_name="m",
        )
        self.assertTrue(pc.use_api_prompt)
        self.assertEqual(pc.model_target, "ApiTestCase")
        self.assertEqual(pc.template_key, "API_CASE_PROMPT_TEMPLATE")
        self.assertIn("{", pc.input_data)

        pc2 = get_ai_prompt_context(
            "api",
            api_spec="",
            case_name="登录接口",
            requirement="实现登录",
            module_name="m",
        )
        self.assertIn("登录接口", pc2.input_data)

        pc3 = get_ai_prompt_context(
            "functional", requirement="下单流程", module_name="订单"
        )
        self.assertFalse(pc3.use_api_prompt)
        self.assertEqual(pc3.model_target, "TestCase")

    def test_build_user_message_api_without_spec_appends_infer_block(self):
        ctx = {
            "test_type": "api",
            "requirement": "用户登录",
            "api_spec": "",
            "module_name": "登录",
            "test_type_focus": "",
            "case_name": "",
        }
        msg = build_user_message_for_generate(ctx)
        self.assertIn("接口上下文", msg)
        self.assertIn("根据名称预测接口", msg)

    def test_build_system_prompt_routes_api_vs_functional(self):
        ctx_api = {
            "test_type": "api",
            "module_name": "m",
            "requirement": "r",
            "test_type_focus": "f",
            "api_spec": "",
        }
        ctx_fn = {
            "test_type": "functional",
            "module_name": "m",
            "requirement": "r",
            "test_type_focus": "f",
        }
        p_api = build_system_prompt_for_generate(ctx_api)
        p_fn = build_system_prompt_for_generate(ctx_fn)
        self.assertIn("资深接口自动化测试专家", p_api)
        self.assertIn("request_body", p_api)
        self.assertIn("assert_logic", p_api)
        self.assertIn("expectedResult", p_fn)
        self.assertIn("Ultra-Granular", p_fn)

    def test_dispatch_ai_generation_matches_api_and_functional(self):
        ctx_api = {
            "test_type": "api",
            "module_name": "m",
            "requirement": "r",
            "test_type_focus": "",
            "api_spec": "",
            "case_name": "登录",
        }
        d_api = dispatch_ai_generation(ctx_api)
        self.assertTrue(d_api.should_enrich_api)
        self.assertIn("method", d_api.system_prompt)
        self.assertIn("接口上下文", d_api.user_message)

        ctx_fn = {
            "test_type": "functional",
            "module_name": "m",
            "requirement": "r",
            "test_type_focus": "f",
        }
        d_fn = dispatch_ai_generation(ctx_fn)
        self.assertFalse(d_fn.should_enrich_api)
        self.assertIn("expectedResult", d_fn.system_prompt)
        self.assertNotIn("接口上下文", d_fn.user_message)

    def test_sanitize_ai_raw_item_maps_legacy_and_coerces(self):
        s = sanitize_ai_raw_item_for_apitestcase(None)
        self.assertEqual(s["method"], "GET")
        self.assertEqual(s["body"], {})

        s2 = sanitize_ai_raw_item_for_apitestcase(
            {
                "http_method": "post",
                "path": "/api/x",
                "headers": {"X": {"a": 1}},
                "request_body": '{"k":1}',
            }
        )
        self.assertEqual(s2["method"], "POST")
        self.assertEqual(s2["url"], "/api/x")
        self.assertEqual(s2["headers"]["X"], '{"a": 1}')
        self.assertEqual(s2["body"], {"k": 1})

        s3 = sanitize_ai_raw_item_for_apitestcase({"method": "INVALID"})
        self.assertEqual(s3["method"], "GET")

    def test_enrich_normalized_case_with_request_config(self):
        norm = {
            "case_name": "临时",
            "level": "P0",
            "precondition": "",
            "steps": "1. 调用",
            "expected_result": "成功",
            "module_name": "用户",
        }
        raw = {
            "businessId": "API-9",
            "request_config": {
                "method": "POST",
                "url": "https://x.test/api/v1/login",
                "headers": {"Content-Type": "application/json"},
                "body": {"username": "a"},
            },
            "assertions": [
                {
                    "kind": "status_code",
                    "op": "==",
                    "value": 200,
                    "description_zh": "状态码 200",
                }
            ],
            "assertion_logic_text": "check status_code == 200",
        }
        out = enrich_normalized_case_with_api_fields(norm, raw, 0)
        self.assertEqual(out["api_method"], "POST")
        self.assertIn("login", out["api_url"])
        self.assertEqual(out["api_expected_status"], 200)
        self.assertTrue(out["case_name"].startswith("[API-9]"))

    def test_enrich_flat_fields_and_response_assert(self):
        norm = {
            "case_name": "x",
            "level": "P0",
            "precondition": "",
            "steps": "",
            "expected_result": "",
            "module_name": "m",
        }
        raw = {
            "businessId": "API-1",
            "method": "PUT",
            "url": "https://api.test/v2/items/1",
            "headers": {"Content-Type": "application/json"},
            "request_body": {"name": "n"},
            "response_assert": {
                "expected_status": 204,
                "logic_text": "check status_code == 204",
                "rules": [],
            },
        }
        out = enrich_normalized_case_with_api_fields(norm, raw, 0)
        self.assertEqual(out["api_method"], "PUT")
        self.assertEqual(out["api_url"], "https://api.test/v2/items/1")
        self.assertEqual(out["api_body"], {"name": "n"})
        self.assertEqual(out["api_expected_status"], 204)

    def test_enrich_assert_logic_extracts_status(self):
        norm = {
            "case_name": "x",
            "level": "P0",
            "precondition": "",
            "steps": "",
            "expected_result": "",
            "module_name": "m",
        }
        raw = {
            "businessId": "API-1",
            "method": "GET",
            "url": "https://api.test/health",
            "headers": {},
            "request_body": {},
            "assert_logic": "status == 200 且 msg == 'success'",
        }
        out = enrich_normalized_case_with_api_fields(norm, raw, 0)
        self.assertEqual(out["api_expected_status"], 200)
        self.assertIn("status == 200", out.get("assertion_logic_text", ""))

    def test_renumber_api_business_ids(self):
        cases = [
            {"case_name": "[API-1] A", "business_id": "API-1"},
            {"case_name": "[API-99] B", "business_id": "API-99"},
        ]
        renumber_api_business_ids(cases)
        self.assertEqual(cases[0]["business_id"], "API-1")
        self.assertEqual(cases[1]["business_id"], "API-2")
        self.assertIn("[API-2]", cases[1]["case_name"])

    @patch("assistant.views.OpenAI")
    def test_api_test_connection_force_iflytek_model_and_normalize_base_url(
        self, mock_openai_cls
    ):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="u_iflytek",
            password="pass123456",
            real_name="测试管理员",
        )
        client = APIClient()
        client.force_authenticate(user=user)

        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Connection successful"
        mock_completion.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_cls.return_value = mock_client

        resp = client.post(
            "/api/ai/test-connection/",
            {
                "api_key": "sk-iflytek",
                "model": IFLYTEK_MAAS_MODEL_TYPE,
                "api_base_url": IFLYTEK_MAAS_CHAT_COMPLETIONS,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("success"))
        self.assertEqual(resp.data.get("model"), IFLYTEK_MAAS_MODEL_TYPE)

        mock_openai_cls.assert_called_once_with(
            api_key="sk-iflytek",
            base_url=IFLYTEK_MAAS_OPENAI_BASE,
            timeout=20.0,
        )
        mock_client.chat.completions.create.assert_called_once()
        kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs.get("model"), IFLYTEK_MAAS_MODEL_TYPE)


class KnowledgeRagTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="rag_test_user",
            password="pass123456",
            real_name="RAG Tester",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch("assistant.views.KnowledgeSearcher.search_similar")
    def test_knowledge_search_api(self, mock_search):
        mock_search.return_value = [
            {
                "article_id": 1,
                "title": "登录模板",
                "category": "template",
                "tags": ["登录"],
            }
        ]
        resp = self.client.post(
            "/api/assistant/knowledge/search/",
            {
                "query_text": "登录",
                "top_k": 3,
                "category": "template",
                "tag": "登录",
                "min_score": 0.2,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("success"))
        self.assertEqual(resp.data.get("top_k"), 3)
        self.assertEqual(resp.data.get("category"), "template")
        self.assertEqual(resp.data.get("tag"), "登录")
        self.assertEqual(resp.data.get("min_score"), 0.2)
        self.assertEqual(len(resp.data.get("results") or []), 1)
        mock_search.assert_called_once()

    @patch("testcase.views.KnowledgeSearcher.search_similar")
    def test_case_create_returns_knowledge_recommendations(self, mock_search):
        mock_search.return_value = [
            {
                "article_id": 2,
                "title": "API最佳实践",
                "category": "best_practice",
                "tags": ["API"],
            }
        ]
        project = TestProject.objects.create(
            project_name="RAG-P",
            description="rag project",
            project_status=1,
            progress=5,
        )
        project.members.add(self.user)
        module = TestModule.objects.create(
            project=project,
            name="登录模块",
            test_type="api",
        )
        payload = {
            "module": module.id,
            "case_name": "登录接口校验",
            "test_type": "api",
            "level": "P1",
            "api_url": "https://httpbin.org/get",
            "api_method": "GET",
            "api_headers": {"Accept": "application/json"},
        }
        resp = self.client.post("/api/testcase/cases/", payload, format="json")
        self.assertIn(resp.status_code, (200, 201))
        self.assertIn("knowledge_recommendations", resp.data)
        self.assertEqual(len(resp.data.get("knowledge_recommendations") or []), 1)

    @patch("assistant.knowledge_rag.KnowledgeIndexer.index_article")
    def test_knowledge_article_save_triggers_index(self, mock_index):
        KnowledgeArticle.objects.create(
            title="登录模板",
            category="template",
            markdown_content="# 模板",
            tags=["登录", "API"],
        )
        self.assertTrue(mock_index.called)

    @patch("assistant.knowledge_rag.KnowledgeIndexer.delete_article")
    def test_knowledge_article_delete_triggers_remove_index(self, mock_delete):
        article = KnowledgeArticle.objects.create(
            title="FAQ 1",
            category="faq",
            markdown_content="content",
            tags=[],
        )
        article.delete()
        self.assertTrue(mock_delete.called)

    @patch(
        "assistant.management.commands.reindex_knowledge_base.KnowledgeIndexer.reindex_all"
    )
    def test_reindex_knowledge_base_command(self, mock_reindex):
        mock_reindex.return_value = {"total": 3, "success": 2, "failed": 1}
        out = StringIO()
        call_command("reindex_knowledge_base", stdout=out)
        self.assertIn("知识库重建完成", out.getvalue())
        self.assertIn("total=3", out.getvalue())

    def test_knowledge_articles_filter_by_category_and_tag(self):
        KnowledgeArticle.objects.create(
            title="登录模板A",
            category="template",
            markdown_content="A",
            tags=["登录", "模板"],
            creator=self.user,
        )
        KnowledgeArticle.objects.create(
            title="性能FAQ",
            category="faq",
            markdown_content="B",
            tags=["性能"],
            creator=self.user,
        )
        by_cat = self.client.get("/api/assistant/knowledge-articles/?category=template")
        self.assertEqual(by_cat.status_code, 200)
        if isinstance(by_cat.data, list):
            self.assertGreaterEqual(len(by_cat.data), 1)
        else:
            self.assertGreaterEqual(
                (by_cat.data.get("count") or len(by_cat.data.get("results") or [])), 1
            )
        by_tag = self.client.get("/api/assistant/knowledge-articles/?tag=登录")
        self.assertEqual(by_tag.status_code, 200)

    @patch("assistant.knowledge_rag.KnowledgeIndexer.index_article")
    def test_knowledge_article_create_upload_mode_requires_file_or_content(
        self, mock_index
    ):
        resp = self.client.post(
            "/api/assistant/knowledge-articles/",
            {
                "title": "上传创建",
                "category": "template",
                "tags": ["上传", "文本"],
                "text_source": "upload",
            },
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(mock_index.called)

    def test_extract_text_api_success_for_txt(self):
        f = SimpleUploadedFile(
            "k.txt", "提取测试".encode("utf-8"), content_type="text/plain"
        )
        resp = self.client.post(
            "/api/assistant/knowledge/extract-text/",
            {"file": f},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("success"))
        self.assertIn("提取测试", resp.data.get("text", ""))

    def test_extract_text_api_rejects_unsupported_suffix(self):
        f = SimpleUploadedFile(
            "bad.exe", b"abc", content_type="application/octet-stream"
        )
        resp = self.client.post(
            "/api/assistant/knowledge/extract-text/",
            {"file": f},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("仅支持", resp.data.get("message", ""))

    @override_settings(KNOWLEDGE_UPLOAD_MAX_SIZE=1)
    def test_extract_text_api_rejects_oversized_file(self):
        f = SimpleUploadedFile("k.txt", b"ab", content_type="text/plain")
        resp = self.client.post(
            "/api/assistant/knowledge/extract-text/",
            {"file": f},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("文件过大", resp.data.get("message", ""))


class AiBatchAndSemanticDedupTests(TestCase):
    def test_build_batch_generation_prompt_contains_constraints(self):
        prompt = build_batch_generation_prompt(
            module_name="登录模块",
            requirement="用户登录",
            test_type_focus="功能测试",
            existing_titles=["用户名密码登录成功", "密码错误提示"],
            min_count=5,
        )
        self.assertIn("不少于 5 条", prompt)
        self.assertIn("合法 JSON Array", prompt)
        self.assertIn("已有用例标题", prompt)

    def test_parse_batch_json_array_supports_array_and_object_wrapped(self):
        arr = parse_batch_json_array(
            '[{"title":"a","type":"正向","steps":"s","expected":"e"}]'
        )
        self.assertEqual(len(arr), 1)
        obj = parse_batch_json_array(
            '{"cases":[{"title":"b","type":"逆向","steps":"s2","expected":"e2"}]}'
        )
        self.assertEqual(len(obj), 1)
        with self.assertRaises(ValueError):
            parse_batch_json_array('{"x":1}')

    def test_backfill_api_request_fields_in_batch(self):
        from assistant.api_case_generation import backfill_api_request_fields_in_batch

        cases = [
            {
                "api_url": "https://real.api/login",
                "api_method": "POST",
                "api_headers": {"Content-Type": "application/json"},
                "api_body": {"username": "a", "password": "b"},
            },
            {
                "api_url": "https://api.example.com/pa",
                "api_method": "GET",
                "api_headers": {},
                "api_body": {},
                "request_config": {
                    "method": "GET",
                    "url": "old",
                    "headers": {},
                    "body": {},
                },
            },
        ]
        backfill_api_request_fields_in_batch(cases)
        self.assertEqual(cases[1]["api_url"], "https://real.api/login")
        self.assertEqual(cases[1]["api_method"], "POST")
        self.assertEqual(
            cases[1]["api_headers"].get("Content-Type"), "application/json"
        )
        self.assertEqual(cases[1]["api_body"], {"username": "a", "password": "b"})
        rc = cases[1].get("request_config")
        self.assertIsInstance(rc, dict)
        self.assertEqual(rc.get("url"), cases[1]["api_url"])

    def test_normalize_batch_case_item(self):
        item = normalize_batch_case_item(
            {
                "title": "登录成功",
                "type": "正向",
                "steps": "输入账号密码",
                "expected": "登录成功",
            },
            0,
        )
        self.assertEqual(item["case_name"], "登录成功")
        self.assertEqual(item["level"], "P2")
        self.assertEqual(item["expected_result"], "登录成功")
        self.assertEqual(item.get("module_name"), "")
        with_mod = normalize_batch_case_item(
            {
                "title": "登录失败",
                "type": "逆向",
                "steps": "s",
                "expected": "e",
                "module_name": "用户登录模块",
                "level": "P1",
            },
            1,
        )
        self.assertEqual(with_mod["module_name"], "用户登录模块")
        self.assertEqual(with_mod["level"], "P1")

    def test_cosine_similarity(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0, places=6)
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0, places=6)

    @patch("assistant.services.semantic_dedup.embed_batch")
    def test_semantic_deduplicate_cases(self, mock_embed_batch):
        generated = [
            {"case_name": "登录成功", "steps": "输入正确账号密码"},
            {"case_name": "注册成功", "steps": "输入新用户信息"},
        ]
        existing = [{"case_name": "用户登录主流程", "steps": "输入正确账号密码"}]
        # 第一组为 generated 向量，第二组为 existing 向量
        mock_embed_batch.side_effect = [
            [[1.0, 0.0], [0.0, 1.0]],
            [[1.0, 0.0]],
        ]
        out = semantic_deduplicate_cases(
            generated,
            existing,
            api_key="k",
            base_url="https://x",
            threshold=0.85,
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["case_name"], "注册成功")


class AiPatchApplyRollbackTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="aipatch_u1",
            password="pass-aipatch-1",
            real_name="AiPatch User",
        )
        self.project = TestProject.objects.create(
            project_name="ProjAiPatch",
            creator=self.user,
        )
        self.project.members.add(self.user)
        self.module = TestModule.objects.create(
            project=self.project,
            name="ModAiPatch",
            test_type=TEST_CASE_TYPE_FUNCTIONAL,
        )
        self.case = TestCaseModel.objects.create(
            module=self.module,
            case_name="Case AiPatch",
            test_type=TEST_CASE_TYPE_FUNCTIONAL,
            creator=self.user,
            updater=self.user,
        )
        TestCaseStep.objects.create(
            testcase=self.case,
            step_number=1,
            step_desc="旧步骤1",
            expected_result="旧预期1",
            creator=self.user,
            updater=self.user,
        )
        TestCaseStep.objects.create(
            testcase=self.case,
            step_number=2,
            step_desc="旧步骤2",
            expected_result="旧预期2",
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

    def test_apply_and_rollback_patch_replace_steps(self):
        patch = AiPatch.objects.create(
            creator=self.user,
            target_type="testcase.TestCase",
            target_id=str(self.case.id),
            source_execution_log_id=self.log.id,
            status=AiPatch.STATUS_DRAFT,
            before={},
            after={
                "steps": [
                    {"step_desc": "新步骤A", "expected_result": "新预期A"},
                    {"step_desc": "新步骤B", "expected_result": "新预期B"},
                ]
            },
            changes=[{"op": "replace_all_steps"}],
        )

        r = self.client.post(
            f"/api/ai/patches/{patch.id}/apply/",
            {"confirm": True},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        patch.refresh_from_db()
        self.assertEqual(patch.status, AiPatch.STATUS_APPLIED)

        active = list(
            TestCaseStep.objects.filter(testcase=self.case, is_deleted=False).order_by(
                "step_number"
            )
        )
        self.assertEqual([s.step_desc for s in active], ["新步骤A", "新步骤B"])

        r2 = self.client.post(
            f"/api/ai/patches/{patch.id}/rollback/",
            {"confirm": True},
            format="json",
        )
        self.assertEqual(r2.status_code, 200)
        patch.refresh_from_db()
        self.assertEqual(patch.status, AiPatch.STATUS_ROLLED_BACK)

        active2 = list(
            TestCaseStep.objects.filter(testcase=self.case, is_deleted=False).order_by(
                "step_number"
            )
        )
        self.assertEqual([s.step_desc for s in active2], ["旧步骤1", "旧步骤2"])


class KnowledgeOrgSharingAndArtifactsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.u1 = user_model.objects.create_user(
            username="kb_u1",
            password="pass123456",
            real_name="KB U1",
        )
        self.u2 = user_model.objects.create_user(
            username="kb_u2",
            password="pass123456",
            real_name="KB U2",
        )
        self.org = Organization.objects.create(org_name="OrgA", creator=self.u1, updater=self.u1)
        self.org.members.add(self.u1, self.u2)
        self.client1 = APIClient()
        self.client1.force_authenticate(user=self.u1)
        self.client2 = APIClient()
        self.client2.force_authenticate(user=self.u2)

    def test_document_list_includes_org_shared_docs(self):
        private_doc = KnowledgeDocument.objects.create(
            title="Private",
            file_name="p.md",
            document_type=KnowledgeDocument.DOC_TYPE_MD,
            status=KnowledgeDocument.STATUS_COMPLETED,
            visibility_scope=KnowledgeDocument.VISIBILITY_PRIVATE,
            org=self.org,
            creator=self.u1,
            updater=self.u1,
        )
        org_doc = KnowledgeDocument.objects.create(
            title="OrgShared",
            file_name="o.md",
            document_type=KnowledgeDocument.DOC_TYPE_MD,
            status=KnowledgeDocument.STATUS_COMPLETED,
            visibility_scope=KnowledgeDocument.VISIBILITY_ORG,
            org=self.org,
            creator=self.u1,
            updater=self.u1,
        )
        r = self.client2.get("/api/assistant/knowledge/documents/?page=1&page_size=50")
        self.assertEqual(r.status_code, 200)
        ids = [x.get("id") for x in (r.data.get("results") or [])]
        self.assertIn(org_doc.id, ids)
        self.assertNotIn(private_doc.id, ids)

    def test_create_generated_test_artifact_from_doc(self):
        doc = KnowledgeDocument.objects.create(
            title="OrgShared",
            file_name="o.md",
            document_type=KnowledgeDocument.DOC_TYPE_MD,
            status=KnowledgeDocument.STATUS_COMPLETED,
            visibility_scope=KnowledgeDocument.VISIBILITY_ORG,
            org=self.org,
            creator=self.u1,
            updater=self.u1,
        )
        payload = {
            "artifact_type": "test_plan",
            "title": "Plan1",
            "doc_id": doc.id,
            "content": {"a": 1},
            "citations": [{"index": 1, "text": "x"}],
        }
        r = self.client2.post("/api/assistant/knowledge/artifacts/", payload, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.data.get("success"))
        item_id = (r.data.get("data") or {}).get("id")
        self.assertTrue(item_id)
        self.assertTrue(
            GeneratedTestArtifact.objects.filter(pk=item_id, is_deleted=False).exists()
        )
