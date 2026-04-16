"""
测试模块 Repository
提供测试模块的数据访问方法
"""
from typing import Optional, List
from django.db.models import QuerySet
from common.repositories.base_repository import BaseRepository
from testcase.models import TestModule


class ModuleRepository(BaseRepository[TestModule]):
    """
    测试模块 Repository

    提供测试模块的数据访问方法

    Example:
        >>> repo = ModuleRepository()
        >>> module = repo.get_by_id(1)
        >>> modules = repo.get_by_project(project_id=1)
    """

    def __init__(self):
        """初始化 ModuleRepository"""
        super().__init__(TestModule)

    def get_by_project(self, project_id: int) -> QuerySet:
        """
        按项目查询模块

        Args:
            project_id: 项目 ID

        Returns:
            QuerySet 对象
        """
        return self.model.objects.filter(
            project_id=project_id,
            is_deleted=False
        ).select_related('creator', 'parent').order_by('sort_order', '-create_time')

    def get_root_modules(self, project_id: int) -> QuerySet:
        """
        获取根模块（没有父模块的模块）

        Args:
            project_id: 项目 ID

        Returns:
            QuerySet 对象
        """
        return self.model.objects.filter(
            project_id=project_id,
            parent__isnull=True,
            is_deleted=False
        ).select_related('creator').order_by('sort_order', '-create_time')

    def get_children(self, parent_id: int) -> QuerySet:
        """
        获取子模块

        Args:
            parent_id: 父模块 ID

        Returns:
            QuerySet 对象
        """
        return self.model.objects.filter(
            parent_id=parent_id,
            is_deleted=False
        ).select_related('creator').order_by('sort_order', '-create_time')

    def exists_by_name(
        self,
        project_id: int,
        module_name: str,
        parent_id: Optional[int] = None,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        检查模块名称是否存在（同一父模块下）

        Args:
            project_id: 项目 ID
            module_name: 模块名称
            parent_id: 父模块 ID
            exclude_id: 排除的模块 ID（用于更新时检查）

        Returns:
            是否存在
        """
        qs = self.model.objects.filter(
            project_id=project_id,
            module_name=module_name,
            parent_id=parent_id,
            is_deleted=False
        )

        if exclude_id:
            qs = qs.exclude(id=exclude_id)

        return qs.exists()
