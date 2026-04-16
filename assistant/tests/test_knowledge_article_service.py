"""
KnowledgeArticle Service 单元测试
"""
import pytest
from django.contrib.auth import get_user_model
from assistant.services.knowledge_article_service import KnowledgeArticleService
from assistant.models import KnowledgeArticle
from common.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    DuplicateException
)

User = get_user_model()


@pytest.mark.django_db
class TestKnowledgeArticleService:
    """知识文章 Service 测试"""

    def test_create_article_success(self, user):
        """测试成功创建文章"""
        service = KnowledgeArticleService()

        data = {
            'title': '新文章',
            'markdown_content': '# 标题\n内容',
            'category': KnowledgeArticle.CATEGORY_TEMPLATE,
            'tags': ['测试']
        }

        article = service.create_article(data, user)

        assert article.id is not None
        assert article.title == '新文章'
        assert article.creator == user

    def test_create_article_missing_title(self, user):
        """测试创建文章时缺少标题"""
        service = KnowledgeArticleService()

        data = {
            'markdown_content': '内容'
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_article(data, user)

        assert "标题不能为空" in str(exc_info.value)

    def test_create_article_missing_content(self, user):
        """测试创建文章时缺少内容"""
        service = KnowledgeArticleService()

        data = {
            'title': '新文章'
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_article(data, user)

        assert "内容不能为空" in str(exc_info.value)

    def test_create_article_duplicate_title(self, knowledge_article, user):
        """测试创建文章时标题重复"""
        service = KnowledgeArticleService()

        data = {
            'title': knowledge_article.title,
            'markdown_content': '内容'
        }

        with pytest.raises(DuplicateException) as exc_info:
            service.create_article(data, user)

        assert "已存在" in str(exc_info.value)

    def test_create_article_invalid_category(self, user):
        """测试创建文章时分类无效"""
        service = KnowledgeArticleService()

        data = {
            'title': '新文章',
            'markdown_content': '内容',
            'category': 'invalid_category'
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_article(data, user)

        assert "无效的分类" in str(exc_info.value)

    def test_create_article_invalid_visibility(self, user):
        """测试创建文章时可见范围无效"""
        service = KnowledgeArticleService()

        data = {
            'title': '新文章',
            'markdown_content': '内容',
            'visibility_scope': 'invalid_scope'
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_article(data, user)

        assert "无效的可见范围" in str(exc_info.value)

    def test_update_article_success(self, knowledge_article, user):
        """测试成功更新文章"""
        service = KnowledgeArticleService()

        data = {
            'title': '更新后的标题',
            'markdown_content': '更新后的内容'
        }

        updated = service.update_article(knowledge_article.id, data, user)

        assert updated.title == '更新后的标题'
        assert updated.markdown_content == '更新后的内容'

    def test_update_article_not_found(self, user):
        """测试更新不存在的文章"""
        service = KnowledgeArticleService()

        data = {'title': '新标题'}

        with pytest.raises(ResourceNotFoundException) as exc_info:
            service.update_article(99999, data, user)

        assert "知识文章不存在" in str(exc_info.value)

    def test_update_article_duplicate_title(self, user, knowledge_article):
        """测试更新文章时标题重复"""
        service = KnowledgeArticleService()

        another_article = KnowledgeArticle.objects.create(
            title='另一篇文章',
            category=KnowledgeArticle.CATEGORY_TEMPLATE,
            markdown_content='内容',
            creator=user
        )

        data = {'title': knowledge_article.title}

        with pytest.raises(DuplicateException) as exc_info:
            service.update_article(another_article.id, data, user)

        assert "已存在" in str(exc_info.value)

    def test_delete_article(self, knowledge_article):
        """测试删除文章"""
        service = KnowledgeArticleService()

        result = service.delete(knowledge_article.id)

        assert result is True

        knowledge_article.refresh_from_db()
        assert knowledge_article.is_deleted is True

    def test_get_all(self, user):
        """测试获取所有文章"""
        service = KnowledgeArticleService()

        KnowledgeArticle.objects.create(
            title='文章1',
            category=KnowledgeArticle.CATEGORY_TEMPLATE,
            markdown_content='内容',
            creator=user
        )
        KnowledgeArticle.objects.create(
            title='文章2',
            category=KnowledgeArticle.CATEGORY_FAQ,
            markdown_content='内容',
            creator=user
        )

        articles = service.get_all()

        assert len(articles) == 2

    def test_get_by_category(self, user):
        """测试根据分类获取文章"""
        service = KnowledgeArticleService()

        KnowledgeArticle.objects.create(
            title='文章1',
            category=KnowledgeArticle.CATEGORY_TEMPLATE,
            markdown_content='内容',
            creator=user
        )
        KnowledgeArticle.objects.create(
            title='文章2',
            category=KnowledgeArticle.CATEGORY_FAQ,
            markdown_content='内容',
            creator=user
        )

        articles = service.get_by_category(KnowledgeArticle.CATEGORY_TEMPLATE)

        assert articles.count() == 1

    def test_count_by_category(self, user):
        """测试统计文章数量"""
        service = KnowledgeArticleService()

        KnowledgeArticle.objects.create(
            title='文章1',
            category=KnowledgeArticle.CATEGORY_TEMPLATE,
            markdown_content='内容',
            creator=user
        )
        KnowledgeArticle.objects.create(
            title='文章2',
            category=KnowledgeArticle.CATEGORY_FAQ,
            markdown_content='内容',
            creator=user
        )

        count = service.count_by_category()
        assert count == 2

        count = service.count_by_category(KnowledgeArticle.CATEGORY_TEMPLATE)
        assert count == 1
