"""
项目 Repository
提供项目的数据访问方法
"""
from typing import Optional, Dict, List
from django.db.models import QuerySet, Q
from common.repositories.base_repository import BaseRepository
from project.models import TestProject


class ProjectRepository(BaseRepository[TestProject]):
    """
    项目 Repository

    提供项目的数据访问方法，包括查询、创建、更新、删除等操作

    Example:
        >>> repo = ProjectRepository()
        >>> project = repo.get_by_id(1)
        >>> projects = repo.get_all()
    """

    def __init__(self):
        """初始化 ProjectRepository"""
        super().__init__(TestProject)

    def get_all(self, filters: Optional[Dict] = None) -> QuerySet:
        """
        获取所有项目

        Args:
            filters: 过滤条件，支持:
                - project_status: 项目状态
                - search: 搜索关键词（项目名称或描述）

        Returns:
            QuerySet 对象
        """
        qs = self.model.objects.filter(
            is_deleted=False
        ).select_related('creator', 'parent')

        if filters:
            # 按状态过滤
            if 'project_status' in filters and filters['project_status']:
                qs = qs.filter(project_status=filters['project_status'])

            # 搜索关键词
            if 'search' in filters and filters['search']:
                search = filters['search']
                qs = qs.filter(
                    Q(project_name__icontains=search) |
                    Q(description__icontains=search)
                )

        return qs.order_by('-create_time')

    def get_root_projects(self) -> QuerySet:
        """
        获取根项目（没有父项目的项目）

        Returns:
            QuerySet 对象
        """
        return self.model.objects.filter(
            parent__isnull=True,
            is_deleted=False
        ).select_related('creator').order_by('-create_time')

    def get_sub_projects(self, parent_id: int) -> QuerySet:
        """
        获取子项目

        Args:
            parent_id: 父项目 ID

        Returns:
            QuerySet 对象
        """
        return self.model.objects.filter(
            parent_id=parent_id,
            is_deleted=False
        ).select_related('creator', 'parent').order_by('-create_time')

    def exists_by_name(self, project_name: str, exclude_id: Optional[int] = None) -> bool:
        """
        检查项目名称是否存在

        Args:
            project_name: 项目名称
            exclude_id: 排除的项目 ID（用于更新时检查）

        Returns:
            是否存在
        """
        qs = self.model.objects.filter(
            project_name=project_name,
            is_deleted=False
        )

        if exclude_id:
            qs = qs.exclude(id=exclude_id)

        return qs.exists()

    def count_by_status(self, project_status: Optional[int] = None) -> int:
        """
        统计项目数

        Args:
            project_status: 项目状态（可选）

        Returns:
            项目数量
        """
        qs = self.model.objects.filter(is_deleted=False)

        if project_status:
            qs = qs.filter(project_status=project_status)

        return qs.count()

    def get_with_members(self, project_id: int) -> Optional[TestProject]:
        """
        获取项目及其成员

        Args:
            project_id: 项目 ID

        Returns:
            项目对象（包含成员），如果不存在返回 None
        """
        return self.model.objects.filter(
            id=project_id,
            is_deleted=False
        ).select_related('creator', 'parent').prefetch_related('members').first()
