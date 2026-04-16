from django.db.models import Q
from rest_framework.pagination import PageNumberPagination

from common.views import *
from defect.models import *
from defect.serialize import *
from testcase.models import ExecutionLog
from execution.models import ApiScenarioRun, ApiScenarioStepRun
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from common.models import AuditEvent
from common.services.audit import record_audit_event


class DefectPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 500


class TestDefectViewSet(BaseModelViewSet):
    queryset = TestDefect.objects.all()
    serializer_class = TestDefectSerializer
    pagination_class = DefectPagination

    def get_queryset(self):
        p = self.request.query_params
        r = p.get("recycle")
        recycle_mode = r is not None and str(r).strip().lower() in ("1", "true", "yes")
        if not recycle_mode:
            d = p.get("is_deleted")
            recycle_mode = d is not None and str(d).strip().lower() in ("1", "true", "yes")

        if recycle_mode:
            qs = TestDefect.objects.filter(is_deleted=True)
            user = getattr(self.request, "user", None)
            if (
                self.enable_data_scope
                and user
                and getattr(user, "is_authenticated", False)
                and not self._is_admin_user(user)
            ):
                qs = self._apply_member_scope(qs, user)
        else:
            qs = super().get_queryset()

        qs = qs.select_related("release_version", "handler", "creator", "module")
        if p.get("severity"):
            try:
                severity = int(p["severity"])
            except (TypeError, ValueError):
                return qs.none()
            qs = qs.filter(severity=severity)
        if p.get("status"):
            try:
                defect_status = int(p["status"])
            except (TypeError, ValueError):
                return qs.none()
            qs = qs.filter(status=defect_status)
        if p.get("priority"):
            try:
                priority = int(p["priority"])
            except (TypeError, ValueError):
                return qs.none()
            qs = qs.filter(priority=priority)
        rv = p.get("release_version")
        if rv:
            try:
                release_version_id = int(rv)
            except (TypeError, ValueError):
                return qs.none()
            qs = qs.filter(release_version_id=release_version_id)
        q = p.get("search")
        if q:
            qs = qs.filter(Q(defect_no__icontains=q) | Q(defect_name__icontains=q))
        return qs.order_by("-create_time")

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
        if len(ids) > 500:
            raise ValidationError({"msg": "单次最多处理 500 条", "code": 400, "data": None})
        seen = set()
        uniq = []
        for i in ids:
            if i in seen:
                continue
            seen.add(i)
            uniq.append(i)
        return uniq

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
        obj = get_object_or_404(TestDefect.objects.filter(is_deleted=True), pk=pk)
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
        qs = TestDefect.objects.filter(id__in=ids, is_deleted=True)
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
        updated = qs.update(is_deleted=False)
        missing = [i for i in ids if i not in set(found_ids)]
        return Response({"success": True, "restored": int(updated), "skipped": len(missing), "missing_ids": missing})

    @action(detail=True, methods=["post"], url_path="hard-delete")
    def hard_delete(self, request, pk=None):
        """回收站彻底删除：仅允许删除 is_deleted=True 的记录。"""
        obj = get_object_or_404(TestDefect.objects.filter(is_deleted=True), pk=pk)
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
        qs = TestDefect.objects.filter(id__in=ids, is_deleted=True).order_by("id")
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

    def perform_create(self, serializer):
        from django.db import IntegrityError, transaction
        from rest_framework.exceptions import ValidationError

        user = self.request.user
        vd = serializer.validated_data

        defect_no = (vd.get("defect_no") or "").strip()

        handler = vd.get("handler")

        if handler is None:
            if user.is_authenticated:
                handler = user
            else:
                raise ValidationError({"handler": "创建缺陷必须指定处理人"})

        # 检测重复缺陷（同版本+模块+标题+严重程度）
        duplicate = (
            TestDefect.objects.filter(
                is_deleted=False,
                release_version=vd.get("release_version"),
                module=vd.get("module"),
                defect_name=vd.get("defect_name"),
                severity=vd.get("severity"),
            )
            .order_by("-id")
            .first()
        )
        if duplicate:
            raise ValidationError(
                {
                    "defect_name": "可能存在重复缺陷：已存在相同标题和严重程度的缺陷",
                    "duplicate_id": duplicate.id,
                }
            )

        # 并发安全的编号生成：事务锁 + 唯一约束冲突重试
        if not defect_no:
            for _ in range(5):
                try:
                    with transaction.atomic():
                        last = (
                            TestDefect.objects.select_for_update()
                            .order_by("-id")
                            .first()
                        )
                        next_id = 1 if not last else last.id + 1
                        defect_no = f"DEF-{next_id:05d}"
                        kwargs = {"defect_no": defect_no, "handler": handler}
                        if user.is_authenticated:
                            return serializer.save(creator=user, **kwargs)
                        return serializer.save(**kwargs)
                except IntegrityError:
                    defect_no = ""
            raise ValidationError({"defect_no": "缺陷编号生成冲突，请重试"})

        # 手工编号/外部传入时：验证唯一性（同时靠数据库约束兜底）
        if TestDefect.objects.filter(defect_no=defect_no, is_deleted=False).exists():
            raise ValidationError({"defect_no": "缺陷编号已存在"})

        kwargs = {"defect_no": defect_no, "handler": handler}
        if user.is_authenticated:
            serializer.save(creator=user, **kwargs)
        else:
            serializer.save(**kwargs)


class DefectFromExecutionAPIView(APIView):
    """
    从执行证据包快速创建缺陷（企业内网常用闭环入口）。

    POST /api/defect/defects/from-execution/
    body:
    - execution_log_id: int (可选)
    - scenario_run_id: int (可选)
    - defect_name: string (可选，缺省自动生成)
    - severity/priority: int (可选)
    - handler_id: int (可选，缺省为当前用户)
    """

    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        execution_log_id = payload.get("execution_log_id")
        scenario_run_id = payload.get("scenario_run_id")
        if execution_log_id in (None, "") and scenario_run_id in (None, ""):
            return Response(
                {"msg": "请提供 execution_log_id 或 scenario_run_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return Response({"msg": "认证失败"}, status=status.HTTP_401_UNAUTHORIZED)

        severity = payload.get("severity")
        priority = payload.get("priority")
        try:
            severity = int(severity) if severity not in (None, "") else 3
        except (TypeError, ValueError):
            severity = 3
        try:
            priority = int(priority) if priority not in (None, "") else 2
        except (TypeError, ValueError):
            priority = 2

        defect_name = (payload.get("defect_name") or "").strip()
        reproduction_steps = []
        attachments = []
        module = None
        environment = ""
        content_lines = []

        if execution_log_id not in (None, ""):
            try:
                eid = int(execution_log_id)
            except (TypeError, ValueError):
                return Response({"msg": "execution_log_id 非法"}, status=400)
            ex = (
                ExecutionLog.objects.filter(pk=eid)
                .select_related("test_case", "test_case__module")
                .first()
            )
            if not ex:
                return Response({"msg": "执行日志不存在"}, status=404)
            tc = ex.test_case
            module = getattr(tc, "module", None)
            defect_name = defect_name or f"接口用例失败: {tc.case_name}"
            environment = ""
            content_lines.append(f"trace_id: {ex.trace_id or ''}")
            content_lines.append(f"url: {ex.request_url}")
            content_lines.append(f"method: {ex.request_method}")
            content_lines.append(f"status: {ex.response_status_code}")
            if ex.error_message:
                content_lines.append(f"error: {ex.error_message}")
            reproduction_steps.append(
                {
                    "title": "请求与响应摘要",
                    "request": ex.request_payload or {},
                    "response": ex.response_payload or {},
                    "assertions": ex.assertion_results or [],
                }
            )
        else:
            try:
                rid = int(scenario_run_id)
            except (TypeError, ValueError):
                return Response({"msg": "scenario_run_id 非法"}, status=400)
            run = ApiScenarioRun.objects.filter(pk=rid).select_related("scenario").first()
            if not run:
                return Response({"msg": "场景运行不存在"}, status=404)
            defect_name = defect_name or f"场景失败: {run.scenario.name}"
            content_lines.append(f"scenario_trace_id: {run.trace_id}")
            content_lines.append(f"scenario_status: {run.status}")
            # 取失败步骤证据
            step_runs = list(
                ApiScenarioStepRun.objects.filter(run_id=run.id)
                .order_by("order", "id")
                .values("order", "test_case_id", "execution_log_id", "passed", "message")
            )
            for sr in step_runs:
                if sr.get("passed"):
                    continue
                ex_id = sr.get("execution_log_id")
                ex = ExecutionLog.objects.filter(pk=ex_id).first() if ex_id else None
                reproduction_steps.append(
                    {
                        "title": f"失败步骤(order={sr.get('order')})",
                        "step": sr,
                        "request": (ex.request_payload if ex else {}) if ex else {},
                        "response": (ex.response_payload if ex else {}) if ex else {},
                        "assertions": (ex.assertion_results if ex else []) if ex else [],
                    }
                )
            environment = ""

        defect = TestDefect.objects.create(
            defect_no="",
            defect_name=defect_name[:255],
            release_version=None,
            severity=severity,
            priority=priority,
            status=1,
            handler=user,
            module=module,
            defect_content="\n".join([x for x in content_lines if x])[:8000],
            reproduction_steps=reproduction_steps,
            attachments=attachments,
            environment=str(environment or "")[:255],
            creator=user,
            updater=user,
        )
        record_audit_event(
            action=AuditEvent.ACTION_CREATE,
            actor=user,
            instance=defect,
            request=request,
            extra={
                "source": "from_execution",
                "execution_log_id": int(execution_log_id) if execution_log_id not in (None, "") else None,
                "scenario_run_id": int(scenario_run_id) if scenario_run_id not in (None, "") else None,
            },
        )
        return Response({"success": True, "id": defect.id})


class DefectFromSecurityFindingAPIView(APIView):
    """
    从安全 finding 快速创建缺陷（用于 AI 安全分析闭环）。

    POST /api/defect/defects/from-security-finding/
    body:
    - finding: object（必填，包含 rule_id/title/description/suggested_request 等）
    - module_id: int（可选）
    - release_version_id: int（可选）
    - severity/priority: int（可选）
    - handler_id: int（可选，缺省为当前用户）
    - environment: string（可选）
    """

    def post(self, request):
        import json as _json

        from project.models import ReleasePlan
        from testcase.models import TestModule
        from user.models import User

        payload = request.data if isinstance(request.data, dict) else {}
        finding = payload.get("finding")
        if not isinstance(finding, dict):
            return Response({"msg": "finding 必填且为对象"}, status=status.HTTP_400_BAD_REQUEST)

        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return Response({"msg": "认证失败"}, status=status.HTTP_401_UNAUTHORIZED)

        title = str(finding.get("title") or "").strip()
        rule_id = str(finding.get("rule_id") or "").strip()
        desc = str(finding.get("description") or "").strip()
        suggested = finding.get("suggested_request") if isinstance(finding.get("suggested_request"), dict) else {}

        defect_name = (payload.get("defect_name") or "").strip() or f"[安全] {rule_id} {title}".strip()

        severity = payload.get("severity")
        priority = payload.get("priority")
        try:
            severity = int(severity) if severity not in (None, "") else 2
        except (TypeError, ValueError):
            severity = 2
        try:
            priority = int(priority) if priority not in (None, "") else 1
        except (TypeError, ValueError):
            priority = 1

        handler_id = payload.get("handler_id")
        handler = None
        if handler_id not in (None, ""):
            try:
                hid = int(handler_id)
            except (TypeError, ValueError):
                return Response({"msg": "handler_id 非法"}, status=400)
            handler = User.objects.filter(pk=hid, is_deleted=False).first()
            if not handler:
                return Response({"msg": "handler 不存在"}, status=404)
        else:
            handler = user

        module_id = payload.get("module_id")
        module = None
        if module_id not in (None, ""):
            try:
                mid = int(module_id)
            except (TypeError, ValueError):
                return Response({"msg": "module_id 非法"}, status=400)
            module = TestModule.objects.filter(pk=mid, is_deleted=False).first()

        rv_id = payload.get("release_version_id")
        release_version = None
        if rv_id not in (None, ""):
            try:
                rid = int(rv_id)
            except (TypeError, ValueError):
                return Response({"msg": "release_version_id 非法"}, status=400)
            release_version = ReleasePlan.objects.filter(pk=rid, is_deleted=False).first()

        environment = str(payload.get("environment") or "").strip()[:255]

        content_lines = []
        if title:
            content_lines.append(f"title: {title}")
        if rule_id:
            content_lines.append(f"rule_id: {rule_id}")
        if desc:
            content_lines.append(desc)
        if suggested:
            content_lines.append("")
            content_lines.append("suggested_request:")
            content_lines.append(_json.dumps(suggested, ensure_ascii=False)[:4000])
        defect_content = "\n".join(content_lines)[:10000]

        reproduction_steps = [{"title": "安全 Finding", "finding": finding}]

        defect = TestDefect.objects.create(
            defect_no="",
            defect_name=defect_name[:255],
            release_version=release_version,
            severity=severity,
            priority=priority,
            status=1,
            handler=handler,
            module=module,
            defect_content=defect_content,
            reproduction_steps=reproduction_steps,
            attachments=[],
            environment=environment,
            creator=user,
            updater=user,
        )
        if not defect.defect_no:
            for _ in range(5):
                last = TestDefect.objects.filter(is_deleted=False).order_by("-id").first()
                next_id = 1 if not last else last.id + 1
                no = f"DEF-{next_id:05d}"
                if not TestDefect.objects.filter(defect_no=no, is_deleted=False).exists():
                    defect.defect_no = no
                    defect.save(update_fields=["defect_no", "update_time"])
                    break

        record_audit_event(
            action=AuditEvent.ACTION_CREATE,
            actor=user,
            instance=defect,
            request=request,
            extra={"source": "security_finding", "rule_id": rule_id, "finding": finding},
        )
        return Response({"success": True, "id": defect.id, "defect_no": defect.defect_no, "defect_name": defect.defect_name})

    def perform_update(self, serializer):
        from rest_framework.exceptions import ValidationError

        instance = serializer.instance
        old_status = instance.status
        new_status = serializer.validated_data.get("status", old_status)

        # 状态流转验证：只有处理人可以关闭；且仅允许“处理中” -> “已关闭”
        if new_status == 4:
            if old_status != 2:
                raise ValidationError({"status": "已关闭只能从“处理中”状态流转"})
            if getattr(self.request.user, "pk", None) != instance.handler_id:
                raise ValidationError({"status": "只有处理人可以将缺陷标记为已关闭"})

        user = self.request.user
        if user and user.is_authenticated:
            serializer.save(updater=user)
        else:
            serializer.save()
