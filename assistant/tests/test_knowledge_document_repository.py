"""
KnowledgeDocument Repository 单元测试
"""
import pytest
from django.contrib.auth import get_user_model
from assistant.repositories.knowledge_document_repository import KnowledgeDocumentRepository
from assistant.models import KnowledgeDocument

User = get_user_model()


@pytest.mark.django_db
class TestKnowledgeDocumentRepository:
    """知识文档 Repository 测试"""

    def test_get_by_id(self, knowledge_document):
        """测试根据 ID 获取文档"""
        repo = KnowledgeDocumentRepository()
        result = repo.get_by_id(knowledge_document.id)

        assert result is not None
        assert result.id == knowledge_document.id
        assert result.title == '测试文档'

    def test_get_by_id_not_found(self):
        """测试获取不存在的文档"""
        repo = KnowledgeDocumentRepository()
        result = repo.get_by_id(99999)

        assert result is None

    def test_get_all(self, user, module):
        """测试获取所有文档"""
        repo = KnowledgeDocumentRepository()

        KnowledgeDocument.objects.create(
            title='文档1',
            document_type=KnowledgeDocument.DOC_TYPE_PDF,
            status=KnowledgeDocument.STATUS_PENDING,
            module=module,
            creator=user
        )
        KnowledgeDocument.objects.create(
            title='文档2',
            document_type=KnowledgeDocument.DOC_TYPE_MD,
            status=KnowledgeDocument.STATUS_COMPLETED,
            module=module,
            creator=user
        )

        docs = repo.get_all()
        assert docs.count() == 2

    def test_get_all_with_filters(self, user, module):
        """测试带过滤条件获取文档"""
        repo = KnowledgeDocumentRepository()

        KnowledgeDocument.objects.create(
            title='文档1',
            document_type=KnowledgeDocument.DOC_TYPE_PDF,
            status=KnowledgeDocument.STATUS_PENDING,
            module=module,
            creator=user
        )
        KnowledgeDocument.objects.create(
            title='文档2',
            document_type=KnowledgeDocument.DOC_TYPE_MD,
            status=KnowledgeDocument.STATUS_COMPLETED,
            module=module,
            creator=user
        )

        docs = repo.get_all(filters={'status': KnowledgeDocument.STATUS_PENDING})
        assert docs.count() == 1
        assert docs.first().status == KnowledgeDocument.STATUS_PENDING

    def test_get_all_with_search(self, user, module):
        """测试搜索文档"""
        repo = KnowledgeDocumentRepository()

        KnowledgeDocument.objects.create(
            title='登录文档',
            document_type=KnowledgeDocument.DOC_TYPE_PDF,
            module=module,
            creator=user
        )
        KnowledgeDocument.objects.create(
            title='注册文档',
            document_type=KnowledgeDocument.DOC_TYPE_PDF,
            module=module,
            creator=user
        )

        docs = repo.get_all(filters={'search': '登录'})
        assert docs.count() == 1
        assert docs.first().title == '登录文档'

    def test_get_by_status(self, user, module):
        """测试根据状态获取文档"""
        repo = KnowledgeDocumentRepository()

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
            status=KnowledgeDocument.STATUS_PENDING,
            module=module,
            creator=user
        )

        docs = repo.get_by_status(KnowledgeDocument.STATUS_PENDING)
        assert docs.count() == 2

    def test_get_by_module(self, user, module):
        """测试根据模块获取文档"""
        repo = KnowledgeDocumentRepository()

        KnowledgeDocument.objects.create(
            title='文档1',
            document_type=KnowledgeDocument.DOC_TYPE_PDF,
            module=module,
            creator=user
        )
        KnowledgeDocument.objects.create(
            title='文档2',
            document_type=KnowledgeDocument.DOC_TYPE_PDF,
            module=module,
            creator=user
        )

        docs = repo.get_by_module(module.id)
        assert docs.count() == 2

    def test_get_by_article(self, user, module):
        """测试根据文章获取文档"""
        repo = KnowledgeDocumentRepository()

        from assistant.models import KnowledgeArticle

        article = KnowledgeArticle.objects.create(
            title='测试文章2',
            category=KnowledgeArticle.CATEGORY_TEMPLATE,
            markdown_content='内容',
            creator=user
        )

        doc = KnowledgeDocument.objects.create(
            title='文档1',
            document_type=KnowledgeDocument.DOC_TYPE_PDF,
            module=module,
            article=article,
            creator=user
        )

        docs = repo.get_by_article(article.id)
        assert docs.count() >= 1
        assert doc in docs

    def test_exists_by_vector_db_id(self, knowledge_document):
        """测试检查向量数据库ID是否存在"""
        repo = KnowledgeDocumentRepository()

        knowledge_document.vector_db_id = 'test_vector_id'
        knowledge_document.save()

        exists = repo.exists_by_vector_db_id('test_vector_id')
        assert exists is True

        exists = repo.exists_by_vector_db_id('non_existent_id')
        assert exists is False

    def test_create(self, user, module):
        """测试创建文档"""
        repo = KnowledgeDocumentRepository()

        data = {
            'title': '新文档',
            'document_type': KnowledgeDocument.DOC_TYPE_PDF,
            'status': KnowledgeDocument.STATUS_PENDING,
            'module': module
        }

        doc = repo.create(data, creator=user)

        assert doc.id is not None
        assert doc.title == '新文档'
        assert doc.creator == user

    def test_update(self, knowledge_document):
        """测试更新文档"""
        repo = KnowledgeDocumentRepository()

        data = {
            'title': '更新后的标题',
            'status': KnowledgeDocument.STATUS_COMPLETED
        }

        updated = repo.update(knowledge_document.id, data)

        assert updated is not None
        assert updated.title == '更新后的标题'
        assert updated.status == KnowledgeDocument.STATUS_COMPLETED

    def test_update_status(self, knowledge_document):
        """测试更新文档状态"""
        repo = KnowledgeDocumentRepository()

        updated = repo.update_status(
            knowledge_document.id,
            KnowledgeDocument.STATUS_COMPLETED
        )

        assert updated is not None
        assert updated.status == KnowledgeDocument.STATUS_COMPLETED

    def test_delete_soft(self, knowledge_document):
        """测试软删除文档"""
        repo = KnowledgeDocumentRepository()

        result = repo.delete(knowledge_document.id, soft=True)

        assert result is True

        knowledge_document.refresh_from_db()
        assert knowledge_document.is_deleted is True

    def test_count_by_status(self, user, module):
        """测试统计文档数量"""
        repo = KnowledgeDocumentRepository()

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

        count = repo.count_by_status()
        assert count == 2

        count = repo.count_by_status(KnowledgeDocument.STATUS_PENDING)
        assert count == 1
