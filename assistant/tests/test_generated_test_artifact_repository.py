"""
GeneratedTestArtifact Repository 单元测试
"""
import pytest
from django.contrib.auth import get_user_model
from assistant.repositories.generated_test_artifact_repository import GeneratedTestArtifactRepository
from assistant.models import GeneratedTestArtifact

User = get_user_model()


@pytest.mark.django_db
class TestGeneratedTestArtifactRepository:
    """生成测试资产 Repository 测试"""

    def test_get_by_id(self, generated_artifact):
        """测试根据 ID 获取资产"""
        repo = GeneratedTestArtifactRepository()
        result = repo.get_by_id(generated_artifact.id)

        assert result is not None
        assert result.id == generated_artifact.id
        assert result.title == '测试用例草稿'

    def test_get_by_id_not_found(self):
        """测试获取不存在的资产"""
        repo = GeneratedTestArtifactRepository()
        result = repo.get_by_id(99999)

        assert result is None

    def test_get_all(self, user, project, module, knowledge_document):
        """测试获取所有资产"""
        repo = GeneratedTestArtifactRepository()

        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_CASE_DRAFT,
            title='资产1',
            project=project,
            module=module,
            creator=user
        )
        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_TEST_PLAN,
            title='资产2',
            project=project,
            module=module,
            creator=user
        )

        artifacts = repo.get_all()
        assert artifacts.count() == 2

    def test_get_all_with_filters(self, user, project, module):
        """测试带过滤条件获取资产"""
        repo = GeneratedTestArtifactRepository()

        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_CASE_DRAFT,
            title='资产1',
            project=project,
            module=module,
            creator=user
        )
        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_TEST_PLAN,
            title='资产2',
            project=project,
            module=module,
            creator=user
        )

        artifacts = repo.get_all(filters={'artifact_type': GeneratedTestArtifact.TYPE_CASE_DRAFT})
        assert artifacts.count() == 1
        assert artifacts.first().artifact_type == GeneratedTestArtifact.TYPE_CASE_DRAFT

    def test_get_all_with_search(self, user, project, module):
        """测试搜索资产"""
        repo = GeneratedTestArtifactRepository()

        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_CASE_DRAFT,
            title='登录用例',
            project=project,
            module=module,
            creator=user
        )
        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_CASE_DRAFT,
            title='注册用例',
            project=project,
            module=module,
            creator=user
        )

        artifacts = repo.get_all(filters={'search': '登录'})
        assert artifacts.count() == 1
        assert artifacts.first().title == '登录用例'

    def test_get_by_project(self, user, project, module):
        """测试根据项目获取资产"""
        repo = GeneratedTestArtifactRepository()

        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_CASE_DRAFT,
            title='资产1',
            project=project,
            module=module,
            creator=user
        )
        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_TEST_PLAN,
            title='资产2',
            project=project,
            module=module,
            creator=user
        )

        artifacts = repo.get_by_project(project.id)
        assert artifacts.count() == 2

    def test_get_by_module(self, user, project, module):
        """测试根据模块获取资产"""
        repo = GeneratedTestArtifactRepository()

        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_CASE_DRAFT,
            title='资产1',
            project=project,
            module=module,
            creator=user
        )

        artifacts = repo.get_by_module(module.id)
        assert artifacts.count() == 1

    def test_get_by_artifact_type(self, user, project, module):
        """测试根据资产类型获取"""
        repo = GeneratedTestArtifactRepository()

        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_CASE_DRAFT,
            title='资产1',
            project=project,
            module=module,
            creator=user
        )
        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_CASE_DRAFT,
            title='资产2',
            project=project,
            module=module,
            creator=user
        )

        artifacts = repo.get_by_artifact_type(GeneratedTestArtifact.TYPE_CASE_DRAFT)
        assert artifacts.count() == 2

    def test_get_by_source_document(self, user, project, module, knowledge_document):
        """测试根据来源文档获取资产"""
        repo = GeneratedTestArtifactRepository()

        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_CASE_DRAFT,
            title='资产1',
            project=project,
            module=module,
            source_document=knowledge_document,
            creator=user
        )

        artifacts = repo.get_by_source_document(knowledge_document.id)
        assert artifacts.count() == 1

    def test_create(self, user, project, module):
        """测试创建资产"""
        repo = GeneratedTestArtifactRepository()

        data = {
            'artifact_type': GeneratedTestArtifact.TYPE_CASE_DRAFT,
            'title': '新资产',
            'content': {'cases': []},
            'project': project,
            'module': module
        }

        artifact = repo.create(data, creator=user)

        assert artifact.id is not None
        assert artifact.title == '新资产'
        assert artifact.creator == user

    def test_update(self, generated_artifact):
        """测试更新资产"""
        repo = GeneratedTestArtifactRepository()

        data = {
            'title': '更新后的标题',
            'content': {'cases': [{'name': '新用例'}]}
        }

        updated = repo.update(generated_artifact.id, data)

        assert updated is not None
        assert updated.title == '更新后的标题'

    def test_delete_soft(self, generated_artifact):
        """测试软删除资产"""
        repo = GeneratedTestArtifactRepository()

        result = repo.delete(generated_artifact.id, soft=True)

        assert result is True

        generated_artifact.refresh_from_db()
        assert generated_artifact.is_deleted is True

    def test_count_by_type(self, user, project, module):
        """测试统计资产数量"""
        repo = GeneratedTestArtifactRepository()

        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_CASE_DRAFT,
            title='资产1',
            project=project,
            module=module,
            creator=user
        )
        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_TEST_PLAN,
            title='资产2',
            project=project,
            module=module,
            creator=user
        )

        count = repo.count_by_type()
        assert count == 2

        count = repo.count_by_type(GeneratedTestArtifact.TYPE_CASE_DRAFT)
        assert count == 1

    def test_count_by_project(self, user, project, module):
        """测试统计项目的资产数量"""
        repo = GeneratedTestArtifactRepository()

        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_CASE_DRAFT,
            title='资产1',
            project=project,
            module=module,
            creator=user
        )
        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_TEST_PLAN,
            title='资产2',
            project=project,
            module=module,
            creator=user
        )

        count = repo.count_by_project(project.id)
        assert count == 2
