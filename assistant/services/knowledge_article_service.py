"""
KnowledgeArticle Service
"""
from typing import Optional
from django.db import transaction
from common.services.base_service import BaseService
from common.exceptions import ValidationException, DuplicateException, ResourceNotFoundException
from assistant.models import KnowledgeArticle
from assistant.repositories.knowledge_article_repository import KnowledgeArticleRepository


class KnowledgeArticleService(BaseService[KnowledgeArticle]):
    """知识文章 Service"""

    def __init__(self):
        super().__init__(KnowledgeArticleRepository())

    @transaction.atomic
    def create_article(self, data: dict, creator) -> KnowledgeArticle:
        """创建知识文章"""
        if not data.get('title'):
            raise ValidationException("标题不能为空")

        if not data.get('markdown_content'):
            raise ValidationException("内容不能为空")

        if self.repository.exists_by_title(data['title']):
            raise DuplicateException(f"标题 '{data['title']}' 已存在")

        category = data.get('category', KnowledgeArticle.CATEGORY_TEMPLATE)
        if category not in dict(KnowledgeArticle.CATEGORY_CHOICES):
            raise ValidationException(f"无效的分类: {category}")

        visibility_scope = data.get('visibility_scope', KnowledgeArticle.VISIBILITY_PRIVATE)
        if visibility_scope not in dict(KnowledgeArticle.VISIBILITY_CHOICES):
            raise ValidationException(f"无效的可见范围: {visibility_scope}")

        article_data = {
            'title': data['title'],
            'category': category,
            'markdown_content': data['markdown_content'],
            'visibility_scope': visibility_scope,
            'tags': data.get('tags', []),
        }

        if 'org_id' in data:
            article_data['org_id'] = data['org_id']

        return self.repository.create(article_data, creator=creator)

    @transaction.atomic
    def update_article(self, article_id: int, data: dict, updater) -> KnowledgeArticle:
        """更新知识文章"""
        article = self.repository.get_by_id(article_id)
        if not article:
            raise ResourceNotFoundException("知识文章不存在")

        if 'title' in data and data['title'] != article.title:
            if self.repository.exists_by_title(data['title'], exclude_id=article_id):
                raise DuplicateException(f"标题 '{data['title']}' 已存在")

        if 'category' in data:
            if data['category'] not in dict(KnowledgeArticle.CATEGORY_CHOICES):
                raise ValidationException(f"无效的分类: {data['category']}")

        if 'visibility_scope' in data:
            if data['visibility_scope'] not in dict(KnowledgeArticle.VISIBILITY_CHOICES):
                raise ValidationException(f"无效的可见范围: {data['visibility_scope']}")

        return self.repository.update(article_id, data)

    def get_by_category(self, category: str):
        """根据分类获取文章"""
        return self.repository.get_by_category(category)

    def get_by_visibility(self, visibility_scope: str, org_id: Optional[int] = None):
        """根据可见范围获取文章"""
        return self.repository.get_by_visibility(visibility_scope, org_id)

    def search_by_tags(self, tags: list):
        """根据标签搜索文章"""
        return self.repository.search_by_tags(tags)

    def count_by_category(self, category: Optional[str] = None) -> int:
        """统计文章数量"""
        return self.repository.count_by_category(category)
