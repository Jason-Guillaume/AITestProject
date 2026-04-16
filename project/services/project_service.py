"""
项目 Service
提供项目的业务逻辑
"""
from typing import List, Dict, Optional
from django.db import transaction
from common.services.base_service import BaseService
from common.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    DuplicateException
)
from project.repositories.project_repository import ProjectRepository
from project.models import TestProject


class ProjectService(BaseService[TestProject]):
    """
    项目 Service

    提供项目的业务逻辑，包括创建、更新、删除、查询等操作

    Example:
        >>> service = ProjectService()
        >>> project = service.create_project(data, user)
        >>> projects = service.get_all()
    """

    def __init__(self):
        """初始化 ProjectService"""
        super().__init__(ProjectRepository())

    def get_all(self, filters: Optional[Dict] = None) -> List[TestProject]:
        """
        获取所有项目

        Args:
            filters: 过滤条件

        Returns:
            项目列表
        """
        return list(self.repository.get_all(filters))

    def get_root_projects(self) -> List[TestProject]:
        """
        获取根项目

        Returns:
            根项目列表
        """
        return list(self.repository.get_root_projects())

    def get_sub_projects(self, parent_id: int) -> List[TestProject]:
        """
        获取子项目

        Args:
            parent_id: 父项目 ID

        Returns:
            子项目列表
        """
        return list(self.repository.get_sub_projects(parent_id))

    def get_with_members(self, project_id: int) -> Optional[TestProject]:
        """
        获取项目及其成员

        Args:
            project_id: 项目 ID

        Returns:
            项目对象（包含成员）

        Raises:
            ResourceNotFoundException: 项目不存在
        """
        project = self.repository.get_with_members(project_id)
        if not project:
            raise ResourceNotFoundException("项目不存在")
        return project

    @transaction.atomic
    def create_project(self, data: Dict, user) -> TestProject:
        """
        创建项目

        Args:
            data: 项目数据
            user: 当前用户

        Returns:
            创建的项目对象

        Raises:
            ValidationException: 数据验证失败
            ResourceNotFoundException: 父项目不存在
            DuplicateException: 项目名称重复
        """
        # 验证必填字段
        if not data.get('project_name'):
            raise ValidationException("项目名称不能为空")

        # 验证父项目是否存在
        if 'parent_id' in data and data['parent_id']:
            parent = self.repository.get_by_id(data['parent_id'])
            if not parent:
                raise ResourceNotFoundException("父项目不存在")

        # 检查项目名称是否重复
        if self.repository.exists_by_name(data['project_name']):
            raise DuplicateException(f"项目名称 '{data['project_name']}' 已存在")

        # 创建项目
        project = self.repository.create(data, creator=user)

        return project

    @transaction.atomic
    def update_project(
        self,
        project_id: int,
        data: Dict,
        user
    ) -> TestProject:
        """
        更新项目

        Args:
            project_id: 项目 ID
            data: 更新的数据
            user: 当前用户

        Returns:
            更新后的项目对象

        Raises:
            ResourceNotFoundException: 项目不存在
            DuplicateException: 项目名称重复
        """
        project = self.repository.get_by_id(project_id)
        if not project:
            raise ResourceNotFoundException("项目不存在")

        # 验证父项目是否存在
        if 'parent_id' in data and data['parent_id']:
            parent = self.repository.get_by_id(data['parent_id'])
            if not parent:
                raise ResourceNotFoundException("父项目不存在")

        # 检查项目名称是否重复
        if 'project_name' in data and data['project_name'] != project.project_name:
            if self.repository.exists_by_name(
                data['project_name'],
                exclude_id=project_id
            ):
                raise DuplicateException(f"项目名称 '{data['project_name']}' 已存在")

        updated_project = self.repository.update(project_id, data)
        return updated_project

    def count_by_status(self, project_status: Optional[int] = None) -> int:
        """统计项目数"""
        return self.repository.count_by_status(project_status)

    @transaction.atomic
    def add_member(self, project_id: int, user_id: int) -> TestProject:
        """
        添加项目成员

        Args:
            project_id: 项目 ID
            user_id: 用户 ID

        Returns:
            更新后的项目对象

        Raises:
            ResourceNotFoundException: 项目不存在
        """
        project = self.repository.get_by_id(project_id)
        if not project:
            raise ResourceNotFoundException("项目不存在")

        project.members.add(user_id)
        return project

    @transaction.atomic
    def remove_member(self, project_id: int, user_id: int) -> TestProject:
        """
        移除项目成员

        Args:
            project_id: 项目 ID
            user_id: 用户 ID

        Returns:
            更新后的项目对象

        Raises:
            ResourceNotFoundException: 项目不存在
        """
        project = self.repository.get_by_id(project_id)
        if not project:
            raise ResourceNotFoundException("项目不存在")

        project.members.remove(user_id)
        return project
