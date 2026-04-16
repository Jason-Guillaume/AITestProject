"""
Organization Repository
"""
from typing import Optional
from django.db.models import QuerySet, Q
from common.repositories.base_repository import BaseRepository
from user.models import Organization


class OrganizationRepository(BaseRepository[Organization]):
    """组织 Repository"""

    def __init__(self):
        super().__init__(Organization)

    def get_all(self, filters: Optional[dict] = None) -> QuerySet[Organization]:
        """获取所有组织"""
        queryset = self.model.objects.filter(is_deleted=False).prefetch_related('members')

        if not filters:
            return queryset

        if 'search' in filters and filters['search']:
            search_term = filters['search']
            queryset = queryset.filter(
                Q(org_name__icontains=search_term) |
                Q(description__icontains=search_term)
            )

        return queryset.order_by('-create_time')

    def get_by_name(self, org_name: str) -> Optional[Organization]:
        """根据组织名称获取组织"""
        return self.model.objects.filter(
            org_name=org_name,
            is_deleted=False
        ).first()

    def exists_by_name(self, org_name: str, exclude_id: Optional[int] = None) -> bool:
        """检查组织名称是否存在"""
        queryset = self.model.objects.filter(org_name=org_name, is_deleted=False)

        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)

        return queryset.exists()

    def get_user_organizations(self, user_id: int) -> QuerySet[Organization]:
        """获取用户所属的组织"""
        return self.model.objects.filter(
            members__id=user_id,
            is_deleted=False
        ).order_by('-create_time')

    def count_organizations(self) -> int:
        """统计组织数量"""
        return self.model.objects.filter(is_deleted=False).count()
