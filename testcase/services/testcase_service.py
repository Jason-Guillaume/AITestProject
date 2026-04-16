"""
测试用例 Service
提供测试用例的业务逻辑
"""
from typing import List, Dict, Optional
from django.db import transaction
from common.services.base_service import BaseService
from common.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    DuplicateException
)
from testcase.repositories.testcase_repository import TestCaseRepository
from testcase.repositories.module_repository import ModuleRepository
from testcase.models import TestCase


class TestCaseService(BaseService[TestCase]):
    """
    测试用例 Service

    提供测试用例的业务逻辑，包括创建、更新、删除、查询等操作

    Example:
        >>> service = TestCaseService()
        >>> testcase = service.create_testcase(data, user)
        >>> testcases = service.get_by_project(project_id=1)
    """

    def __init__(self):
        """初始化 TestCaseService"""
        super().__init__(TestCaseRepository())
        self.module_repo = ModuleRepository()

    def get_by_project(
        self,
        project_id: int,
        filters: Optional[Dict] = None
    ) -> List[TestCase]:
        """
        获取项目下的用例

        Args:
            project_id: 项目 ID
            filters: 过滤条件

        Returns:
            用例列表
        """
        return list(self.repository.get_by_project(project_id, filters))

    def get_by_module(self, module_id: int) -> List[TestCase]:
        """
        获取模块下的用例

        Args:
            module_id: 模块 ID

        Returns:
            用例列表
        """
        return list(self.repository.get_by_module(module_id))

    def get_with_steps(self, testcase_id: int) -> Optional[TestCase]:
        """
        获取用例及其步骤

        Args:
            testcase_id: 用例 ID

        Returns:
            用例对象（包含步骤）

        Raises:
            ResourceNotFoundException: 用例不存在
        """
        testcase = self.repository.get_with_steps(testcase_id)
        if not testcase:
            raise ResourceNotFoundException("测试用例不存在")
        return testcase

    @transaction.atomic
    def create_testcase(self, data: Dict, user) -> TestCase:
        """
        创建测试用例

        Args:
            data: 用例数据
            user: 当前用户

        Returns:
            创建的用例对象

        Raises:
            ValidationException: 数据验证失败
            ResourceNotFoundException: 模块不存在
            DuplicateException: 用例名称重复
        """
        # 验证必填字段
        if not data.get('case_name'):
            raise ValidationException("用例名称不能为空")

        if not data.get('project_id') and not data.get('module_id'):
            raise ValidationException("项目 ID 或模块 ID 不能为空")

        # 验证模块是否存在
        if 'module_id' in data and data['module_id']:
            module = self.module_repo.get_by_id(data['module_id'])
            if not module:
                raise ResourceNotFoundException("模块不存在")
            project_id = module.project_id
        else:
            project_id = data.get('project_id')

        # 检查用例名称是否重复
        if self.repository.exists_by_name(project_id, data['case_name']):
            raise DuplicateException(f"用例名称 '{data['case_name']}' 已存在")

        # 移除 project_id，因为 TestCase 模型没有这个字段
        create_data = {k: v for k, v in data.items() if k != 'project_id'}

        # 创建用例
        testcase = self.repository.create(create_data, creator=user)

        return testcase

    @transaction.atomic
    def batch_create_testcases(
        self,
        testcases_data: List[Dict],
        user
    ) -> Dict:
        """
        批量创建测试用例

        Args:
            testcases_data: 用例数据列表
            user: 当前用户

        Returns:
            包含创建结果的字典
        """
        created_cases = []
        errors = []

        for idx, data in enumerate(testcases_data):
            try:
                testcase = self.create_testcase(data, user)
                created_cases.append(testcase)
            except Exception as e:
                errors.append({
                    "index": idx,
                    "data": data,
                    "error": str(e)
                })

        return {
            "success_count": len(created_cases),
            "error_count": len(errors),
            "created_cases": created_cases,
            "errors": errors
        }

    @transaction.atomic
    def update_testcase(
        self,
        testcase_id: int,
        data: Dict,
        user
    ) -> TestCase:
        """
        更新测试用例

        Args:
            testcase_id: 用例 ID
            data: 更新的数据
            user: 当前用户

        Returns:
            更新后的用例对象

        Raises:
            ResourceNotFoundException: 用例不存在
        """
        testcase = self.repository.get_by_id(testcase_id)
        if not testcase:
            raise ResourceNotFoundException("测试用例不存在")

        if 'module_id' in data and data['module_id']:
            module = self.module_repo.get_by_id(data['module_id'])
            if not module:
                raise ResourceNotFoundException("模块不存在")

        if 'case_name' in data and data['case_name'] != testcase.case_name:
            # 获取项目 ID
            project_id = testcase.module.project_id if testcase.module else None
            if project_id and self.repository.exists_by_name(
                project_id,
                data['case_name'],
                exclude_id=testcase_id
            ):
                raise DuplicateException(f"用例名称 '{data['case_name']}' 已存在")

        updated_testcase = self.repository.update(testcase_id, data)
        return updated_testcase

    def count_by_project(self, project_id: int, test_type: Optional[str] = None) -> int:
        """统计项目用例数"""
        return self.repository.count_by_project(project_id, test_type)

    def count_by_module(self, module_id: int) -> int:
        """统计模块用例数"""
        return self.repository.count_by_module(module_id)
