"""
缺陷 Service
提供缺陷的业务逻辑
"""
from typing import List, Dict, Optional
from django.db import transaction
from common.services.base_service import BaseService
from common.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    DuplicateException
)
from defect.repositories.defect_repository import DefectRepository
from defect.models import TestDefect


class DefectService(BaseService[TestDefect]):
    """
    缺陷 Service

    提供缺陷的业务逻辑，包括创建、更新、删除、查询等操作

    Example:
        >>> service = DefectService()
        >>> defect = service.create_defect(data, user)
        >>> defects = service.get_all()
    """

    def __init__(self):
        """初始化 DefectService"""
        super().__init__(DefectRepository())

    def get_all(self, filters: Optional[Dict] = None) -> List[TestDefect]:
        """
        获取所有缺陷

        Args:
            filters: 过滤条件

        Returns:
            缺陷列表
        """
        return list(self.repository.get_all(filters))

    def get_by_release(self, release_id: int) -> List[TestDefect]:
        """
        获取版本下的缺陷

        Args:
            release_id: 版本 ID

        Returns:
            缺陷列表
        """
        return list(self.repository.get_by_release(release_id))

    def get_by_handler(self, handler_id: int) -> List[TestDefect]:
        """
        获取处理人的缺陷

        Args:
            handler_id: 处理人 ID

        Returns:
            缺陷列表
        """
        return list(self.repository.get_by_handler(handler_id))

    @transaction.atomic
    def create_defect(self, data: Dict, user) -> TestDefect:
        """
        创建缺陷

        Args:
            data: 缺陷数据
            user: 当前用户

        Returns:
            创建的缺陷对象

        Raises:
            ValidationException: 数据验证失败
            DuplicateException: 缺陷编号重复
        """
        # 验证必填字段
        if not data.get('defect_no'):
            raise ValidationException("缺陷编号不能为空")

        if not data.get('defect_name'):
            raise ValidationException("缺陷标题不能为空")

        if not data.get('handler_id'):
            raise ValidationException("处理人不能为空")

        # 检查缺陷编号是否重复
        if self.repository.exists_by_no(data['defect_no']):
            raise DuplicateException(f"缺陷编号 '{data['defect_no']}' 已存在")

        # 创建缺陷
        defect = self.repository.create(data, creator=user)

        return defect

    @transaction.atomic
    def update_defect(
        self,
        defect_id: int,
        data: Dict,
        user
    ) -> TestDefect:
        """
        更新缺陷

        Args:
            defect_id: 缺陷 ID
            data: 更新的数据
            user: 当前用户

        Returns:
            更新后的缺陷对象

        Raises:
            ResourceNotFoundException: 缺陷不存在
            DuplicateException: 缺陷编号重复
        """
        defect = self.repository.get_by_id(defect_id)
        if not defect:
            raise ResourceNotFoundException("缺陷不存在")

        # 检查缺陷编号是否重复
        if 'defect_no' in data and data['defect_no'] != defect.defect_no:
            if self.repository.exists_by_no(
                data['defect_no'],
                exclude_id=defect_id
            ):
                raise DuplicateException(f"缺陷编号 '{data['defect_no']}' 已存在")

        updated_defect = self.repository.update(defect_id, data)
        return updated_defect

    def count_by_status(self, status: Optional[int] = None) -> int:
        """统计缺陷数"""
        return self.repository.count_by_status(status)

    def count_by_severity(self, severity: int) -> int:
        """按严重程度统计缺陷数"""
        return self.repository.count_by_severity(severity)

    @transaction.atomic
    def update_status(self, defect_id: int, status: int, user) -> TestDefect:
        """
        更新缺陷状态

        Args:
            defect_id: 缺陷 ID
            status: 新状态
            user: 当前用户

        Returns:
            更新后的缺陷对象

        Raises:
            ResourceNotFoundException: 缺陷不存在
        """
        defect = self.repository.get_by_id(defect_id)
        if not defect:
            raise ResourceNotFoundException("缺陷不存在")

        return self.repository.update(defect_id, {'status': status})

    @transaction.atomic
    def assign_handler(self, defect_id: int, handler_id: int, user) -> TestDefect:
        """
        分配处理人

        Args:
            defect_id: 缺陷 ID
            handler_id: 处理人 ID
            user: 当前用户

        Returns:
            更新后的缺陷对象

        Raises:
            ResourceNotFoundException: 缺陷不存在
        """
        defect = self.repository.get_by_id(defect_id)
        if not defect:
            raise ResourceNotFoundException("缺陷不存在")

        return self.repository.update(defect_id, {'handler_id': handler_id})
