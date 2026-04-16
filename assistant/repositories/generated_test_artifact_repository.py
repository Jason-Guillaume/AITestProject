"""
GeneratedTestArtifact Repository
"""
from typing import Optional
from django.db.models import QuerySet, Q
from common.repositories.base_repository import BaseRepository
from assistant.models import GeneratedTestArtifact


class GeneratedTestArtifactRepository(BaseRepository[GeneratedTestArtifact]):
    """生成测试资产 Repository"""

    def __init__(self):
        super().__init__(GeneratedTestArtifact)

    def get_all(self, filters: Optional[dict] = None) -> QuerySet[GeneratedTestArtifact]:
        """获取所有测试资产"""
        queryset = self.model.objects.filter(is_deleted=False).select_related(
            'project', 'module', 'source_document', 'creator'
        )

        if not filters:
            return queryset

        if 'artifact_type' in filters:
            queryset = queryset.filter(artifact_type=filters['artifact_type'])

        if 'project_id' in filters:
            queryset = queryset.filter(project_id=filters['project_id'])

        if 'module_id' in filters:
            queryset = queryset.filter(module_id=filters['module_id'])

        if 'org_id' in filters:
            queryset = queryset.filter(org_id=filters['org_id'])

        if 'source_document_id' in filters:
            queryset = queryset.filter(source_document_id=filters['source_document_id'])

        if 'search' in filters and filters['search']:
            search_term = filters['search']
            queryset = queryset.filter(
                Q(title__icontains=search_term) |
                Q(source_question__icontains=search_term)
            )

        return queryset.order_by('-create_time')

    def get_by_project(self, project_id: int) -> QuerySet[GeneratedTestArtifact]:
        """根据项目获取测试资产"""
        return self.model.objects.filter(
            project_id=project_id,
            is_deleted=False
        ).select_related('project', 'module', 'source_document').order_by('-create_time')

    def get_by_module(self, module_id: int) -> QuerySet[GeneratedTestArtifact]:
        """根据模块获取测试资产"""
        return self.model.objects.filter(
            module_id=module_id,
            is_deleted=False
        ).select_related('project', 'module', 'source_document').order_by('-create_time')

    def get_by_artifact_type(self, artifact_type: str) -> QuerySet[GeneratedTestArtifact]:
        """根据资产类型获取"""
        return self.model.objects.filter(
            artifact_type=artifact_type,
            is_deleted=False
        ).select_related('project', 'module', 'source_document').order_by('-create_time')

    def get_by_source_document(self, source_document_id: int) -> QuerySet[GeneratedTestArtifact]:
        """根据来源文档获取测试资产"""
        return self.model.objects.filter(
            source_document_id=source_document_id,
            is_deleted=False
        ).order_by('-create_time')

    def count_by_type(self, artifact_type: Optional[str] = None) -> int:
        """统计测试资产数量"""
        queryset = self.model.objects.filter(is_deleted=False)

        if artifact_type:
            queryset = queryset.filter(artifact_type=artifact_type)

        return queryset.count()

    def count_by_project(self, project_id: int) -> int:
        """统计项目的测试资产数量"""
        return self.model.objects.filter(
            project_id=project_id,
            is_deleted=False
        ).count()
