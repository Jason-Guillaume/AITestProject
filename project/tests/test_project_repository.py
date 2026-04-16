"""
Project Repository 单元测试
"""
import pytest
from django.contrib.auth import get_user_model
from project.repositories.project_repository import ProjectRepository
from project.models import TestProject

User = get_user_model()


@pytest.mark.django_db
class TestProjectRepository:
    """项目 Repository 测试"""

    def test_get_by_id(self, project):
        """测试根据 ID 获取项目"""
        repo = ProjectRepository()
        result = repo.get_by_id(project.id)

        assert result is not None
        assert result.id == project.id
        assert result.project_name == '测试项目'

    def test_get_by_id_not_found(self):
        """测试获取不存在的项目"""
        repo = ProjectRepository()
        result = repo.get_by_id(99999)

        assert result is None

    def test_get_all(self, user):
        """测试获取所有项目"""
        repo = ProjectRepository()

        # 创建测试数据
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

        # 查询所有项目
        projects = repo.get_all()
        assert projects.count() == 2

        # 按状态过滤
        projects = repo.get_all(filters={'project_status': 1})
        assert projects.count() == 1
        assert projects.first().project_status == 1

    def test_get_all_with_search(self, user):
        """测试搜索项目"""
        repo = ProjectRepository()

        TestProject.objects.create(
            project_name='登录模块测试',
            description='测试登录功能',
            creator=user
        )
        TestProject.objects.create(
            project_name='注册模块测试',
            description='测试注册功能',
            creator=user
        )

        # 搜索关键词
        projects = repo.get_all(filters={'search': '登录'})
        assert projects.count() == 1
        assert projects.first().project_name == '登录模块测试'

    def test_get_root_projects(self, user, parent_project):
        """测试获取根项目"""
        repo = ProjectRepository()

        # 创建子项目
        TestProject.objects.create(
            project_name='子项目',
            parent=parent_project,
            creator=user
        )

        # 查询根项目
        root_projects = repo.get_root_projects()
        assert root_projects.count() == 1
        assert root_projects.first().project_name == '父项目'

    def test_get_sub_projects(self, user, parent_project):
        """测试获取子项目"""
        repo = ProjectRepository()

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

        # 查询子项目
        sub_projects = repo.get_sub_projects(parent_project.id)
        assert sub_projects.count() == 2

    def test_exists_by_name(self, project):
        """测试检查项目名称是否存在"""
        repo = ProjectRepository()

        # 存在的名称
        exists = repo.exists_by_name('测试项目')
        assert exists is True

        # 不存在的名称
        exists = repo.exists_by_name('不存在的项目')
        assert exists is False

        # 排除当前项目
        exists = repo.exists_by_name('测试项目', exclude_id=project.id)
        assert exists is False

    def test_create(self, user):
        """测试创建项目"""
        repo = ProjectRepository()

        data = {
            'project_name': '新测试项目',
            'description': '新项目描述',
            'project_status': 1
        }

        project = repo.create(data, creator=user)

        assert project.id is not None
        assert project.project_name == '新测试项目'
        assert project.creator == user

    def test_update(self, project):
        """测试更新项目"""
        repo = ProjectRepository()

        data = {
            'project_name': '更新后的名称',
            'description': '更新后的描述'
        }

        updated = repo.update(project.id, data)

        assert updated is not None
        assert updated.project_name == '更新后的名称'
        assert updated.description == '更新后的描述'

    def test_delete_soft(self, project):
        """测试软删除项目"""
        repo = ProjectRepository()

        result = repo.delete(project.id, soft=True)

        assert result is True

        # 验证软删除
        project.refresh_from_db()
        assert project.is_deleted is True

    def test_count_by_status(self, user):
        """测试统计项目数"""
        repo = ProjectRepository()

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

        # 统计所有项目
        count = repo.count_by_status()
        assert count == 2

        # 按状态统计
        count = repo.count_by_status(project_status=1)
        assert count == 1

    def test_get_with_members(self, project, user):
        """测试获取项目及其成员"""
        repo = ProjectRepository()

        # 添加成员
        project.members.add(user)

        result = repo.get_with_members(project.id)

        assert result is not None
        assert result.id == project.id
        assert result.members.count() == 1
