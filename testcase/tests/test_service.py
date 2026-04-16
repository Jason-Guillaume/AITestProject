"""
TestCase Service 单元测试
"""
import pytest
from django.contrib.auth import get_user_model
from testcase.services.testcase_service import TestCaseService
from testcase.models import TestCase
from common.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    DuplicateException
)

User = get_user_model()


@pytest.mark.django_db
class TestTestCaseService:
    """测试用例 Service 测试"""

    def test_create_testcase_success(self, project, module, user):
        """测试成功创建用例"""
        service = TestCaseService()

        data = {
            'case_name': '新测试用例',
            'test_type': 'functional',
            'module_id': module.id
        }

        testcase = service.create_testcase(data, user)

        assert testcase.id is not None
        assert testcase.case_name == '新测试用例'
        assert testcase.creator == user
        assert testcase.module_id == module.id

    def test_create_testcase_missing_name(self, project, user):
        """测试创建用例时缺少名称"""
        service = TestCaseService()

        data = {
            'test_type': 'functional',
            'project_id': project.id
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_testcase(data, user)

        assert "用例名称不能为空" in str(exc_info.value)

    def test_create_testcase_missing_project(self, user):
        """测试创建用例时缺少项目 ID 和模块 ID"""
        service = TestCaseService()

        data = {
            'case_name': '测试用例',
            'test_type': 'functional'
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_testcase(data, user)

        assert "项目 ID 或模块 ID 不能为空" in str(exc_info.value)

    def test_create_testcase_invalid_module(self, project, user):
        """测试创建用例时模块不存在"""
        service = TestCaseService()

        data = {
            'case_name': '测试用例',
            'test_type': 'functional',
            'project_id': project.id,
            'module_id': 99999
        }

        with pytest.raises(ResourceNotFoundException) as exc_info:
            service.create_testcase(data, user)

        assert "模块不存在" in str(exc_info.value)

    def test_create_testcase_duplicate_name(self, project, module, testcase, user):
        """测试创建用例时名称重复"""
        service = TestCaseService()

        data = {
            'case_name': testcase.case_name,
            'test_type': 'functional',
            'module_id': module.id
        }

        with pytest.raises(DuplicateException) as exc_info:
            service.create_testcase(data, user)

        assert "已存在" in str(exc_info.value)

    def test_batch_create_testcases(self, project, module, user):
        """测试批量创建用例"""
        service = TestCaseService()

        testcases_data = [
            {
                'case_name': '批量用例1',
                'test_type': 'functional',
                'module_id': module.id
            },
            {
                'case_name': '批量用例2',
                'test_type': 'api',
                'module_id': module.id
            }
        ]

        result = service.batch_create_testcases(testcases_data, user)

        assert result['success_count'] == 2
        assert result['error_count'] == 0
        assert len(result['created_cases']) == 2

    def test_batch_create_testcases_with_errors(self, project, module, user):
        """测试批量创建用例（包含错误）"""
        service = TestCaseService()

        testcases_data = [
            {
                'case_name': '正常用例',
                'test_type': 'functional',
                'module_id': module.id
            },
            {
                'test_type': 'api',
                'module_id': module.id
            }
        ]

        result = service.batch_create_testcases(testcases_data, user)

        assert result['success_count'] == 1
        assert result['error_count'] == 1
        assert len(result['errors']) == 1

    def test_update_testcase_success(self, testcase, user):
        """测试成功更新用例"""
        service = TestCaseService()

        data = {
            'case_name': '更新后的名称'
        }

        updated = service.update_testcase(testcase.id, data, user)

        assert updated.case_name == '更新后的名称'

    def test_update_testcase_not_found(self, user):
        """测试更新不存在的用例"""
        service = TestCaseService()

        data = {'case_name': '新名称'}

        with pytest.raises(ResourceNotFoundException) as exc_info:
            service.update_testcase(99999, data, user)

        assert "测试用例不存在" in str(exc_info.value)

    def test_update_testcase_duplicate_name(self, project, module, testcase, user):
        """测试更新用例时名称重复"""
        service = TestCaseService()

        # 创建另一个用例
        another_case = TestCase.objects.create(
            case_name='另一个用例',
            test_type='functional',
            module=module,
            creator=user
        )

        data = {'case_name': testcase.case_name}

        with pytest.raises(DuplicateException) as exc_info:
            service.update_testcase(another_case.id, data, user)

        assert "已存在" in str(exc_info.value)

    def test_delete_testcase(self, testcase):
        """测试删除用例"""
        service = TestCaseService()

        result = service.delete(testcase.id)

        assert result is True

        testcase.refresh_from_db()
        assert testcase.is_deleted is True

    def test_get_by_project(self, project, module, user):
        """测试按项目获取用例"""
        service = TestCaseService()

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

        testcases = service.get_by_project(project.id)

        assert len(testcases) == 2

    def test_get_with_steps(self, testcase):
        """测试获取用例及其步骤"""
        service = TestCaseService()

        result = service.get_with_steps(testcase.id)

        assert result is not None
        assert result.id == testcase.id

    def test_get_with_steps_not_found(self):
        """测试获取不存在的用例"""
        service = TestCaseService()

        with pytest.raises(ResourceNotFoundException) as exc_info:
            service.get_with_steps(99999)

        assert "测试用例不存在" in str(exc_info.value)

    def test_count_by_project(self, project, module, user):
        """测试统计项目用例数"""
        service = TestCaseService()

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

        count = service.count_by_project(project.id)
        assert count == 2

        count_api = service.count_by_project(project.id, test_type='api')
        assert count_api == 1
