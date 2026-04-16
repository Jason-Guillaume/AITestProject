"""
TestReportRepository 测试
"""
import pytest
from execution.repositories import TestReportRepository


@pytest.mark.django_db
class TestTestReportRepository:
    """测试报告 Repository 测试"""

    def setup_method(self):
        """初始化"""
        self.repository = TestReportRepository()

    def test_get_by_id(self, test_report):
        """测试根据ID获取测试报告"""
        result = self.repository.get_by_id(test_report.id)
        assert result is not None
        assert result.report_name == '测试报告1'

    def test_get_by_id_not_found(self):
        """测试获取不存在的测试报告"""
        result = self.repository.get_by_id(99999)
        assert result is None

    def test_get_all(self, test_report):
        """测试获取所有测试报告"""
        result = self.repository.get_all()
        assert result.count() >= 1
        assert test_report in result

    def test_get_all_with_filters(self, test_report):
        """测试带过滤条件获取测试报告"""
        result = self.repository.get_all({'plan_id': test_report.plan_id})
        assert result.count() >= 1
        assert test_report in result

    def test_get_all_with_project_filter(self, test_report):
        """测试按项目过滤"""
        result = self.repository.get_all({'project_id': test_report.project_id})
        assert result.count() >= 1
        assert test_report in result

    def test_get_all_with_create_method_filter(self, test_report):
        """测试按创建方式过滤"""
        result = self.repository.get_all({'create_method': 1})
        assert result.count() >= 1
        assert test_report in result

    def test_get_all_with_search(self, test_report):
        """测试搜索功能"""
        result = self.repository.get_all({'search': '测试报告'})
        assert result.count() >= 1
        assert test_report in result

    def test_get_by_plan(self, test_report):
        """测试根据测试计划获取报告"""
        result = self.repository.get_by_plan(test_report.plan_id)
        assert result.count() >= 1
        assert test_report in result

    def test_get_by_project(self, test_report):
        """测试根据项目获取报告"""
        result = self.repository.get_by_project(test_report.project_id)
        assert result.count() >= 1
        assert test_report in result

    def test_get_by_trace_id(self, test_report):
        """测试根据追踪ID获取报告"""
        result = self.repository.get_by_trace_id('trace-001')
        assert result is not None
        assert result.report_name == '测试报告1'

    def test_get_by_trace_id_not_found(self):
        """测试获取不存在的追踪ID"""
        result = self.repository.get_by_trace_id('not-exists')
        assert result is None

    def test_exists_by_name(self, test_report):
        """测试检查报告名称是否存在"""
        assert self.repository.exists_by_name('测试报告1') is True
        assert self.repository.exists_by_name('不存在的报告') is False

    def test_exists_by_name_exclude(self, test_report):
        """测试检查报告名称是否存在（排除指定ID）"""
        assert self.repository.exists_by_name('测试报告1', exclude_id=test_report.id) is False

    def test_count_by_plan(self, test_report):
        """测试统计测试计划的报告数量"""
        count = self.repository.count_by_plan(test_report.plan_id)
        assert count >= 1

    def test_create(self, test_plan, project, user):
        """测试创建测试报告"""
        from datetime import datetime
        data = {
            'report_name': '新测试报告',
            'plan': test_plan,
            'project': project,
            'environment': '测试环境',
            'create_method': 1,
            'trace_id': 'trace-002',
            'case_count': 50,
            'pass_rate': 80.0,
            'start_time': datetime.now(),
            'end_time': datetime.now(),
            'creator': user
        }
        result = self.repository.create(data)
        assert result.id is not None
        assert result.report_name == '新测试报告'

    def test_update(self, test_report, user):
        """测试更新测试报告"""
        result = self.repository.update(test_report.id, {
            'report_name': '更新后的报告',
            'updater': user
        })
        assert result.report_name == '更新后的报告'

    def test_delete(self, test_report):
        """测试删除测试报告"""
        self.repository.delete(test_report.id)
        result = self.repository.get_by_id(test_report.id)
        assert result is None
