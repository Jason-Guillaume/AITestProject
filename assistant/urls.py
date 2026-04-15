from django.urls import path
from rest_framework.routers import DefaultRouter

from assistant.views import (
    KnowledgeArticleViewSet,
    KnowledgeArticleChunksPreviewAPIView,
    KnowledgeCategoryOptionsAPIView,
    KnowledgeDocumentListAPIView,
    KnowledgeDocumentIngestAPIView,
    KnowledgeDocumentDeleteAPIView,
    KnowledgeDocumentRetryAPIView,
    KnowledgeDocumentStatusAPIView,
    KnowledgeDocumentChunksPreviewAPIView,
    KnowledgeDocumentUploadAPIView,
    KnowledgeAutoFillFromFileAPIView,
    KnowledgeExtractTextAPIView,
    KnowledgeRuntimeStatusAPIView,
    KnowledgeSearchAPIView,
    LlmTestConnectionAPIView,
)

router = DefaultRouter()
router.register(r"knowledge-articles", KnowledgeArticleViewSet)

urlpatterns = [
    path("llm/test-connection/", LlmTestConnectionAPIView.as_view()),
    path("knowledge/search/", KnowledgeSearchAPIView.as_view()),
    path("knowledge/categories/", KnowledgeCategoryOptionsAPIView.as_view()),
    path("knowledge/extract-text/", KnowledgeExtractTextAPIView.as_view()),
    path("knowledge/autofill-from-file/", KnowledgeAutoFillFromFileAPIView.as_view()),
    path("knowledge/documents/upload/", KnowledgeDocumentUploadAPIView.as_view()),
    path("knowledge/documents/ingest/", KnowledgeDocumentIngestAPIView.as_view()),
    path("knowledge/documents/", KnowledgeDocumentListAPIView.as_view()),
    path(
        "knowledge/documents/<int:doc_id>/status/",
        KnowledgeDocumentStatusAPIView.as_view(),
    ),
    path(
        "knowledge/documents/<int:doc_id>/chunks-preview/",
        KnowledgeDocumentChunksPreviewAPIView.as_view(),
    ),
    path(
        "knowledge/documents/<int:doc_id>/retry/",
        KnowledgeDocumentRetryAPIView.as_view(),
    ),
    path("knowledge/documents/<int:doc_id>/", KnowledgeDocumentDeleteAPIView.as_view()),
    path(
        "knowledge/articles/<int:article_id>/chunks-preview/",
        KnowledgeArticleChunksPreviewAPIView.as_view(),
    ),
    path("knowledge/runtime-status/", KnowledgeRuntimeStatusAPIView.as_view()),
] + router.urls
