"""
TestPlan Service
"""
from typing import Optional
from django.db import transaction
from django.contrib.auth import get_user_model
from common.services.base_service import BaseService
from common.exceptions import ValidationException, DuplicateException, ResourceNotFoundException
from execution.models import TestPlan
from execution.repositories import TestPlanRepository

User = get_user_model()


class TestPlanService(BaseService[TestPlan]):
    """测试计划 Service"""

    def __init__(self):
        super().__init__(TestPlanRepository())

    @transaction.atomic
    def create_test_plan(self, data: dict, creator) -> TestPlan:
        """创建测试计划"""
        # 验证必填字段
        if not data.get('plan_name'):
            raise ValidationException("计划名称不能为空")

        if not data.get('version_id'):
            raise ValidationException("版本不能为空")

        if not data.get('environment'):
            raise ValidationException("测试环境不能为空")

        # 检查计划名称是否重复
        if self.repository.exists_by_name(data['plan_name']):
            raise DuplicateException(f"计划名称 '{data['plan_name']}' 已存在")

        # 创建测试计划
        test_plan = self.repository.create({
            'plan_name': data['plan_name'],
            'version_id': data['version_id'],
            'iteration': data.get('iteration', ''),
            'environment': data['environment'],
            'plan_status': data.get('plan_status', 1),  # 默认未开始
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date'),
            'creator': creator,
        })

        # 添加测试人员
        if 'tester_ids' in data and data['tester_ids']:
            testers = User.objects.filter(id__in=data['tester_ids'])
            test_plan.testers.set(testers)

        return test_plan

    @transaction.atomic
    def update_test_plan(self, plan_id: int, data: dict, updater) -> TestPlan:
        """更新测试计划"""
        test_plan = self.repository.get_by_id(plan_id)
        if not test_plan:
            raise ResourceNotFoundException(f"测试计划 ID {plan_id} 不存在")

        # 检查计划名称是否重复
        if 'plan_name' in data:
            if self.repository.exists_by_name(data['plan_name'], exclude_id=plan_id):
                raise DuplicateException(f"计划名称 '{data['plan_name']}' 已存在")

        # 更新字段
        update_fields = {}
        for field in ['plan_name', 'version_id', 'iteration', 'environment',
                      'plan_status', 'start_date', 'end_date']:
            if field in data:
                update_fields[field] = data[field]

        if update_fields:
            update_fields['updater'] = updater
            test_plan = self.repository.update(plan_id, update_fields)

        # 更新测试人员
        if 'tester_ids' in data:
            testers = User.objects.filter(id__in=data['tester_ids'])
            test_plan.testers.set(testers)

        return test_plan

    @transaction.atomic
    def update_status(self, plan_id: int, plan_status: int, updater) -> TestPlan:
        """更新测试计划状态"""
        test_plan = self.repository.get_by_id(plan_id)
        if not test_plan:
            raise ResourceNotFoundException(f"测试计划 ID {plan_id} 不存在")

        if plan_status not in [1, 2, 3, 4]:  # 1-未开始 2-进行中 3-已完成 4-已取消
            raise ValidationException("无效的计划状态")

        return self.repository.update(plan_id, {
            'plan_status': plan_status,
            'updater': updater
        })

    @transaction.atomic
    def add_tester(self, plan_id: int, user_id: int) -> TestPlan:
        """添加测试人员"""
        test_plan = self.repository.get_by_id(plan_id)
        if not test_plan:
            raise ResourceNotFoundException(f"测试计划 ID {plan_id} 不存在")

        try:
            user = User.objects.get(id=user_id, is_deleted=False)
        except User.DoesNotExist:
            raise ResourceNotFoundException(f"用户 ID {user_id} 不存在")

        test_plan.testers.add(user)
        return test_plan

    @transaction.atomic
    def remove_tester(self, plan_id: int, user_id: int) -> TestPlan:
        """移除测试人员"""
        test_plan = self.repository.get_by_id(plan_id)
        if not test_plan:
            raise ResourceNotFoundException(f"测试计划 ID {plan_id} 不存在")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ResourceNotFoundException(f"用户 ID {user_id} 不存在")

        test_plan.testers.remove(user)
        return test_plan
