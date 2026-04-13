import json
import logging
import socket
from urllib.parse import urljoin

import requests
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from common.views import *
from testcase.models import *
from testcase.serialize import *
from testcase.services.case_subtypes import (
    create_typed_case,
    get_api_profile_for_execute,
)
from testcase.services.api_execution import preview_resolved_request, run_api_case
from testcase.services.ai_openai import ai_fill_test_data, ai_import_api_cases
from testcase.services.variable_runtime import suggest_extractions
from assistant.knowledge_rag import KnowledgeSearcher
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.db.models import Max, F, Q

logger = logging.getLogger(__name__)


def _environment_http_probe_url(base_url: str, health_path: str) -> str:
    """将 Base URL 与可选相对路径拼接为本次 HTTP 探测地址。"""
    base = (base_url or "").strip()
    path = (health_path or "").strip()
    if not path:
        return base
    root = base if base.endswith("/") else base + "/"
    return urljoin(root, path.lstrip("/"))


_MAX_UPLOAD_IMAGE_SIZE = 5 * 1024 * 1024
_MAX_UPLOAD_IMAGE_COUNT = 10
_ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}


def _recycle_mode_from_params(params) -> bool:
    """是否查看回收站：recycle=1 / is_deleted=true 等。"""
    r = params.get("recycle")
    if r is not None and str(r).strip().lower() in ("1", "true", "yes"):
        return True
    d = params.get("is_deleted")
    if d is not None and str(d).strip().lower() in ("1", "true", "yes"):
        return True
    return False


def _module_self_and_descendant_ids(root_id: int, project_id=None):
    """包含 root 及其所有子模块 id（用于树节点筛选用例）。"""
    try:
        rid = int(root_id)
    except (TypeError, ValueError):
        return []
    ids = {rid}
    frontier = [rid]
    q_base = TestModule.objects.filter(is_deleted=False)
    if project_id is not None:
        try:
            q_base = q_base.filter(project_id=int(project_id))
        except (TypeError, ValueError):
            pass
    while frontier:
        cur = frontier.pop()
        for cid in q_base.filter(parent_id=cur).values_list("id", flat=True):
            if cid not in ids:
                ids.add(cid)
                frontier.append(cid)
    return list(ids)


class TestCasePagination(PageNumberPagination):
    """与前端 page / page_size 对齐（DRF 标准分页）。"""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


# Create your views here.

class TestModuleViewSet(BaseModelViewSet):
    queryset = TestModule.objects.all()
    serializer_class = TestModuleSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        project = self.request.query_params.get("project")
        if project not in (None, ""):
            try:
                project_id = int(project)
            except (TypeError, ValueError):
                return qs.none()
            qs = qs.filter(project_id=project_id)
        test_type = (self.request.query_params.get("testType") or "").strip()
        allowed = {c[0] for c in TEST_CASE_TYPE_CHOICES}
        if test_type and test_type in allowed:
            qs = qs.filter(test_type=test_type)
        return qs.order_by("parent_id", "id")


class TestEnvironmentViewSet(BaseModelViewSet):
    queryset = TestEnvironment.objects.all()
    serializer_class = TestEnvironmentSerializer

    @action(detail=True, methods=["post"], url_path="validate")
    def validate_environment(self, request, pk=None):
        """
        校验环境连通性：
        - HTTP: 对 base_url（或与 health_check_path 拼接后的地址）发 GET
        - 请求体可选 health_path：仅本次校验覆盖环境上保存的路径
        - DB: host/port TCP 可达性
        """
        env_obj = self.get_object()
        timeout = request.data.get("timeout", 5)
        try:
            timeout = int(timeout)
        except (TypeError, ValueError):
            timeout = 5
        timeout = min(max(timeout, 1), 30)

        result = {"ok": True, "http": {"ok": False}, "db": {"ok": False}}

        if "health_path" in request.data:
            probe_path = str(request.data.get("health_path") or "").strip()
        else:
            probe_path = (getattr(env_obj, "health_check_path", None) or "").strip()

        base = (env_obj.base_url or "").strip()
        if not base:
            result["http"] = {"ok": False, "error": "未配置 Base URL，无法执行 HTTP 探测"}
            result["ok"] = False
        else:
            full_url = _environment_http_probe_url(base, probe_path)
            try:
                resp = requests.get(full_url, timeout=timeout)
                result["http"] = {
                    "ok": True,
                    "status_code": resp.status_code,
                    "url": full_url,
                }
            except Exception as exc:
                logger.warning("环境 HTTP 校验失败: env_id=%s, err=%s", env_obj.id, exc)
                result["http"] = {"ok": False, "error": str(exc), "url": full_url}
                result["ok"] = False

        db_cfg = env_obj.db_config if isinstance(env_obj.db_config, dict) else {}
        db_host = str(db_cfg.get("host", "")).strip()
        db_port = db_cfg.get("port")
        if db_host and db_port:
            try:
                db_port = int(db_port)
                with socket.create_connection((db_host, db_port), timeout=timeout):
                    pass
                result["db"] = {"ok": True, "host": db_host, "port": db_port}
            except Exception as exc:
                logger.warning("环境 DB 校验失败: env_id=%s, err=%s", env_obj.id, exc)
                result["db"] = {"ok": False, "error": str(exc), "host": db_host, "port": db_port}
                result["ok"] = False
        elif db_cfg:
            result["db"] = {"ok": False, "error": "db_config 缺少 host/port"}
            result["ok"] = False

        return Response(result)


class EnvironmentVariableViewSet(BaseModelViewSet):
    queryset = EnvironmentVariable.objects.select_related("environment").all()
    serializer_class = EnvironmentVariableSerializer

class TestCaseViewSet(BaseModelViewSet):
    queryset = TestCase.objects.all()
    serializer_class = TestCaseSerializer
    pagination_class = TestCasePagination

    def perform_destroy(self, instance):
        """软删除：禁止物理 delete，与 batch-delete 行为一致。"""
        if instance.is_deleted:
            return
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["is_deleted", "deleted_at", "update_time"])

    def create(self, request, *args, **kwargs):
        case_title = ""
        if isinstance(request.data, dict):
            case_title = (request.data.get("case_name") or "").strip()
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            detail = getattr(exc, "detail", None)
            code = None
            if isinstance(detail, dict):
                raw_code = detail.get("code")
                if isinstance(raw_code, list) and raw_code:
                    code = str(raw_code[0])
                elif raw_code is not None:
                    code = str(raw_code)
            if code == "RECYCLE_CONFLICT":
                return Response(detail, status=status.HTTP_409_CONFLICT)
            raise
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        payload = dict(serializer.data)
        # 相似用例推荐：创建时基于标题到知识库检索模板/实践。
        try:
            payload["knowledge_recommendations"] = (
                KnowledgeSearcher.search_similar(case_title, top_k=5) if case_title else []
            )
        except Exception:
            payload["knowledge_recommendations"] = []
        return Response(payload, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        params = self.request.query_params
        recycle_mode = _recycle_mode_from_params(params)

        user = getattr(self.request, "user", None)
        if recycle_mode:
            qs = TestCase.all_objects.filter(is_deleted=True)
            if self.enable_data_scope:
                if not user or not user.is_authenticated or self._is_admin_user(user):
                    pass
                else:
                    qs = self._apply_member_scope(qs, user)
        else:
            qs = super().get_queryset()

        project = params.get("project")
        project_id = None
        if project not in (None, ""):
            try:
                project_id = int(project)
            except (TypeError, ValueError):
                return qs.none()
            if recycle_mode and user and getattr(user, "is_authenticated", False):
                # 回收站：无 module 的软删用例仅用 module__project_id 会筛掉（module 被删或 SET_NULL）。
                # 普通用户：本人创建的孤儿；管理员：创建者须为该项目成员，避免跨项目误展示。
                if self._is_admin_user(user):
                    qs = qs.filter(
                        Q(module__project_id=project_id)
                        | Q(module__isnull=True, creator__projects=project_id)
                    ).distinct()
                else:
                    qs = qs.filter(
                        Q(module__project_id=project_id)
                        | Q(module__isnull=True, creator=user)
                    )
            else:
                qs = qs.filter(module__project_id=project_id)
        # 回收站列表须覆盖「本项目 + 测试类型」下全部软删项；忽略 module 以免残留筛选导致「回收站是空的」
        module = params.get("module")
        if not recycle_mode and module not in (None, ""):
            try:
                mid = int(module)
            except (TypeError, ValueError):
                mid = None
            if mid is not None:
                mod_ids = _module_self_and_descendant_ids(mid, project_id)
                if mod_ids:
                    qs = qs.filter(module_id__in=mod_ids)
                else:
                    qs = qs.none()
        search = (params.get("search") or "").strip()
        if search:
            qs = qs.filter(case_name__icontains=search)
        test_type = (params.get("testType") or "").strip()
        allowed = {c[0] for c in TestCase.TEST_TYPE_CHOICES}
        if test_type and test_type in allowed:
            qs = qs.filter(test_type=test_type)

        qs = qs.select_related(
            "apitestcase",
            "perftestcase",
            "securitytestcase",
            "uitestcase",
        )
        if recycle_mode:
            return qs.order_by("-deleted_at", "-id")
        return qs.order_by("-id")

    def _parse_id_list(self, raw_ids):
        if not isinstance(raw_ids, list) or not raw_ids:
            return None, Response(
                {"msg": "请提供非空的 ids 数组"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            id_list = [int(x) for x in raw_ids]
        except (TypeError, ValueError):
            return None, Response(
                {"msg": "ids 中的元素须为整数"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(id_list) > 500:
            return None, Response(
                {"msg": "单次最多处理 500 条"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return id_list, None

    @action(detail=False, methods=["post"], url_path="batch-delete")
    def batch_delete(self, request):
        """批量逻辑删除（与单条 delete 行为一致）。"""
        id_list, err = self._parse_id_list(request.data.get("ids"))
        if err is not None:
            return err
        # 不得沿用「回收站列表」语义：若请求 URL 误带 recycle=1，get_queryset 只剩已删行，id 匹配为 0
        qs = TestCase.objects.filter(is_deleted=False, id__in=id_list)
        user = getattr(request, "user", None)
        if self.enable_data_scope and user and user.is_authenticated and not self._is_admin_user(user):
            qs = self._apply_member_scope(qs, user)
        params = request.query_params
        proj = params.get("project")
        if proj not in (None, ""):
            try:
                pid = int(proj)
                qs = qs.filter(module__project_id=pid)
            except (TypeError, ValueError):
                qs = qs.none()
        n = qs.update(is_deleted=True, deleted_at=timezone.now())
        return Response({"deleted": n, "msg": f"已删除 {n} 条用例"})

    @action(detail=False, methods=["get"], url_path="recycle-bin")
    def recycle_bin(self, request):
        """回收站列表：与 GET /cases/?recycle=1 相同，复用 get_queryset（含 project/module 等筛选）。"""
        qp = request.query_params
        mutable = getattr(qp, "_mutable", False)
        qp._mutable = True
        qp["recycle"] = "1"
        try:
            return self.list(request)
        finally:
            qp.pop("recycle", None)
            qp._mutable = mutable

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        case = get_object_or_404(TestCase.deleted_objects, pk=pk)
        case.restore()
        return Response({"msg": "已恢复", "id": case.id})

    @action(detail=True, methods=["delete"], url_path="hard-delete")
    def hard_delete(self, request, pk=None):
        case = get_object_or_404(TestCase.deleted_objects, pk=pk)
        case.hard_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="batch-execute")
    def batch_execute(self, request):
        """批量记录一次执行（exec_count +1）。"""
        id_list, err = self._parse_id_list(request.data.get("ids"))
        if err is not None:
            return err
        qs = self.get_queryset().filter(id__in=id_list)
        n = qs.update(exec_count=F("exec_count") + 1)
        return Response({"updated": n, "msg": f"已为 {n} 条用例记录执行"})

    @action(detail=True, methods=["post"], url_path="execute-api")
    def execute_api(self, request, pk=None):
        """
        执行单条 API 用例：发起真实 HTTP，写入 ExecutionLog + ApiTestLog（兼容旧字段）。
        路径：POST /api/testcase/cases/<id>/execute-api/
        请求体可选与 run-api 相同字段，例如 environment_id（与登记环境 base_url 拼接相对路径）。
        """
        ov = request.data if isinstance(request.data, dict) else {}
        return self._run_api_core(request, overrides=ov, write_legacy_apilog=True)

    @action(detail=True, methods=["post"], url_path="run-api")
    def run_api(self, request, pk=None):
        """
        执行 API 用例并允许在请求体中覆盖 url/method/headers/body/expected_status。
        仅写入 ExecutionLog（不写 ApiTestLog）。
        POST /api/testcase/cases/<id>/run-api/
        """
        ov = request.data if isinstance(request.data, dict) else {}
        return self._run_api_core(
            request, overrides=ov, write_legacy_apilog=False
        )

    @action(detail=True, methods=["post"], url_path="preview-run-api")
    def preview_run_api(self, request, pk=None):
        """
        预览执行前最终请求（不发网络请求）：
        - 应用 environment_id 对 base_url 拼接
        - 应用环境变量/运行时变量替换 ${var}
        """
        case = self.get_object()
        if case.test_type != TestCase.TEST_TYPE_API:
            return Response(
                {"msg": "仅 API 测试类型的用例支持预览执行请求"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        api_prof = get_api_profile_for_execute(case)
        if api_prof is None:
            return Response(
                {"msg": "API 用例扩展数据缺失，请编辑保存该用例后再预览"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ov = request.data if isinstance(request.data, dict) else {}
        try:
            data = preview_resolved_request(api_prof, overrides=ov)
        except ValueError as exc:
            return Response({"msg": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data)

    def _run_api_core(self, request, overrides, write_legacy_apilog: bool):
        case = self.get_object()
        if case.test_type != TestCase.TEST_TYPE_API:
            return Response(
                {"msg": "仅 API 测试类型的用例支持「执行」"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        api_prof = get_api_profile_for_execute(case)
        if api_prof is None:
            return Response(
                {"msg": "API 用例扩展数据缺失，请编辑保存该用例后再执行"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = run_api_case(
                case,
                api_prof,
                overrides=overrides,
                user=request.user,
                write_legacy_apilog=write_legacy_apilog,
            )
        except ValueError as exc:
            return Response(
                {"msg": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payload = {
            "execution_log": ExecutionLogSerializer(
                result.execution_log, context={"request": request}
            ).data,
            "msg": result.message,
            "extracted_variables": result.extracted_variables,
        }
        if result.api_test_log is not None:
            payload["log"] = ApiTestLogSerializer(
                result.api_test_log, context={"request": request}
            ).data
        return Response(payload)

    @action(detail=True, methods=["get"], url_path="execution-logs")
    def execution_logs(self, request, pk=None):
        """分页列出该用例的 ExecutionLog。"""
        case = self.get_object()
        qs = ExecutionLog.objects.filter(
            test_case=case, is_deleted=False
        ).order_by("-create_time")
        page = self.paginate_queryset(qs)
        if page is not None:
            ser = ExecutionLogSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(ser.data)
        ser = ExecutionLogSerializer(qs, many=True, context={"request": request})
        return Response({"results": ser.data, "count": qs.count()})

    @action(detail=True, methods=["get"], url_path="versions")
    def versions(self, request, pk=None):
        """分页列出该用例的快照版本（按时间倒序）。"""
        case = self.get_object()
        qs = (
            TestCaseVersion.objects.filter(test_case=case, is_deleted=False)
            .select_related("release_plan", "creator")
            .order_by("-create_time", "-id")
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            ser = TestCaseVersionSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(ser.data)
        ser = TestCaseVersionSerializer(qs, many=True, context={"request": request})
        return Response({"results": ser.data, "count": qs.count()})

    @action(detail=True, methods=["post"], url_path="rollback-version")
    def rollback_version(self, request, pk=None):
        """
        按 TestCaseVersion 快照回溯当前用例。
        body: {"version_id": 123}
        """
        case = self.get_object()
        raw_vid = request.data.get("version_id")
        try:
            version_id = int(raw_vid)
        except (TypeError, ValueError):
            return Response({"msg": "version_id 必须为整数"}, status=status.HTTP_400_BAD_REQUEST)

        version = TestCaseVersion.objects.filter(
            id=version_id, test_case=case, is_deleted=False
        ).first()
        if version is None:
            return Response({"msg": "快照不存在"}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            baseline = TestCaseVersion.create_version(
                test_case=case,
                release_plan=version.release_plan,
                creator=request.user,
                source_version=version,
            )
            case.apply_snapshot_payload(version.case_snapshot or {})

        return Response(
            {
                "msg": "回溯成功",
                "rollback_to_version_id": version.id,
                "baseline_version_id": baseline.id,
            }
        )


class TestCaseStepViewSet(BaseModelViewSet):
    queryset = TestCaseStep.objects.all()
    serializer_class = TestCaseStepSerializer

class TestDesignViewSet(BaseModelViewSet):
    queryset = TestDesign.objects.all()
    serializer_class = TestDesignSerializer


class TestApproachViewSet(BaseModelViewSet):
    queryset = TestApproach.objects.all()
    serializer_class = TestApproachSerializer

    @action(methods=["get"], detail=True, url_path="images")
    def list_images(self, request, pk=None):
        approach = self.get_object()
        qs = approach.images.all().order_by("sort_order", "-create_time")
        serializer = TestApproachImageSerializer(qs, many=True, context={"request": request})
        return Response({"results": serializer.data, "count": qs.count()})

    @action(methods=["post"], detail=True, url_path="images/upload")
    def upload_images(self, request, pk=None):
        """
        上传方案图片（支持多文件）。
        前端建议使用 multipart form-data 字段名：`images`。
        """

        approach = self.get_object()
        files = request.FILES.getlist("images")
        if not files:
            # 兼容部分组件：单文件上传时可能叫 image/file
            single = request.FILES.get("image") or request.FILES.get("file")
            if single:
                files = [single]

        if not files:
            return Response({"msg": "未接收到图片文件"}, status=status.HTTP_400_BAD_REQUEST)
        if len(files) > _MAX_UPLOAD_IMAGE_COUNT:
            return Response(
                {"msg": f"单次最多上传 {_MAX_UPLOAD_IMAGE_COUNT} 张图片"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for f in files:
            ext = (str(getattr(f, "name", "")).rsplit(".", 1)[-1] or "").lower()
            if ext not in _ALLOWED_IMAGE_EXTENSIONS:
                return Response(
                    {"msg": f"仅支持图片格式：{', '.join(sorted(_ALLOWED_IMAGE_EXTENSIONS))}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if int(getattr(f, "size", 0) or 0) > _MAX_UPLOAD_IMAGE_SIZE:
                return Response(
                    {"msg": "图片大小不能超过 5MB"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        last_order = (
            approach.images.aggregate(m=Max("sort_order")).get("m") or 0
        )

        user = request.user
        created = []
        for i, f in enumerate(files):
            kwargs = {
                "approach": approach,
                "image": f,
                "sort_order": last_order + i + 1,
            }
            if user and user.is_authenticated:
                kwargs["creator"] = user
                kwargs["updater"] = user
            created.append(TestApproachImage.objects.create(**kwargs))

        # 兼容旧字段：如果没有封面图，就自动取第一张
        first = approach.images.all().order_by("sort_order", "-create_time").first()
        if first and first.image and not approach.cover_image:
            approach.cover_image = first.image.url
            approach.save(update_fields=["cover_image"])

        serializer = TestApproachImageSerializer(
            created, many=True, context={"request": request}
        )
        return Response({"results": serializer.data, "count": len(created)}, status=status.HTTP_201_CREATED)

    @action(
        methods=["delete"],
        detail=True,
        url_path=r"images/(?P<image_id>\d+)",
    )
    def delete_image(self, request, pk=None, image_id=None):
        """删除指定方案下的一张图片（硬删除记录并移除文件）。"""
        approach = self.get_object()
        img = get_object_or_404(
            TestApproachImage,
            pk=image_id,
            approach=approach,
        )
        if img.image:
            img.image.delete(save=False)
        img.delete()

        first = (
            approach.images.all()
            .order_by("sort_order", "-create_time")
            .first()
        )
        if first and first.image:
            approach.cover_image = first.image.url
        else:
            approach.cover_image = None
        approach.save(update_fields=["cover_image"])

        return Response(status=status.HTTP_204_NO_CONTENT)


def _user_can_write_module_cases(user, module) -> bool:
    if not user or not user.is_authenticated:
        return False
    if (
        user.is_superuser
        or user.is_staff
        or getattr(user, "is_system_admin", False)
    ):
        return True
    proj = module.project
    if getattr(proj, "creator_id", None) == user.pk:
        return True
    return proj.members.filter(pk=user.pk).exists()


class AiFillTestDataAPIView(APIView):
    """
    AI 根据字段结构生成测试数据。
    POST /api/testcase/ai-fill-test-data/
    body: { "fields": [{"name":"phone","type":"string"}], "api_key"?: ... }
    """

    def post(self, request):
        fields = request.data.get("fields")
        if fields is None:
            return Response({"msg": "缺少 fields"}, status=status.HTTP_400_BAD_REQUEST)
        data, err = ai_fill_test_data(
            fields,
            api_key=request.data.get("api_key"),
            base_url=request.data.get("base_url")
            or request.data.get("api_base_url"),
            model=request.data.get("model"),
        )
        if err:
            return Response({"msg": err}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"data": data})


class SuggestExtractionsAPIView(APIView):
    """
    基于响应 JSON 结构生成「变量提取建议」。
    POST /api/testcase/suggest-extractions/
    body: { "json_data": {...} } 或 { "body": {...} } 或直接传任意 JSON 对象
    """

    def post(self, request):
        payload = request.data
        if isinstance(payload, dict):
            if "json_data" in payload:
                data = payload.get("json_data")
            elif "body" in payload:
                data = payload.get("body")
            else:
                data = payload
        else:
            data = payload
        if data is None:
            return Response(
                {"msg": "请提供 json_data 或 body"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"suggestions": suggest_extractions(data)})


class ApiImportFromSpecAPIView(APIView):
    """
    从 Swagger/OpenAPI JSON 或 cURL 文本解析并批量创建 API 用例。
    POST /api/testcase/import-api-spec/
    body: { "source_type": "swagger"|"curl", "content": "...", "module": id }
    """

    def post(self, request):
        source_type = request.data.get("source_type") or request.data.get("type")
        content = (
            request.data.get("content")
            or request.data.get("text")
            or ""
        )
        raw_mod = request.data.get("module") or request.data.get("module_id")
        if raw_mod in (None, ""):
            return Response(
                {"msg": "请提供 module 或 module_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            mid = int(raw_mod)
        except (TypeError, ValueError):
            return Response(
                {"msg": "module 须为整数"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        module = TestModule.objects.filter(pk=mid, is_deleted=False).first()
        if module is None:
            return Response({"msg": "模块不存在"}, status=status.HTTP_404_NOT_FOUND)
        if not _user_can_write_module_cases(request.user, module):
            return Response({"msg": "无权在该模块下创建用例"}, status=status.HTTP_403_FORBIDDEN)
        if module.test_type != TEST_CASE_TYPE_API:
            return Response(
                {"msg": "目标模块的测试类型须为 API 测试"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items, err = ai_import_api_cases(
            str(source_type or ""),
            str(content),
            api_key=request.data.get("api_key"),
            base_url=request.data.get("base_url")
            or request.data.get("api_base_url"),
            model=request.data.get("model"),
        )
        if err:
            return Response({"msg": err}, status=status.HTTP_400_BAD_REQUEST)

        is_curl = str(source_type or "").strip().lower() == "curl"
        stored_curl = (str(content or "").strip()[:120_000]) if is_curl else ""

        user = request.user
        created_ids = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = (item.get("case_name") or "未命名接口").strip()[:255]
            headers = item.get("api_headers")
            if not isinstance(headers, dict):
                headers = {}
            body = item.get("api_body")
            if not isinstance(body, (dict, list)):
                body = {}
            exp = item.get("api_expected_status")
            if exp is not None:
                try:
                    exp = int(exp)
                except (TypeError, ValueError):
                    exp = None
            api_payload = {
                "api_url": str(item.get("api_url", "") or "")[:2048],
                "api_method": str(item.get("api_method", "GET") or "GET")
                .strip()
                .upper()[:16],
                "api_headers": headers,
                "api_body": body,
                "api_expected_status": exp,
            }
            if stored_curl:
                api_payload["api_source_curl"] = stored_curl
            base = {
                "module": module,
                "case_name": name,
                "test_type": TEST_CASE_TYPE_API,
                "level": "P2",
                "is_valid": True,
            }
            if user.is_authenticated:
                base["creator"] = user
                base["updater"] = user
            case = create_typed_case(
                TEST_CASE_TYPE_API,
                base,
                api_payload,
                {},
                {},
                {},
            )
            created_ids.append(case.id)

        return Response({"created": len(created_ids), "ids": created_ids})

