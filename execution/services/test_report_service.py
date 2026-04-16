"""
TestReport Service
"""
from typing import Optional
from django.db import transaction
from common.services.base_service import BaseService
from common.exceptions import ValidationException, DuplicateException, ResourceNotFoundException
from execution.models import TestReport
from execution.repositories import TestReportRepository


class TestReportService(BaseService[TestReport]):
    """测试报告 Service"""

    def __init__(self):
        super().__init__(TestReportRepository())

    @transaction.atomic
    def create_test_report(self, data: dict, creator) -> TestReport:
        """创建测试报告"""
        # 验证必填字段
        if not data.get('report_name'):
            raise ValidationException("报告名称不能为空")

        if not data.get('plan_id'):
            raise ValidationException("测试计划不能为空")

        if not data.get('project_id'):
            raise ValidationException("项目不能为空")

        # 检查报告名称是否重复
        if self.repository.exists_by_name(data['report_name']):
            raise DuplicateException(f"报告名称 '{data['report_name']}' 已存在")

        # 创建测试报告
        from datetime import datetime
        test_report = self.repository.create({
            'report_name': data['report_name'],
            'plan_id': data['plan_id'],
            'project_id': data['project_id'],
            'environment': data.get('environment', ''),
            'create_method': data.get('create_method', 1),  # 默认手动创建
            'trace_id': data.get('trace_id', ''),
            'case_count': data.get('case_count', 0),
            'pass_rate': data.get('pass_rate', 0.0),
            'defect_count': data.get('defect_count', 0),
            'start_time': data.get('start_time', datetime.now()),
            'end_time': data.get('end_time', datetime.now()),
            'creator': creator,
        })

        return test_report

    @transaction.atomic
    def update_test_report(self, report_id: int, data: dict, updater) -> TestReport:
        """更新测试报告"""
        test_report = self.repository.get_by_id(report_id)
        if not test_report:
            raise ResourceNotFoundException(f"测试报告 ID {report_id} 不存在")

        # 检查报告名称是否重复
        if 'report_name' in data:
            if self.repository.exists_by_name(data['report_name'], exclude_id=report_id):
                raise DuplicateException(f"报告名称 '{data['report_name']}' 已存在")

        # 更新字段
        update_fields = {}
        for field in ['report_name', 'environment', 'case_count', 'pass_rate',
                      'defect_count']:
            if field in data:
                update_fields[field] = data[field]

        if update_fields:
            update_fields['updater'] = updater
            test_report = self.repository.update(report_id, update_fields)

        return test_report

    @transaction.atomic
    def update_statistics(self, report_id: int, statistics: dict, updater) -> TestReport:
        """更新测试报告统计数据"""
        test_report = self.repository.get_by_id(report_id)
        if not test_report:
            raise ResourceNotFoundException(f"测试报告 ID {report_id} 不存在")

        # 计算通过率
        case_count = statistics.get('case_count', 0)
        passed = statistics.get('passed_cases', 0)
        pass_rate = (passed / case_count * 100) if case_count > 0 else 0.0

        return self.repository.update(report_id, {
            'case_count': case_count,
            'pass_rate': round(pass_rate, 2),
            'defect_count': statistics.get('defect_count', 0),
            'updater': updater
        })
