"""
Organization Service
"""
from typing import Optional
from django.db import transaction
from common.services.base_service import BaseService
from common.exceptions import ValidationException, DuplicateException, ResourceNotFoundException
from user.models import Organization
from user.repositories.organization_repository import OrganizationRepository


class OrganizationService(BaseService[Organization]):
    """组织 Service"""

    def __init__(self):
        super().__init__(OrganizationRepository())

    @transaction.atomic
    def create_organization(self, data: dict, creator) -> Organization:
        """创建组织"""
        if not data.get('org_name'):
            raise ValidationException("组织名称不能为空")

        if self.repository.exists_by_name(data['org_name']):
            raise DuplicateException(f"组织名称 '{data['org_name']}' 已存在")

        org_data = {
            'org_name': data['org_name'],
            'description': data.get('description', ''),
        }

        return self.repository.create(org_data, creator=creator)

    @transaction.atomic
    def update_organization(self, org_id: int, data: dict, updater) -> Organization:
        """更新组织"""
        org = self.repository.get_by_id(org_id)
        if not org:
            raise ResourceNotFoundException("组织不存在")

        if 'org_name' in data and data['org_name'] != org.org_name:
            if self.repository.exists_by_name(data['org_name'], exclude_id=org_id):
                raise DuplicateException(f"组织名称 '{data['org_name']}' 已存在")

        return self.repository.update(org_id, data)

    def get_by_name(self, org_name: str) -> Optional[Organization]:
        """根据组织名称获取组织"""
        return self.repository.get_by_name(org_name)

    def get_user_organizations(self, user_id: int):
        """获取用户所属的组织"""
        return self.repository.get_user_organizations(user_id)

    def count_organizations(self) -> int:
        """统计组织数量"""
        return self.repository.count_organizations()

    @transaction.atomic
    def add_member(self, org_id: int, user_id: int) -> Organization:
        """添加成员到组织"""
        org = self.repository.get_by_id(org_id)
        if not org:
            raise ResourceNotFoundException("组织不存在")

        from user.models import User
        user = User.objects.filter(id=user_id, is_deleted=False).first()
        if not user:
            raise ResourceNotFoundException("用户不存在")

        org.members.add(user)
        return org

    @transaction.atomic
    def remove_member(self, org_id: int, user_id: int) -> Organization:
        """从组织移除成员"""
        org = self.repository.get_by_id(org_id)
        if not org:
            raise ResourceNotFoundException("组织不存在")

        from user.models import User
        user = User.objects.filter(id=user_id).first()
        if not user:
            raise ResourceNotFoundException("用户不存在")

        org.members.remove(user)
        return org
