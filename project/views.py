from django.shortcuts import render

# Create your views here.
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.exceptions import ValidationError
from common.views import BaseModelViewSet
from project.models import TestProject, TestTask, ReleasePlan
from project.serialize import TestProjectSerializer, TestTaskSerializer, ReleasePlanSerializer

class TestProjectViewSet(BaseModelViewSet):
    """项目管理 API"""
    queryset = TestProject.objects.select_related("parent", "creator", "updater").prefetch_related(
        "members"
    )
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
                    raise ValidationError({"project": "您不是该项目成员，无权创建发布计划"})

        if user.is_authenticated:
            serializer.save(creator=user)
        else:
            serializer.save()