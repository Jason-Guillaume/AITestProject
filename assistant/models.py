from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
import os

from common.models import BaseModel
from testcase.models import TestModule
from django.conf import settings


class KnowledgeArticle(BaseModel):
    """RAG 测试知识库文章。"""

    VISIBILITY_PRIVATE = "private"
    VISIBILITY_PROJECT = "project"
    VISIBILITY_ORG = "org"
    VISIBILITY_CHOICES = [
        (VISIBILITY_PRIVATE, "仅自己可见"),
        (VISIBILITY_PROJECT, "项目内共享"),
        (VISIBILITY_ORG, "组织内共享"),
    ]

    org = models.ForeignKey(
        "user.Organization",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="knowledge_articles",
        verbose_name="所属组织",
    )
    visibility_scope = models.CharField(
        max_length=16,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PRIVATE,
        db_index=True,
        verbose_name="可见范围",
    )

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

    VISIBILITY_PRIVATE = KnowledgeArticle.VISIBILITY_PRIVATE
    VISIBILITY_PROJECT = KnowledgeArticle.VISIBILITY_PROJECT
    VISIBILITY_ORG = KnowledgeArticle.VISIBILITY_ORG
    VISIBILITY_CHOICES = KnowledgeArticle.VISIBILITY_CHOICES

    org = models.ForeignKey(
        "user.Organization",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="knowledge_documents",
        verbose_name="所属组织",
    )
    visibility_scope = models.CharField(
        max_length=16,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PRIVATE,
        db_index=True,
        verbose_name="可见范围",
    )

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
    category = models.CharField(
        max_length=64, blank=True, default="", verbose_name="分类"
    )
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
    semantic_chunks = models.JSONField(
        default=list, blank=True, verbose_name="语义切片"
    )
    error_message = models.TextField(blank=True, default="", verbose_name="失败原因")

    class Meta:
        db_table = "knowledge_document"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["category", "status", "-created_at"]),
        ]


class GeneratedTestArtifact(BaseModel):
    """
    生成测试资产（最小闭环）：
    - 允许从知识文档切片/知识库问答 citations 生成结构化产物并落库
    - 保存引用来源，便于追溯与审计
    """

    TYPE_TEST_PLAN = "test_plan"
    TYPE_TEST_POINTS = "test_points"
    TYPE_CASE_DRAFT = "case_draft"
    TYPE_API_SCENARIO = "api_scenario"
    TYPE_CHOICES = [
        (TYPE_TEST_PLAN, "测试计划"),
        (TYPE_TEST_POINTS, "测试点"),
        (TYPE_CASE_DRAFT, "用例草稿"),
        (TYPE_API_SCENARIO, "API 场景"),
    ]

    org = models.ForeignKey(
        "user.Organization",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_test_artifacts",
        verbose_name="所属组织",
    )
    project = models.ForeignKey(
        "project.TestProject",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_test_artifacts",
        verbose_name="所属项目",
    )
    module = models.ForeignKey(
        TestModule,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_test_artifacts",
        verbose_name="关联模块",
    )
    source_document = models.ForeignKey(
        KnowledgeDocument,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_artifacts",
        verbose_name="来源知识文档",
    )
    source_question = models.TextField(
        blank=True,
        default="",
        verbose_name="来源问题（可选）",
    )

    artifact_type = models.CharField(
        max_length=32,
        choices=TYPE_CHOICES,
        db_index=True,
        verbose_name="资产类型",
    )
    title = models.CharField(max_length=255, blank=True, default="", verbose_name="标题")
    content = models.JSONField(default=dict, blank=True, verbose_name="结构化内容")
    citations = models.JSONField(default=list, blank=True, verbose_name="引用来源（citations/chunks）")
    model_used = models.CharField(max_length=128, blank=True, default="", verbose_name="模型（可选）")

    class Meta:
        db_table = "generated_test_artifact"
        ordering = ("-create_time",)
        indexes = [
            models.Index(fields=["artifact_type", "-create_time"]),
            models.Index(fields=["project", "-create_time"]),
            models.Index(fields=["module", "-create_time"]),
            models.Index(fields=["source_document", "-create_time"]),
        ]


class AiUsageEvent(models.Model):
    """
    AI 治理：调用审计与用量统计（最小可用版本）。

    设计目标：
    - 记录“谁在什么时候调用了哪个 AI 能力、是否成功、耗时与规模”等关键字段
    - 不落敏感原文：仅保存字符数、关键枚举与少量 meta（已做脱敏）
    """

    ACTION_GENERATE_CASES = "generate_cases"
    ACTION_GENERATE_CASES_STREAM = "generate_cases_stream"
    ACTION_PHASE1_PREVIEW = "phase1_preview"
    ACTION_TEST_CONNECTION = "test_connection"
    ACTION_VERIFY_CONNECTION = "verify_connection"
    ACTION_KNOWLEDGE_AUTOFILL = "knowledge_autofill"
    ACTION_KNOWLEDGE_ASK = "knowledge_ask"
    ACTION_SECURITY_GENERATE = "security_generate"
    ACTION_SECURITY_ANALYZE = "security_analyze"
    ACTION_CHOICES = [
        (ACTION_GENERATE_CASES, "生成用例（同步）"),
        (ACTION_GENERATE_CASES_STREAM, "生成用例（流式）"),
        (ACTION_PHASE1_PREVIEW, "Phase1 预览"),
        (ACTION_TEST_CONNECTION, "模型连通性测试"),
        (ACTION_VERIFY_CONNECTION, "固定模型连通性校验"),
        (ACTION_KNOWLEDGE_AUTOFILL, "知识库自动填表"),
        (ACTION_KNOWLEDGE_ASK, "知识库问答（可追溯）"),
        (ACTION_SECURITY_GENERATE, "安全用例生成（规则）"),
        (ACTION_SECURITY_ANALYZE, "执行安全分析（规则）"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_usage_events",
        verbose_name="调用用户",
    )
    action = models.CharField(
        max_length=64, choices=ACTION_CHOICES, db_index=True, verbose_name="动作"
    )
    endpoint = models.CharField(
        max_length=128, blank=True, default="", verbose_name="接口路径"
    )
    success = models.BooleanField(default=False, db_index=True, verbose_name="是否成功")
    status_code = models.IntegerField(default=0, verbose_name="HTTP 状态码")
    error_code = models.CharField(
        max_length=64, blank=True, default="", verbose_name="错误码（可选）"
    )
    error_message = models.CharField(
        max_length=512, blank=True, default="", verbose_name="错误摘要（脱敏）"
    )

    model_used = models.CharField(
        max_length=128, blank=True, default="", verbose_name="模型名"
    )
    test_type = models.CharField(
        max_length=32, blank=True, default="", verbose_name="测试类型（可选）"
    )
    module_id = models.IntegerField(
        null=True, blank=True, db_index=True, verbose_name="模块ID（可选）"
    )
    streamed = models.BooleanField(default=False, verbose_name="是否流式")
    all_covered = models.BooleanField(default=False, verbose_name="是否判定无需生成")

    latency_ms = models.IntegerField(default=0, verbose_name="耗时(ms)")
    prompt_chars = models.IntegerField(default=0, verbose_name="输入字符数")
    output_chars = models.IntegerField(default=0, verbose_name="输出字符数")
    cases_count = models.IntegerField(default=0, verbose_name="生成用例条数（可选）")

    meta = models.JSONField(default=dict, blank=True, verbose_name="元信息（脱敏）")
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, verbose_name="创建时间"
    )

    class Meta:
        db_table = "ai_usage_event"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]


class AiPatch(models.Model):
    """
    AI 变更补丁（最小可用）：
    - 由 AI 建议生成，但默认不自动写入业务对象
    - 支持 apply / rollback，并可审计
    """

    STATUS_DRAFT = "draft"
    STATUS_APPLIED = "applied"
    STATUS_ROLLED_BACK = "rolled_back"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "草稿"),
        (STATUS_APPLIED, "已应用"),
        (STATUS_ROLLED_BACK, "已回滚"),
        (STATUS_CANCELLED, "已取消"),
    ]

    RISK_LOW = "low"
    RISK_MEDIUM = "medium"
    RISK_HIGH = "high"
    RISK_CHOICES = [
        (RISK_LOW, "低"),
        (RISK_MEDIUM, "中"),
        (RISK_HIGH, "高"),
    ]

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_patches",
        verbose_name="创建人",
    )
    target_type = models.CharField(
        max_length=64, db_index=True, verbose_name="目标类型（app.Model）"
    )
    target_id = models.CharField(max_length=64, db_index=True, verbose_name="目标ID")
    source_execution_log_id = models.IntegerField(
        null=True, blank=True, db_index=True, verbose_name="来源执行日志ID（可选）"
    )

    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True
    )
    risk_level = models.CharField(
        max_length=16, choices=RISK_CHOICES, default=RISK_MEDIUM, db_index=True
    )
    summary = models.CharField(max_length=512, blank=True, default="", verbose_name="摘要")
    risks = models.CharField(max_length=1000, blank=True, default="", verbose_name="风险说明")

    before = models.JSONField(default=dict, blank=True, verbose_name="应用前快照（最小）")
    after = models.JSONField(default=dict, blank=True, verbose_name="应用后目标（最小）")
    changes = models.JSONField(default=list, blank=True, verbose_name="变更描述（结构化）")

    applied_at = models.DateTimeField(null=True, blank=True, db_index=True)
    rolled_back_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_patch"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["target_type", "target_id", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]


class AiCaseGenerationRun(models.Model):
    """
    AI 生成用例批次（run）：
    - 记录一次“生成请求→产出”的关键元数据，便于追溯、导入关联、质量回放与成本分析。
    - 不保存完整敏感原文：仅保存 hash、少量摘要与结构化结果（如 Phase1 分析）。
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_case_generation_runs",
        verbose_name="发起用户",
    )

    action = models.CharField(
        max_length=64, blank=True, default="", db_index=True, verbose_name="动作"
    )
    test_type = models.CharField(
        max_length=32, blank=True, default="", db_index=True, verbose_name="测试类型"
    )
    module_id = models.IntegerField(
        null=True, blank=True, db_index=True, verbose_name="模块ID（可选）"
    )
    streamed = models.BooleanField(default=False, verbose_name="是否流式")

    model_used = models.CharField(
        max_length=128, blank=True, default="", verbose_name="模型名"
    )
    prompt_version = models.CharField(
        max_length=64, blank=True, default="v1", verbose_name="提示词版本"
    )
    params = models.JSONField(default=dict, blank=True, verbose_name="参数（脱敏）")

    requirement_sha256 = models.CharField(
        max_length=64, blank=True, default="", db_index=True, verbose_name="需求哈希"
    )
    requirement_preview = models.CharField(
        max_length=256, blank=True, default="", verbose_name="需求摘要（脱敏）"
    )
    ext_config = models.JSONField(
        default=dict, blank=True, verbose_name="扩展配置（脱敏）"
    )

    phase1_analysis = models.JSONField(
        default=dict, blank=True, verbose_name="Phase1 分析结果"
    )
    phase1_override = models.JSONField(
        default=dict, blank=True, verbose_name="Phase1 覆盖输入（可选）"
    )

    success = models.BooleanField(default=False, db_index=True, verbose_name="是否成功")
    all_covered = models.BooleanField(default=False, verbose_name="是否判定无需生成")
    cases_count = models.IntegerField(default=0, verbose_name="生成用例条数")
    prompt_chars = models.IntegerField(default=0, verbose_name="输入字符数")
    output_chars = models.IntegerField(default=0, verbose_name="输出字符数")
    latency_ms = models.IntegerField(default=0, verbose_name="耗时(ms)")

    error_code = models.CharField(
        max_length=64, blank=True, default="", verbose_name="错误码（可选）"
    )
    error_message = models.CharField(
        max_length=512, blank=True, default="", verbose_name="错误摘要（脱敏）"
    )

    meta = models.JSONField(default=dict, blank=True, verbose_name="元信息（脱敏）")
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, verbose_name="创建时间"
    )

    class Meta:
        db_table = "ai_case_generation_run"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["test_type", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["module_id", "-created_at"]),
        ]


class UIScriptUpload(models.Model):
    """UI自动化脚本上传模型"""

    class ScriptType(models.TextChoices):
        LINEAR = 'LINEAR', _('线性脚本')
        POM = 'POM', _('Page Object Model')

    id = models.AutoField(primary_key=True, verbose_name='脚本ID')
    name = models.CharField(
        max_length=255,
        verbose_name='脚本名称',
        help_text='脚本的显示名称'
    )
    script_type = models.CharField(
        max_length=10,
        choices=ScriptType.choices,
        default=ScriptType.LINEAR,
        verbose_name='脚本类型'
    )

    file_path = models.FileField(
        upload_to='ui_scripts/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['py', 'zip'])],
        blank=True,
        null=True,
        verbose_name='脚本文件',
        help_text='单文件(.py)或ZIP包'
    )

    git_repo_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='Git仓库URL',
        help_text='关联的Git仓库地址（可选）'
    )

    entry_point = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='执行入口路径',
        help_text='脚本执行的入口文件路径，如: main.py 或 tests/test_login.py'
    )

    workspace_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='工作空间路径',
        help_text='ZIP解压后的目录路径'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='是否启用'
    )

    class Meta:
        db_table = 'ui_script_upload'
        verbose_name = 'UI自动化脚本'
        verbose_name_plural = 'UI自动化脚本'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['script_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_script_type_display()})"

    @property
    def file_extension(self):
        """获取文件扩展名"""
        return os.path.splitext(self.file_path.name)[1]

    @property
    def is_zip(self):
        """判断是否为ZIP文件"""
        return self.file_extension.lower() == '.zip'


class UIScriptExecution(models.Model):
    """UI脚本执行记录"""

    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_TIMEOUT = 'timeout'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, '等待执行'),
        (STATUS_RUNNING, '执行中'),
        (STATUS_SUCCESS, '执行成功'),
        (STATUS_FAILED, '执行失败'),
        (STATUS_TIMEOUT, '执行超时'),
        (STATUS_CANCELLED, '已取消'),
    ]

    id = models.AutoField(primary_key=True, verbose_name='执行ID')
    execution_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name='执行唯一标识'
    )

    script = models.ForeignKey(
        UIScriptUpload,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='关联脚本'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name='执行状态'
    )

    return_code = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='返回码'
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='开始时间'
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='完成时间'
    )

    duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name='执行时长(秒)'
    )

    error_message = models.TextField(
        blank=True,
        default='',
        verbose_name='错误信息'
    )

    log_file_path = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name='日志文件路径'
    )

    triggered_by = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='触发方式'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )

    class Meta:
        db_table = 'ui_script_execution'
        verbose_name = 'UI脚本执行记录'
        verbose_name_plural = 'UI脚本执行记录'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['execution_id']),
            models.Index(fields=['script', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"{self.script.name} - {self.execution_id} ({self.get_status_display()})"

    @property
    def is_running(self):
        """是否正在执行"""
        return self.status == self.STATUS_RUNNING

    @property
    def is_completed(self):
        """是否已完成"""
        return self.status in [
            self.STATUS_SUCCESS,
            self.STATUS_FAILED,
            self.STATUS_TIMEOUT,
            self.STATUS_CANCELLED
        ]

    @property
    def is_success(self):
        """是否执行成功"""
        return self.status == self.STATUS_SUCCESS
