"""
测试配置文件
"""
import pytest
from django.contrib.auth import get_user_model
from testcase.models import TestCase, TestModule
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
        creator=user
    )


@pytest.fixture
def module(db, project, user):
    """创建测试模块"""
    return TestModule.objects.create(
        name='测试模块',
        project=project,
        creator=user
    )


@pytest.fixture
def testcase(db, project, module, user):
    """创建测试用例"""
    return TestCase.objects.create(
        case_name='测试用例1',
        test_type='functional',
        module=module,
        creator=user
    )
