"""
测试配置文件
"""
import pytest
from django.contrib.auth import get_user_model
from project.models import TestProject

User = get_user_model()


@pytest.fixture
def user(db):
    """创建测试用户"""
    return User.objects.create_user(
        username='testuser',
        password='testpass123',
        real_name='测试用户'
    )


@pytest.fixture
def project(db, user):
    """创建测试项目"""
    return TestProject.objects.create(
        project_name='测试项目',
        description='这是一个测试项目',
        project_status=1,
        creator=user
    )


@pytest.fixture
def parent_project(db, user):
    """创建父项目"""
    return TestProject.objects.create(
        project_name='父项目',
        description='这是一个父项目',
        project_status=1,
        creator=user
    )
