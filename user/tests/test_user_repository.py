"""
User Repository 单元测试
"""
import pytest
from django.contrib.auth import get_user_model
from user.repositories.user_repository import UserRepository

User = get_user_model()


@pytest.mark.django_db
class TestUserRepository:
    """用户 Repository 测试"""

    def test_get_by_id(self, user):
        """测试根据 ID 获取用户"""
        repo = UserRepository()
        result = repo.get_by_id(user.id)

        assert result is not None
        assert result.id == user.id
        assert result.username == 'testuser'

    def test_get_by_id_not_found(self):
        """测试获取不存在的用户"""
        repo = UserRepository()
        result = repo.get_by_id(99999)

        assert result is None

    def test_get_by_username(self, user):
        """测试根据用户名获取用户"""
        repo = UserRepository()
        result = repo.get_by_username('testuser')

        assert result is not None
        assert result.username == 'testuser'

    def test_get_by_username_not_found(self):
        """测试获取不存在的用户名"""
        repo = UserRepository()
        result = repo.get_by_username('nonexistent')

        assert result is None

    def test_get_by_email(self, user):
        """测试根据邮箱获取用户"""
        repo = UserRepository()
        result = repo.get_by_email('test@example.com')

        assert result is not None
        assert result.email == 'test@example.com'

    def test_exists_by_username(self, user):
        """测试检查用户名是否存在"""
        repo = UserRepository()

        exists = repo.exists_by_username('testuser')
        assert exists is True

        exists = repo.exists_by_username('nonexistent')
        assert exists is False

        exists = repo.exists_by_username('testuser', exclude_id=user.id)
        assert exists is False

    def test_exists_by_email(self, user):
        """测试检查邮箱是否存在"""
        repo = UserRepository()

        exists = repo.exists_by_email('test@example.com')
        assert exists is True

        exists = repo.exists_by_email('nonexistent@example.com')
        assert exists is False

        exists = repo.exists_by_email('test@example.com', exclude_id=user.id)
        assert exists is False

    def test_get_active_users(self, user):
        """测试获取活跃用户"""
        repo = UserRepository()

        User.objects.create_user(
            username='inactive',
            password='pass123',
            real_name='停用用户',
            is_active=False
        )

        active_users = repo.get_active_users()
        assert active_users.count() >= 1
        assert all(u.is_active for u in active_users)

    def test_get_system_admins(self, admin_user):
        """测试获取系统管理员"""
        repo = UserRepository()

        admins = repo.get_system_admins()
        assert admins.count() >= 1
        assert all(u.is_system_admin for u in admins)

    def test_count_by_status(self, user):
        """测试统计用户数量"""
        repo = UserRepository()

        User.objects.create_user(
            username='user2',
            password='pass123',
            real_name='用户2',
            is_active=False
        )

        total = repo.count_by_status()
        assert total >= 2

        active = repo.count_by_status(is_active=True)
        assert active >= 1

        inactive = repo.count_by_status(is_active=False)
        assert inactive >= 1

    def test_get_all_with_search(self, user):
        """测试搜索用户"""
        repo = UserRepository()

        User.objects.create_user(
            username='john',
            password='pass123',
            real_name='John Doe',
            email='john@example.com'
        )

        users = repo.get_all(filters={'search': 'john'})
        assert users.count() >= 1

    def test_create(self, user):
        """测试创建用户"""
        repo = UserRepository()

        data = {
            'username': 'newuser',
            'password': 'newpass123',
            'real_name': '新用户',
            'email': 'new@example.com'
        }

        new_user = repo.create(data, creator=user)

        assert new_user.id is not None
        assert new_user.username == 'newuser'

    def test_update(self, user):
        """测试更新用户"""
        repo = UserRepository()

        data = {
            'real_name': '更新后的名字',
            'phone_number': '13800138000'
        }

        updated = repo.update(user.id, data)

        assert updated is not None
        assert updated.real_name == '更新后的名字'
        assert updated.phone_number == '13800138000'

    def test_delete_soft(self, user):
        """测试软删除用户"""
        repo = UserRepository()

        result = repo.delete(user.id, soft=True)

        assert result is True

        user.refresh_from_db()
        assert user.is_deleted is True
