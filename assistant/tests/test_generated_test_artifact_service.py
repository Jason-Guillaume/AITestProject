"""
GeneratedTestArtifact Service 单元测试
"""
import pytest
from django.contrib.auth import get_user_model
from assistant.services.generated_test_artifact_service import GeneratedTestArtifactService
from assistant.models import GeneratedTestArtifact
from common.exceptions import (
    ResourceNotFoundException,
    ValidationException
)

User = get_user_model()


@pytest.mark.django_db
class TestGeneratedTestArtifactService:
    """生成测试资产 Service 测试"""

    def test_create_artifact_success(self, user, project, module):
        """测试成功创建资产"""
        service = GeneratedTestArtifactService()

        data = {
            'artifact_type': GeneratedTestArtifact.TYPE_CASE_DRAFT,
            'title': '新资产',
            'content': {'cases': [{'name': '测试用例'}]},
            'project_id': project.id,
            'module_id': module.id
        }

        artifact = service.create_artifact(data, user)

        assert artifact.id is not None
        assert artifact.title == '新资产'
        assert artifact.creator == user

    def test_create_artifact_missing_type(self, user):
        """测试创建资产时缺少类型"""
        service = GeneratedTestArtifactService()

        data = {
            'title': '新资产'
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_artifact(data, user)

        assert "资产类型不能为空" in str(exc_info.value)

    def test_create_artifact_invalid_type(self, user):
        """测试创建资产时类型无效"""
        service = GeneratedTestArtifactService()

        data = {
            'artifact_type': 'invalid_type',
            'title': '新资产'
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_artifact(data, user)

        assert "无效的资产类型" in str(exc_info.value)

    def test_update_artifact_success(self, generated_artifact, user):
        """测试成功更新资产"""
        service = GeneratedTestArtifactService()

        data = {
            'title': '更新后的标题',
            'content': {'cases': [{'name': '新用例'}]}
        }

        updated = service.update_artifact(generated_artifact.id, data, user)

        assert updated.title == '更新后的标题'

    def test_update_artifact_not_found(self, user):
        """测试更新不存在的资产"""
        service = GeneratedTestArtifactService()

        data = {'title': '新标题'}

        with pytest.raises(ResourceNotFoundException) as exc_info:
            service.update_artifact(99999, data, user)

        assert "测试资产不存在" in str(exc_info.value)

    def test_update_artifact_invalid_type(self, generated_artifact, user):
        """测试更新资产时类型无效"""
        service = GeneratedTestArtifactService()

        data = {'artifact_type': 'invalid_type'}

        with pytest.raises(ValidationException) as exc_info:
            service.update_artifact(generated_artifact.id, data, user)

        assert "无效的资产类型" in str(exc_info.value)

    def test_delete_artifact(self, generated_artifact):
        """测试删除资产"""
        service = GeneratedTestArtifactService()

        result = service.delete(generated_artifact.id)

        assert result is True

        generated_artifact.refresh_from_db()
        assert generated_artifact.is_deleted is True

    def test_get_all(self, user, project, module):
        """测试获取所有资产"""
        service = GeneratedTestArtifactService()

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

        artifacts = service.get_all()

        assert len(artifacts) == 2

    def test_get_by_project(self, user, project, module):
        """测试根据项目获取资产"""
        service = GeneratedTestArtifactService()

        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_CASE_DRAFT,
            title='资产1',
            project=project,
            module=module,
            creator=user
        )

        artifacts = service.get_by_project(project.id)

        assert artifacts.count() == 1

    def test_get_by_module(self, user, project, module):
        """测试根据模块获取资产"""
        service = GeneratedTestArtifactService()

        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_CASE_DRAFT,
            title='资产1',
            project=project,
            module=module,
            creator=user
        )

        artifacts = service.get_by_module(module.id)

        assert artifacts.count() == 1

    def test_get_by_artifact_type(self, user, project, module):
        """测试根据资产类型获取"""
        service = GeneratedTestArtifactService()

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

        artifacts = service.get_by_artifact_type(GeneratedTestArtifact.TYPE_CASE_DRAFT)

        assert artifacts.count() == 1

    def test_get_by_source_document(self, user, project, module, knowledge_document):
        """测试根据来源文档获取资产"""
        service = GeneratedTestArtifactService()

        GeneratedTestArtifact.objects.create(
            artifact_type=GeneratedTestArtifact.TYPE_CASE_DRAFT,
            title='资产1',
            project=project,
            module=module,
            source_document=knowledge_document,
            creator=user
        )

        artifacts = service.get_by_source_document(knowledge_document.id)

        assert artifacts.count() == 1

    def test_count_by_type(self, user, project, module):
        """测试统计资产数量"""
        service = GeneratedTestArtifactService()

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

        count = service.count_by_type()
        assert count == 2

        count = service.count_by_type(GeneratedTestArtifact.TYPE_CASE_DRAFT)
        assert count == 1

    def test_count_by_project(self, user, project, module):
        """测试统计项目的资产数量"""
        service = GeneratedTestArtifactService()

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

        count = service.count_by_project(project.id)
        assert count == 2
