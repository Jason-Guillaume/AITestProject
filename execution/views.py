from common.views import *
from common.services.audit import record_execute_audit
from execution.models import *
from execution.serialize import *
from execution.scheduler import TestScheduler, execute_scheduled_task
from execution.services.metric_calculator import MetricCalculator
from execution.tasks import run_api_scenario_run
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.authtoken.models import Token
from django.utils import timezone
from django.core.cache import cache
from django.http import StreamingHttpResponse, JsonResponse
from django.views import View
from datetime import timedelta, datetime, time
from django.db import transaction
from django.db.models import Avg, Count, DateField, Q
from django.db.models.functions import TruncDate

import logging
import uuid
import json
import asyncio
from asgiref.sync import sync_to_async
from typing import List

from execution.services.scenario_generator import (
    build_scenario_draft_from_curl_list,
    build_scenario_draft_from_openapi,
)
from common.services.audit import record_audit_event
from common.models import AuditEvent

logger = logging.getLogger(__name__)


class ApiScenarioViewSet(BaseModelViewSet):
    queryset = ApiScenario.objects.all()
    serializer_class = ApiScenarioSerializer

    @action(detail=True, methods=["post"], url_path="run")
    def run_scenario(self, request, pk=None):
        """
        触发一次场景执行（异步）：
        POST /api/execution/api-scenarios/<id>/run/
        body 可选：
        - environment_id: number
        - variables: object
        """
        scenario = self.get_object()
        if not getattr(scenario, "is_active", True):
            raise ValidationError({"msg": "场景未启用", "code": 400, "data": None})

        payload = request.data if isinstance(request.data, dict) else {}
        env_id = payload.get("environment_id")
        variables = payload.get("variables")
        if variables is not None and not isinstance(variables, dict):
            raise ValidationError({"msg": "variables 必须为对象", "code": 400, "data": None})

        if env_id is None:
            env_id = getattr(scenario, "environment_id", None)
        else:
            try:
                env_id = int(env_id)
            except (TypeError, ValueError):
                env_id = None

        init_vars = dict(getattr(scenario, "default_variables", None) or {})
        if isinstance(variables, dict):
            init_vars.update(variables)

        run = ApiScenarioRun.objects.create(
            scenario=scenario,
            status=ApiScenarioRun.STATUS_PENDING,
            environment_id=env_id,
            initial_variables=init_vars,
            final_variables={},
            summary={},
            creator=request.user if getattr(request.user, "is_authenticated", False) else None,
            updater=request.user if getattr(request.user, "is_authenticated", False) else None,
        )
        async_result = run_api_scenario_run.delay(int(run.id), overrides={"variables": init_vars})
        ApiScenarioRun.objects.filter(pk=run.pk).update(celery_task_id=str(async_result.id or ""))
        run.refresh_from_db()
        record_execute_audit(
            actor=request.user,
            instance=scenario,
            request=request,
            extra={"scenario_id": int(scenario.id), "scenario_run_id": int(run.id)},
        )
        return Response({"success": True, "run_id": int(run.id), "celery_task_id": run.celery_task_id})


class ApiScenarioGenerateAPIView(APIView):
    """
    POST /api/execution/api-scenarios/generate/
    输入 OpenAPI(JSON/YAML) 或 curl_list，生成可执行场景草稿；可选 confirm_create 落库为 ApiScenario+ApiScenarioStep+ApiTestCase。

    body:
    - project_id: 必填
    - module_id: 必填（用于落库创建 API 用例）
    - environment_id: 可选（落库时写入 ApiScenario.environment）
    - base_url: 可选（优先于 openapi servers[0].url）
    - scenario_name: 可选
    - max_steps: 可选，默认 30（上限 100）
    - openapi_spec: 与 curl_list 二选一
    - curl_list: string[]
    - confirm_create: bool（默认 false）
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from project.models import TestProject
        from testcase.models import TestModule, TEST_CASE_TYPE_API, TestCaseStep
        from testcase.services.case_subtypes import create_typed_case, API_DEFAULTS, PERF_DEFAULTS, SECURITY_DEFAULTS, UI_DEFAULTS

        body = request.data if isinstance(request.data, dict) else {}

        try:
            project_id = int(body.get("project_id"))
        except (TypeError, ValueError):
            return Response({"success": False, "message": "project_id 必填且为整数"}, status=400)
        try:
            module_id = int(body.get("module_id"))
        except (TypeError, ValueError):
            return Response({"success": False, "message": "module_id 必填且为整数"}, status=400)

        env_id = body.get("environment_id")
        try:
            env_id = int(env_id) if env_id not in (None, "") else None
        except (TypeError, ValueError):
            env_id = None

        base_url = str(body.get("base_url") or "").strip()
        scenario_name = str(body.get("scenario_name") or "").strip()
        try:
            max_steps = int(body.get("max_steps") or 30)
        except (TypeError, ValueError):
            max_steps = 30
        max_steps = max(1, min(max_steps, 100))

        openapi_spec = body.get("openapi_spec")
        curl_list = body.get("curl_list")
        confirm_create = body.get("confirm_create") is True

        if not openapi_spec and not curl_list:
            return Response({"success": False, "message": "openapi_spec 或 curl_list 必须提供其一"}, status=400)

        # 权限与数据范围：按 project 成员对齐（复用 project.members）
        proj = TestProject.objects.filter(pk=project_id, is_deleted=False).first()
        if not proj:
            return Response({"success": False, "message": "项目不存在"}, status=404)
        if not (
            getattr(request.user, "is_system_admin", False)
            or getattr(request.user, "is_superuser", False)
            or getattr(request.user, "is_staff", False)
            or proj.members.filter(pk=request.user.pk, is_deleted=False).exists()
        ):
            return Response({"success": False, "message": "无权限访问该项目"}, status=403)

        mod = TestModule.objects.filter(pk=module_id, is_deleted=False).select_related("project").first()
        if not mod or int(getattr(mod, "project_id", 0) or 0) != int(project_id):
            return Response({"success": False, "message": "module_id 不属于该项目"}, status=400)

        try:
            if openapi_spec:
                draft = build_scenario_draft_from_openapi(
                    openapi_spec_text=str(openapi_spec),
                    base_url=base_url,
                    scenario_name=scenario_name,
                    max_steps=max_steps,
                )
                source = "openapi"
            else:
                if not isinstance(curl_list, list):
                    return Response({"success": False, "message": "curl_list 必须为数组"}, status=400)
                draft = build_scenario_draft_from_curl_list(
                    curl_list=[str(x) for x in curl_list],
                    scenario_name=scenario_name,
                    max_steps=max_steps,
                )
                source = "curl_list"
        except ValueError as exc:
            return Response({"success": False, "message": str(exc)}, status=400)

        record_execute_audit(
            actor=request.user,
            instance=None,
            request=request,
            extra={
                "action": "scenario_generate",
                "source": source,
                "project_id": int(project_id),
                "module_id": int(module_id),
                "steps": int(len(draft.get("steps") or [])),
            },
        )

        if not confirm_create:
            return Response({"success": True, "draft": draft})

        # confirm_create: 落库创建
        steps = draft.get("steps") or []
        if not isinstance(steps, list) or not steps:
            return Response({"success": False, "message": "草稿 steps 为空，无法创建"}, status=400)

        with transaction.atomic():
            scenario = ApiScenario.objects.create(
                project_id=int(project_id),
                environment_id=env_id,
                name=str(draft.get("scenario", {}).get("name") or "AI 场景")[:255],
                default_variables=draft.get("scenario", {}).get("default_variables") or {},
                failure_strategy=ApiScenario.STRATEGY_ABORT,
                is_active=True,
                creator=request.user,
                updater=request.user,
            )
            created_case_ids: List[int] = []
            for idx, st in enumerate(steps, start=1):
                req = (st or {}).get("request") if isinstance(st, dict) else None
                if not isinstance(req, dict):
                    continue
                method = str(req.get("method") or "GET").upper()
                url = str(req.get("url") or "").strip()
                if not url:
                    continue
                headers = req.get("headers") if isinstance(req.get("headers"), dict) else {}
                body_obj = req.get("body")
                if not isinstance(body_obj, (dict, list, str, int, float, bool)) and body_obj is not None:
                    body_obj = {}
                exp_status = req.get("expected_status")
                try:
                    exp_status = int(exp_status) if exp_status not in (None, "") else None
                except (TypeError, ValueError):
                    exp_status = None

                case_name = str(st.get("name") or f"{method} {url}")[:255]
                base_data = {
                    "module_id": int(module_id),
                    "case_name": case_name,
                    "test_type": TEST_CASE_TYPE_API,
                    "creator": request.user,
                    "updater": request.user,
                }
                api = dict(API_DEFAULTS)
                api.update(
                    {
                        "api_url": url[:2048],
                        "api_method": method,
                        "api_headers": headers,
                        "api_body": body_obj if isinstance(body_obj, (dict, list)) else ({"raw": str(body_obj)} if body_obj else {}),
                        "api_expected_status": exp_status,
                        "api_source_curl": "",
                    }
                )
                case = create_typed_case(
                    TEST_CASE_TYPE_API,
                    base_data,
                    api,
                    dict(PERF_DEFAULTS),
                    dict(SECURITY_DEFAULTS),
                    dict(UI_DEFAULTS),
                )
                created_case_ids.append(int(case.id))

                TestCaseStep.objects.create(
                    testcase=case,
                    step_number=1,
                    step_desc=f"调用 {method} {url}"[:4000],
                    expected_result=(f"状态码为 {exp_status}" if exp_status else "状态码为 2xx")[:2000],
                    assertions=[],
                    creator=request.user,
                    updater=request.user,
                )

                ApiScenarioStep.objects.create(
                    scenario=scenario,
                    order=idx,
                    name=case_name[:255],
                    test_case=case,
                    is_enabled=True,
                    failure_strategy="",
                    extraction_rules=st.get("extraction_rules") if isinstance(st.get("extraction_rules"), list) else [],
                    step_overrides={},
                    creator=request.user,
                    updater=request.user,
                )

        record_audit_event(
            action=AuditEvent.ACTION_CREATE,
            actor=request.user,
            instance=scenario,
            request=request,
            extra={
                "scenario_id": int(scenario.id),
                "source": source,
                "created_case_ids": created_case_ids[:200],
                "cases_count": int(len(created_case_ids)),
            },
        )

        return Response(
            {
                "success": True,
                "scenario_id": int(scenario.id),
                "created_case_ids": created_case_ids,
                "steps_count": int(len(created_case_ids)),
            }
        )

class ApiScenarioStepViewSet(BaseModelViewSet):
    queryset = ApiScenarioStep.objects.all().select_related("scenario", "test_case")
    serializer_class = ApiScenarioStepSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        scenario_id = self.request.query_params.get("scenario_id")
        if scenario_id not in (None, ""):
            try:
                sid = int(scenario_id)
            except (TypeError, ValueError):
                return qs.none()
            qs = qs.filter(scenario_id=sid)
        return qs


class ApiScenarioRunViewSet(BaseModelViewSet):
    queryset = ApiScenarioRun.objects.all().select_related("scenario")
    serializer_class = ApiScenarioRunSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        scenario_id = self.request.query_params.get("scenario_id")
        if scenario_id not in (None, ""):
            try:
                sid = int(scenario_id)
            except (TypeError, ValueError):
                return qs.none()
            qs = qs.filter(scenario_id=sid)
        trace_id = (self.request.query_params.get("trace_id") or "").strip()
        if trace_id:
            qs = qs.filter(trace_id=trace_id)
        return qs


class ApiScenarioStepRunViewSet(BaseModelViewSet):
    queryset = ApiScenarioStepRun.objects.all()
    serializer_class = ApiScenarioStepRunSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        run_id = self.request.query_params.get("run_id")
        if run_id not in (None, ""):
            try:
                rid = int(run_id)
            except (TypeError, ValueError):
                return qs.none()
            qs = qs.filter(run_id=rid)
        return qs


class DashboardStreamView(View):
    """
    Dashboard SSE 事件流（推送刷新信号）。
    EventSource 无法自定义 Authorization 头，支持 ?token=<DRF Token>。
    """

    @staticmethod
    def _resolve_user(request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            return user
        token_key = (request.GET.get("token") or "").strip()
        if not token_key:
            auth_header = request.META.get("HTTP_AUTHORIZATION", "")
            if auth_header.lower().startswith("token "):
                token_key = auth_header.split(" ", 1)[1].strip()
        if not token_key:
            return None
        try:
            token = Token.objects.select_related("user").get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            return None

    async def get(self, request, *args, **kwargs):
        """
        重要：SSE 是长连接；在 ASGI 下若用同步 view + time.sleep 会占用线程池，
        当连接数变多时可能导致其它 API（如删除/保存）被“饿死”出现超时/异常。

        这里改为 async + asyncio.sleep，避免占用同步线程池。
        """

        user = await sync_to_async(self._resolve_user)(request)
        if not user:
            return JsonResponse({"detail": "认证失败"}, status=401)

        project_id = request.GET.get("project_id")

        async def event_stream():
            yield "retry: 3000\n\n"
            while True:
                payload = {
                    "type": "dashboard_tick",
                    "ts": timezone.now().isoformat(),
                    "project_id": project_id,
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                await asyncio.sleep(3)

        response = StreamingHttpResponse(
            streaming_content=event_stream(),
            content_type="text/event-stream; charset=utf-8",
        )
        response["Cache-Control"] = "no-cache, no-store, no-transform"
        response["Pragma"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class TestPlanViewSet(BaseModelViewSet):
    queryset = TestPlan.objects.all().prefetch_related("testers")
    serializer_class = TestPlanSerializer

    def _parse_id_list(self, raw_ids):
        if raw_ids is None:
            raise ValidationError({"msg": "ids 必填", "code": 400, "data": None})
        if not isinstance(raw_ids, list):
            raise ValidationError({"msg": "ids 必须为数组", "code": 400, "data": None})
        ids = []
        for x in raw_ids:
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                continue
        ids = [i for i in ids if i > 0]
        if not ids:
            raise ValidationError({"msg": "ids 不能为空", "code": 400, "data": None})
        # 去重但保持顺序
        seen = set()
        uniq = []
        for i in ids:
            if i in seen:
                continue
            seen.add(i)
            uniq.append(i)
        return uniq

    @action(detail=False, methods=["post"], url_path="batch-copy")
    def batch_copy(self, request):
        """
        批量复制测试计划（复制字段 + testers；重置状态为未开始）。
        POST /api/execution/plans/batch-copy/
        body: { ids: number[], name_suffix?: string }
        """
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        suffix = str(request.data.get("name_suffix") or "（复制）").strip()[:32] or "（复制）"

        src_qs = (
            self.get_queryset()
            .filter(id__in=ids, is_deleted=False)
            .prefetch_related("testers")
        )
        src_list = list(src_qs)
        src_ids = {int(o.id) for o in src_list}
        missing = [i for i in ids if i not in src_ids]
        if not src_list:
            return Response(
                {"success": True, "created": 0, "created_ids": [], "missing_ids": ids}
            )

        created_ids = []
        errors = []
        user = request.user if getattr(request, "user", None) is not None else None
        with transaction.atomic():
            for src in src_list:
                try:
                    new_obj = TestPlan.objects.create(
                        plan_name=str(src.plan_name or "")[:220] + suffix,
                        iteration=src.iteration,
                        version_id=src.version_id,
                        environment=src.environment,
                        req_count=int(src.req_count or 0),
                        case_count=int(src.case_count or 0),
                        coverage_rate=src.coverage_rate,
                        plan_status=TestPlan.plan_status.field.default if hasattr(TestPlan, "plan_status") else 1,
                        pass_rate=0,
                        defect_count=int(src.defect_count or 0),
                        start_date=src.start_date,
                        end_date=src.end_date,
                        creator=user if (user and getattr(user, "is_authenticated", False)) else None,
                        updater=user if (user and getattr(user, "is_authenticated", False)) else None,
                    )
                    testers = list(src.testers.all())
                    if testers:
                        new_obj.testers.set(testers)
                    created_ids.append(int(new_obj.id))
                except Exception as e:
                    errors.append({"id": int(src.id), "error": str(e)})
        return Response(
            {
                "success": len(errors) == 0,
                "created": len(created_ids),
                "created_ids": created_ids,
                "missing_ids": missing,
                "errors": errors,
            }
        )

    @action(detail=False, methods=["post"], url_path="batch-delete")
    def batch_delete(self, request):
        """
        批量软删除测试计划（数据范围与列表一致）。
        POST /api/execution/plans/batch-delete/
        body: { ids: number[] }
        """
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        qs = self.get_queryset().filter(id__in=ids, is_deleted=False)
        found_ids = list(qs.values_list("id", flat=True))
        if not found_ids:
            return Response({"success": True, "deleted": 0, "skipped": len(ids), "missing_ids": ids})
        with transaction.atomic():
            updated = qs.update(is_deleted=True)
        missing = [i for i in ids if i not in set(found_ids)]
        return Response(
            {
                "success": True,
                "deleted": int(updated),
                "skipped": len(missing),
                "missing_ids": missing,
            }
        )

    @action(detail=False, methods=["post"], url_path="batch-update")
    def batch_update(self, request):
        """
        批量更新测试计划（对所有 ids 应用同一 patch）。
        POST /api/execution/plans/batch-update/
        body: { ids: number[], patch: object }
        """
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        patch = request.data.get("patch")
        if not isinstance(patch, dict) or not patch:
            raise ValidationError({"msg": "patch 必须为非空对象", "code": 400, "data": None})

        allowed_keys = {
            "plan_name",
            "iteration",
            "version",
            "environment",
            "req_count",
            "case_count",
            "coverage_rate",
            "plan_status",
            "pass_rate",
            "defect_count",
            "testers",
            "start_date",
            "end_date",
        }
        cleaned = {k: v for (k, v) in patch.items() if k in allowed_keys}
        if not cleaned:
            raise ValidationError({"msg": "patch 未包含可更新字段", "code": 400, "data": None})

        qs = self.get_queryset().filter(id__in=ids, is_deleted=False).prefetch_related("testers")
        found = list(qs)
        found_ids = {int(o.id) for o in found}
        missing = [i for i in ids if i not in found_ids]

        updated_ids = []
        errors = []
        with transaction.atomic():
            for obj in found:
                ser = self.get_serializer(obj, data=cleaned, partial=True)
                try:
                    ser.is_valid(raise_exception=True)
                    self.perform_update(ser)
                    updated_ids.append(int(obj.id))
                except Exception as e:
                    errors.append({"id": int(obj.id), "error": str(e)})
        return Response(
            {
                "success": len(errors) == 0,
                "updated": len(updated_ids),
                "updated_ids": updated_ids,
                "missing_ids": missing,
                "errors": errors,
            }
        )


class TestReportViewSet(BaseModelViewSet):
    queryset = TestReport.objects.all()
    serializer_class = TestReportSerializer

    def _parse_id_list(self, raw_ids):
        if raw_ids is None:
            raise ValidationError({"msg": "ids 必填", "code": 400, "data": None})
        if not isinstance(raw_ids, list):
            raise ValidationError({"msg": "ids 必须为数组", "code": 400, "data": None})
        ids = []
        for x in raw_ids:
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                continue
        ids = [i for i in ids if i > 0]
        if not ids:
            raise ValidationError({"msg": "ids 不能为空", "code": 400, "data": None})
        seen = set()
        uniq = []
        for i in ids:
            if i in seen:
                continue
            seen.add(i)
            uniq.append(i)
        return uniq

    @action(detail=False, methods=["post"], url_path="batch-delete")
    def batch_delete(self, request):
        """
        批量软删除测试报告（数据范围与列表一致）。
        POST /api/execution/reports/batch-delete/
        body: { ids: number[] }
        """
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        qs = self.get_queryset().filter(id__in=ids, is_deleted=False)
        found_ids = list(qs.values_list("id", flat=True))
        if not found_ids:
            return Response({"success": True, "deleted": 0, "skipped": len(ids), "missing_ids": ids})
        with transaction.atomic():
            updated = qs.update(is_deleted=True)
        missing = [i for i in ids if i not in set(found_ids)]
        return Response(
            {
                "success": True,
                "deleted": int(updated),
                "skipped": len(missing),
                "missing_ids": missing,
            }
        )

    @action(detail=False, methods=["post"], url_path="batch-update")
    def batch_update(self, request):
        """
        批量更新测试报告（对所有 ids 应用同一 patch）。
        POST /api/execution/reports/batch-update/
        body: { ids: number[], patch: object }
        """
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        patch = request.data.get("patch")
        if not isinstance(patch, dict) or not patch:
            raise ValidationError({"msg": "patch 必须为非空对象", "code": 400, "data": None})

        allowed_keys = {
            "report_name",
            "plan",
            "environment",
            "req_count",
            "case_count",
            "coverage_rate",
            "pass_rate",
            "defect_count",
            "start_time",
            "end_time",
        }
        cleaned = {k: v for (k, v) in patch.items() if k in allowed_keys}
        if not cleaned:
            raise ValidationError({"msg": "patch 未包含可更新字段", "code": 400, "data": None})

        qs = self.get_queryset().filter(id__in=ids, is_deleted=False)
        found = list(qs)
        found_ids = {int(o.id) for o in found}
        missing = [i for i in ids if i not in found_ids]

        updated_ids = []
        errors = []
        with transaction.atomic():
            for obj in found:
                ser = self.get_serializer(obj, data=cleaned, partial=True)
                try:
                    ser.is_valid(raise_exception=True)
                    self.perform_update(ser)
                    updated_ids.append(int(obj.id))
                except Exception as e:
                    errors.append({"id": int(obj.id), "error": str(e)})
        return Response(
            {
                "success": len(errors) == 0,
                "updated": len(updated_ids),
                "updated_ids": updated_ids,
                "missing_ids": missing,
                "errors": errors,
            }
        )

    @action(detail=False, methods=["post"], url_path="batch-copy")
    def batch_copy(self, request):
        """
        批量复制测试报告（复制字段；默认 create_method=1；重置 trace/execution 引用）。
        POST /api/execution/reports/batch-copy/
        body: { ids: number[], name_suffix?: string }
        """
        if not isinstance(request.data, dict):
            raise ValidationError(
                {"msg": "请求体必须为 JSON 对象", "code": 400, "data": None}
            )
        ids = self._parse_id_list(request.data.get("ids"))
        suffix = str(request.data.get("name_suffix") or "（复制）").strip()[:32] or "（复制）"

        src_qs = self.get_queryset().filter(id__in=ids, is_deleted=False)
        src_list = list(src_qs)
        src_ids = {int(o.id) for o in src_list}
        missing = [i for i in ids if i not in src_ids]
        if not src_list:
            return Response(
                {"success": True, "created": 0, "created_ids": [], "missing_ids": ids}
            )

        created_ids = []
        errors = []
        user = request.user if getattr(request, "user", None) is not None else None
        with transaction.atomic():
            for src in src_list:
                try:
                    new_obj = TestReport.objects.create(
                        plan_id=src.plan_id,
                        report_name=(str(src.report_name or "")[:220] + suffix),
                        create_method=1,
                        environment=src.environment,
                        req_count=int(src.req_count or 0),
                        case_count=int(src.case_count or 0),
                        coverage_rate=src.coverage_rate,
                        pass_rate=src.pass_rate,
                        defect_count=int(src.defect_count or 0),
                        start_time=src.start_time,
                        end_time=src.end_time,
                        trace_id="",
                        execution_log_id=None,
                        request_payload=None,
                        response_payload=None,
                        project_id=src.project_id,
                        creator=user if (user and getattr(user, "is_authenticated", False)) else None,
                        updater=user if (user and getattr(user, "is_authenticated", False)) else None,
                    )
                    created_ids.append(int(new_obj.id))
                except Exception as e:
                    errors.append({"id": int(src.id), "error": str(e)})
        return Response(
            {
                "success": len(errors) == 0,
                "created": len(created_ids),
                "created_ids": created_ids,
                "missing_ids": missing,
                "errors": errors,
            }
        )


class PerfTaskPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class PerfTaskViewSet(BaseModelViewSet):
    queryset = PerfTask.objects.all()
    serializer_class = PerfTaskSerializer
    pagination_class = PerfTaskPagination
    lookup_field = "task_id"

    def _parse_task_id_list(self, raw_ids):
        if raw_ids is None:
            raise ValidationError({"msg": "task_ids 必填", "code": 400, "data": None})
        if not isinstance(raw_ids, list):
            raise ValidationError(
                {"msg": "task_ids 必须为数组", "code": 400, "data": None}
            )
        ids = []
        for x in raw_ids:
            s = str(x or "").strip()
            if not s:
                continue
            ids.append(s[:64])
        if not ids:
            raise ValidationError({"msg": "task_ids 不能为空", "code": 400, "data": None})
        seen = set()
        uniq = []
        for i in ids:
            if i in seen:
                continue
            seen.add(i)
            uniq.append(i)
        return uniq

    def get_queryset(self):
        queryset = super().get_queryset()
        request = self.request
        name = request.query_params.get("name")
        status_value = request.query_params.get("status")
        executor = request.query_params.get("executor")

        if name:
            queryset = queryset.filter(task_name__icontains=name)
        if status_value:
            queryset = queryset.filter(status=status_value)
        if executor:
            queryset = queryset.filter(executor__icontains=executor)

        return queryset.order_by("-create_time")

    @action(detail=False, methods=["post"], url_path="batch-delete")
    def batch_delete(self, request):
        """
        批量软删除性能任务（基于 task_id；数据范围与列表一致）。
        POST /api/perf/tasks/batch-delete/
        body: { task_ids: string[] }
        """
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        task_ids = self._parse_task_id_list(request.data.get("task_ids"))
        qs = self.get_queryset().filter(task_id__in=task_ids, is_deleted=False)
        found_ids = list(qs.values_list("task_id", flat=True))
        if not found_ids:
            return Response({"success": True, "deleted": 0, "skipped": len(task_ids), "missing_task_ids": task_ids})
        with transaction.atomic():
            updated = qs.update(is_deleted=True)
        missing = [i for i in task_ids if i not in set(found_ids)]
        return Response(
            {
                "success": True,
                "deleted": int(updated),
                "skipped": len(missing),
                "missing_task_ids": missing,
            }
        )

    @action(detail=False, methods=["post"], url_path="batch-update")
    def batch_update(self, request):
        """
        批量更新性能任务（对所有 task_id 应用同一 patch）。
        POST /api/perf/tasks/batch-update/
        body: { task_ids: string[], patch: object }
        """
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        task_ids = self._parse_task_id_list(request.data.get("task_ids"))
        patch = request.data.get("patch")
        if not isinstance(patch, dict) or not patch:
            raise ValidationError({"msg": "patch 必须为非空对象", "code": 400, "data": None})
        allowed_keys = {
            "task_name",
            "scenario",
            "concurrency",
            "duration",
            "status",
            "executor",
        }
        cleaned = {k: v for (k, v) in patch.items() if k in allowed_keys}
        if not cleaned:
            raise ValidationError({"msg": "patch 未包含可更新字段", "code": 400, "data": None})

        qs = self.get_queryset().filter(task_id__in=task_ids, is_deleted=False)
        found = list(qs)
        found_ids = {str(o.task_id) for o in found}
        missing = [i for i in task_ids if i not in found_ids]

        updated_task_ids = []
        errors = []
        with transaction.atomic():
            for obj in found:
                ser = self.get_serializer(obj, data=cleaned, partial=True)
                try:
                    ser.is_valid(raise_exception=True)
                    self.perform_update(ser)
                    updated_task_ids.append(str(obj.task_id))
                except Exception as e:
                    errors.append({"task_id": str(obj.task_id), "error": str(e)})
        return Response(
            {
                "success": len(errors) == 0,
                "updated": len(updated_task_ids),
                "updated_task_ids": updated_task_ids,
                "missing_task_ids": missing,
                "errors": errors,
            }
        )

    def perform_create(self, serializer):
        user = self.request.user
        task_id = f"PT-{uuid.uuid4().hex[:8].upper()}"
        if user and user.is_authenticated:
            serializer.save(task_id=task_id, creator=user)
        else:
            serializer.save(task_id=task_id)

    @action(methods=["post"], detail=True, url_path="run")
    def run(self, request, pk=None, task_id=None):
        task = self.get_object()
        if task.status == PerfTask.STATUS_RUNNING:
            return Response(
                {"detail": "任务正在运行中，无需重复触发"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if task.status == PerfTask.STATUS_COMPLETED:
            return Response(
                {"detail": "已完成任务不可直接执行，请复制后重跑"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task.status = PerfTask.STATUS_RUNNING
        if request.user and request.user.is_authenticated:
            task.executor = request.user.real_name or request.user.username
            task.updater = request.user
        task.save(update_fields=["status", "executor", "updater", "update_time"])
        return Response(
            {"detail": "任务已触发执行", "task_id": task.task_id},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="batch-copy")
    def batch_copy(self, request):
        """
        批量复制性能任务（复制配置；新 task_id；状态重置为 pending）。
        POST /api/perf/tasks/batch-copy/
        body: { task_ids: string[], name_suffix?: string }
        """
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        task_ids = self._parse_task_id_list(request.data.get("task_ids"))
        suffix = str(request.data.get("name_suffix") or "（复制）").strip()[:32] or "（复制）"
        src_qs = self.get_queryset().filter(task_id__in=task_ids, is_deleted=False)
        src_list = list(src_qs)
        src_ids = {str(o.task_id) for o in src_list}
        missing = [i for i in task_ids if i not in src_ids]
        if not src_list:
            return Response(
                {"success": True, "created": 0, "created_task_ids": [], "missing_task_ids": task_ids}
            )

        created_task_ids = []
        errors = []
        user = request.user if getattr(request, "user", None) is not None else None
        with transaction.atomic():
            for src in src_list:
                try:
                    new_tid = f"PT-{uuid.uuid4().hex[:8].upper()}"
                    new_obj = PerfTask.objects.create(
                        task_id=new_tid,
                        task_name=(str(src.task_name or "")[:220] + suffix),
                        scenario=src.scenario,
                        concurrency=src.concurrency,
                        duration=src.duration,
                        status=PerfTask.STATUS_PENDING,
                        executor=src.executor,
                        creator=user if (user and getattr(user, "is_authenticated", False)) else None,
                        updater=user if (user and getattr(user, "is_authenticated", False)) else None,
                    )
                    created_task_ids.append(str(new_obj.task_id))
                except Exception as e:
                    errors.append({"task_id": str(src.task_id), "error": str(e)})
        return Response(
            {
                "success": len(errors) == 0,
                "created": len(created_task_ids),
                "created_task_ids": created_task_ids,
                "missing_task_ids": missing,
                "errors": errors,
            }
        )


class DashboardSummaryAPIView(APIView):
    """
    首页/工作台仪表盘聚合接口
    返回：统计卡片、折线图（周/月）、饼图、柱状图、最近测试任务列表
    """

    def _humanize_delta(self, dt):
        if not dt:
            return "-"
        now = timezone.now()
        diff = now - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return f"{seconds}秒前" if seconds > 0 else "刚刚"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}分钟前"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}小时前"
        days = hours // 24
        return f"{days}天前"

    def _last_n_days(self, n):
        today = timezone.localdate()
        dates = [today - timedelta(days=i) for i in range(n - 1, -1, -1)]
        return dates

    def _count_by_day(self, model_cls, field_name, dates):
        if not dates:
            return []
        start = timezone.make_aware(datetime.combine(dates[0], time.min))
        end = timezone.make_aware(datetime.combine(dates[-1], time.max))
        day_expr = TruncDate(field_name, output_field=DateField())
        rows = (
            model_cls.objects.filter(
                is_deleted=False,
                **{f"{field_name}__gte": start, f"{field_name}__lte": end},
            )
            .annotate(day=day_expr)
            .values("day")
            .annotate(total=Count("id"))
        )
        day_to_count = {row["day"]: row["total"] for row in rows}
        return [int(day_to_count.get(d, 0)) for d in dates]

    def get(self, request, *args, **kwargs):
        # 统一使用真实数据；如果表为空则返回 0，确保前端不会报错
        from testcase.models import TestCase
        from defect.models import TestDefect

        project_id = (request.query_params.get("project_id") or "").strip()
        user = getattr(request, "user", None)
        is_admin = bool(
            user
            and getattr(user, "is_authenticated", False)
            and (
                getattr(user, "is_superuser", False)
                or getattr(user, "is_staff", False)
                or bool(getattr(user, "is_system_admin", False))
            )
        )

        def _case_scope_qs():
            qs = TestCase.objects.filter(is_deleted=False)
            if project_id:
                try:
                    pid = int(project_id)
                except (TypeError, ValueError):
                    return qs.none()
                return qs.filter(module__project_id=pid)
            if user and getattr(user, "is_authenticated", False) and not is_admin:
                return qs.filter(
                    Q(module__project__members=user) | Q(creator=user)
                ).distinct()
            return qs

        def _defect_scope_qs():
            qs = TestDefect.objects.filter(is_deleted=False)
            if project_id:
                try:
                    pid = int(project_id)
                except (TypeError, ValueError):
                    return qs.none()
                # 缺陷模型不一定有 project 字段：优先走常见链路（用例/模块/项目）
                if hasattr(TestDefect, "project_id"):
                    return qs.filter(project_id=pid)
                if hasattr(TestDefect, "testcase_id"):
                    return qs.filter(testcase__module__project_id=pid)
                if hasattr(TestDefect, "test_case_id"):
                    return qs.filter(test_case__module__project_id=pid)
                return qs
            if user and getattr(user, "is_authenticated", False) and not is_admin:
                if hasattr(TestDefect, "creator_id"):
                    return qs.filter(
                        Q(creator=user)
                        | Q(testcase__module__project__members=user)
                        | Q(test_case__module__project__members=user)
                    ).distinct()
            return qs

        # --------------------------
        # 统计卡片
        # --------------------------
        total_cases = _case_scope_qs().count()

        # 今日“执行用例”近似：今日生成的测试报告数量
        today = timezone.localdate()
        start_today = timezone.make_aware(datetime.combine(today, time.min))
        end_today = start_today + timedelta(days=1)
        today_reports_qs = TestReport.objects.filter(
            is_deleted=False, create_time__gte=start_today, create_time__lt=end_today
        )
        if project_id:
            try:
                pid = int(project_id)
            except (TypeError, ValueError):
                pid = None
            if pid is not None:
                if hasattr(TestReport, "project_id"):
                    today_reports_qs = today_reports_qs.filter(project_id=pid)
                else:
                    today_reports_qs = today_reports_qs.filter(
                        plan__version__project_id=pid
                    )
        today_reports = today_reports_qs.count()

        # 未解决缺陷：状态非“已关闭”(4)
        unresolved_defects = _defect_scope_qs().exclude(status=4).count()

        completed_plans = TestPlan.objects.filter(is_deleted=False, plan_status=3)
        if completed_plans.exists():
            pass_rate = float(
                completed_plans.aggregate(avg_rate=Avg("pass_rate")).get("avg_rate")
                or 0.0
            )
        else:
            pass_rate = 0.0

        # 对比昨日：同样采用“今日/昨日”口径的简单增量（用于前端展示）
        yesterday = today - timedelta(days=1)
        start_yesterday = timezone.make_aware(datetime.combine(yesterday, time.min))
        end_yesterday = start_yesterday + timedelta(days=1)
        yesterday_reports_qs = TestReport.objects.filter(
            is_deleted=False,
            create_time__gte=start_yesterday,
            create_time__lt=end_yesterday,
        )
        if project_id:
            try:
                pid = int(project_id)
            except (TypeError, ValueError):
                pid = None
            if pid is not None:
                if hasattr(TestReport, "project_id"):
                    yesterday_reports_qs = yesterday_reports_qs.filter(project_id=pid)
                else:
                    yesterday_reports_qs = yesterday_reports_qs.filter(
                        plan__version__project_id=pid
                    )
        yesterday_reports = yesterday_reports_qs.count()
        yesterday_unresolved_new = (
            _defect_scope_qs()
            .exclude(status=4)
            .filter(create_time__gte=start_yesterday, create_time__lt=end_yesterday)
            .count()
        )

        # 总用例：对比“昨日新增用例数”
        yesterday_new_cases = (
            _case_scope_qs()
            .filter(create_time__gte=start_yesterday, create_time__lt=end_yesterday)
            .count()
        )
        today_new_cases = (
            _case_scope_qs()
            .filter(create_time__gte=start_today, create_time__lt=end_today)
            .count()
        )

        total_cases_delta = today_new_cases - yesterday_new_cases
        today_reports_delta = today_reports - yesterday_reports
        today_unresolved_new = (
            _defect_scope_qs()
            .exclude(status=4)
            .filter(create_time__gte=start_today, create_time__lt=end_today)
            .count()
        )
        unresolved_defects_delta = today_unresolved_new - yesterday_unresolved_new

        # --------------------------
        # 图表数据
        # --------------------------
        last7 = self._last_n_days(7)
        last30 = self._last_n_days(30)

        week_executed = self._count_by_day(TestReport, "create_time", last7)
        week_defects = self._count_by_day(TestDefect, "create_time", last7)
        month_executed = self._count_by_day(TestReport, "create_time", last30)
        month_defects = self._count_by_day(TestDefect, "create_time", last30)

        week_x = [d.strftime("%m/%d") for d in last7]
        month_x = [d.strftime("%m/%d") for d in last30]

        # 饼图：按缺陷严重程度映射到“安全/合规/性能/功能”
        # 1 致命 -> 安全；2 严重 -> 合规；3 一般 -> 性能；4 建议 -> 功能
        severity_map = {1: "安全", 2: "合规", 3: "性能", 4: "功能"}
        pie_items = []
        for sev in [1, 2, 3, 4]:
            v = TestDefect.objects.filter(is_deleted=False, severity=sev).count()
            pie_items.append({"name": severity_map[sev], "value": v})

        # 柱状图：近 7 天缺陷新增数
        bar_x = week_x
        bar_values = week_defects

        # --------------------------
        # 最近测试任务（统一做成“活动流”）
        # --------------------------
        activities = []
        # 运行中测试计划
        running_plans = TestPlan.objects.filter(
            is_deleted=False, plan_status=2
        ).order_by("-update_time")[:2]
        for p in running_plans:
            activities.append(
                {
                    "id": f"plan-{p.id}",
                    "tag": "进行中",
                    "tagType": "warning",
                    "text": p.plan_name,
                    "time": self._humanize_delta(p.update_time),
                }
            )

        # 新缺陷
        new_defects = TestDefect.objects.filter(is_deleted=False, status=1).order_by(
            "-update_time"
        )[:2]
        for d in new_defects:
            activities.append(
                {
                    "id": f"defect-{d.id}",
                    "tag": "新缺陷",
                    "tagType": "danger",
                    "text": f"{d.defect_name}",
                    "time": self._humanize_delta(d.update_time),
                }
            )

        # 运行中性能任务
        perf_running = PerfTask.objects.filter(
            is_deleted=False, status=PerfTask.STATUS_RUNNING
        ).order_by("-update_time")[:1]
        for t in perf_running:
            activities.append(
                {
                    "id": f"perftask-{t.id}",
                    "tag": "进行中",
                    "tagType": "info",
                    "text": f"性能任务：{t.task_name}",
                    "time": self._humanize_delta(t.update_time),
                }
            )

        # 补齐：用已完成测试计划
        if len(activities) < 6:
            finished = TestPlan.objects.filter(
                is_deleted=False, plan_status=3
            ).order_by("-update_time")[: (6 - len(activities))]
            for p in finished:
                activities.append(
                    {
                        "id": f"plan-done-{p.id}",
                        "tag": "已完成",
                        "tagType": "success",
                        "text": p.plan_name,
                        "time": self._humanize_delta(p.update_time),
                    }
                )

        # --------------------------
        # 返回
        # --------------------------
        return Response(
            {
                "statCards": {
                    "totalCases": {
                        "value": total_cases,
                        "label": "测试用例总数",
                        "delta": total_cases_delta,
                        "barBg": "#e6f4ff",
                        "barColor": "#1677ff",
                        "barWidth": f"{max(10, min(100, 50 + total_cases_delta * 10))}%",
                    },
                    "todayExecuted": {
                        "value": today_reports,
                        "label": "今日执行用例",
                        "delta": today_reports_delta,
                        "barBg": "#e6fffb",
                        "barColor": "#13c2c2",
                        "barWidth": f"{max(10, min(100, 50 + today_reports_delta * 20))}%",
                    },
                    "unresolvedDefects": {
                        "value": unresolved_defects,
                        "label": "未解决缺陷",
                        "delta": unresolved_defects_delta,
                        "barBg": "#fff7e6",
                        "barColor": "#fa8c16",
                        "barWidth": f"{max(10, min(100, 50 + unresolved_defects_delta * 10))}%",
                    },
                    "passRate": {
                        "value": f"{round(pass_rate, 0)}%",
                        "label": "用例通过率",
                        "delta": 0,
                        "barBg": "#f6ffed",
                        "barColor": "#52c41a",
                        "barWidth": f"{min(max(int(pass_rate), 0), 100)}%",
                    },
                },
                "lineChart": {
                    "week": {
                        "x": week_x,
                        "executed": week_executed,
                        "defects": week_defects,
                    },
                    "month": {
                        "x": month_x,
                        "executed": month_executed,
                        "defects": month_defects,
                    },
                },
                "pieChart": {"items": pie_items},
                "barChart": {"x": bar_x, "values": bar_values},
                "activities": activities[:6],
            }
        )


class QualityDashboardView(APIView):
    """
    测试质量分析接口（ECharts 友好结构）：
    - 各模块缺陷分布
    - 用例通过率趋势
    - 需求覆盖率
    """

    def _resolve_dates(self, time_range: str):
        tr = (time_range or "30d").strip().lower()
        days_map = {"7d": 7, "14d": 14, "30d": 30, "90d": 90}
        days = days_map.get(tr, 30)
        end_date = timezone.localdate()
        start_date = end_date - timedelta(days=days - 1)
        start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
        end_dt = timezone.make_aware(datetime.combine(end_date, time.max))
        return start_date, end_date, start_dt, end_dt

    def _fill_daily_rate(self, start_date, end_date, day_rate_map):
        labels = []
        values = []
        cur = start_date
        while cur <= end_date:
            labels.append(cur.strftime("%m/%d"))
            values.append(round(float(day_rate_map.get(cur, 0.0)), 2))
            cur += timedelta(days=1)
        return labels, values

    def get(self, request, *args, **kwargs):
        project_id = request.query_params.get("project_id")
        time_range = (request.query_params.get("time_range") or "30d").strip().lower()
        start_date, end_date, _, _ = self._resolve_dates(time_range)
        pid = None
        if project_id not in (None, ""):
            try:
                pid = int(project_id)
            except (TypeError, ValueError):
                return Response(
                    {"msg": "project_id 必须为整数"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        cache_key = f"quality_dashboard_metric:{pid if pid is not None else 'null'}:{start_date.isoformat()}:{end_date.isoformat()}:{time_range}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        calculator = MetricCalculator()
        days = []
        cur = start_date
        while cur <= end_date:
            days.append(cur)
            calculator.calc_pass_rate(pid, cur)
            calculator.calc_defect_density(pid, cur)
            calculator.calc_requirement_coverage(pid, cur)
            cur += timedelta(days=1)

        metrics_qs = TestQualityMetric.objects.filter(
            is_deleted=False,
            metric_date__gte=start_date,
            metric_date__lte=end_date,
        )
        metrics_qs = metrics_qs.filter(
            dimension__project_id=(pid if pid is not None else None)
        )

        metric_map = {
            TestQualityMetric.METRIC_PASS_RATE: {},
            TestQualityMetric.METRIC_DEFECT_DENSITY: {},
            TestQualityMetric.METRIC_REQUIREMENT_COVERAGE: {},
        }
        for item in metrics_qs:
            metric_map.setdefault(item.metric_type, {})[item.metric_date] = float(
                item.metric_value
            )

        x_axis = [d.strftime("%m/%d") for d in days]
        pass_rate_series = [
            round(metric_map[TestQualityMetric.METRIC_PASS_RATE].get(d, 0.0), 4)
            for d in days
        ]
        defect_density_series = [
            round(metric_map[TestQualityMetric.METRIC_DEFECT_DENSITY].get(d, 0.0), 4)
            for d in days
        ]
        req_cov_series = [
            round(
                metric_map[TestQualityMetric.METRIC_REQUIREMENT_COVERAGE].get(d, 0.0), 4
            )
            for d in days
        ]

        payload = {
            "filters": {
                "project_id": pid,
                "time_range": "30d",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "trendChart": {
                "xAxis": x_axis,
                "series": [
                    {
                        "name": "用例通过率(%)",
                        "type": "line",
                        "smooth": True,
                        "data": pass_rate_series,
                    },
                    {
                        "name": "缺陷密度",
                        "type": "line",
                        "smooth": True,
                        "data": defect_density_series,
                    },
                    {
                        "name": "需求覆盖率(%)",
                        "type": "line",
                        "smooth": True,
                        "data": req_cov_series,
                    },
                ],
            },
            "latestMetrics": {
                "date": end_date.isoformat(),
                "pass_rate": pass_rate_series[-1] if pass_rate_series else 0.0,
                "defect_density": (
                    defect_density_series[-1] if defect_density_series else 0.0
                ),
                "requirement_coverage": req_cov_series[-1] if req_cov_series else 0.0,
            },
            "raw": {
                "pass_rate": {
                    "metric_type": TestQualityMetric.METRIC_PASS_RATE,
                    "points": [
                        {"date": d.isoformat(), "value": pass_rate_series[idx]}
                        for idx, d in enumerate(days)
                    ],
                },
                "defect_density": {
                    "metric_type": TestQualityMetric.METRIC_DEFECT_DENSITY,
                    "points": [
                        {"date": d.isoformat(), "value": defect_density_series[idx]}
                        for idx, d in enumerate(days)
                    ],
                },
                "requirement_coverage": {
                    "metric_type": TestQualityMetric.METRIC_REQUIREMENT_COVERAGE,
                    "points": [
                        {"date": d.isoformat(), "value": req_cov_series[idx]}
                        for idx, d in enumerate(days)
                    ],
                },
            },
            "chartsCompat": {
                "passRateTrend": {
                    "xAxis": x_axis,
                    "series": [
                        {
                            "name": "用例通过率(%)",
                            "type": "line",
                            "smooth": True,
                            "data": pass_rate_series,
                        }
                    ],
                },
                "defectDensityTrend": {
                    "xAxis": x_axis,
                    "series": [
                        {
                            "name": "缺陷密度",
                            "type": "line",
                            "smooth": True,
                            "data": defect_density_series,
                        }
                    ],
                },
                "requirementCoverageTrend": {
                    "xAxis": x_axis,
                    "series": [
                        {
                            "name": "需求覆盖率(%)",
                            "type": "line",
                            "smooth": True,
                            "data": req_cov_series,
                        }
                    ],
                },
            },
        }
        cache.set(cache_key, payload, timeout=60)
        return Response(payload)


class ScheduledTaskViewSet(BaseModelViewSet):
    queryset = ScheduledTask.objects.prefetch_related("test_cases").all()
    serializer_class = ScheduledTaskSerializer

    def _parse_id_list(self, raw_ids):
        if raw_ids is None:
            raise ValidationError({"msg": "ids 必填", "code": 400, "data": None})
        if not isinstance(raw_ids, list):
            raise ValidationError({"msg": "ids 必须为数组", "code": 400, "data": None})
        ids = []
        for x in raw_ids:
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                continue
        ids = [i for i in ids if i > 0]
        if not ids:
            raise ValidationError({"msg": "ids 不能为空", "code": 400, "data": None})
        seen = set()
        uniq = []
        for i in ids:
            if i in seen:
                continue
            seen.add(i)
            uniq.append(i)
        return uniq

    @action(detail=False, methods=["post"], url_path="batch-delete")
    def batch_delete(self, request):
        """
        批量软删除调度任务（数据范围与列表一致）。
        POST /api/execution/scheduled-tasks/batch-delete/
        body: { ids: number[] }
        """
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        qs = self.get_queryset().filter(id__in=ids, is_deleted=False)
        found = list(qs)
        found_ids = {int(o.id) for o in found}
        missing = [i for i in ids if i not in found_ids]
        if not found:
            return Response({"success": True, "deleted": 0, "skipped": len(ids), "missing_ids": ids})

        deleted = 0
        errors = []
        with transaction.atomic():
            for obj in found:
                try:
                    self.perform_destroy(obj)
                    deleted += 1
                except Exception as e:
                    errors.append({"id": int(obj.id), "error": str(e)})
        return Response(
            {
                "success": len(errors) == 0,
                "deleted": deleted,
                "missing_ids": missing,
                "errors": errors,
            }
        )

    @action(detail=False, methods=["post"], url_path="batch-update")
    def batch_update(self, request):
        """
        批量更新调度任务（对所有 ids 应用同一 patch；会触发 scheduler sync）。
        POST /api/execution/scheduled-tasks/batch-update/
        body: { ids: number[], patch: object }
        """
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        patch = request.data.get("patch")
        if not isinstance(patch, dict) or not patch:
            raise ValidationError({"msg": "patch 必须为非空对象", "code": 400, "data": None})
        allowed_keys = {
            "name",
            "cron_expression",
            "status",
            "environment",
            "test_case_ids",
        }
        cleaned = {k: v for (k, v) in patch.items() if k in allowed_keys}
        if not cleaned:
            raise ValidationError({"msg": "patch 未包含可更新字段", "code": 400, "data": None})

        qs = self.get_queryset().filter(id__in=ids, is_deleted=False).prefetch_related("test_cases")
        found = list(qs)
        found_ids = {int(o.id) for o in found}
        missing = [i for i in ids if i not in found_ids]

        updated_ids = []
        errors = []
        with transaction.atomic():
            for obj in found:
                ser = self.get_serializer(obj, data=cleaned, partial=True)
                try:
                    ser.is_valid(raise_exception=True)
                    self.perform_update(ser)
                    updated_ids.append(int(obj.id))
                except Exception as e:
                    errors.append({"id": int(obj.id), "error": str(e)})
        return Response(
            {
                "success": len(errors) == 0,
                "updated": len(updated_ids),
                "updated_ids": updated_ids,
                "missing_ids": missing,
                "errors": errors,
            }
        )

    @action(detail=False, methods=["post"], url_path="batch-copy")
    def batch_copy(self, request):
        """
        批量复制定时任务（复制 cron/环境/用例；新 job_id；默认状态 active）。
        POST /api/execution/scheduled-tasks/batch-copy/
        body: { ids: number[], name_suffix?: string }
        """
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        suffix = str(request.data.get("name_suffix") or "（复制）").strip()[:32] or "（复制）"

        src_qs = (
            self.get_queryset()
            .filter(id__in=ids, is_deleted=False)
            .prefetch_related("test_cases")
        )
        src_list = list(src_qs)
        src_ids = {int(o.id) for o in src_list}
        missing = [i for i in ids if i not in src_ids]
        if not src_list:
            return Response({"success": True, "created": 0, "created_ids": [], "missing_ids": ids})

        created_ids = []
        errors = []
        user = request.user if getattr(request, "user", None) is not None else None
        with transaction.atomic():
            for src in src_list:
                try:
                    new_obj = ScheduledTask.objects.create(
                        name=(str(src.name or "")[:96] + suffix),
                        cron_expression=src.cron_expression,
                        status=ScheduledTask.STATUS_ACTIVE,
                        job_id=f"scheduled-task-{uuid.uuid4().hex}",
                        environment_id=src.environment_id,
                        creator=user if (user and getattr(user, "is_authenticated", False)) else None,
                        updater=user if (user and getattr(user, "is_authenticated", False)) else None,
                    )
                    cases = list(src.test_cases.all())
                    if cases:
                        new_obj.test_cases.set(cases)
                    # 复制后同步调度器（失败则回滚本事务）
                    TestScheduler.instance().sync_task(new_obj)
                    created_ids.append(int(new_obj.id))
                except Exception as e:
                    errors.append({"id": int(src.id), "error": str(e)})
        return Response(
            {
                "success": len(errors) == 0,
                "created": len(created_ids),
                "created_ids": created_ids,
                "missing_ids": missing,
                "errors": errors,
            }
        )

    def perform_create(self, serializer):
        instance = serializer.save(job_id=f"scheduled-task-{uuid.uuid4().hex}")
        try:
            TestScheduler.instance().sync_task(instance)
        except Exception as exc:
            logger.exception("创建调度任务后同步失败: task_id=%s", instance.id)
            raise ValidationError({"msg": f"任务已创建，但调度同步失败: {exc}"})

    def perform_update(self, serializer):
        instance = serializer.save()
        try:
            TestScheduler.instance().sync_task(instance)
        except Exception as exc:
            logger.exception("更新调度任务后同步失败: task_id=%s", instance.id)
            raise ValidationError({"msg": f"任务已更新，但调度同步失败: {exc}"})

    def perform_destroy(self, instance):
        instance.status = ScheduledTask.STATUS_DISABLED
        instance.is_deleted = True
        instance.save(update_fields=["status", "is_deleted", "update_time"])
        TestScheduler.instance().remove_task(instance.id)

    @action(detail=True, methods=["post"], url_path="pause")
    def pause(self, request, pk=None):
        task = self.get_object()
        task.status = ScheduledTask.STATUS_PAUSED
        task.save(update_fields=["status", "update_time"])
        TestScheduler.instance().sync_task(task)
        return Response({"msg": "任务已暂停"})

    @action(detail=True, methods=["post"], url_path="resume")
    def resume(self, request, pk=None):
        task = self.get_object()
        task.status = ScheduledTask.STATUS_ACTIVE
        task.save(update_fields=["status", "update_time"])
        TestScheduler.instance().sync_task(task)
        return Response({"msg": "任务已恢复"})

    @action(detail=True, methods=["post"], url_path="trigger")
    def trigger(self, request, pk=None):
        task = self.get_object()
        execute_scheduled_task(task.id)
        return Response({"msg": "任务已手动触发"})


class ScheduledTaskLogViewSet(BaseModelViewSet):
    queryset = ScheduledTaskLog.objects.select_related("scheduled_task").all()
    serializer_class = ScheduledTaskLogSerializer

    def _parse_id_list(self, raw_ids):
        if raw_ids is None:
            raise ValidationError({"msg": "ids 必填", "code": 400, "data": None})
        if not isinstance(raw_ids, list):
            raise ValidationError({"msg": "ids 必须为数组", "code": 400, "data": None})
        ids = []
        for x in raw_ids:
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                continue
        ids = [i for i in ids if i > 0]
        if not ids:
            raise ValidationError({"msg": "ids 不能为空", "code": 400, "data": None})
        seen = set()
        uniq = []
        for i in ids:
            if i in seen:
                continue
            seen.add(i)
            uniq.append(i)
        return uniq

    def get_queryset(self):
        qs = super().get_queryset()
        scheduled_task = self.request.query_params.get("scheduled_task")
        status_value = (self.request.query_params.get("status") or "").strip()
        message_kw = (self.request.query_params.get("message") or "").strip()
        if scheduled_task not in (None, ""):
            try:
                task_id = int(scheduled_task)
            except (TypeError, ValueError):
                return qs.none()
            qs = qs.filter(scheduled_task_id=task_id)
        if status_value:
            qs = qs.filter(status=status_value)
        if message_kw:
            qs = qs.filter(message__icontains=message_kw)
        return qs.order_by("-trigger_time", "-id")

    @action(detail=False, methods=["post"], url_path="batch-delete")
    def batch_delete(self, request):
        """
        批量软删除调度日志（用于清理；数据范围与列表一致）。
        POST /api/execution/scheduled-task-logs/batch-delete/
        body: { ids: number[] }
        """
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        qs = self.get_queryset().filter(id__in=ids, is_deleted=False)
        found_ids = list(qs.values_list("id", flat=True))
        if not found_ids:
            return Response({"success": True, "deleted": 0, "skipped": len(ids), "missing_ids": ids})
        with transaction.atomic():
            updated = qs.update(is_deleted=True)
        missing = [i for i in ids if i not in set(found_ids)]
        return Response(
            {
                "success": True,
                "deleted": int(updated),
                "skipped": len(missing),
                "missing_ids": missing,
            }
        )

    @action(detail=False, methods=["post"], url_path="batch-delete-by-filter")
    def batch_delete_by_filter(self, request):
        """
        按筛选条件批量软删除调度日志（用于清理历史；数据范围与列表一致）。
        POST /api/execution/scheduled-task-logs/batch-delete-by-filter/
        body:
        - scheduled_task?: number
        - status?: string
        - message?: string
        - before_days?: number (>=1，默认 7；删除 trigger_time < now - days)
        - max_delete?: number (1..5000，默认 500)
        """
        if not isinstance(request.data, dict):
            raise ValidationError(
                {"msg": "请求体必须为 JSON 对象", "code": 400, "data": None}
            )
        body = request.data
        before_days_raw = body.get("before_days")
        max_delete_raw = body.get("max_delete")
        try:
            before_days = int(before_days_raw) if before_days_raw not in (None, "") else 7
        except (TypeError, ValueError):
            before_days = 7
        before_days = max(before_days, 1)
        try:
            max_delete = int(max_delete_raw) if max_delete_raw not in (None, "") else 500
        except (TypeError, ValueError):
            max_delete = 500
        max_delete = min(max(max_delete, 1), 5000)

        qs = self.get_queryset().filter(is_deleted=False)
        # 额外筛选：scheduled_task/status/message（与列表一致）
        scheduled_task = body.get("scheduled_task")
        if scheduled_task not in (None, ""):
            try:
                task_id = int(scheduled_task)
            except (TypeError, ValueError):
                task_id = None
            if task_id is not None:
                qs = qs.filter(scheduled_task_id=task_id)
        status_value = (body.get("status") or "").strip()
        if status_value:
            qs = qs.filter(status=status_value)
        message_kw = (body.get("message") or "").strip()
        if message_kw:
            qs = qs.filter(message__icontains=message_kw)

        cutoff = timezone.now() - timedelta(days=before_days)
        qs = qs.filter(trigger_time__lt=cutoff).order_by("trigger_time", "id")

        target_ids = list(qs.values_list("id", flat=True)[:max_delete])
        if not target_ids:
            return Response({"success": True, "deleted": 0, "message": "无符合条件的可清理日志"})
        with transaction.atomic():
            updated = (
                ScheduledTaskLog.objects.filter(id__in=target_ids, is_deleted=False)
                .update(is_deleted=True)
            )
        return Response(
            {
                "success": True,
                "deleted": int(updated),
                "before_days": before_days,
                "max_delete": max_delete,
            }
        )
