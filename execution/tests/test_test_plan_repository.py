"""
TestPlanRepository 测试
"""
import pytest
from execution.repositories import TestPlanRepository


@pytest.mark.django_db
class TestTestPlanRepository:
    """测试计划 Repository 测试"""

    def setup_method(self):
        """初始化"""
        self.repository = TestPlanRepository()

    def test_get_by_id(self, test_plan):
        """测试根据ID获取测试计划"""
        result = self.repository.get_by_id(test_plan.id)
        assert result is not None
        assert result.plan_name == '测试计划1'

    def test_get_by_id_not_found(self):
        """测试获取不存在的测试计划"""
        result = self.repository.get_by_id(99999)
        assert result is None

    def test_get_all(self, test_plan):
        """测试获取所有测试计划"""
        result = self.repository.get_all()
        assert result.count() >= 1
        assert test_plan in result

    def test_get_all_with_filters(self, test_plan):
        """测试带过滤条件获取测试计划"""
        result = self.repository.get_all({'plan_status': 1})
        assert result.count() >= 1
        assert test_plan in result

    def test_get_all_with_version_filter(self, test_plan):
        """测试按版本过滤"""
        result = self.repository.get_all({'version_id': test_plan.version_id})
        assert result.count() >= 1
        assert test_plan in result

    def test_get_all_with_search(self, test_plan):
        """测试搜索功能"""
        result = self.repository.get_all({'search': '测试计划'})
        assert result.count() >= 1
        assert test_plan in result

    def test_get_by_version(self, test_plan):
        """测试根据版本获取测试计划"""
        result = self.repository.get_by_version(test_plan.version_id)
        assert result.count() >= 1
        assert test_plan in result

    def test_get_by_status(self, test_plan):
        """测试根据状态获取测试计划"""
        result = self.repository.get_by_status(1)
        assert result.count() >= 1
        assert test_plan in result

    def test_exists_by_name(self, test_plan):
        """测试检查计划名称是否存在"""
        assert self.repository.exists_by_name('测试计划1') is True
        assert self.repository.exists_by_name('不存在的计划') is False

    def test_exists_by_name_exclude(self, test_plan):
        """测试检查计划名称是否存在（排除指定ID）"""
        assert self.repository.exists_by_name('测试计划1', exclude_id=test_plan.id) is False

    def test_count_by_status(self, test_plan):
        """测试统计测试计划数量"""
        count = self.repository.count_by_status(1)
        assert count >= 1

    def test_count_by_status_all(self, test_plan):
        """测试统计所有测试计划数量"""
        count = self.repository.count_by_status()
        assert count >= 1

    def test_create(self, version, user):
        """测试创建测试计划"""
        data = {
            'plan_name': '新测试计划',
            'version': version,
            'iteration': 'Sprint 2',
            'environment': '生产环境',
            'plan_status': 1,
            'creator': user
        }
        result = self.repository.create(data)
        assert result.id is not None
        assert result.plan_name == '新测试计划'

    def test_update(self, test_plan, user):
        """测试更新测试计划"""
        result = self.repository.update(test_plan.id, {
            'plan_name': '更新后的计划',
            'updater': user
        })
        assert result.plan_name == '更新后的计划'

    def test_delete(self, test_plan):
        """测试删除测试计划"""
        self.repository.delete(test_plan.id)
        result = self.repository.get_by_id(test_plan.id)
        assert result is None
