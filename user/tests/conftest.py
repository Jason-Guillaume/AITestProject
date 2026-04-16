"""
测试配置文件
"""
import pytest
from django.contrib.auth import get_user_model
from user.models import Organization

User = get_user_model()


@pytest.fixture
def user(db):
    """创建测试用户"""
    return User.objects.create_user(
        username='testuser',
        password='testpass123',
        real_name='测试用户',
        email='test@example.com'
    )


@pytest.fixture
def admin_user(db):
    """创建管理员用户"""
    return User.objects.create_user(
        username='admin',
        password='adminpass123',
        real_name='管理员',
        email='admin@example.com',
        is_system_admin=True
    )


@pytest.fixture
def organization(db, user):
    """创建测试组织"""
    return Organization.objects.create(
        org_name='测试组织',
        description='这是一个测试组织',
        creator=user
    )
