
# Create your views here.
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from common.views import BaseModelViewSet
from common.services.audit import record_export_audit
from common.models import AuditEvent
from common.services.audit import record_audit_event
from project.models import TestProject, TestTask, ReleasePlan
from project.serialize import (
    TestProjectSerializer,
    TestTaskSerializer,
    ReleasePlanSerializer,
)
from project.services.release_risk_brief import build_release_risk_brief


class TestProjectViewSet(BaseModelViewSet):
    """项目管理 API"""

    queryset = TestProject.objects.select_related(
        "parent", "creator", "updater"
    ).prefetch_related("members")
    serializer_class = TestProjectSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @action(detail=False, methods=["get"], url_path="recycle")
    def recycle(self, request):
        """
        回收站列表：仅返回 is_deleted=True 的项目。
        支持 ?q= 关键词搜索（project_name/description/parent_name）。
        """
        qs = self.queryset.filter(is_deleted=True)
        q = (request.query_params.get("q") or "").strip()
        if q:
            from django.db.models import Q

            qs = qs.filter(
                Q(project_name__icontains=q)
                | Q(description__icontains=q)
                | Q(parent__project_name__icontains=q)
            )

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        """
        恢复软删除项目：is_deleted=True -> False
        """
        try:
            obj = self.queryset.get(pk=pk, is_deleted=True)
        except TestProject.DoesNotExist:
            return Response({"success": False, "message": "项目不存在或未在回收站"}, status=404)
        user = getattr(request, "user", None)
        obj.is_deleted = False
        if user and getattr(user, "is_authenticated", False):
            obj.updater = user
        obj.save(update_fields=["is_deleted", "updater", "update_time"])
        return Response({"success": True})

    @action(detail=True, methods=["post"], url_path="hard-delete")
    def hard_delete(self, request, pk=None):
        """
        回收站彻底删除（真实删除记录）。
        仅允许删除 is_deleted=True 的项目，避免误删在线项目。
        """
        try:
            obj = self.queryset.get(pk=pk, is_deleted=True)
        except TestProject.DoesNotExist:
            return Response({"success": False, "message": "项目不存在或未在回收站"}, status=404)
        user = getattr(request, "user", None)
        before = obj
        obj.delete()
        record_audit_event(
            action=AuditEvent.ACTION_DELETE,
            actor=user,
            instance=before,
            request=request,
            before=before,
            after=None,
        )
        return Response({"success": True})

    @action(detail=False, methods=["post"], url_path="bulk-soft-delete")
    def bulk_soft_delete(self, request):
        """
        批量软删除：body { ids: [] }
        """
        ids = request.data.get("ids") or []
        if not isinstance(ids, list) or not ids:
            raise ValidationError({"ids": "请提供 ids 列表"})
        ids = [int(x) for x in ids if str(x).strip().isdigit()]
        if not ids:
            raise ValidationError({"ids": "ids 参数不合法"})
        user = getattr(request, "user", None)
        qs = self.get_queryset().filter(id__in=ids, is_deleted=False)
        update_fields = {"is_deleted": True}
        if user and getattr(user, "is_authenticated", False):
            update_fields["updater"] = user
        qs.update(**update_fields)
        return Response({"success": True, "count": qs.count()})

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request):
        """
        批量恢复：body { ids: [] }
        """
        ids = request.data.get("ids") or []
        if not isinstance(ids, list) or not ids:
            raise ValidationError({"ids": "请提供 ids 列表"})
        ids = [int(x) for x in ids if str(x).strip().isdigit()]
        if not ids:
            raise ValidationError({"ids": "ids 参数不合法"})
        user = getattr(request, "user", None)
        qs = self.queryset.filter(id__in=ids, is_deleted=True)
        update_fields = {"is_deleted": False}
        if user and getattr(user, "is_authenticated", False):
            update_fields["updater"] = user
        qs.update(**update_fields)
        return Response({"success": True, "count": qs.count()})

    @action(detail=False, methods=["post"], url_path="bulk-hard-delete")
    def bulk_hard_delete(self, request):
        """
        回收站批量彻底删除：body { ids: [] }
        仅对 is_deleted=True 的项目生效。
        """
        ids = request.data.get("ids") or []
        if not isinstance(ids, list) or not ids:
            raise ValidationError({"ids": "请提供 ids 列表"})
        ids = [int(x) for x in ids if str(x).strip().isdigit()]
        if not ids:
            raise ValidationError({"ids": "ids 参数不合法"})
        user = getattr(request, "user", None)
        qs = self.queryset.filter(id__in=ids, is_deleted=True).order_by("id")
        deleted = 0
        # 用逐条 delete 保证级联/信号行为一致
        for obj in qs.iterator(chunk_size=200):
            before = obj
            obj.delete()
            deleted += 1
            record_audit_event(
                action=AuditEvent.ACTION_DELETE,
                actor=user,
                instance=before,
                request=request,
                before=before,
                after=None,
            )
        return Response({"success": True, "count": deleted})

    @action(detail=False, methods=["post"], url_path="bulk-status")
    def bulk_status(self, request):
        """
        批量改状态：body { ids: [], project_status: 1|2 }
        默认保留 progress；若设为已完成则强制 progress=100。
        """
        ids = request.data.get("ids") or []
        status = request.data.get("project_status")
        if not isinstance(ids, list) or not ids:
            raise ValidationError({"ids": "请提供 ids 列表"})
        try:
            st = int(status)
        except (TypeError, ValueError):
            raise ValidationError({"project_status": "project_status 参数不合法"})
        if st not in (TestProject.STATUS_IN_PROGRESS, TestProject.STATUS_COMPLETED):
            raise ValidationError({"project_status": "project_status 参数不合法"})

        ids = [int(x) for x in ids if str(x).strip().isdigit()]
        if not ids:
            raise ValidationError({"ids": "ids 参数不合法"})

        user = getattr(request, "user", None)
        qs = self.get_queryset().filter(id__in=ids, is_deleted=False)
        update_fields = {"project_status": st}
        if st == TestProject.STATUS_COMPLETED:
            update_fields["progress"] = 100
        if user and getattr(user, "is_authenticated", False):
            update_fields["updater"] = user
        qs.update(**update_fields)
        return Response({"success": True, "count": qs.count()})

    @action(detail=False, methods=["get"], url_path="export.csv")
    def export_csv(self, request):
        """
        导出项目 CSV：\n
        - mode=filtered|selected (默认 filtered)\n
        - q= (filtered)\n
        - ids=1,2,3 (selected)\n
        - include_deleted=0|1 (默认 0)\n
        """
        from django.http import StreamingHttpResponse
        from django.db.models import Q

        mode = (request.query_params.get("mode") or "filtered").strip()
        include_deleted = (request.query_params.get("include_deleted") or "0").strip() in ("1", "true", "True")
        q = (request.query_params.get("q") or "").strip()
        ids_raw = (request.query_params.get("ids") or "").strip()

        if mode == "selected":
            ids = []
            for part in ids_raw.split(","):
                part = part.strip()
                if part.isdigit():
                    ids.append(int(part))
            if not ids:
                raise ValidationError({"ids": "selected 模式下必须提供 ids"})
            qs = self.queryset.filter(id__in=ids)
            if not include_deleted:
                qs = qs.filter(is_deleted=False)
        else:
            qs = self.queryset
            qs = qs.filter(is_deleted=False) if not include_deleted else qs
            if q:
                qs = qs.filter(
                    Q(project_name__icontains=q)
                    | Q(description__icontains=q)
                    | Q(parent__project_name__icontains=q)
                )

        qs = qs.select_related("parent", "creator", "updater").order_by("-update_time", "-id")

        columns = [
            "id",
            "project_name",
            "project_status_display",
            "progress",
            "parent_name",
            "creator_name",
            "create_time",
            "update_time",
            "is_deleted",
        ]

        def _csv_escape(v):
            s = "" if v is None else str(v)
            s = s.replace("\r", " ").replace("\n", " ")
            if '"' in s:
                s = s.replace('"', '""')
            if any(ch in s for ch in [",", '"']):
                return f'"{s}"'
            return s

        def stream():
            yield ",".join(columns) + "\n"
            for o in qs.iterator(chunk_size=500):
                row = [
                    int(o.id),
                    o.project_name or "",
                    o.get_project_status_display(),
                    int(o.progress or 0),
                    o.parent.project_name if o.parent_id and o.parent else "",
                    getattr(o.creator, "real_name", "") if getattr(o, "creator_id", None) else "",
                    (str(o.create_time).replace("T", " ")[:19] if getattr(o, "create_time", None) else ""),
                    (str(o.update_time).replace("T", " ")[:19] if getattr(o, "update_time", None) else ""),
                    "1" if getattr(o, "is_deleted", False) else "0",
                ]
                yield ",".join(_csv_escape(x) for x in row) + "\n"

        resp = StreamingHttpResponse(stream(), content_type="text/csv; charset=utf-8")
        resp["Cache-Control"] = "no-store"
        resp["Content-Disposition"] = 'attachment; filename="projects.csv"'
        record_export_audit(
            actor=request.user,
            instance=None,
            request=request,
            extra={
                "mode": mode,
                "include_deleted": bool(include_deleted),
                "q": q,
                "ids_count": len(ids_raw.split(",")) if ids_raw else 0,
            },
        )
        return resp


class TestTaskViewSet(BaseModelViewSet):
    """测试任务 API"""

    queryset = TestTask.objects.select_related("assignee", "creator", "updater").all()
    serializer_class = TestTaskSerializer


class ReleasePlanViewSet(BaseModelViewSet):
    """发布计划 API（可按 ?project=<id> 筛选所属项目）"""

    queryset = ReleasePlan.objects.select_related("project", "creator", "updater").all()
    serializer_class = ReleasePlanSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get("project")
        if project_id:
            try:
                pid = int(project_id)
            except (TypeError, ValueError):
                return qs.none()
            qs = qs.filter(project_id=pid)
        return qs

    def perform_create(self, serializer):
        """
        创建发布计划时校验：非管理员必须是该项目成员。
        """
        user = self.request.user
        project_id = self.request.data.get("project")
        if project_id:
            try:
                pid = int(project_id)
            except (TypeError, ValueError):
                raise ValidationError({"project": "项目参数不合法"})
            try:
                project = TestProject.objects.get(pk=pid, is_deleted=False)
            except TestProject.DoesNotExist:
                raise ValidationError({"project": "项目不存在"})

            if user.is_authenticated and not self._is_admin_user(user):
                if not project.members.filter(pk=user.pk, is_deleted=False).exists():
                    raise ValidationError(
                        {"project": "您不是该项目成员，无权创建发布计划"}
                    )

        if user.is_authenticated:
            serializer.save(creator=user)
        else:
            serializer.save()

    @action(detail=True, methods=["get"], url_path="risk-brief")
    def risk_brief(self, request, pk=None):
        """
        发布计划只读风险简报（ORM 聚合，无大模型）：
        GET /api/project/releases/<id>/risk-brief/?days=7
        """
        release = self.get_object()
        try:
            days = int(request.query_params.get("days", "7"))
        except (TypeError, ValueError):
            days = 7
        data = build_release_risk_brief(release, execution_days=days)
        return Response(data)

    @action(detail=True, methods=["get"], url_path="never-executed-cases")
    def never_executed_cases(self, request, pk=None):
        """
        发布计划“窗口内从未执行用例”清单（只读）。
        GET /api/project/releases/<id>/never-executed-cases/?days=7&limit=500
        """
        release = self.get_object()
        try:
            days = int(request.query_params.get("days", "7"))
        except (TypeError, ValueError):
            days = 7
        try:
            limit = int(request.query_params.get("limit", "500"))
        except (TypeError, ValueError):
            limit = 500
        limit = max(1, min(limit, 5000))

        data = build_release_risk_brief(release, execution_days=days)
        ids = data.get("never_executed_case_ids") or []
        if not isinstance(ids, list):
            ids = []

        from testcase.models import TestCase

        qs = (
            TestCase.objects.filter(is_deleted=False, id__in=ids)
            .select_related("module")
            .only("id", "case_name", "test_type", "module_id", "module__name")
        )
        rows = []
        id_to_obj = {int(o.id): o for o in qs}
        for cid in ids[:limit]:
            o = id_to_obj.get(int(cid))
            if not o:
                continue
            mod = getattr(o, "module", None)
            rows.append(
                {
                    "id": int(o.id),
                    "case_name": o.case_name,
                    "test_type": o.test_type,
                    "module_id": getattr(o, "module_id", None),
                    "module_name": getattr(mod, "name", "") if mod else "",
                }
            )
        return Response({"success": True, "days": days, "total": len(ids), "items": rows})

    @action(detail=True, methods=["get"], url_path="never-executed-cases/export.csv")
    def export_never_executed_cases_csv(self, request, pk=None):
        """
        导出窗口内从未执行用例 CSV：
        GET /api/project/releases/<id>/never-executed-cases/export.csv?days=7&limit=20000
        """
        from django.http import StreamingHttpResponse

        release = self.get_object()
        try:
            days = int(request.query_params.get("days", "7"))
        except (TypeError, ValueError):
            days = 7
        try:
            limit = int(request.query_params.get("limit", "20000"))
        except (TypeError, ValueError):
            limit = 20000
        limit = max(1, min(limit, 200000))

        data = build_release_risk_brief(release, execution_days=days)
        ids = data.get("never_executed_case_ids") or []
        if not isinstance(ids, list):
            ids = []
        ids = ids[:limit]

        from testcase.models import TestCase

        qs = (
            TestCase.objects.filter(is_deleted=False, id__in=ids)
            .select_related("module")
            .only("id", "case_name", "test_type", "module_id", "module__name")
        )
        id_to_obj = {int(o.id): o for o in qs}

        columns = ["id", "case_name", "test_type", "module_id", "module_name"]

        def _csv_escape(v):
            s = "" if v is None else str(v)
            s = s.replace("\r", " ").replace("\n", " ")
            if '"' in s:
                s = s.replace('"', '""')
            if any(ch in s for ch in [",", '"']):
                return f'"{s}"'
            return s

        def stream():
            yield ",".join(columns) + "\n"
            for cid in ids:
                o = id_to_obj.get(int(cid))
                if not o:
                    continue
                mod = getattr(o, "module", None)
                row = [
                    int(o.id),
                    o.case_name or "",
                    o.test_type or "",
                    getattr(o, "module_id", None),
                    getattr(mod, "name", "") if mod else "",
                ]
                yield ",".join(_csv_escape(x) for x in row) + "\n"

        resp = StreamingHttpResponse(stream(), content_type="text/csv; charset=utf-8")
        filename = f"release-{release.id}-never-executed-{days}d.csv"
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        resp["Cache-Control"] = "no-store"
        record_export_audit(
            actor=request.user,
            instance=release,
            request=request,
            extra={"release_id": int(release.id), "days": int(days), "rows": int(len(ids))},
        )
        return resp
