"""
Repository 基类
提供通用的数据访问方法，包括 CRUD 操作和缓存管理
"""
from typing import Generic, TypeVar, Optional, List, Dict, Any
from django.db.models import Model, QuerySet
from django.core.cache import cache
from django.db import transaction

T = TypeVar('T', bound=Model)


class BaseRepository(Generic[T]):
    """
    Repository 基类

    提供通用的数据访问方法，所有具体的 Repository 都应该继承此类

    Attributes:
        model: Django Model 类
        cache_prefix: 缓存键前缀
        cache_ttl: 缓存过期时间（秒）

    Example:
        >>> class TestCaseRepository(BaseRepository[TestCase]):
        ...     def __init__(self):
        ...         super().__init__(TestCase)
    """

    def __init__(self, model: type[T]):
        """
        初始化 Repository

        Args:
            model: Django Model 类
        """
        self.model = model
        self.cache_prefix = model._meta.db_table
        self.cache_ttl = 300  # 默认 5 分钟

    def get_by_id(self, obj_id: int) -> Optional[T]:
        """
        根据 ID 获取对象（带缓存）

        Args:
            obj_id: 对象 ID

        Returns:
            对象实例，如果不存在返回 None
        """
        cache_key = f"{self.cache_prefix}:{obj_id}"
        obj = cache.get(cache_key)

        if obj is None:
            obj = self.model.objects.filter(
                id=obj_id,
                is_deleted=False
            ).first()

            if obj:
                cache.set(cache_key, obj, self.cache_ttl)

        return obj

    def get_all(self, filters: Optional[Dict[str, Any]] = None) -> QuerySet:
        """
        获取所有对象

        Args:
            filters: 过滤条件字典

        Returns:
            QuerySet 对象
        """
        qs = self.model.objects.filter(is_deleted=False)

        if filters:
            qs = qs.filter(**filters)

        return qs

    def get_by_ids(self, obj_ids: List[int]) -> QuerySet:
        """
        根据 ID 列表批量获取对象

        Args:
            obj_ids: ID 列表

        Returns:
            QuerySet 对象
        """
        return self.model.objects.filter(
            id__in=obj_ids,
            is_deleted=False
        )

    def exists(self, **filters) -> bool:
        """
        检查对象是否存在

        Args:
            **filters: 过滤条件

        Returns:
            是否存在
        """
        return self.model.objects.filter(
            is_deleted=False,
            **filters
        ).exists()

    def count(self, **filters) -> int:
        """
        统计对象数量

        Args:
            **filters: 过滤条件

        Returns:
            对象数量
        """
        return self.model.objects.filter(
            is_deleted=False,
            **filters
        ).count()

    @transaction.atomic
    def create(self, data: Dict[str, Any], **kwargs) -> T:
        """
        创建对象

        Args:
            data: 对象数据字典
            **kwargs: 额外的字段（如 creator）

        Returns:
            创建的对象实例
        """
        obj = self.model.objects.create(**data, **kwargs)
        self._invalidate_cache()
        return obj

    @transaction.atomic
    def bulk_create(self, data_list: List[Dict[str, Any]], **kwargs) -> List[T]:
        """
        批量创建对象

        Args:
            data_list: 对象数据列表
            **kwargs: 额外的字段

        Returns:
            创建的对象列表
        """
        objects = [self.model(**data, **kwargs) for data in data_list]
        created_objects = self.model.objects.bulk_create(objects)
        self._invalidate_cache()
        return created_objects

    @transaction.atomic
    def update(self, obj_id: int, data: Dict[str, Any]) -> Optional[T]:
        """
        更新对象

        Args:
            obj_id: 对象 ID
            data: 更新的数据字典

        Returns:
            更新后的对象实例，如果不存在返回 None
        """
        obj = self.get_by_id(obj_id)
        if not obj:
            return None

        for key, value in data.items():
            setattr(obj, key, value)
        obj.save()

        self._invalidate_cache(obj_id)
        return obj

    @transaction.atomic
    def update_by_filter(self, filters: Dict[str, Any], data: Dict[str, Any]) -> int:
        """
        根据条件批量更新

        Args:
            filters: 过滤条件
            data: 更新的数据

        Returns:
            更新的对象数量
        """
        count = self.model.objects.filter(
            is_deleted=False,
            **filters
        ).update(**data)

        self._invalidate_cache()
        return count

    @transaction.atomic
    def delete(self, obj_id: int, soft: bool = True) -> bool:
        """
        删除对象（软删除或硬删除）

        Args:
            obj_id: 对象 ID
            soft: 是否软删除，默认 True

        Returns:
            是否删除成功
        """
        obj = self.get_by_id(obj_id)
        if not obj:
            return False

        if soft:
            obj.is_deleted = True
            obj.save()
        else:
            obj.delete()

        self._invalidate_cache(obj_id)
        return True

    @transaction.atomic
    def delete_by_filter(self, filters: Dict[str, Any], soft: bool = True) -> int:
        """
        根据条件批量删除

        Args:
            filters: 过滤条件
            soft: 是否软删除

        Returns:
            删除的对象数量
        """
        qs = self.model.objects.filter(is_deleted=False, **filters)

        if soft:
            count = qs.update(is_deleted=True)
        else:
            count = qs.count()
            qs.delete()

        self._invalidate_cache()
        return count

    def _invalidate_cache(self, obj_id: Optional[int] = None):
        """
        清除缓存

        Args:
            obj_id: 对象 ID，如果为 None 则清除所有相关缓存
        """
        if obj_id:
            cache_key = f"{self.cache_prefix}:{obj_id}"
            cache.delete(cache_key)
        else:
            # 清除所有相关缓存
            # 使用 delete_pattern 如果可用，否则跳过（测试环境）
            if hasattr(cache, 'delete_pattern'):
                cache.delete_pattern(f"{self.cache_prefix}:*")
            # 在测试环境中，LocMemCache 不支持 delete_pattern，可以忽略

    def _build_cache_key(self, *args) -> str:
        """
        构建缓存键

        Args:
            *args: 缓存键参数

        Returns:
            缓存键字符串
        """
        parts = [self.cache_prefix] + [str(arg) for arg in args]
        return ":".join(parts)
