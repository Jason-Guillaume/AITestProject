"""
Organization Repository 单元测试
"""
import pytest
from django.contrib.auth import get_user_model
from user.repositories.organization_repository import OrganizationRepository
from user.models import Organization

User = get_user_model()


@pytest.mark.django_db
class TestOrganizationRepository:
    """组织 Repository 测试"""

    def test_get_by_id(self, organization):
        """测试根据 ID 获取组织"""
        repo = OrganizationRepository()
        result = repo.get_by_id(organization.id)

        assert result is not None
        assert result.id == organization.id
        assert result.org_name == '测试组织'

    def test_get_by_id_not_found(self):
        """测试获取不存在的组织"""
        repo = OrganizationRepository()
        result = repo.get_by_id(99999)

        assert result is None

    def test_get_by_name(self, organization):
        """测试根据名称获取组织"""
        repo = OrganizationRepository()
        result = repo.get_by_name('测试组织')

        assert result is not None
        assert result.org_name == '测试组织'

    def test_exists_by_name(self, organization):
        """测试检查组织名称是否存在"""
        repo = OrganizationRepository()

        exists = repo.exists_by_name('测试组织')
        assert exists is True

        exists = repo.exists_by_name('不存在的组织')
        assert exists is False

        exists = repo.exists_by_name('测试组织', exclude_id=organization.id)
        assert exists is False

    def test_get_user_organizations(self, user, organization):
        """测试获取用户所属的组织"""
        repo = OrganizationRepository()

        organization.members.add(user)

        orgs = repo.get_user_organizations(user.id)
        assert orgs.count() >= 1

    def test_create(self, user):
        """测试创建组织"""
        repo = OrganizationRepository()

        data = {
            'org_name': '新组织',
            'description': '新组织描述'
        }

        org = repo.create(data, creator=user)

        assert org.id is not None
        assert org.org_name == '新组织'
        assert org.creator == user

    def test_update(self, organization):
        """测试更新组织"""
        repo = OrganizationRepository()

        data = {
            'org_name': '更新后的组织',
            'description': '更新后的描述'
        }

        updated = repo.update(organization.id, data)

        assert updated is not None
        assert updated.org_name == '更新后的组织'
        assert updated.description == '更新后的描述'

    def test_delete_soft(self, organization):
        """测试软删除组织"""
        repo = OrganizationRepository()

        result = repo.delete(organization.id, soft=True)

        assert result is True

        organization.refresh_from_db()
        assert organization.is_deleted is True

    def test_count_organizations(self, organization):
        """测试统计组织数量"""
        repo = OrganizationRepository()

        count = repo.count_organizations()
        assert count >= 1
