"""
测试配置文件
"""
import pytest
from django.contrib.auth import get_user_model
from defect.models import TestDefect

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
def handler(db):
    """创建处理人"""
    return User.objects.create_user(
        username='handler',
        password='testpass123',
        real_name='处理人'
    )


@pytest.fixture
def defect(db, user, handler):
    """创建测试缺陷"""
    return TestDefect.objects.create(
        defect_no='BUG-001',
        defect_name='测试缺陷',
        defect_content='这是一个测试缺陷',
        severity=2,
        priority=2,
        status=1,
        handler=handler,
        creator=user
    )
