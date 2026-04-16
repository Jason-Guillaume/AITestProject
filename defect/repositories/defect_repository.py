"""
缺陷 Repository
提供缺陷的数据访问方法
"""
from typing import Optional, Dict, List
from django.db.models import QuerySet, Q
from common.repositories.base_repository import BaseRepository
from defect.models import TestDefect


class DefectRepository(BaseRepository[TestDefect]):
    """
    缺陷 Repository

    提供缺陷的数据访问方法，包括查询、创建、更新、删除等操作

    Example:
        >>> repo = DefectRepository()
        >>> defect = repo.get_by_id(1)
        >>> defects = repo.get_all()
    """

    def __init__(self):
        """初始化 DefectRepository"""
        super().__init__(TestDefect)

    def get_all(self, filters: Optional[Dict] = None) -> QuerySet:
        """
        获取所有缺陷

        Args:
            filters: 过滤条件，支持:
                - status: 缺陷状态
                - severity: 严重程度
                - priority: 优先级
                - handler_id: 处理人 ID
                - module_id: 模块 ID
                - search: 搜索关键词（缺陷标题或内容）

        Returns:
            QuerySet 对象
        """
        qs = self.model.objects.filter(
            is_deleted=False
        ).select_related('creator', 'handler', 'module', 'release_version')

        if filters:
            # 按状态过滤
            if 'status' in filters and filters['status']:
                qs = qs.filter(status=filters['status'])

            # 按严重程度过滤
            if 'severity' in filters and filters['severity']:
                qs = qs.filter(severity=filters['severity'])

            # 按优先级过滤
            if 'priority' in filters and filters['priority']:
                qs = qs.filter(priority=filters['priority'])

            # 按处理人过滤
            if 'handler_id' in filters and filters['handler_id']:
                qs = qs.filter(handler_id=filters['handler_id'])

            # 按模块过滤
            if 'module_id' in filters and filters['module_id']:
                qs = qs.filter(module_id=filters['module_id'])

            # 搜索关键词
            if 'search' in filters and filters['search']:
                search = filters['search']
                qs = qs.filter(
                    Q(defect_name__icontains=search) |
                    Q(defect_content__icontains=search) |
                    Q(defect_no__icontains=search)
                )

        return qs.order_by('-create_time')

    def get_by_release(self, release_id: int) -> QuerySet:
        """
        获取版本下的缺陷

        Args:
            release_id: 版本 ID

        Returns:
            QuerySet 对象
        """
        return self.model.objects.filter(
            release_version_id=release_id,
            is_deleted=False
        ).select_related('creator', 'handler', 'module').order_by('-create_time')

    def get_by_handler(self, handler_id: int) -> QuerySet:
        """
        获取处理人的缺陷

        Args:
            handler_id: 处理人 ID

        Returns:
            QuerySet 对象
        """
        return self.model.objects.filter(
            handler_id=handler_id,
            is_deleted=False
        ).select_related('creator', 'handler', 'module', 'release_version').order_by('-create_time')

    def exists_by_no(self, defect_no: str, exclude_id: Optional[int] = None) -> bool:
        """
        检查缺陷编号是否存在

        Args:
            defect_no: 缺陷编号
            exclude_id: 排除的缺陷 ID（用于更新时检查）

        Returns:
            是否存在
        """
        qs = self.model.objects.filter(
            defect_no=defect_no,
            is_deleted=False
        )

        if exclude_id:
            qs = qs.exclude(id=exclude_id)

        return qs.exists()

    def count_by_status(self, status: Optional[int] = None) -> int:
        """
        统计缺陷数

        Args:
            status: 缺陷状态（可选）

        Returns:
            缺陷数量
        """
        qs = self.model.objects.filter(is_deleted=False)

        if status:
            qs = qs.filter(status=status)

        return qs.count()

    def count_by_severity(self, severity: int) -> int:
        """
        按严重程度统计缺陷数

        Args:
            severity: 严重程度

        Returns:
            缺陷数量
        """
        return self.model.objects.filter(
            severity=severity,
            is_deleted=False
        ).count()
