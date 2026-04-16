"""
测试用例 Repository
提供测试用例的数据访问方法
"""
from typing import Optional, Dict, List
from django.db.models import QuerySet, Q
from common.repositories.base_repository import BaseRepository
from testcase.models import TestCase


class TestCaseRepository(BaseRepository[TestCase]):
    """
    测试用例 Repository

    提供测试用例的数据访问方法，包括查询、创建、更新、删除等操作

    Example:
        >>> repo = TestCaseRepository()
        >>> testcase = repo.get_by_id(1)
        >>> testcases = repo.get_by_project(project_id=1)
    """

    def __init__(self):
        """初始化 TestCaseRepository"""
        super().__init__(TestCase)

    def get_by_project(
        self,
        project_id: int,
        filters: Optional[Dict] = None
    ) -> QuerySet:
        """
        按项目查询用例

        Args:
            project_id: 项目 ID
            filters: 过滤条件，支持:
                - test_type: 测试类型
                - module_id: 模块 ID
                - search: 搜索关键词（用例名称）

        Returns:
            QuerySet 对象
        """
        qs = self.model.objects.filter(
            module__project_id=project_id,
            is_deleted=False
        ).select_related('creator', 'module', 'module__project')

        if filters:
            # 按测试类型过滤
            if 'test_type' in filters and filters['test_type']:
                qs = qs.filter(test_type=filters['test_type'])

            # 按模块过滤
            if 'module_id' in filters and filters['module_id']:
                qs = qs.filter(module_id=filters['module_id'])

            # 搜索关键词
            if 'search' in filters and filters['search']:
                search = filters['search']
                qs = qs.filter(Q(case_name__icontains=search))

        return qs.order_by('-create_time')

    def get_by_module(self, module_id: int) -> QuerySet:
        """
        按模块查询用例

        Args:
            module_id: 模块 ID

        Returns:
            QuerySet 对象
        """
        return self.model.objects.filter(
            module_id=module_id,
            is_deleted=False
        ).select_related('creator', 'module').order_by('-create_time')

    def count_by_project(self, project_id: int, test_type: Optional[str] = None) -> int:
        """
        统计项目用例数

        Args:
            project_id: 项目 ID
            test_type: 测试类型（可选）

        Returns:
            用例数量
        """
        qs = self.model.objects.filter(
            module__project_id=project_id,
            is_deleted=False
        )

        if test_type:
            qs = qs.filter(test_type=test_type)

        return qs.count()

    def count_by_module(self, module_id: int) -> int:
        """
        统计模块用例数

        Args:
            module_id: 模块 ID

        Returns:
            用例数量
        """
        return self.model.objects.filter(
            module_id=module_id,
            is_deleted=False
        ).count()

    def get_with_steps(self, testcase_id: int) -> Optional[TestCase]:
        """
        获取用例及其步骤

        Args:
            testcase_id: 用例 ID

        Returns:
            用例对象（包含步骤），如果不存在返回 None
        """
        from django.db.models import Prefetch
        from testcase.models import TestCaseStep

        return self.model.objects.filter(
            id=testcase_id,
            is_deleted=False
        ).select_related('creator', 'module').prefetch_related(
            Prefetch(
                'steps',
                queryset=TestCaseStep.objects.order_by('step_number')
            )
        ).first()

    def exists_by_name(self, project_id: int, case_name: str, exclude_id: Optional[int] = None) -> bool:
        """
        检查用例名称是否存在

        Args:
            project_id: 项目 ID
            case_name: 用例名称
            exclude_id: 排除的用例 ID（用于更新时检查）

        Returns:
            是否存在
        """
        qs = self.model.objects.filter(
            module__project_id=project_id,
            case_name=case_name,
            is_deleted=False
        )

        if exclude_id:
            qs = qs.exclude(id=exclude_id)

        return qs.exists()
