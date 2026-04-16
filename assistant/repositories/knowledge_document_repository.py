"""
KnowledgeDocument Repository
"""
from typing import Optional
from django.db.models import QuerySet, Q
from common.repositories.base_repository import BaseRepository
from assistant.models import KnowledgeDocument


class KnowledgeDocumentRepository(BaseRepository[KnowledgeDocument]):
    """知识文档 Repository"""

    def __init__(self):
        super().__init__(KnowledgeDocument)

    def get_all(self, filters: Optional[dict] = None) -> QuerySet[KnowledgeDocument]:
        """获取所有知识文档"""
        queryset = self.model.objects.filter(is_deleted=False).select_related(
            'module', 'article', 'creator'
        )

        if not filters:
            return queryset

        if 'status' in filters:
            queryset = queryset.filter(status=filters['status'])

        if 'document_type' in filters:
            queryset = queryset.filter(document_type=filters['document_type'])

        if 'source_type' in filters:
            queryset = queryset.filter(source_type=filters['source_type'])

        if 'module_id' in filters:
            queryset = queryset.filter(module_id=filters['module_id'])

        if 'org_id' in filters:
            queryset = queryset.filter(org_id=filters['org_id'])

        if 'visibility_scope' in filters:
            queryset = queryset.filter(visibility_scope=filters['visibility_scope'])

        if 'search' in filters and filters['search']:
            search_term = filters['search']
            queryset = queryset.filter(
                Q(title__icontains=search_term) |
                Q(file_name__icontains=search_term) |
                Q(semantic_summary__icontains=search_term)
            )

        if 'tags' in filters and filters['tags']:
            queryset = queryset.filter(tags__contains=filters['tags'])

        return queryset.order_by('-created_at')

    def get_by_status(self, status: str) -> QuerySet[KnowledgeDocument]:
        """根据状态获取文档"""
        return self.model.objects.filter(
            status=status,
            is_deleted=False
        ).select_related('module', 'article').order_by('-created_at')

    def get_by_module(self, module_id: int) -> QuerySet[KnowledgeDocument]:
        """根据模块获取文档"""
        return self.model.objects.filter(
            module_id=module_id,
            is_deleted=False
        ).select_related('module', 'article').order_by('-created_at')

    def get_by_article(self, article_id: int) -> QuerySet[KnowledgeDocument]:
        """根据文章获取文档"""
        return self.model.objects.filter(
            article_id=article_id,
            is_deleted=False
        ).order_by('-created_at')

    def get_stuck_processing_docs(self) -> QuerySet[KnowledgeDocument]:
        """获取卡住的处理中文档"""
        from django.utils import timezone
        from datetime import timedelta

        stuck_threshold = timezone.now() - timedelta(hours=1)

        return self.model.objects.filter(
            status=KnowledgeDocument.STATUS_PROCESSING,
            is_deleted=False,
            created_at__lt=stuck_threshold
        )

    def exists_by_vector_db_id(self, vector_db_id: str) -> bool:
        """检查向量数据库ID是否存在"""
        return self.model.objects.filter(
            vector_db_id=vector_db_id,
            is_deleted=False
        ).exists()

    def count_by_status(self, status: Optional[str] = None) -> int:
        """统计文档数量"""
        queryset = self.model.objects.filter(is_deleted=False)

        if status:
            queryset = queryset.filter(status=status)

        return queryset.count()

    def update_status(self, doc_id: int, status: str, error_message: str = "") -> Optional[KnowledgeDocument]:
        """更新文档状态"""
        doc = self.get_by_id(doc_id)
        if not doc:
            return None

        data = {'status': status}
        if error_message:
            data['error_message'] = error_message

        return self.update(doc_id, data)
