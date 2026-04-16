"""
KnowledgeArticle Repository 单元测试
"""
import pytest
from django.contrib.auth import get_user_model
from assistant.repositories.knowledge_article_repository import KnowledgeArticleRepository
from assistant.models import KnowledgeArticle

User = get_user_model()


@pytest.mark.django_db
class TestKnowledgeArticleRepository:
    """知识文章 Repository 测试"""

    def test_get_by_id(self, knowledge_article):
        """测试根据 ID 获取文章"""
        repo = KnowledgeArticleRepository()
        result = repo.get_by_id(knowledge_article.id)

        assert result is not None
        assert result.id == knowledge_article.id
        assert result.title == '测试文章'

    def test_get_by_id_not_found(self):
        """测试获取不存在的文章"""
        repo = KnowledgeArticleRepository()
        result = repo.get_by_id(99999)

        assert result is None

    def test_get_all(self, user):
        """测试获取所有文章"""
        repo = KnowledgeArticleRepository()

        KnowledgeArticle.objects.create(
            title='文章1',
            category=KnowledgeArticle.CATEGORY_TEMPLATE,
            markdown_content='内容1',
            creator=user
        )
        KnowledgeArticle.objects.create(
            title='文章2',
            category=KnowledgeArticle.CATEGORY_FAQ,
            markdown_content='内容2',
            creator=user
        )

        articles = repo.get_all()
        assert articles.count() == 2

    def test_get_all_with_filters(self, user):
        """测试带过滤条件获取文章"""
        repo = KnowledgeArticleRepository()

        KnowledgeArticle.objects.create(
            title='模板文章',
            category=KnowledgeArticle.CATEGORY_TEMPLATE,
            markdown_content='内容',
            creator=user
        )
        KnowledgeArticle.objects.create(
            title='FAQ文章',
            category=KnowledgeArticle.CATEGORY_FAQ,
            markdown_content='内容',
            creator=user
        )

        articles = repo.get_all(filters={'category': KnowledgeArticle.CATEGORY_TEMPLATE})
        assert articles.count() == 1
        assert articles.first().category == KnowledgeArticle.CATEGORY_TEMPLATE

    def test_get_all_with_search(self, user):
        """测试搜索文章"""
        repo = KnowledgeArticleRepository()

        KnowledgeArticle.objects.create(
            title='登录测试',
            category=KnowledgeArticle.CATEGORY_TEMPLATE,
            markdown_content='登录功能测试',
            creator=user
        )
        KnowledgeArticle.objects.create(
            title='注册测试',
            category=KnowledgeArticle.CATEGORY_TEMPLATE,
            markdown_content='注册功能测试',
            creator=user
        )

        articles = repo.get_all(filters={'search': '登录'})
        assert articles.count() == 1
        assert articles.first().title == '登录测试'

    def test_get_by_category(self, user):
        """测试根据分类获取文章"""
        repo = KnowledgeArticleRepository()

        KnowledgeArticle.objects.create(
            title='文章1',
            category=KnowledgeArticle.CATEGORY_TEMPLATE,
            markdown_content='内容',
            creator=user
        )
        KnowledgeArticle.objects.create(
            title='文章2',
            category=KnowledgeArticle.CATEGORY_TEMPLATE,
            markdown_content='内容',
            creator=user
        )

        articles = repo.get_by_category(KnowledgeArticle.CATEGORY_TEMPLATE)
        assert articles.count() == 2

    def test_get_by_visibility(self, user):
        """测试根据可见范围获取文章"""
        repo = KnowledgeArticleRepository()

        KnowledgeArticle.objects.create(
            title='私有文章',
            category=KnowledgeArticle.CATEGORY_TEMPLATE,
            markdown_content='内容',
            visibility_scope=KnowledgeArticle.VISIBILITY_PRIVATE,
            creator=user
        )
        KnowledgeArticle.objects.create(
            title='项目文章',
            category=KnowledgeArticle.CATEGORY_TEMPLATE,
            markdown_content='内容',
            visibility_scope=KnowledgeArticle.VISIBILITY_PROJECT,
            creator=user
        )

        articles = repo.get_by_visibility(KnowledgeArticle.VISIBILITY_PRIVATE)
        assert articles.count() == 1

    def test_search_by_tags(self, user):
        """测试根据标签搜索文章"""
        repo = KnowledgeArticleRepository()

        KnowledgeArticle.objects.create(
            title='文章1',
            category=KnowledgeArticle.CATEGORY_TEMPLATE,
            markdown_content='内容',
            tags=['python', 'django'],
            creator=user
        )
        KnowledgeArticle.objects.create(
            title='文章2',
            category=KnowledgeArticle.CATEGORY_TEMPLATE,
            markdown_content='内容',
            tags=['java', 'spring'],
            creator=user
        )

        articles = repo.search_by_tags(['python'])
        assert articles.count() == 1

    def test_exists_by_title(self, knowledge_article):
        """测试检查标题是否存在"""
        repo = KnowledgeArticleRepository()

        exists = repo.exists_by_title('测试文章')
        assert exists is True

        exists = repo.exists_by_title('不存在的文章')
        assert exists is False

        exists = repo.exists_by_title('测试文章', exclude_id=knowledge_article.id)
        assert exists is False

    def test_create(self, user):
        """测试创建文章"""
        repo = KnowledgeArticleRepository()

        data = {
            'title': '新文章',
            'category': KnowledgeArticle.CATEGORY_TEMPLATE,
            'markdown_content': '新内容',
            'tags': ['新标签']
        }

        article = repo.create(data, creator=user)

        assert article.id is not None
        assert article.title == '新文章'
        assert article.creator == user

    def test_update(self, knowledge_article):
        """测试更新文章"""
        repo = KnowledgeArticleRepository()

        data = {
            'title': '更新后的标题',
            'markdown_content': '更新后的内容'
        }

        updated = repo.update(knowledge_article.id, data)

        assert updated is not None
        assert updated.title == '更新后的标题'
        assert updated.markdown_content == '更新后的内容'

    def test_delete_soft(self, knowledge_article):
        """测试软删除文章"""
        repo = KnowledgeArticleRepository()

        result = repo.delete(knowledge_article.id, soft=True)

        assert result is True

        knowledge_article.refresh_from_db()
        assert knowledge_article.is_deleted is True

    def test_count_by_category(self, user):
        """测试统计文章数量"""
        repo = KnowledgeArticleRepository()

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

        count = repo.count_by_category()
        assert count == 2

        count = repo.count_by_category(KnowledgeArticle.CATEGORY_TEMPLATE)
        assert count == 1
