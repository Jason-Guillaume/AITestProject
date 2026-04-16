"""
GeneratedTestArtifact Service
"""
from typing import Optional
from django.db import transaction
from common.services.base_service import BaseService
from common.exceptions import ValidationException, ResourceNotFoundException
from assistant.models import GeneratedTestArtifact
from assistant.repositories.generated_test_artifact_repository import GeneratedTestArtifactRepository


class GeneratedTestArtifactService(BaseService[GeneratedTestArtifact]):
    """生成测试资产 Service"""

    def __init__(self):
        super().__init__(GeneratedTestArtifactRepository())

    @transaction.atomic
    def create_artifact(self, data: dict, creator) -> GeneratedTestArtifact:
        """创建测试资产"""
        if not data.get('artifact_type'):
            raise ValidationException("资产类型不能为空")

        artifact_type = data['artifact_type']
        if artifact_type not in dict(GeneratedTestArtifact.TYPE_CHOICES):
            raise ValidationException(f"无效的资产类型: {artifact_type}")

        artifact_data = {
            'artifact_type': artifact_type,
            'title': data.get('title', ''),
            'content': data.get('content', {}),
            'citations': data.get('citations', []),
            'model_used': data.get('model_used', ''),
            'source_question': data.get('source_question', ''),
        }

        if 'org_id' in data:
            artifact_data['org_id'] = data['org_id']

        if 'project_id' in data:
            artifact_data['project_id'] = data['project_id']

        if 'module_id' in data:
            artifact_data['module_id'] = data['module_id']

        if 'source_document_id' in data:
            artifact_data['source_document_id'] = data['source_document_id']

        return self.repository.create(artifact_data, creator=creator)

    @transaction.atomic
    def update_artifact(self, artifact_id: int, data: dict, updater) -> GeneratedTestArtifact:
        """更新测试资产"""
        artifact = self.repository.get_by_id(artifact_id)
        if not artifact:
            raise ResourceNotFoundException("测试资产不存在")

        if 'artifact_type' in data:
            if data['artifact_type'] not in dict(GeneratedTestArtifact.TYPE_CHOICES):
                raise ValidationException(f"无效的资产类型: {data['artifact_type']}")

        return self.repository.update(artifact_id, data)

    def get_by_project(self, project_id: int):
        """根据项目获取测试资产"""
        return self.repository.get_by_project(project_id)

    def get_by_module(self, module_id: int):
        """根据模块获取测试资产"""
        return self.repository.get_by_module(module_id)

    def get_by_artifact_type(self, artifact_type: str):
        """根据资产类型获取"""
        return self.repository.get_by_artifact_type(artifact_type)

    def get_by_source_document(self, source_document_id: int):
        """根据来源文档获取测试资产"""
        return self.repository.get_by_source_document(source_document_id)

    def count_by_type(self, artifact_type: Optional[str] = None) -> int:
        """统计测试资产数量"""
        return self.repository.count_by_type(artifact_type)

    def count_by_project(self, project_id: int) -> int:
        """统计项目的测试资产数量"""
        return self.repository.count_by_project(project_id)
