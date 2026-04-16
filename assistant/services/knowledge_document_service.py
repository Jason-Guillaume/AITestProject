"""
KnowledgeDocument Service
"""
from typing import Optional
from django.db import transaction
from common.services.base_service import BaseService
from common.exceptions import ValidationException, ResourceNotFoundException
from assistant.models import KnowledgeDocument
from assistant.repositories.knowledge_document_repository import KnowledgeDocumentRepository


class KnowledgeDocumentService(BaseService[KnowledgeDocument]):
    """知识文档 Service"""

    def __init__(self):
        super().__init__(KnowledgeDocumentRepository())

    @transaction.atomic
    def create_document(self, data: dict, creator) -> KnowledgeDocument:
        """创建知识文档"""
        if not data.get('title'):
            raise ValidationException("标题不能为空")

        document_type = data.get('document_type', KnowledgeDocument.DOC_TYPE_MD)
        if document_type not in dict(KnowledgeDocument.DOC_TYPE_CHOICES):
            raise ValidationException(f"无效的文档类型: {document_type}")

        source_type = data.get('source_type', KnowledgeDocument.SOURCE_UPLOAD)
        if source_type not in dict(KnowledgeDocument.SOURCE_CHOICES):
            raise ValidationException(f"无效的来源类型: {source_type}")

        visibility_scope = data.get('visibility_scope', KnowledgeDocument.VISIBILITY_PRIVATE)
        if visibility_scope not in dict(KnowledgeDocument.VISIBILITY_CHOICES):
            raise ValidationException(f"无效的可见范围: {visibility_scope}")

        doc_data = {
            'title': data['title'],
            'document_type': document_type,
            'source_type': source_type,
            'visibility_scope': visibility_scope,
            'status': data.get('status', KnowledgeDocument.STATUS_PENDING),
            'file_name': data.get('file_name', ''),
            'category': data.get('category', ''),
            'tags': data.get('tags', []),
        }

        if 'module_id' in data:
            doc_data['module_id'] = data['module_id']

        if 'org_id' in data:
            doc_data['org_id'] = data['org_id']

        if 'article_id' in data:
            doc_data['article_id'] = data['article_id']

        if 'file_path' in data:
            doc_data['file_path'] = data['file_path']

        if 'source_url' in data:
            doc_data['source_url'] = data['source_url']

        return self.repository.create(doc_data, creator=creator)

    @transaction.atomic
    def update_document(self, doc_id: int, data: dict, updater) -> KnowledgeDocument:
        """更新知识文档"""
        doc = self.repository.get_by_id(doc_id)
        if not doc:
            raise ResourceNotFoundException("知识文档不存在")

        if 'document_type' in data:
            if data['document_type'] not in dict(KnowledgeDocument.DOC_TYPE_CHOICES):
                raise ValidationException(f"无效的文档类型: {data['document_type']}")

        if 'status' in data:
            if data['status'] not in dict(KnowledgeDocument.STATUS_CHOICES):
                raise ValidationException(f"无效的状态: {data['status']}")

        return self.repository.update(doc_id, data)

    def update_status(self, doc_id: int, status: str, error_message: str = "") -> KnowledgeDocument:
        """更新文档状态"""
        if status not in dict(KnowledgeDocument.STATUS_CHOICES):
            raise ValidationException(f"无效的状态: {status}")

        doc = self.repository.update_status(doc_id, status, error_message)
        if not doc:
            raise ResourceNotFoundException("知识文档不存在")

        return doc

    def get_by_status(self, status: str):
        """根据状态获取文档"""
        return self.repository.get_by_status(status)

    def get_by_module(self, module_id: int):
        """根据模块获取文档"""
        return self.repository.get_by_module(module_id)

    def get_by_article(self, article_id: int):
        """根据文章获取文档"""
        return self.repository.get_by_article(article_id)

    def get_stuck_processing_docs(self):
        """获取卡住的处理中文档"""
        return self.repository.get_stuck_processing_docs()

    def count_by_status(self, status: Optional[str] = None) -> int:
        """统计文档数量"""
        return self.repository.count_by_status(status)

    @transaction.atomic
    def mark_stuck_docs_failed(self) -> int:
        """标记卡住的文档为失败"""
        stuck_docs = self.get_stuck_processing_docs()
        count = 0

        for doc in stuck_docs:
            self.update_status(
                doc.id,
                KnowledgeDocument.STATUS_FAILED,
                "处理超时，已自动标记为失败"
            )
            count += 1

        return count
