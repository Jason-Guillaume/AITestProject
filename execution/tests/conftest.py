"""
Execution 模块测试配置
"""
import pytest
from django.contrib.auth import get_user_model
from project.models import TestProject, ReleasePlan
from execution.models import TestPlan, TestReport

User = get_user_model()


@pytest.fixture
def user(db):
    """创建测试用户"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def project(db, user):
    """创建测试项目"""
    return TestProject.objects.create(
        project_name='测试项目',
        description='测试项目描述',
        creator=user
    )


@pytest.fixture
def version(db, project, user):
    """创建测试版本"""
    return ReleasePlan.objects.create(
        release_name='v1.0.0',
        version_no='1.0.0',
        project=project,
        release_date='2026-05-01',
        creator=user
    )


@pytest.fixture
def test_plan(db, version, user):
    """创建测试计划"""
    plan = TestPlan.objects.create(
        plan_name='测试计划1',
        version=version,
        iteration='Sprint 1',
        environment='测试环境',
        plan_status=1,
        creator=user
    )
    plan.testers.add(user)
    return plan


@pytest.fixture
def test_report(db, test_plan, project, user):
    """创建测试报告"""
    from datetime import datetime
    return TestReport.objects.create(
        report_name='测试报告1',
        plan=test_plan,
        project=project,
        environment='测试环境',
        create_method=1,
        trace_id='trace-001',
        case_count=100,
        pass_rate=80.0,
        defect_count=15,
        start_time=datetime.now(),
        end_time=datetime.now(),
        creator=user
    )
