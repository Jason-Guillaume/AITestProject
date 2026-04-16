"""
Organization Service 单元测试
"""
import pytest
from django.contrib.auth import get_user_model
from user.services.organization_service import OrganizationService
from user.models import Organization
from common.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    DuplicateException
)

User = get_user_model()


@pytest.mark.django_db
class TestOrganizationService:
    """组织 Service 测试"""

    def test_create_organization_success(self, user):
        """测试成功创建组织"""
        service = OrganizationService()

        data = {
            'org_name': '新组织',
            'description': '新组织描述'
        }

        org = service.create_organization(data, creator=user)

        assert org.id is not None
        assert org.org_name == '新组织'
        assert org.creator == user

    def test_create_organization_missing_name(self, user):
        """测试创建组织时缺少名称"""
        service = OrganizationService()

        data = {
            'description': '描述'
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_organization(data, creator=user)

        assert "组织名称不能为空" in str(exc_info.value)

    def test_create_organization_duplicate_name(self, organization, user):
        """测试创建组织时名称重复"""
        service = OrganizationService()

        data = {
            'org_name': organization.org_name,
            'description': '描述'
        }

        with pytest.raises(DuplicateException) as exc_info:
            service.create_organization(data, creator=user)

        assert "已存在" in str(exc_info.value)

    def test_update_organization_success(self, organization, user):
        """测试成功更新组织"""
        service = OrganizationService()

        data = {
            'org_name': '更新后的组织',
            'description': '更新后的描述'
        }

        updated = service.update_organization(organization.id, data, updater=user)

        assert updated.org_name == '更新后的组织'
        assert updated.description == '更新后的描述'

    def test_update_organization_not_found(self, user):
        """测试更新不存在的组织"""
        service = OrganizationService()

        data = {'org_name': '新名称'}

        with pytest.raises(ResourceNotFoundException) as exc_info:
            service.update_organization(99999, data, updater=user)

        assert "组织不存在" in str(exc_info.value)

    def test_update_organization_duplicate_name(self, user, organization):
        """测试更新组织时名称重复"""
        service = OrganizationService()

        another_org = Organization.objects.create(
            org_name='另一个组织',
            description='描述',
            creator=user
        )

        data = {'org_name': organization.org_name}

        with pytest.raises(DuplicateException) as exc_info:
            service.update_organization(another_org.id, data, updater=user)

        assert "已存在" in str(exc_info.value)

    def test_get_by_name(self, organization):
        """测试根据名称获取组织"""
        service = OrganizationService()

        result = service.get_by_name('测试组织')

        assert result is not None
        assert result.org_name == '测试组织'

    def test_get_user_organizations(self, user, organization):
        """测试获取用户所属的组织"""
        service = OrganizationService()

        organization.members.add(user)

        orgs = service.get_user_organizations(user.id)

        assert orgs.count() >= 1

    def test_add_member(self, organization, user):
        """测试添加成员"""
        service = OrganizationService()

        new_user = User.objects.create_user(
            username='newmember',
            password='pass123',
            real_name='新成员'
        )

        updated = service.add_member(organization.id, new_user.id)

        assert new_user in updated.members.all()

    def test_remove_member(self, organization, user):
        """测试移除成员"""
        service = OrganizationService()

        organization.members.add(user)

        updated = service.remove_member(organization.id, user.id)

        assert user not in updated.members.all()

    def test_count_organizations(self, organization):
        """测试统计组织数量"""
        service = OrganizationService()

        count = service.count_organizations()
        assert count >= 1

    def test_delete_organization(self, organization):
        """测试删除组织"""
        service = OrganizationService()

        result = service.delete(organization.id)

        assert result is True

        organization.refresh_from_db()
        assert organization.is_deleted is True
