"""
KnowledgeDocument Service 单元测试
"""
import pytest
from django.contrib.auth import get_user_model
from assistant.services.knowledge_document_service import KnowledgeDocumentService
from assistant.models import KnowledgeDocument
from common.exceptions import (
    ResourceNotFoundException,
    ValidationException
)

User = get_user_model()


@pytest.mark.django_db
class TestKnowledgeDocumentService:
    """知识文档 Service 测试"""

    def test_create_document_success(self, user, module):
        """测试成功创建文档"""
        service = KnowledgeDocumentService()

        data = {
            'title': '新文档',
            'document_type': KnowledgeDocument.DOC_TYPE_PDF,
            'source_type': KnowledgeDocument.SOURCE_UPLOAD,
            'module_id': module.id
        }

        doc = service.create_document(data, user)

        assert doc.id is not None
        assert doc.title == '新文档'
        assert doc.creator == user

    def test_create_document_missing_title(self, user):
        """测试创建文档时缺少标题"""
        service = KnowledgeDocumentService()

        data = {
            'document_type': KnowledgeDocument.DOC_TYPE_PDF
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_document(data, user)

        assert "标题不能为空" in str(exc_info.value)

    def test_create_document_invalid_type(self, user):
        """测试创建文档时类型无效"""
        service = KnowledgeDocumentService()

        data = {
            'title': '新文档',
            'document_type': 'invalid_type'
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_document(data, user)

        assert "无效的文档类型" in str(exc_info.value)

    def test_create_document_invalid_source(self, user):
        """测试创建文档时来源类型无效"""
        service = KnowledgeDocumentService()

        data = {
            'title': '新文档',
            'source_type': 'invalid_source'
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_document(data, user)

        assert "无效的来源类型" in str(exc_info.value)

    def test_create_document_invalid_visibility(self, user):
        """测试创建文档时可见范围无效"""
        service = KnowledgeDocumentService()

        data = {
            'title': '新文档',
            'visibility_scope': 'invalid_scope'
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_document(data, user)

        assert "无效的可见范围" in str(exc_info.value)

    def test_update_document_success(self, knowledge_document, user):
        """测试成功更新文档"""
        service = KnowledgeDocumentService()

        data = {
            'title': '更新后的标题',
            'status': KnowledgeDocument.STATUS_COMPLETED
        }

        updated = service.update_document(knowledge_document.id, data, user)

        assert updated.title == '更新后的标题'
        assert updated.status == KnowledgeDocument.STATUS_COMPLETED

    def test_update_document_not_found(self, user):
        """测试更新不存在的文档"""
        service = KnowledgeDocumentService()

        data = {'title': '新标题'}

        with pytest.raises(ResourceNotFoundException) as exc_info:
            service.update_document(99999, data, user)

        assert "知识文档不存在" in str(exc_info.value)

    def test_update_document_invalid_type(self, knowledge_document, user):
        """测试更新文档时类型无效"""
        service = KnowledgeDocumentService()

        data = {'document_type': 'invalid_type'}

        with pytest.raises(ValidationException) as exc_info:
            service.update_document(knowledge_document.id, data, user)

        assert "无效的文档类型" in str(exc_info.value)

    def test_update_status_success(self, knowledge_document):
        """测试成功更新状态"""
        service = KnowledgeDocumentService()

        updated = service.update_status(
            knowledge_document.id,
            KnowledgeDocument.STATUS_COMPLETED
        )

        assert updated.status == KnowledgeDocument.STATUS_COMPLETED

    def test_update_status_invalid(self, knowledge_document):
        """测试更新状态时状态无效"""
        service = KnowledgeDocumentService()

        with pytest.raises(ValidationException) as exc_info:
            service.update_status(knowledge_document.id, 'invalid_status')

        assert "无效的状态" in str(exc_info.value)

    def test_update_status_not_found(self):
        """测试更新不存在文档的状态"""
        service = KnowledgeDocumentService()

        with pytest.raises(ResourceNotFoundException) as exc_info:
            service.update_status(99999, KnowledgeDocument.STATUS_COMPLETED)

        assert "知识文档不存在" in str(exc_info.value)

    def test_delete_document(self, knowledge_document):
        """测试删除文档"""
        service = KnowledgeDocumentService()

        result = service.delete(knowledge_document.id)

        assert result is True

        knowledge_document.refresh_from_db()
        assert knowledge_document.is_deleted is True

    def test_get_all(self, user, module):
        """测试获取所有文档"""
        service = KnowledgeDocumentService()

        KnowledgeDocument.objects.create(
            title='文档1',
            document_type=KnowledgeDocument.DOC_TYPE_PDF,
            module=module,
            creator=user
        )
        KnowledgeDocument.objects.create(
            title='文档2',
            document_type=KnowledgeDocument.DOC_TYPE_MD,
            module=module,
            creator=user
        )

        docs = service.get_all()

        assert len(docs) == 2

    def test_get_by_status(self, user, module):
        """测试根据状态获取文档"""
        service = KnowledgeDocumentService()

        KnowledgeDocument.objects.create(
            title='文档1',
            document_type=KnowledgeDocument.DOC_TYPE_PDF,
            status=KnowledgeDocument.STATUS_PENDING,
            module=module,
            creator=user
        )
        KnowledgeDocument.objects.create(
            title='文档2',
            document_type=KnowledgeDocument.DOC_TYPE_PDF,
            status=KnowledgeDocument.STATUS_COMPLETED,
            module=module,
            creator=user
        )

        docs = service.get_by_status(KnowledgeDocument.STATUS_PENDING)

        assert docs.count() == 1

    def test_get_by_module(self, user, module):
        """测试根据模块获取文档"""
        service = KnowledgeDocumentService()

        KnowledgeDocument.objects.create(
            title='文档1',
            document_type=KnowledgeDocument.DOC_TYPE_PDF,
            module=module,
            creator=user
        )

        docs = service.get_by_module(module.id)

        assert docs.count() == 1

    def test_count_by_status(self, user, module):
        """测试统计文档数量"""
        service = KnowledgeDocumentService()

        KnowledgeDocument.objects.create(
            title='文档1',
            document_type=KnowledgeDocument.DOC_TYPE_PDF,
            status=KnowledgeDocument.STATUS_PENDING,
            module=module,
            creator=user
        )
        KnowledgeDocument.objects.create(
            title='文档2',
            document_type=KnowledgeDocument.DOC_TYPE_PDF,
            status=KnowledgeDocument.STATUS_COMPLETED,
            module=module,
            creator=user
        )

        count = service.count_by_status()
        assert count == 2

        count = service.count_by_status(KnowledgeDocument.STATUS_PENDING)
        assert count == 1
