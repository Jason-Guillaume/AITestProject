from django.db import models

from common.models import BaseModel
from testcase.models import TestModule


class KnowledgeArticle(BaseModel):
    """RAG 测试知识库文章。"""

    CATEGORY_TEMPLATE = "template"
    CATEGORY_BEST_PRACTICE = "best_practice"
    CATEGORY_FAQ = "faq"
    CATEGORY_FUNCTIONAL = "functional_test"
    CATEGORY_API = "api_test"
    CATEGORY_PERFORMANCE = "performance_test"
    CATEGORY_SECURITY = "security_test"
    CATEGORY_UI_AUTOMATION = "ui_automation_test"
    CATEGORY_CHOICES = [
        (CATEGORY_TEMPLATE, "用例模板"),
        (CATEGORY_BEST_PRACTICE, "最佳实践"),
        (CATEGORY_FAQ, "FAQ"),
        (CATEGORY_FUNCTIONAL, "功能测试"),
        (CATEGORY_API, "接口测试"),
        (CATEGORY_PERFORMANCE, "性能测试"),
        (CATEGORY_SECURITY, "安全测试"),
        (CATEGORY_UI_AUTOMATION, "UI自动化"),
    ]

    title = models.CharField(max_length=255, verbose_name="标题")
    category = models.CharField(
        max_length=32,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_TEMPLATE,
        verbose_name="分类",
    )
    markdown_content = models.TextField(verbose_name="Markdown内容")
    tags = models.JSONField(default=list, blank=True, verbose_name="标签")

    class Meta:
        db_table = "knowledge_article"
        ordering = ("-create_time",)
        indexes = [
            models.Index(fields=["category", "-create_time"]),
        ]


class KnowledgeDocument(BaseModel):
    """知识库文档。"""

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "待处理"),
        (STATUS_PROCESSING, "处理中"),
        (STATUS_COMPLETED, "已完成"),
        (STATUS_FAILED, "失败"),
    ]
    SOURCE_UPLOAD = "upload"
    SOURCE_ARTICLE = "article"
    SOURCE_CHOICES = [
        (SOURCE_UPLOAD, "上传文档"),
        (SOURCE_ARTICLE, "知识文章"),
    ]
    DOC_TYPE_PDF = "pdf"
    DOC_TYPE_MD = "md"
    DOC_TYPE_URL = "url"
    DOC_TYPE_CHOICES = [
        (DOC_TYPE_PDF, "PDF"),
        (DOC_TYPE_MD, "MD"),
        (DOC_TYPE_URL, "URL"),
    ]

    title = models.CharField(max_length=255, verbose_name="标题")
    file_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="文件名",
    )
    module = models.ForeignKey(
        TestModule,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="knowledge_documents",
        verbose_name="模块分类（测试模块）",
    )
    category = models.CharField(max_length=64, blank=True, default="", verbose_name="分类")
    document_type = models.CharField(
        max_length=16,
        choices=DOC_TYPE_CHOICES,
        default=DOC_TYPE_MD,
        verbose_name="文档类型",
    )
    tags = models.JSONField(default=list, blank=True, verbose_name="标签")
    source_type = models.CharField(
        max_length=16,
        choices=SOURCE_CHOICES,
        default=SOURCE_UPLOAD,
        verbose_name="来源类型",
    )
    article = models.ForeignKey(
        KnowledgeArticle,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ingest_docs",
        verbose_name="关联文章",
    )
    file_path = models.FileField(
        upload_to="knowledge_documents/",
        null=True,
        blank=True,
        verbose_name="文件路径",
    )
    source_url = models.URLField(
        max_length=2000,
        blank=True,
        default="",
        verbose_name="URL 来源地址",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="处理状态",
    )
    vector_db_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
        verbose_name="向量数据库ID",
    )
    semantic_summary = models.TextField(blank=True, default="", verbose_name="语义摘要")
    semantic_chunks = models.JSONField(default=list, blank=True, verbose_name="语义切片")
    error_message = models.TextField(blank=True, default="", verbose_name="失败原因")

    class Meta:
        db_table = "knowledge_document"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["category", "status", "-created_at"]),
        ]
