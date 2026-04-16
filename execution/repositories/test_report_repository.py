"""
TestReport Repository
"""
from typing import Optional
from django.db.models import QuerySet, Q
from common.repositories.base_repository import BaseRepository
from execution.models import TestReport


class TestReportRepository(BaseRepository[TestReport]):
    """测试报告 Repository"""

    def __init__(self):
        super().__init__(TestReport)

    def get_all(self, filters: Optional[dict] = None) -> QuerySet[TestReport]:
        """获取所有测试报告"""
        queryset = self.model.objects.filter(is_deleted=False).select_related(
            'plan', 'project', 'creator'
        )

        if not filters:
            return queryset

        if 'plan_id' in filters:
            queryset = queryset.filter(plan_id=filters['plan_id'])

        if 'project_id' in filters:
            queryset = queryset.filter(project_id=filters['project_id'])

        if 'create_method' in filters:
            queryset = queryset.filter(create_method=filters['create_method'])

        if 'search' in filters and filters['search']:
            search_term = filters['search']
            queryset = queryset.filter(
                Q(report_name__icontains=search_term) |
                Q(environment__icontains=search_term)
            )

        return queryset.order_by('-create_time')

    def get_by_plan(self, plan_id: int) -> QuerySet[TestReport]:
        """根据测试计划获取报告"""
        return self.model.objects.filter(
            plan_id=plan_id,
            is_deleted=False
        ).select_related('plan').order_by('-create_time')

    def get_by_project(self, project_id: int) -> QuerySet[TestReport]:
        """根据项目获取报告"""
        return self.model.objects.filter(
            project_id=project_id,
            is_deleted=False
        ).select_related('plan', 'project').order_by('-create_time')

    def get_by_trace_id(self, trace_id: str) -> Optional[TestReport]:
        """根据追踪ID获取报告"""
        return self.model.objects.filter(
            trace_id=trace_id,
            is_deleted=False
        ).first()

    def exists_by_name(self, report_name: str, exclude_id: Optional[int] = None) -> bool:
        """检查报告名称是否存在"""
        queryset = self.model.objects.filter(report_name=report_name, is_deleted=False)

        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)

        return queryset.exists()

    def count_by_plan(self, plan_id: int) -> int:
        """统计测试计划的报告数量"""
        return self.model.objects.filter(
            plan_id=plan_id,
            is_deleted=False
        ).count()
