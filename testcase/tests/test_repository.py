"""
TestCase Repository 单元测试
"""
import pytest
from django.contrib.auth import get_user_model
from testcase.repositories.testcase_repository import TestCaseRepository
from testcase.models import TestCase

User = get_user_model()


@pytest.mark.django_db
class TestTestCaseRepository:
    """测试用例 Repository 测试"""

    def test_get_by_id(self, testcase):
        """测试根据 ID 获取用例"""
        repo = TestCaseRepository()
        result = repo.get_by_id(testcase.id)

        assert result is not None
        assert result.id == testcase.id
        assert result.case_name == '测试用例1'

    def test_get_by_id_not_found(self):
        """测试获取不存在的用例"""
        repo = TestCaseRepository()
        result = repo.get_by_id(99999)

        assert result is None

    def test_get_by_project(self, project, module, user):
        """测试按项目查询用例"""
        repo = TestCaseRepository()

        # 创建测试数据
        TestCase.objects.create(
            case_name='用例1',
            test_type='functional',
            module=module,
            creator=user
        )
        TestCase.objects.create(
            case_name='用例2',
            test_type='api',
            module=module,
            creator=user
        )

        # 查询所有用例
        testcases = repo.get_by_project(project.id)
        assert testcases.count() == 2

        # 按类型过滤
        testcases = repo.get_by_project(
            project.id,
            filters={'test_type': 'api'}
        )
        assert testcases.count() == 1
        assert testcases.first().test_type == 'api'

    def test_get_by_project_with_search(self, project, module, user):
        """测试按项目查询用例（带搜索）"""
        repo = TestCaseRepository()

        TestCase.objects.create(
            case_name='登录测试',
            test_type='functional',
            module=module,
            creator=user
        )
        TestCase.objects.create(
            case_name='注册测试',
            test_type='functional',
            module=module,
            creator=user
        )

        # 搜索关键词
        testcases = repo.get_by_project(
            project.id,
            filters={'search': '登录'}
        )
        assert testcases.count() == 1
        assert testcases.first().case_name == '登录测试'

    def test_count_by_project(self, project, module, user):
        """测试统计项目用例数"""
        repo = TestCaseRepository()

        # 创建测试数据
        TestCase.objects.create(
            case_name='用例1',
            test_type='functional',
            module=module,
            creator=user
        )
        TestCase.objects.create(
            case_name='用例2',
            test_type='api',
            module=module,
            creator=user
        )

        # 统计所有用例
        count = repo.count_by_project(project.id)
        assert count == 2

        # 按类型统计
        count = repo.count_by_project(project.id, test_type='api')
        assert count == 1

    def test_exists_by_name(self, project, testcase):
        """测试检查用例名称是否存在"""
        repo = TestCaseRepository()

        # 存在的名称
        exists = repo.exists_by_name(project.id, '测试用例1')
        assert exists is True

        # 不存在的名称
        exists = repo.exists_by_name(project.id, '不存在的用例')
        assert exists is False

        # 排除当前用例
        exists = repo.exists_by_name(
            project.id,
            '测试用例1',
            exclude_id=testcase.id
        )
        assert exists is False

    def test_create(self, module, user):
        """测试创建用例"""
        repo = TestCaseRepository()

        data = {
            'case_name': '新测试用例',
            'test_type': 'functional',
            'module': module
        }

        testcase = repo.create(data, creator=user)

        assert testcase.id is not None
        assert testcase.case_name == '新测试用例'
        assert testcase.creator == user

    def test_update(self, testcase):
        """测试更新用例"""
        repo = TestCaseRepository()

        data = {
            'case_name': '更新后的名称'
        }

        updated = repo.update(testcase.id, data)

        assert updated is not None
        assert updated.case_name == '更新后的名称'

    def test_delete_soft(self, testcase):
        """测试软删除用例"""
        repo = TestCaseRepository()

        result = repo.delete(testcase.id, soft=True)

        assert result is True

        # 验证软删除
        testcase.refresh_from_db()
        assert testcase.is_deleted is True

    def test_get_with_steps(self, testcase):
        """测试获取用例及其步骤"""
        repo = TestCaseRepository()

        result = repo.get_with_steps(testcase.id)

        assert result is not None
        assert result.id == testcase.id
