"""
KnowledgeArticle Repository
"""
from typing import Optional
from django.db.models import QuerySet, Q
from common.repositories.base_repository import BaseRepository
from assistant.models import KnowledgeArticle


class KnowledgeArticleRepository(BaseRepository[KnowledgeArticle]):
    """知识文章 Repository"""

    def __init__(self):
        super().__init__(KnowledgeArticle)

    def get_all(self, filters: Optional[dict] = None) -> QuerySet[KnowledgeArticle]:
        """获取所有知识文章"""
        queryset = self.model.objects.filter(is_deleted=False)

        if not filters:
            return queryset

        if 'category' in filters:
            queryset = queryset.filter(category=filters['category'])

        if 'visibility_scope' in filters:
            queryset = queryset.filter(visibility_scope=filters['visibility_scope'])

        if 'org_id' in filters:
            queryset = queryset.filter(org_id=filters['org_id'])

        if 'search' in filters and filters['search']:
            search_term = filters['search']
            queryset = queryset.filter(
                Q(title__icontains=search_term) |
                Q(markdown_content__icontains=search_term)
            )

        if 'tags' in filters and filters['tags']:
            queryset = queryset.filter(tags__contains=filters['tags'])

        return queryset.order_by('-create_time')

    def get_by_category(self, category: str) -> QuerySet[KnowledgeArticle]:
        """根据分类获取文章"""
        return self.model.objects.filter(
            category=category,
            is_deleted=False
        ).order_by('-create_time')

    def get_by_visibility(self, visibility_scope: str, org_id: Optional[int] = None) -> QuerySet[KnowledgeArticle]:
        """根据可见范围获取文章"""
        queryset = self.model.objects.filter(
            visibility_scope=visibility_scope,
            is_deleted=False
        )

        if org_id:
            queryset = queryset.filter(org_id=org_id)

        return queryset.order_by('-create_time')

    def search_by_tags(self, tags: list) -> QuerySet[KnowledgeArticle]:
        """根据标签搜索文章"""
        queryset = self.model.objects.filter(is_deleted=False)

        for tag in tags:
            queryset = queryset.filter(tags__contains=[tag])

        return queryset.order_by('-create_time')

    def exists_by_title(self, title: str, exclude_id: Optional[int] = None) -> bool:
        """检查标题是否存在"""
        queryset = self.model.objects.filter(title=title, is_deleted=False)

        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)

        return queryset.exists()

    def count_by_category(self, category: Optional[str] = None) -> int:
        """统计文章数量"""
        queryset = self.model.objects.filter(is_deleted=False)

        if category:
            queryset = queryset.filter(category=category)

        return queryset.count()
