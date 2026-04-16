"""
User Repository
"""
from typing import Optional
from django.db.models import QuerySet, Q
from common.repositories.base_repository import BaseRepository
from user.models import User


class UserRepository(BaseRepository[User]):
    """用户 Repository"""

    def __init__(self):
        super().__init__(User)

    def get_all(self, filters: Optional[dict] = None) -> QuerySet[User]:
        """获取所有用户"""
        queryset = self.model.objects.filter(is_deleted=False)

        if not filters:
            return queryset

        if 'is_active' in filters:
            queryset = queryset.filter(is_active=filters['is_active'])

        if 'is_system_admin' in filters:
            queryset = queryset.filter(is_system_admin=filters['is_system_admin'])

        if 'search' in filters and filters['search']:
            search_term = filters['search']
            queryset = queryset.filter(
                Q(username__icontains=search_term) |
                Q(real_name__icontains=search_term) |
                Q(email__icontains=search_term) |
                Q(phone_number__icontains=search_term)
            )

        return queryset.order_by('-create_time')

    def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return self.model.objects.filter(
            username=username,
            is_deleted=False
        ).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return self.model.objects.filter(
            email=email,
            is_deleted=False
        ).first()

    def exists_by_username(self, username: str, exclude_id: Optional[int] = None) -> bool:
        """检查用户名是否存在"""
        queryset = self.model.objects.filter(username=username, is_deleted=False)

        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)

        return queryset.exists()

    def exists_by_email(self, email: str, exclude_id: Optional[int] = None) -> bool:
        """检查邮箱是否存在"""
        queryset = self.model.objects.filter(email=email, is_deleted=False)

        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)

        return queryset.exists()

    def get_active_users(self) -> QuerySet[User]:
        """获取所有活跃用户"""
        return self.model.objects.filter(
            is_active=True,
            is_deleted=False
        ).order_by('-create_time')

    def get_system_admins(self) -> QuerySet[User]:
        """获取所有系统管理员"""
        return self.model.objects.filter(
            is_system_admin=True,
            is_deleted=False
        ).order_by('-create_time')

    def count_by_status(self, is_active: Optional[bool] = None) -> int:
        """统计用户数量"""
        queryset = self.model.objects.filter(is_deleted=False)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        return queryset.count()
