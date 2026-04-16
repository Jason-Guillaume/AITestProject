"""
Project Service 单元测试
"""
import pytest
from django.contrib.auth import get_user_model
from project.services.project_service import ProjectService
from project.models import TestProject
from common.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    DuplicateException
)

User = get_user_model()


@pytest.mark.django_db
class TestProjectService:
    """项目 Service 测试"""

    def test_create_project_success(self, user):
        """测试成功创建项目"""
        service = ProjectService()

        data = {
            'project_name': '新测试项目',
            'description': '项目描述',
            'project_status': 1
        }

        project = service.create_project(data, user)

        assert project.id is not None
        assert project.project_name == '新测试项目'
        assert project.creator == user

    def test_create_project_missing_name(self, user):
        """测试创建项目时缺少名称"""
        service = ProjectService()

        data = {
            'description': '项目描述',
            'project_status': 1
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_project(data, user)

        assert "项目名称不能为空" in str(exc_info.value)

    def test_create_project_invalid_parent(self, user):
        """测试创建项目时父项目不存在"""
        service = ProjectService()

        data = {
            'project_name': '测试项目',
            'parent_id': 99999
        }

        with pytest.raises(ResourceNotFoundException) as exc_info:
            service.create_project(data, user)

        assert "父项目不存在" in str(exc_info.value)

    def test_create_project_duplicate_name(self, project, user):
        """测试创建项目时名称重复"""
        service = ProjectService()

        data = {
            'project_name': project.project_name,
            'project_status': 1
        }

        with pytest.raises(DuplicateException) as exc_info:
            service.create_project(data, user)

        assert "已存在" in str(exc_info.value)

    def test_update_project_success(self, project, user):
        """测试成功更新项目"""
        service = ProjectService()

        data = {
            'project_name': '更新后的名称',
            'description': '更新后的描述'
        }

        updated = service.update_project(project.id, data, user)

        assert updated.project_name == '更新后的名称'
        assert updated.description == '更新后的描述'

    def test_update_project_not_found(self, user):
        """测试更新不存在的项目"""
        service = ProjectService()

        data = {'project_name': '新名称'}

        with pytest.raises(ResourceNotFoundException) as exc_info:
            service.update_project(99999, data, user)

        assert "项目不存在" in str(exc_info.value)

    def test_update_project_duplicate_name(self, user, project):
        """测试更新项目时名称重复"""
        service = ProjectService()

        # 创建另一个项目
        another_project = TestProject.objects.create(
            project_name='另一个项目',
            project_status=1,
            creator=user
        )

        data = {'project_name': project.project_name}

        with pytest.raises(DuplicateException) as exc_info:
            service.update_project(another_project.id, data, user)

        assert "已存在" in str(exc_info.value)

    def test_delete_project(self, project):
        """测试删除项目"""
        service = ProjectService()

        result = service.delete(project.id)

        assert result is True

        project.refresh_from_db()
        assert project.is_deleted is True

    def test_get_all(self, user):
        """测试获取所有项目"""
        service = ProjectService()

        TestProject.objects.create(
            project_name='项目1',
            project_status=1,
            creator=user
        )
        TestProject.objects.create(
            project_name='项目2',
            project_status=2,
            creator=user
        )

        projects = service.get_all()

        assert len(projects) == 2

    def test_get_root_projects(self, user, parent_project):
        """测试获取根项目"""
        service = ProjectService()

        # 创建子项目
        TestProject.objects.create(
            project_name='子项目',
            parent=parent_project,
            creator=user
        )

        root_projects = service.get_root_projects()

        assert len(root_projects) == 1
        assert root_projects[0].project_name == '父项目'

    def test_get_sub_projects(self, user, parent_project):
        """测试获取子项目"""
        service = ProjectService()

        # 创建子项目
        TestProject.objects.create(
            project_name='子项目1',
            parent=parent_project,
            creator=user
        )
        TestProject.objects.create(
            project_name='子项目2',
            parent=parent_project,
            creator=user
        )

        sub_projects = service.get_sub_projects(parent_project.id)

        assert len(sub_projects) == 2

    def test_get_with_members(self, project, user):
        """测试获取项目及其成员"""
        service = ProjectService()

        # 添加成员
        project.members.add(user)

        result = service.get_with_members(project.id)

        assert result is not None
        assert result.id == project.id
        assert result.members.count() == 1

    def test_get_with_members_not_found(self):
        """测试获取不存在的项目"""
        service = ProjectService()

        with pytest.raises(ResourceNotFoundException) as exc_info:
            service.get_with_members(99999)

        assert "项目不存在" in str(exc_info.value)

    def test_count_by_status(self, user):
        """测试统计项目数"""
        service = ProjectService()

        TestProject.objects.create(
            project_name='项目1',
            project_status=1,
            creator=user
        )
        TestProject.objects.create(
            project_name='项目2',
            project_status=2,
            creator=user
        )

        count = service.count_by_status()
        assert count == 2

        count_status = service.count_by_status(project_status=1)
        assert count_status == 1

    def test_add_member(self, project, user):
        """测试添加项目成员"""
        service = ProjectService()

        result = service.add_member(project.id, user.id)

        assert result.members.count() == 1
        assert user in result.members.all()

    def test_remove_member(self, project, user):
        """测试移除项目成员"""
        service = ProjectService()

        # 先添加成员
        project.members.add(user)

        result = service.remove_member(project.id, user.id)

        assert result.members.count() == 0
