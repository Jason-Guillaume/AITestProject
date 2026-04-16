"""
TestPlanService 测试
"""
import pytest
from django.contrib.auth import get_user_model
from execution.services import TestPlanService
from common.exceptions import ValidationException, DuplicateException, ResourceNotFoundException

User = get_user_model()


@pytest.mark.django_db
class TestTestPlanService:
    """测试计划 Service 测试"""

    def setup_method(self):
        """初始化"""
        self.service = TestPlanService()

    def test_create_test_plan_success(self, version, user):
        """测试成功创建测试计划"""
        data = {
            'plan_name': '新测试计划',
            'version_id': version.id,
            'iteration': 'Sprint 1',
            'environment': '测试环境',
            'plan_status': 1,
            'description': '测试描述'
        }
        result = self.service.create_test_plan(data, user)
        assert result.id is not None
        assert result.plan_name == '新测试计划'
        assert result.creator == user

    def test_create_test_plan_with_testers(self, version, user):
        """测试创建测试计划并添加测试人员"""
        data = {
            'plan_name': '带测试人员的计划',
            'version_id': version.id,
            'environment': '测试环境',
            'tester_ids': [user.id]
        }
        result = self.service.create_test_plan(data, user)
        assert result.testers.count() == 1
        assert user in result.testers.all()

    def test_create_test_plan_missing_name(self, version, user):
        """测试创建测试计划缺少名称"""
        data = {
            'version_id': version.id,
            'environment': '测试环境'
        }
        with pytest.raises(ValidationException, match="计划名称不能为空"):
            self.service.create_test_plan(data, user)

    def test_create_test_plan_missing_version(self, user):
        """测试创建测试计划缺少版本"""
        data = {
            'plan_name': '测试计划',
            'environment': '测试环境'
        }
        with pytest.raises(ValidationException, match="版本不能为空"):
            self.service.create_test_plan(data, user)

    def test_create_test_plan_missing_environment(self, version, user):
        """测试创建测试计划缺少环境"""
        data = {
            'plan_name': '测试计划',
            'version_id': version.id
        }
        with pytest.raises(ValidationException, match="测试环境不能为空"):
            self.service.create_test_plan(data, user)

    def test_create_test_plan_duplicate_name(self, test_plan, version, user):
        """测试创建重复名称的测试计划"""
        data = {
            'plan_name': test_plan.plan_name,
            'version_id': version.id,
            'environment': '测试环境'
        }
        with pytest.raises(DuplicateException, match="已存在"):
            self.service.create_test_plan(data, user)

    def test_update_test_plan_success(self, test_plan, user):
        """测试成功更新测试计划"""
        data = {
            'plan_name': '更新后的计划',
            'iteration': 'Sprint 2',
            'plan_status': 2
        }
        result = self.service.update_test_plan(test_plan.id, data, user)
        assert result.plan_name == '更新后的计划'
        assert result.iteration == 'Sprint 2'
        assert result.plan_status == 2

    def test_update_test_plan_not_found(self, user):
        """测试更新不存在的测试计划"""
        with pytest.raises(ResourceNotFoundException, match="不存在"):
            self.service.update_test_plan(99999, {'plan_name': '测试'}, user)

    def test_update_test_plan_duplicate_name(self, test_plan, version, user):
        """测试更新为重复的计划名称"""
        # 创建另一个测试计划
        other_plan = self.service.create_test_plan({
            'plan_name': '另一个计划',
            'version_id': version.id,
            'environment': '测试环境'
        }, user)

        # 尝试更新为已存在的名称
        with pytest.raises(DuplicateException, match="已存在"):
            self.service.update_test_plan(other_plan.id, {'plan_name': test_plan.plan_name}, user)

    def test_update_test_plan_with_testers(self, test_plan, user):
        """测试更新测试计划的测试人员"""
        new_user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='pass123'
        )
        data = {'tester_ids': [user.id, new_user.id]}
        result = self.service.update_test_plan(test_plan.id, data, user)
        assert result.testers.count() == 2

    def test_update_status_success(self, test_plan, user):
        """测试成功更新测试计划状态"""
        result = self.service.update_status(test_plan.id, 2, user)
        assert result.plan_status == 2

    def test_update_status_invalid(self, test_plan, user):
        """测试更新为无效的状态"""
        with pytest.raises(ValidationException, match="无效的计划状态"):
            self.service.update_status(test_plan.id, 99, user)

    def test_update_status_not_found(self, user):
        """测试更新不存在的测试计划状态"""
        with pytest.raises(ResourceNotFoundException, match="不存在"):
            self.service.update_status(99999, 2, user)

    def test_add_tester_success(self, test_plan, user):
        """测试成功添加测试人员"""
        new_user = User.objects.create_user(
            username='tester2',
            email='tester2@example.com',
            password='pass123'
        )
        result = self.service.add_tester(test_plan.id, new_user.id)
        assert new_user in result.testers.all()

    def test_add_tester_plan_not_found(self, user):
        """测试添加测试人员到不存在的计划"""
        with pytest.raises(ResourceNotFoundException, match="测试计划.*不存在"):
            self.service.add_tester(99999, user.id)

    def test_add_tester_user_not_found(self, test_plan):
        """测试添加不存在的用户"""
        with pytest.raises(ResourceNotFoundException, match="用户.*不存在"):
            self.service.add_tester(test_plan.id, 99999)

    def test_remove_tester_success(self, test_plan, user):
        """测试成功移除测试人员"""
        result = self.service.remove_tester(test_plan.id, user.id)
        assert user not in result.testers.all()

    def test_remove_tester_plan_not_found(self, user):
        """测试从不存在的计划移除测试人员"""
        with pytest.raises(ResourceNotFoundException, match="测试计划.*不存在"):
            self.service.remove_tester(99999, user.id)

    def test_remove_tester_user_not_found(self, test_plan):
        """测试移除不存在的用户"""
        with pytest.raises(ResourceNotFoundException, match="用户.*不存在"):
            self.service.remove_tester(test_plan.id, 99999)
