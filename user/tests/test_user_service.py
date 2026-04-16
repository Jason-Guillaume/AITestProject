"""
User Service 单元测试
"""
import pytest
from django.contrib.auth import get_user_model
from user.services.user_service import UserService
from common.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    DuplicateException
)

User = get_user_model()


@pytest.mark.django_db
class TestUserService:
    """用户 Service 测试"""

    def test_create_user_success(self, user):
        """测试成功创建用户"""
        service = UserService()

        data = {
            'username': 'newuser',
            'password': 'newpass123',
            'real_name': '新用户',
            'email': 'new@example.com'
        }

        new_user = service.create_user(data, creator=user)

        assert new_user.id is not None
        assert new_user.username == 'newuser'
        assert new_user.real_name == '新用户'

    def test_create_user_missing_username(self, user):
        """测试创建用户时缺少用户名"""
        service = UserService()

        data = {
            'password': 'pass123',
            'real_name': '用户'
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_user(data, creator=user)

        assert "用户名不能为空" in str(exc_info.value)

    def test_create_user_missing_password(self, user):
        """测试创建用户时缺少密码"""
        service = UserService()

        data = {
            'username': 'newuser',
            'real_name': '用户'
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_user(data, creator=user)

        assert "密码不能为空" in str(exc_info.value)

    def test_create_user_missing_real_name(self, user):
        """测试创建用户时缺少真实姓名"""
        service = UserService()

        data = {
            'username': 'newuser',
            'password': 'pass123'
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_user(data, creator=user)

        assert "真实姓名不能为空" in str(exc_info.value)

    def test_create_user_duplicate_username(self, user):
        """测试创建用户时用户名重复"""
        service = UserService()

        data = {
            'username': user.username,
            'password': 'pass123',
            'real_name': '用户'
        }

        with pytest.raises(DuplicateException) as exc_info:
            service.create_user(data, creator=user)

        assert "已存在" in str(exc_info.value)

    def test_create_user_duplicate_email(self, user):
        """测试创建用户时邮箱重复"""
        service = UserService()

        data = {
            'username': 'newuser',
            'password': 'pass123',
            'real_name': '用户',
            'email': user.email
        }

        with pytest.raises(DuplicateException) as exc_info:
            service.create_user(data, creator=user)

        assert "已存在" in str(exc_info.value)

    def test_update_user_success(self, user):
        """测试成功更新用户"""
        service = UserService()

        data = {
            'real_name': '更新后的名字',
            'phone_number': '13800138000'
        }

        updated = service.update_user(user.id, data, updater=user)

        assert updated.real_name == '更新后的名字'
        assert updated.phone_number == '13800138000'

    def test_update_user_not_found(self, user):
        """测试更新不存在的用户"""
        service = UserService()

        data = {'real_name': '新名字'}

        with pytest.raises(ResourceNotFoundException) as exc_info:
            service.update_user(99999, data, updater=user)

        assert "用户不存在" in str(exc_info.value)

    def test_update_user_duplicate_username(self, user):
        """测试更新用户时用户名重复"""
        service = UserService()

        another_user = User.objects.create_user(
            username='another',
            password='pass123',
            real_name='另一个用户'
        )

        data = {'username': user.username}

        with pytest.raises(DuplicateException) as exc_info:
            service.update_user(another_user.id, data, updater=user)

        assert "已存在" in str(exc_info.value)

    def test_get_by_username(self, user):
        """测试根据用户名获取用户"""
        service = UserService()

        result = service.get_by_username('testuser')

        assert result is not None
        assert result.username == 'testuser'

    def test_get_by_email(self, user):
        """测试根据邮箱获取用户"""
        service = UserService()

        result = service.get_by_email('test@example.com')

        assert result is not None
        assert result.email == 'test@example.com'

    def test_activate_user(self, user):
        """测试激活用户"""
        service = UserService()

        user.is_active = False
        user.save()

        activated = service.activate_user(user.id)

        assert activated.is_active is True

    def test_deactivate_user(self, user):
        """测试停用用户"""
        service = UserService()

        deactivated = service.deactivate_user(user.id)

        assert deactivated.is_active is False

    def test_count_by_status(self, user):
        """测试统计用户数量"""
        service = UserService()

        User.objects.create_user(
            username='user2',
            password='pass123',
            real_name='用户2',
            is_active=False
        )

        total = service.count_by_status()
        assert total >= 2

        active = service.count_by_status(is_active=True)
        assert active >= 1
