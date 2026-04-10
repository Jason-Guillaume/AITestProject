from django.shortcuts import render

# Create your views here.
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from common.views import BaseModelViewSet
from project.models import TestProject, TestTask, ReleasePlan
from project.serialize import TestProjectSerializer, TestTaskSerializer, ReleasePlanSerializer

class TestProjectViewSet(BaseModelViewSet):
    """项目管理 API"""
    queryset = TestProject.objects.all()
    serializer_class = TestProjectSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

class TestTaskViewSet(BaseModelViewSet):
    """测试任务 API"""
    queryset = TestTask.objects.all()
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