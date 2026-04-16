
# Create your views here.
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from common.views import BaseModelViewSet
from common.services.audit import record_export_audit
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
