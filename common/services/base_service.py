"""
Service 基类
提供通用的业务逻辑封装，包括事务管理和钩子方法
"""
from typing import Generic, TypeVar, Optional, Dict, List, Any
from django.db import transaction
from common.repositories.base_repository import BaseRepository

T = TypeVar('T')


class BaseService(Generic[T]):
    """
    Service 基类

    提供通用的业务逻辑封装，所有具体的 Service 都应该继承此类

    Attributes:
        repository: Repository 实例

    Example:
        >>> class TestCaseService(BaseService[TestCase]):
        ...     def __init__(self):
        ...         super().__init__(TestCaseRepository())
    """

    def __init__(self, repository: BaseRepository[T]):
        """
        初始化 Service

        Args:
            repository: Repository 实例
        """
        self.repository = repository

    def get_by_id(self, obj_id: int) -> Optional[T]:
        """
        根据 ID 获取对象

        Args:
            obj_id: 对象 ID

        Returns:
            对象实例，如果不存在返回 None
        """
        return self.repository.get_by_id(obj_id)

    def get_all(self, filters: Optional[Dict[str, Any]] = None) -> List[T]:
        """
        获取所有对象

        Args:
            filters: 过滤条件字典

        Returns:
            对象列表
        """
        return list(self.repository.get_all(filters))

    def get_by_ids(self, obj_ids: List[int]) -> List[T]:
        """
        根据 ID 列表批量获取对象

        Args:
            obj_ids: ID 列表

        Returns:
            对象列表
        """
        return list(self.repository.get_by_ids(obj_ids))

    def exists(self, **filters) -> bool:
        """
        检查对象是否存在

        Args:
            **filters: 过滤条件

        Returns:
            是否存在
        """
        return self.repository.exists(**filters)

    def count(self, **filters) -> int:
        """
        统计对象数量

        Args:
            **filters: 过滤条件

        Returns:
            对象数量
        """
        return self.repository.count(**filters)

    @transaction.atomic
    def create(self, data: Dict[str, Any], user=None) -> T:
        """
        创建对象

        Args:
            data: 对象数据字典
            user: 当前用户（可选）

        Returns:
            创建的对象实例
        """
        # 添加创建人信息
        if user:
            data['creator'] = user

        # 调用 Repository 创建
        obj = self.repository.create(data)

        # 执行创建后的钩子
        self._after_create(obj, user)

        return obj

    @transaction.atomic
    def bulk_create(
        self,
        data_list: List[Dict[str, Any]],
        user=None
    ) -> List[T]:
        """
        批量创建对象

        Args:
            data_list: 对象数据列表
            user: 当前用户（可选）

        Returns:
            创建的对象列表
        """
        # 添加创建人信息
        if user:
            for data in data_list:
                data['creator'] = user

        # 调用 Repository 批量创建
        objects = self.repository.bulk_create(data_list)

        # 执行批量创建后的钩子
        self._after_bulk_create(objects, user)

        return objects

    @transaction.atomic
    def update(
        self,
        obj_id: int,
        data: Dict[str, Any],
        user=None
    ) -> Optional[T]:
        """
        更新对象

        Args:
            obj_id: 对象 ID
            data: 更新的数据字典
            user: 当前用户（可选）

        Returns:
            更新后的对象实例，如果不存在返回 None
        """
        # 添加更新人信息
        if user:
            data['updater'] = user

        # 调用 Repository 更新
        obj = self.repository.update(obj_id, data)

        if obj:
            # 执行更新后的钩子
            self._after_update(obj, user)

        return obj

    @transaction.atomic
    def delete(self, obj_id: int, user=None, soft: bool = True) -> bool:
        """
        删除对象

        Args:
            obj_id: 对象 ID
            user: 当前用户（可选）
            soft: 是否软删除，默认 True

        Returns:
            是否删除成功
        """
        # 调用 Repository 删除
        result = self.repository.delete(obj_id, soft=soft)

        if result:
            # 执行删除后的钩子
            self._after_delete(obj_id, user)

        return result

    @transaction.atomic
    def batch_delete(
        self,
        obj_ids: List[int],
        user=None,
        soft: bool = True
    ) -> int:
        """
        批量删除对象

        Args:
            obj_ids: 对象 ID 列表
            user: 当前用户（可选）
            soft: 是否软删除

        Returns:
            删除的对象数量
        """
        count = 0
        for obj_id in obj_ids:
            if self.delete(obj_id, user, soft):
                count += 1

        return count

    # ==================== 钩子方法 ====================
    # 子类可以重写这些方法来实现自定义逻辑

    def _after_create(self, obj: T, user=None):
        """
        创建后的钩子方法

        子类可以重写此方法来实现创建后的自定义逻辑，
        例如：记录审计日志、发送通知等

        Args:
            obj: 创建的对象
            user: 当前用户
        """
        pass

    def _after_bulk_create(self, objects: List[T], user=None):
        """
        批量创建后的钩子方法

        Args:
            objects: 创建的对象列表
            user: 当前用户
        """
        pass

    def _after_update(self, obj: T, user=None):
        """
        更新后的钩子方法

        子类可以重写此方法来实现更新后的自定义逻辑

        Args:
            obj: 更新的对象
            user: 当前用户
        """
        pass

    def _after_delete(self, obj_id: int, user=None):
        """
        删除后的钩子方法

        子类可以重写此方法来实现删除后的自定义逻辑

        Args:
            obj_id: 删除的对象 ID
            user: 当前用户
        """
        pass

    def _validate_create_data(self, data: Dict[str, Any]):
        """
        验证创建数据

        子类可以重写此方法来实现自定义的数据验证逻辑

        Args:
            data: 待验证的数据

        Raises:
            ValidationError: 数据验证失败
        """
        pass

    def _validate_update_data(self, obj_id: int, data: Dict[str, Any]):
        """
        验证更新数据

        子类可以重写此方法来实现自定义的数据验证逻辑

        Args:
            obj_id: 对象 ID
            data: 待验证的数据

        Raises:
            ValidationError: 数据验证失败
        """
        pass
