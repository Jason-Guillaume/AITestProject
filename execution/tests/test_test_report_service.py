"""
TestReportService 测试
"""
import pytest
from execution.services import TestReportService
from common.exceptions import ValidationException, DuplicateException, ResourceNotFoundException


@pytest.mark.django_db
class TestTestReportService:
    """测试报告 Service 测试"""

    def setup_method(self):
        """初始化"""
        self.service = TestReportService()

    def test_create_test_report_success(self, test_plan, project, user):
        """测试成功创建测试报告"""
        from datetime import datetime
        data = {
            'report_name': '新测试报告',
            'plan_id': test_plan.id,
            'project_id': project.id,
            'environment': '测试环境',
            'create_method': 1,
            'trace_id': 'trace-new',
            'case_count': 100,
            'pass_rate': 80.0,
            'start_time': datetime.now(),
            'end_time': datetime.now()
        }
        result = self.service.create_test_report(data, user)
        assert result.id is not None
        assert result.report_name == '新测试报告'
        assert result.creator == user

    def test_create_test_report_missing_name(self, test_plan, project, user):
        """测试创建测试报告缺少名称"""
        data = {
            'plan_id': test_plan.id,
            'project_id': project.id
        }
        with pytest.raises(ValidationException, match="报告名称不能为空"):
            self.service.create_test_report(data, user)

    def test_create_test_report_missing_plan(self, project, user):
        """测试创建测试报告缺少测试计划"""
        data = {
            'report_name': '测试报告',
            'project_id': project.id
        }
        with pytest.raises(ValidationException, match="测试计划不能为空"):
            self.service.create_test_report(data, user)

    def test_create_test_report_missing_project(self, test_plan, user):
        """测试创建测试报告缺少项目"""
        data = {
            'report_name': '测试报告',
            'plan_id': test_plan.id
        }
        with pytest.raises(ValidationException, match="项目不能为空"):
            self.service.create_test_report(data, user)

    def test_create_test_report_duplicate_name(self, test_report, test_plan, project, user):
        """测试创建重复名称的测试报告"""
        data = {
            'report_name': test_report.report_name,
            'plan_id': test_plan.id,
            'project_id': project.id
        }
        with pytest.raises(DuplicateException, match="已存在"):
            self.service.create_test_report(data, user)

    def test_update_test_report_success(self, test_report, user):
        """测试成功更新测试报告"""
        data = {
            'report_name': '更新后的报告',
            'environment': '生产环境',
            'case_count': 150
        }
        result = self.service.update_test_report(test_report.id, data, user)
        assert result.report_name == '更新后的报告'
        assert result.environment == '生产环境'
        assert result.case_count == 150

    def test_update_test_report_not_found(self, user):
        """测试更新不存在的测试报告"""
        with pytest.raises(ResourceNotFoundException, match="不存在"):
            self.service.update_test_report(99999, {'report_name': '测试'}, user)

    def test_update_test_report_duplicate_name(self, test_report, test_plan, project, user):
        """测试更新为重复的报告名称"""
        # 创建另一个测试报告
        other_report = self.service.create_test_report({
            'report_name': '另一个报告',
            'plan_id': test_plan.id,
            'project_id': project.id
        }, user)

        # 尝试更新为已存在的名称
        with pytest.raises(DuplicateException, match="已存在"):
            self.service.update_test_report(other_report.id, {'report_name': test_report.report_name}, user)

    def test_update_statistics_success(self, test_report, user):
        """测试成功更新测试报告统计数据"""
        statistics = {
            'case_count': 200,
            'passed_cases': 180,
            'defect_count': 15
        }
        result = self.service.update_statistics(test_report.id, statistics, user)
        assert result.case_count == 200
        assert result.pass_rate == 90.0  # 180/200 * 100

    def test_update_statistics_calculate_pass_rate(self, test_report, user):
        """测试更新统计数据时自动计算通过率"""
        statistics = {
            'case_count': 50,
            'passed_cases': 40
        }
        result = self.service.update_statistics(test_report.id, statistics, user)
        assert result.pass_rate == 80.0

    def test_update_statistics_zero_total(self, test_report, user):
        """测试总用例数为0时的通过率计算"""
        statistics = {
            'case_count': 0,
            'passed_cases': 0
        }
        result = self.service.update_statistics(test_report.id, statistics, user)
        assert result.pass_rate == 0.0

    def test_update_statistics_not_found(self, user):
        """测试更新不存在的测试报告统计数据"""
        with pytest.raises(ResourceNotFoundException, match="不存在"):
            self.service.update_statistics(99999, {'total_cases': 100}, user)
