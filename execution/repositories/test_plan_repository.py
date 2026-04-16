"""
TestPlan Repository
"""
from typing import Optional
from django.db.models import QuerySet, Q
from common.repositories.base_repository import BaseRepository
from execution.models import TestPlan


class TestPlanRepository(BaseRepository[TestPlan]):
    """测试计划 Repository"""

    def __init__(self):
        super().__init__(TestPlan)

    def get_all(self, filters: Optional[dict] = None) -> QuerySet[TestPlan]:
        """获取所有测试计划"""
        queryset = self.model.objects.filter(is_deleted=False).select_related(
            'version', 'creator'
        ).prefetch_related('testers')

        if not filters:
            return queryset

        if 'plan_status' in filters:
            queryset = queryset.filter(plan_status=filters['plan_status'])

        if 'version_id' in filters:
            queryset = queryset.filter(version_id=filters['version_id'])

        if 'search' in filters and filters['search']:
            search_term = filters['search']
            queryset = queryset.filter(
                Q(plan_name__icontains=search_term) |
                Q(iteration__icontains=search_term) |
                Q(environment__icontains=search_term)
            )

        return queryset.order_by('-create_time')

    def get_by_version(self, version_id: int) -> QuerySet[TestPlan]:
        """根据版本获取测试计划"""
        return self.model.objects.filter(
            version_id=version_id,
            is_deleted=False
        ).select_related('version').order_by('-create_time')

    def get_by_status(self, plan_status: int) -> QuerySet[TestPlan]:
        """根据状态获取测试计划"""
        return self.model.objects.filter(
            plan_status=plan_status,
            is_deleted=False
        ).select_related('version').order_by('-create_time')

    def exists_by_name(self, plan_name: str, exclude_id: Optional[int] = None) -> bool:
        """检查计划名称是否存在"""
        queryset = self.model.objects.filter(plan_name=plan_name, is_deleted=False)

        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)

        return queryset.exists()

    def count_by_status(self, plan_status: Optional[int] = None) -> int:
        """统计测试计划数量"""
        queryset = self.model.objects.filter(is_deleted=False)

        if plan_status is not None:
            queryset = queryset.filter(plan_status=plan_status)

        return queryset.count()
