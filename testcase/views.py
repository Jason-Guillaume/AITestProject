import json
import logging
import socket
import time
from difflib import SequenceMatcher
import re
from urllib.parse import urljoin

import requests
from django.utils import timezone
from django.shortcuts import get_object_or_404
from common.views import *
from testcase.models import *
from testcase.serialize import *
from testcase.services.case_subtypes import (
    create_typed_case,
    get_api_profile_for_execute,
)
from testcase.services.ai_import_precheck_core import precheck_api_draft_item
from testcase.services.api_execution import preview_resolved_request, run_api_case
from testcase.services.ai_openai import ai_fill_test_data, ai_import_api_cases
from testcase.services.ai_case_gate import gate_ai_api_cases
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
            result["http"] = {
                "ok": False,
                "error": "未配置 Base URL，无法执行 HTTP 探测",
            }
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
                result["db"] = {
                    "ok": False,
                    "error": str(exc),
                    "host": db_host,
                    "port": db_port,
                }
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
                KnowledgeSearcher.search_similar(case_title, top_k=5)
                if case_title
                else []
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

        _subtype_rel = {
            TEST_CASE_TYPE_API: ("apitestcase",),
            TEST_CASE_TYPE_PERFORMANCE: ("perftestcase",),
            TEST_CASE_TYPE_SECURITY: ("securitytestcase",),
            TEST_CASE_TYPE_UI_AUTOMATION: ("uitestcase",),
        }
        if test_type == TEST_CASE_TYPE_FUNCTIONAL:
            pass
        elif test_type in _subtype_rel:
            qs = qs.select_related(*_subtype_rel[test_type])
        else:
            qs = qs.select_related(
                "apitestcase",
                "perftestcase",
                "securitytestcase",
                "uitestcase",
            )
        if recycle_mode:
            return qs.order_by("-deleted_at", "-id")
        return qs.order_by("-id")

    @action(detail=False, methods=["post"], url_path="ai-import")
    def ai_import(self, request):
        """
        AI 批量导入测试用例（后端事务 + 逐条结果）：
        POST /api/testcase/cases/ai-import/

        body:
        - project_id: 必填
        - test_type: 必填（functional/api/performance/security/ui-automation）
        - run_id: 可选（assistant.AiCaseGenerationRun id）
        - default_module_id: 可选
        - items: [{ case_name, level, expected_result, precondition, steps, module_name, ...typed fields }]
        """
        if not isinstance(request.data, dict):
            raise ValidationError({"message": "请求体必须为 JSON 对象"})

        project_id = request.data.get("project_id")
        test_type = (request.data.get("test_type") or "").strip()
        run_id = request.data.get("run_id")
        default_module_id = request.data.get("default_module_id")
        strict = request.data.get("strict", False)
        items = request.data.get("items")

        try:
            project_id = int(project_id)
        except (TypeError, ValueError):
            raise ValidationError({"project_id": "project_id 必填且必须为整数"})

        allowed = {c[0] for c in TEST_CASE_TYPE_CHOICES}
        if test_type not in allowed:
            raise ValidationError({"test_type": "test_type 无效"})

        if items is None:
            raise ValidationError({"items": "items 必填"})
        if not isinstance(items, list):
            raise ValidationError({"items": "items 必须为数组"})
        if not items:
            return Response(
                {"success": True, "imported": [], "failed": [], "skipped": 0}
            )

        s_flag = str(strict).strip().lower()
        strict = s_flag in ("1", "true", "yes")

        precheck_overrides = request.data.get("precheck_overrides")
        if not isinstance(precheck_overrides, dict):
            precheck_overrides = {}

        if default_module_id not in (None, ""):
            try:
                default_module_id = int(default_module_id)
            except (TypeError, ValueError):
                default_module_id = None
        else:
            default_module_id = None

        if run_id not in (None, ""):
            try:
                run_id = int(run_id)
            except (TypeError, ValueError):
                run_id = None
        else:
            run_id = None

        module_qs = TestModule.objects.filter(
            project_id=project_id, is_deleted=False, test_type=test_type
        )

        def _norm_module_key(name: str) -> str:
            return (name or "").strip().lower()

        module_names = list(module_qs.values_list("id", "name"))
        module_cache = {_norm_module_key(name): mid for (mid, name) in module_names}
        created_module_cache: dict[str, int] = {}

        module_match_threshold = request.data.get("module_match_threshold", 0.92)
        try:
            module_match_threshold = float(module_match_threshold)
        except (TypeError, ValueError):
            module_match_threshold = 0.92
        module_match_threshold = max(0.70, min(module_match_threshold, 0.99))

        def _best_module_match(name: str):
            """
            返回 (matched_id, matched_name, score)；当 score 不足阈值时 matched_id 为 None。
            """
            raw = (name or "").strip()
            if not raw:
                return None, "", 0.0
            k = _norm_module_key(raw)
            if k in module_cache:
                return module_cache[k], raw, 1.0
            best = (None, "", 0.0)
            for mid, mname in module_names:
                try:
                    score = SequenceMatcher(None, raw, str(mname or "")).ratio()
                except Exception:
                    score = 0.0
                if score > best[2]:
                    best = (mid, str(mname or ""), float(score))
            if best[0] is not None and best[2] >= module_match_threshold:
                return best
            return None, best[1], best[2]

        def _get_or_create_module_id(module_name: str):
            raw = (module_name or "").strip()
            if not raw:
                return None
            k = _norm_module_key(raw)
            if k in created_module_cache:
                return created_module_cache[k], "created", raw, 1.0
            if k in module_cache:
                return module_cache[k], "exact", raw, 1.0

            matched_id, matched_name, score = _best_module_match(raw)
            if matched_id is not None:
                module_cache[k] = matched_id
                return matched_id, "fuzzy", matched_name, score

            user = getattr(request, "user", None)
            m = TestModule.objects.create(
                project_id=project_id,
                name=raw,
                parent_id=None,
                test_type=test_type,
                creator=user if getattr(user, "is_authenticated", False) else None,
                updater=user if getattr(user, "is_authenticated", False) else None,
            )
            module_cache[k] = m.id
            created_module_cache[k] = m.id
            module_names.append((m.id, raw))
            return m.id, "created", raw, 1.0

        def _build_step_desc(row: dict) -> str:
            parts = []
            pre = str(row.get("precondition") or "").strip()
            if pre:
                parts.append(f"【前置条件】\n{pre}")
            steps = str(row.get("steps") or "").strip()
            if steps:
                parts.append(f"【操作步骤】\n{steps}")
            return "\n\n".join(parts) or "（无详细步骤，请编辑补充）"

        def _normalize_steps(row: dict):
            """
            支持两种导入模式：
            1) 兼容旧字段：precondition/steps/expected_result -> 单 step
            2) 结构化 steps：steps_list / steps（数组） -> 多 step

            每个 step:
            - step_desc: string（必填）
            - expected_result: string（可选，默认 '—'）
            """
            # 结构化数组优先
            sl = row.get("steps_list")
            if sl is None:
                sl = row.get("stepsList")
            if sl is None and isinstance(row.get("steps"), list):
                sl = row.get("steps")
            if isinstance(sl, list) and sl:
                out = []
                for it in sl:
                    if not isinstance(it, dict):
                        continue
                    desc = str(
                        it.get("step_desc") or it.get("desc") or it.get("action") or ""
                    ).strip()
                    if not desc:
                        continue
                    exp = (
                        str(
                            it.get("expected_result") or it.get("expected") or ""
                        ).strip()
                        or "—"
                    )
                    out.append({"step_desc": desc, "expected_result": exp})
                if out:
                    return out
            # fallback: 单 step
            exp = str(row.get("expected_result") or "").strip() or "—"
            return [{"step_desc": _build_step_desc(row), "expected_result": exp}]

        imported = []
        failed = []
        skipped = 0

        with transaction.atomic():
            for idx, raw in enumerate(items):
                sp = transaction.savepoint()
                try:
                    if not isinstance(raw, dict):
                        raise ValidationError("item 必须为对象")
                    case_name = str(raw.get("case_name") or "").strip()
                    if not case_name:
                        raise ValidationError("case_name 必填")
                    level = str(raw.get("level") or "").strip() or "P2"

                    module_name = str(
                        raw.get("module_name") or raw.get("moduleName") or ""
                    ).strip()
                    raw_mid = raw.get("module_id") or raw.get("moduleId")
                    mid = None
                    module_resolution = None
                    if raw_mid not in (None, ""):
                        try:
                            mid = int(raw_mid)
                        except (TypeError, ValueError):
                            mid = None
                        if mid is not None:
                            # 校验 module_id 属于本 project + test_type
                            if not module_qs.filter(id=mid).exists():
                                raise ValidationError(
                                    "module_id 不存在或不属于当前项目/测试类型"
                                )
                            module_resolution = {
                                "mode": "explicit",
                                "matched_name": "",
                                "score": 1.0,
                            }
                    if mid is None:
                        resolved = (
                            _get_or_create_module_id(module_name)
                            if module_name
                            else None
                        )
                        mid = resolved[0] if resolved else None
                        module_resolution = (
                            {
                                "mode": resolved[1],
                                "matched_name": resolved[2],
                                "score": resolved[3],
                            }
                            if resolved
                            else None
                        )
                    if not mid and default_module_id:
                        mid = default_module_id
                    if not mid:
                        skipped += 1
                        raise ValidationError(
                            "缺少模块归属（module_name/default_module_id）"
                        )

                    payload: dict = {
                        "case_name": case_name,
                        "level": level,
                        "module": mid,
                        "test_type": test_type,
                        "ai_run": run_id,
                    }

                    if test_type == TEST_CASE_TYPE_API:
                        url = str(raw.get("api_url") or "").strip()
                        method = (
                            str(raw.get("api_method") or "GET").strip().upper()[:16]
                        )
                        if url:
                            payload["api_url"] = url
                        if method:
                            payload["api_method"] = method
                        if strict:
                            if not url:
                                raise ValidationError("API 用例缺少 api_url")
                            if not method:
                                raise ValidationError("API 用例缺少 api_method")
                            pr = precheck_api_draft_item(raw, precheck_overrides)
                            if not pr.get("ok"):
                                msg_parts = []
                                if pr.get("error"):
                                    msg_parts.append(str(pr["error"]))
                                uv = pr.get("unresolved_vars") or []
                                if uv:
                                    msg_parts.append(
                                        "未替换变量: "
                                        + ", ".join(str(x) for x in uv[:20])
                                    )
                                raise ValidationError(
                                    "; ".join(msg_parts) or "API 导入前预检未通过"
                                )
                        if isinstance(raw.get("api_headers"), dict):
                            payload["api_headers"] = raw.get("api_headers")
                        if raw.get("api_body") is not None:
                            payload["api_body"] = raw.get("api_body")
                        if raw.get("api_expected_status") not in (None, ""):
                            try:
                                payload["api_expected_status"] = int(
                                    raw.get("api_expected_status")
                                )
                            except (TypeError, ValueError):
                                pass
                        if raw.get("api_source_curl"):
                            payload["api_source_curl"] = str(
                                raw.get("api_source_curl") or ""
                            )[:2000]

                    if test_type == TEST_CASE_TYPE_SECURITY:
                        if raw.get("attack_surface"):
                            payload["attack_surface"] = str(
                                raw.get("attack_surface") or ""
                            )[:512]
                        if raw.get("tool_preset"):
                            payload["tool_preset"] = str(raw.get("tool_preset") or "")[
                                :128
                            ]
                        rl = str(raw.get("risk_level") or "").strip()
                        if rl in ("高", "中", "低"):
                            payload["risk_level"] = rl

                    serializer = TestCaseSerializer(
                        data=payload, context={"request": request}
                    )
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
                            base = case_name or "用例"
                            suffix = f"·{int(time.time())}"
                            next_name = (base + suffix)[:255]
                            payload["case_name"] = next_name
                            serializer = TestCaseSerializer(
                                data=payload, context={"request": request}
                            )
                            serializer.is_valid(raise_exception=True)
                        else:
                            raise
                    case_obj = serializer.save()

                    user = getattr(request, "user", None)
                    steps = _normalize_steps(raw)
                    if strict and not steps:
                        raise ValidationError("用例缺少可导入的步骤")
                    for sidx, st in enumerate(steps, start=1):
                        TestCaseStep.objects.create(
                            testcase_id=case_obj.id,
                            step_number=sidx,
                            step_desc=str(st.get("step_desc") or "").strip()[:4000]
                            or "（无详细步骤，请编辑补充）",
                            expected_result=str(
                                st.get("expected_result") or ""
                            ).strip()[:2000]
                            or "—",
                            creator=(
                                user
                                if getattr(user, "is_authenticated", False)
                                else None
                            ),
                            updater=(
                                user
                                if getattr(user, "is_authenticated", False)
                                else None
                            ),
                        )

                    imported.append(
                        {
                            "index": idx,
                            "case_id": case_obj.id,
                            "case_name": case_obj.case_name,
                            "steps_created": len(steps),
                            "module_resolution": module_resolution,
                        }
                    )
                    transaction.savepoint_commit(sp)
                except Exception as e:
                    transaction.savepoint_rollback(sp)
                    failed.append({"index": idx, "error": str(e)})

        return Response(
            {
                "success": True,
                "imported": imported,
                "failed": failed,
                "skipped": skipped,
            }
        )

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
        if (
            self.enable_data_scope
            and user
            and user.is_authenticated
            and not self._is_admin_user(user)
        ):
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
        return self._run_api_core(request, overrides=ov, write_legacy_apilog=False)

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

    @action(detail=False, methods=["post"], url_path="batch-preview-run-api")
    def batch_preview_run_api(self, request):
        """
        批量预览 API 用例执行前最终请求（不发网络请求）：
        POST /api/testcase/cases/batch-preview-run-api/

        body:
        - ids: number[]（必填）
        - overrides: object（可选，透传给 preview_resolved_request，例如 environment_id / variables）
        """
        if not isinstance(request.data, dict):
            return Response({"msg": "请求体必须为 JSON 对象"}, status=status.HTTP_400_BAD_REQUEST)
        id_list, err = self._parse_id_list(request.data.get("ids"))
        if err is not None:
            return err
        overrides = request.data.get("overrides") if isinstance(request.data.get("overrides"), dict) else {}

        # 只处理 API 用例
        qs = TestCase.objects.filter(is_deleted=False, id__in=id_list, test_type=TestCase.TEST_TYPE_API)

        # 保持结果顺序与 ids 一致
        by_id = {c.id: c for c in qs}

        var_pat = re.compile(r"\$\{[^}]+\}")

        def _find_unresolved_vars(obj):
            hits = set()
            try:
                text = json.dumps(obj, ensure_ascii=False)
            except Exception:
                text = str(obj)
            for m in var_pat.findall(text or ""):
                hits.add(m)
            return sorted(hits)[:50]

        results = []
        for cid in id_list:
            case = by_id.get(cid)
            if not case:
                results.append({"id": cid, "ok": False, "error": "用例不存在/非 API/已删除"})
                continue
            api_prof = get_api_profile_for_execute(case)
            if api_prof is None:
                results.append({"id": cid, "ok": False, "error": "API 用例扩展数据缺失"})
                continue
            try:
                data = preview_resolved_request(api_prof, overrides=overrides)
                req = (data or {}).get("request") or {}
                unresolved = _find_unresolved_vars(req)
                ok = not unresolved
                results.append(
                    {
                        "id": cid,
                        "case_name": case.case_name,
                        "ok": ok,
                        "request": req,
                        "unresolved_vars": unresolved,
                    }
                )
            except ValueError as exc:
                results.append({"id": cid, "case_name": case.case_name, "ok": False, "error": str(exc)})
            except Exception as exc:
                results.append({"id": cid, "case_name": case.case_name, "ok": False, "error": str(exc)})

        return Response({"success": True, "results": results})

    @action(detail=False, methods=["post"], url_path="ai-import-precheck")
    def ai_import_precheck(self, request):
        """
        AI 导入前批量预检（草稿 items，不要求已落库）：
        POST /api/testcase/cases/ai-import-precheck/

        body:
        - test_type: 必填（目前主要用于 api）
        - overrides: 可选（environment_id / variables 等）
        - items: [{ case_name, api_url, api_method, api_headers, api_body, ... }]

        返回：
        - results: [{ index, ok, unresolved_vars, request:{method,url,...}, error }]
        """
        if not isinstance(request.data, dict):
            return Response({"msg": "请求体必须为 JSON 对象"}, status=status.HTTP_400_BAD_REQUEST)
        test_type = (request.data.get("test_type") or "").strip()
        items = request.data.get("items")
        overrides = request.data.get("overrides") if isinstance(request.data.get("overrides"), dict) else {}
        if not isinstance(items, list) or not items:
            return Response({"success": True, "results": []})
        allowed = {c[0] for c in TEST_CASE_TYPE_CHOICES}
        if test_type and test_type not in allowed:
            return Response({"msg": "test_type 无效"}, status=status.HTTP_400_BAD_REQUEST)

        # 仅对 API 类型做静态预览（不发请求）
        if test_type and test_type != TestCase.TEST_TYPE_API:
            return Response({"success": True, "results": [{"index": i, "ok": True} for i in range(len(items))]})

        results = []
        for i, it in enumerate(items):
            row_name = ""
            if isinstance(it, dict):
                row_name = str(it.get("case_name") or "").strip()
            pr = precheck_api_draft_item(it if isinstance(it, dict) else {}, overrides)
            results.append(
                {
                    "index": i,
                    "case_name": row_name,
                    "ok": pr["ok"],
                    "error": pr.get("error") or "",
                    "unresolved_vars": pr.get("unresolved_vars") or [],
                    "request": pr.get("request") or {},
                }
            )
        return Response({"success": True, "results": results})

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
        qs = ExecutionLog.objects.filter(test_case=case, is_deleted=False).order_by(
            "-create_time"
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            ser = ExecutionLogSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(ser.data)
        ser = ExecutionLogSerializer(qs, many=True, context={"request": request})
        return Response({"results": ser.data, "count": qs.count()})

    @action(detail=True, methods=["post"], url_path="apply-ai-suggested-steps")
    def apply_ai_suggested_steps(self, request, pk=None):
        """
        将用户确认的「AI 修订建议步骤」写回用例（软删除旧步骤后按序新建）。
        POST /api/testcase/cases/<id>/apply-ai-suggested-steps/

        body:
        - execution_log_id: 必填，须为该用例下、未删除、**未通过**的 ExecutionLog
        - suggested_steps: 必填非空数组，每项 { step_desc, expected_result? }
        - confirm_replace_all: 必须为 true（防误触）
        """
        from assistant.services.case_fix_from_execution import can_user_access_execution_log

        case = self.get_object()
        if not isinstance(request.data, dict):
            return Response(
                {"success": False, "message": "请求体必须为 JSON 对象"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        body = request.data
        confirm = body.get("confirm_replace_all")
        if confirm is not True:
            return Response(
                {
                    "success": False,
                    "message": "须将 confirm_replace_all 设为布尔 true 以确认替换全部步骤",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            el_id = int(body.get("execution_log_id"))
        except (TypeError, ValueError):
            return Response(
                {"success": False, "message": "execution_log_id 必填且为整数"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_steps = body.get("suggested_steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            return Response(
                {"success": False, "message": "suggested_steps 必须为非空数组"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        log = (
            ExecutionLog.objects.select_related(
                "test_case__module__project", "test_case__creator"
            )
            .filter(pk=el_id, is_deleted=False)
            .first()
        )
        if not log or not log.test_case_id:
            return Response(
                {"success": False, "message": "执行日志不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if int(log.test_case_id) != int(case.id):
            return Response(
                {"success": False, "message": "该执行记录不属于当前用例"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not can_user_access_execution_log(request.user, log):
            return Response(
                {"success": False, "message": "无权限使用该执行记录"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if bool(log.is_passed):
            return Response(
                {
                    "success": False,
                    "message": "仅允许基于未通过的执行记录应用修订步骤",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        _max_steps = 60
        if len(raw_steps) > _max_steps:
            return Response(
                {
                    "success": False,
                    "message": f"suggested_steps 最多 {_max_steps} 条",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        normalized: list[tuple[str, str]] = []
        for it in raw_steps:
            if not isinstance(it, dict):
                continue
            desc = str(it.get("step_desc") or it.get("desc") or "").strip()
            exp = str(it.get("expected_result") or it.get("expected") or "").strip() or "—"
            if not desc:
                continue
            normalized.append(
                (
                    desc[:4000],
                    exp[:2000],
                )
            )
        if not normalized:
            return Response(
                {"success": False, "message": "suggested_steps 中无有效步骤（需含 step_desc）"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        with transaction.atomic():
            TestCaseStep.objects.filter(testcase=case, is_deleted=False).update(
                is_deleted=True
            )
            for idx, (desc, exp) in enumerate(normalized, start=1):
                TestCaseStep.objects.create(
                    testcase=case,
                    step_number=idx,
                    step_desc=desc,
                    expected_result=exp,
                    creator=user if getattr(user, "is_authenticated", False) else None,
                    updater=user if getattr(user, "is_authenticated", False) else None,
                )
            case.save(update_fields=["update_time"])

        return Response(
            {
                "success": True,
                "message": "已替换步骤",
                "test_case_id": case.id,
                "steps_count": len(normalized),
            }
        )

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
            ser = TestCaseVersionSerializer(
                page, many=True, context={"request": request}
            )
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
            return Response(
                {"msg": "version_id 必须为整数"}, status=status.HTTP_400_BAD_REQUEST
            )

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

    def get_queryset(self):
        """
        支持回收站模式：
        - GET /api/testcase/designs/?recycle=1
        """
        params = self.request.query_params
        recycle_mode = _recycle_mode_from_params(params)
        if recycle_mode:
            qs = TestDesign.objects.filter(is_deleted=True)
            user = getattr(self.request, "user", None)
            if (
                self.enable_data_scope
                and user
                and getattr(user, "is_authenticated", False)
                and not self._is_admin_user(user)
            ):
                qs = self._apply_member_scope(qs, user)
            return qs.order_by("-update_time", "-id")
        return super().get_queryset()

    def _parse_id_list(self, raw_ids):
        if raw_ids is None:
            return [], Response({"msg": "ids 必填"}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(raw_ids, list):
            return [], Response({"msg": "ids 必须为数组"}, status=status.HTTP_400_BAD_REQUEST)
        ids = []
        for x in raw_ids:
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                continue
        ids = [i for i in ids if i > 0]
        if not ids:
            return [], Response({"msg": "ids 不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        seen = set()
        uniq = []
        for i in ids:
            if i in seen:
                continue
            seen.add(i)
            uniq.append(i)
        return uniq, None

    @action(detail=False, methods=["post"], url_path="batch-delete")
    def batch_delete(self, request):
        """
        批量软删除测试设计（数据范围与列表一致）。
        POST /api/testcase/designs/batch-delete/
        body: { ids: number[] }
        """
        id_list, err = self._parse_id_list(request.data.get("ids") if isinstance(request.data, dict) else None)
        if err is not None:
            return err
        qs = self.get_queryset().filter(id__in=id_list, is_deleted=False)
        found = list(qs)
        found_ids = [int(o.id) for o in found]
        if not found_ids:
            return Response({"success": True, "deleted": 0, "skipped": len(id_list), "missing_ids": id_list})
        deleted = 0
        errors = []
        # 注意：单个删除失败会使当前事务进入 broken 状态，继续执行 SQL 会报
        # "You can't execute queries until the end of the atomic block"。
        # 因此这里按条目使用 savepoint 隔离，保证“部分成功”可用。
        for obj in found:
            try:
                with transaction.atomic():
                    self.perform_destroy(obj)
                deleted += 1
            except Exception as e:
                errors.append({"id": int(obj.id), "error": str(e)})
        missing = [i for i in id_list if i not in set(found_ids)]
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
        批量更新测试设计（对所有 ids 应用同一 patch）。
        POST /api/testcase/designs/batch-update/
        body: { ids: number[], patch: object }
        """
        if not isinstance(request.data, dict):
            return Response({"msg": "请求体必须为 JSON 对象"}, status=status.HTTP_400_BAD_REQUEST)
        id_list, err = self._parse_id_list(request.data.get("ids"))
        if err is not None:
            return err
        patch = request.data.get("patch")
        if not isinstance(patch, dict) or not patch:
            return Response({"msg": "patch 必须为非空对象"}, status=status.HTTP_400_BAD_REQUEST)

        allowed_keys = {"design_name", "req_count", "point_count", "case_count", "review_status", "archive_status"}
        cleaned = {k: v for (k, v) in patch.items() if k in allowed_keys}
        if not cleaned:
            return Response({"msg": "patch 未包含可更新字段"}, status=status.HTTP_400_BAD_REQUEST)

        qs = self.get_queryset().filter(id__in=id_list, is_deleted=False)
        found = list(qs)
        found_ids = {int(o.id) for o in found}
        missing = [i for i in id_list if i not in found_ids]

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

    @action(detail=False, methods=["get"], url_path="recycle")
    def recycle(self, request):
        """回收站列表：等价于 ?recycle=1。"""
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
        """回收站恢复：仅允许恢复 is_deleted=True 的记录。"""
        obj = get_object_or_404(TestDesign.objects.filter(is_deleted=True), pk=pk)
        obj.is_deleted = False
        obj.save(update_fields=["is_deleted", "update_time"])
        return Response({"success": True, "id": int(obj.id)})

    @action(detail=False, methods=["post"], url_path="bulk-soft-delete")
    def bulk_soft_delete(self, request):
        """批量软删除：body { ids: [] }。"""
        id_list, err = self._parse_id_list(
            request.data.get("ids") if isinstance(request.data, dict) else None
        )
        if err is not None:
            return err
        qs = self.get_queryset().filter(id__in=id_list, is_deleted=False)
        found_ids = list(qs.values_list("id", flat=True))
        if not found_ids:
            return Response(
                {
                    "success": True,
                    "deleted": 0,
                    "skipped": len(id_list),
                    "missing_ids": id_list,
                }
            )
        with transaction.atomic():
            updated = qs.update(is_deleted=True)
        missing = [i for i in id_list if i not in set(found_ids)]
        return Response(
            {
                "success": True,
                "deleted": int(updated),
                "skipped": len(missing),
                "missing_ids": missing,
            }
        )

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request):
        """回收站批量恢复：body { ids: [] }。"""
        id_list, err = self._parse_id_list(
            request.data.get("ids") if isinstance(request.data, dict) else None
        )
        if err is not None:
            return err
        qs = TestDesign.objects.filter(id__in=id_list, is_deleted=True)
        user = getattr(request, "user", None)
        if (
            self.enable_data_scope
            and user
            and getattr(user, "is_authenticated", False)
            and not self._is_admin_user(user)
        ):
            qs = self._apply_member_scope(qs, user)
        found_ids = list(qs.values_list("id", flat=True))
        if not found_ids:
            return Response(
                {
                    "success": True,
                    "restored": 0,
                    "skipped": len(id_list),
                    "missing_ids": id_list,
                }
            )
        with transaction.atomic():
            updated = qs.update(is_deleted=False)
        missing = [i for i in id_list if i not in set(found_ids)]
        return Response(
            {
                "success": True,
                "restored": int(updated),
                "skipped": len(missing),
                "missing_ids": missing,
            }
        )

    @action(detail=True, methods=["post"], url_path="hard-delete")
    def hard_delete(self, request, pk=None):
        """回收站彻底删除：仅允许删除 is_deleted=True 的记录。"""
        obj = get_object_or_404(TestDesign.objects.filter(is_deleted=True), pk=pk)
        user = getattr(request, "user", None)
        before = obj
        obj.delete()
        try:
            record_audit_event(
                action=AuditEvent.ACTION_DELETE,
                actor=user,
                instance=before,
                request=request,
                before=before,
                after=None,
            )
        except Exception:
            pass
        return Response({"success": True})

    @action(detail=False, methods=["post"], url_path="bulk-hard-delete")
    def bulk_hard_delete(self, request):
        """回收站批量彻底删除：body { ids: [] }，仅对 is_deleted=True 生效。"""
        id_list, err = self._parse_id_list(
            request.data.get("ids") if isinstance(request.data, dict) else None
        )
        if err is not None:
            return err
        user = getattr(request, "user", None)
        qs = TestDesign.objects.filter(id__in=id_list, is_deleted=True).order_by("id")
        if (
            self.enable_data_scope
            and user
            and getattr(user, "is_authenticated", False)
            and not self._is_admin_user(user)
        ):
            qs = self._apply_member_scope(qs, user)
        deleted = 0
        errors = []
        for obj in qs.iterator(chunk_size=200):
            try:
                before = obj
                obj.delete()
                deleted += 1
                try:
                    record_audit_event(
                        action=AuditEvent.ACTION_DELETE,
                        actor=user,
                        instance=before,
                        request=request,
                        before=before,
                        after=None,
                    )
                except Exception:
                    pass
            except Exception as e:
                errors.append({"id": int(getattr(obj, "id", 0) or 0), "error": str(e)})
        return Response({"success": len(errors) == 0, "count": deleted, "errors": errors})


class TestApproachViewSet(BaseModelViewSet):
    queryset = TestApproach.objects.all()
    serializer_class = TestApproachSerializer

    def get_queryset(self):
        """
        支持回收站模式：
        - GET /api/testcase/approaches/?recycle=1
        """
        params = self.request.query_params
        recycle_mode = _recycle_mode_from_params(params)
        if recycle_mode:
            qs = TestApproach.objects.filter(is_deleted=True)
            user = getattr(self.request, "user", None)
            if (
                self.enable_data_scope
                and user
                and getattr(user, "is_authenticated", False)
                and not self._is_admin_user(user)
            ):
                qs = self._apply_member_scope(qs, user)
            return qs.order_by("-update_time", "-id")
        return super().get_queryset()

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
        批量软删除测试方案（数据范围与列表一致）。
        POST /api/testcase/approaches/batch-delete/
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
            return Response({"success": True, "deleted": 0, "missing_ids": ids, "errors": []})
        deleted = 0
        errors = []
        for obj in found:
            try:
                with transaction.atomic():
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

    @action(detail=False, methods=["post"], url_path="batch-copy")
    def batch_copy(self, request):
        """
        批量复制测试方案（复制字段；重置封面图；不复制图片历史）。
        POST /api/testcase/approaches/batch-copy/
        body: { ids: number[], name_suffix?: string }
        """
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        suffix = str(request.data.get("name_suffix") or "（复制）").strip()[:32] or "（复制）"

        qs = self.get_queryset().filter(id__in=ids, is_deleted=False)
        found = list(qs)
        found_ids = {int(o.id) for o in found}
        missing = [i for i in ids if i not in found_ids]
        if not found:
            return Response(
                {"success": True, "created": 0, "created_ids": [], "missing_ids": ids, "errors": []}
            )

        user = request.user if getattr(request, "user", None) is not None else None
        created_ids = []
        errors = []
        with transaction.atomic():
            for src in found:
                try:
                    obj = TestApproach.objects.create(
                        scheme_name=(str(src.scheme_name or "")[:220] + suffix),
                        version=getattr(src, "version", ""),
                        cover_image=None,
                        test_goal=getattr(src, "test_goal", None),
                        test_category=getattr(src, "test_category", 1),
                        creator=user if (user and getattr(user, "is_authenticated", False)) else None,
                        updater=user if (user and getattr(user, "is_authenticated", False)) else None,
                    )
                    created_ids.append(int(obj.id))
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

    @action(methods=["get"], detail=True, url_path="images")
    def list_images(self, request, pk=None):
        approach = self.get_object()
        qs = approach.images.all().order_by("sort_order", "-create_time")
        serializer = TestApproachImageSerializer(
            qs, many=True, context={"request": request}
        )
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
            return Response(
                {"msg": "未接收到图片文件"}, status=status.HTTP_400_BAD_REQUEST
            )
        if len(files) > _MAX_UPLOAD_IMAGE_COUNT:
            return Response(
                {"msg": f"单次最多上传 {_MAX_UPLOAD_IMAGE_COUNT} 张图片"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for f in files:
            ext = (str(getattr(f, "name", "")).rsplit(".", 1)[-1] or "").lower()
            if ext not in _ALLOWED_IMAGE_EXTENSIONS:
                return Response(
                    {
                        "msg": f"仅支持图片格式：{', '.join(sorted(_ALLOWED_IMAGE_EXTENSIONS))}"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if int(getattr(f, "size", 0) or 0) > _MAX_UPLOAD_IMAGE_SIZE:
                return Response(
                    {"msg": "图片大小不能超过 5MB"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        last_order = approach.images.aggregate(m=Max("sort_order")).get("m") or 0

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
        return Response(
            {"results": serializer.data, "count": len(created)},
            status=status.HTTP_201_CREATED,
        )

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

        first = approach.images.all().order_by("sort_order", "-create_time").first()
        if first and first.image:
            approach.cover_image = first.image.url
        else:
            approach.cover_image = None
        approach.save(update_fields=["cover_image"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="recycle")
    def recycle(self, request):
        """回收站列表：等价于 ?recycle=1。"""
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
        """回收站恢复：仅允许恢复 is_deleted=True 的记录。"""
        obj = get_object_or_404(TestApproach.objects.filter(is_deleted=True), pk=pk)
        obj.is_deleted = False
        obj.save(update_fields=["is_deleted", "update_time"])
        return Response({"success": True, "id": int(obj.id)})

    @action(detail=False, methods=["post"], url_path="bulk-soft-delete")
    def bulk_soft_delete(self, request):
        """批量软删除：body { ids: [] }。"""
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
        return Response({"success": True, "deleted": int(updated), "skipped": len(missing), "missing_ids": missing})

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request):
        """回收站批量恢复：body { ids: [] }。"""
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        user = getattr(request, "user", None)
        qs = TestApproach.objects.filter(id__in=ids, is_deleted=True)
        if (
            self.enable_data_scope
            and user
            and getattr(user, "is_authenticated", False)
            and not self._is_admin_user(user)
        ):
            qs = self._apply_member_scope(qs, user)
        found_ids = list(qs.values_list("id", flat=True))
        if not found_ids:
            return Response({"success": True, "restored": 0, "skipped": len(ids), "missing_ids": ids})
        with transaction.atomic():
            updated = qs.update(is_deleted=False)
        missing = [i for i in ids if i not in set(found_ids)]
        return Response({"success": True, "restored": int(updated), "skipped": len(missing), "missing_ids": missing})

    @action(detail=True, methods=["post"], url_path="hard-delete")
    def hard_delete(self, request, pk=None):
        """回收站彻底删除：仅允许删除 is_deleted=True 的记录。"""
        try:
            obj = TestApproach.objects.get(pk=pk, is_deleted=True)
        except TestApproach.DoesNotExist:
            return Response({"success": False, "message": "记录不存在或未在回收站"}, status=404)
        user = getattr(request, "user", None)
        before = obj
        obj.delete()
        try:
            record_audit_event(
                action=AuditEvent.ACTION_DELETE,
                actor=user,
                instance=before,
                request=request,
                before=before,
                after=None,
            )
        except Exception:
            pass
        return Response({"success": True})

    @action(detail=False, methods=["post"], url_path="bulk-hard-delete")
    def bulk_hard_delete(self, request):
        """回收站批量彻底删除：body { ids: [] }，仅对 is_deleted=True 生效。"""
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        user = getattr(request, "user", None)
        qs = TestApproach.objects.filter(id__in=ids, is_deleted=True).order_by("id")
        if (
            self.enable_data_scope
            and user
            and getattr(user, "is_authenticated", False)
            and not self._is_admin_user(user)
        ):
            qs = self._apply_member_scope(qs, user)
        deleted = 0
        errors = []
        for obj in qs.iterator(chunk_size=200):
            try:
                before = obj
                obj.delete()
                deleted += 1
                try:
                    record_audit_event(
                        action=AuditEvent.ACTION_DELETE,
                        actor=user,
                        instance=before,
                        request=request,
                        before=before,
                        after=None,
                    )
                except Exception:
                    pass
            except Exception as e:
                errors.append({"id": int(getattr(obj, "id", 0) or 0), "error": str(e)})
        return Response({"success": len(errors) == 0, "count": deleted, "errors": errors})


def _user_can_write_module_cases(user, module) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff or getattr(user, "is_system_admin", False):
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
            base_url=request.data.get("base_url") or request.data.get("api_base_url"),
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
        content = request.data.get("content") or request.data.get("text") or ""
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
            return Response(
                {"msg": "无权在该模块下创建用例"}, status=status.HTTP_403_FORBIDDEN
            )
        if module.test_type != TEST_CASE_TYPE_API:
            return Response(
                {"msg": "目标模块的测试类型须为 API 测试"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items, err = ai_import_api_cases(
            str(source_type or ""),
            str(content),
            api_key=request.data.get("api_key"),
            base_url=request.data.get("base_url") or request.data.get("api_base_url"),
            model=request.data.get("model"),
        )
        if err:
            return Response({"msg": err}, status=status.HTTP_400_BAD_REQUEST)

        is_curl = str(source_type or "").strip().lower() == "curl"
        stored_curl = (str(content or "").strip()[:120_000]) if is_curl else ""

        user = request.user
        created_ids = []

        gated, errors = gate_ai_api_cases(items if isinstance(items, list) else [])
        for item in gated:
            api_payload = {
                "api_url": item["api_url"],
                "api_method": item["api_method"],
                "api_headers": item["api_headers"],
                "api_body": item["api_body"],
                "api_expected_status": item["api_expected_status"],
            }
            if stored_curl:
                api_payload["api_source_curl"] = stored_curl
            base = {
                "module": module,
                "case_name": item["case_name"],
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

        return Response(
            {"created": len(created_ids), "ids": created_ids, "errors": errors}
        )
