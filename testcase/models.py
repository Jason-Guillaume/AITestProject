import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models, transaction
from django.db.models import Max, F, Q
from django.utils import timezone
from common.models import BaseModel

logger = logging.getLogger(__name__)


class EnvironmentVariableDecryptionError(Exception):
    """敏感环境变量解密失败（密钥轮换、密文损坏等），由调用方决定如何提示或降级。"""


def _build_env_cipher() -> Fernet:
    """
    构建环境变量加解密器：
    1) 优先读取 AITEST_ENV_SECRET_KEY（需为 Fernet key）
    2) 未配置时使用 SECRET_KEY 派生（开发兜底）
    """
    raw_key = getattr(settings, "AITEST_ENV_SECRET_KEY", "") or ""
    if raw_key:
        return Fernet(raw_key.encode("utf-8"))
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    derived = base64.urlsafe_b64encode(digest)
    return Fernet(derived)


_ENV_CIPHER = _build_env_cipher()


class TestApproach(BaseModel):
    scheme_name = models.CharField(max_length=255, verbose_name="方案名称")
    version = models.CharField(max_length=255, verbose_name="版本")
    cover_image = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="封面图"
    )
    test_goal = models.TextField(null=True, blank=True, verbose_name="测试目标")
    test_category = models.IntegerField(
        choices=[
            (1, "单元测试"),
            (2, "集成测试"),
            (3, "系统测试"),
            (4, "用户测试"),
        ],
        default=1,
        verbose_name="测试类型",
    )

    class Meta:
        db_table = "test_approach"


class TestApproachImage(BaseModel):
    """
    方案图片：用于支持同一测试方案的历史上传与多图展示。
    """

    approach = models.ForeignKey(
        TestApproach,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="所属方案",
    )
    image = models.ImageField(
        upload_to="approach_images/",
        null=True,
        blank=True,
        verbose_name="图片文件",
    )
    sort_order = models.IntegerField(default=1, verbose_name="排序")

    class Meta:
        db_table = "test_approach_image"
        ordering = ["sort_order", "-create_time"]


class TestDesign(BaseModel):
    design_name = models.CharField(max_length=255, verbose_name="设计名称")
    req_count = models.IntegerField(default=0, verbose_name="需求数量")
    point_count = models.IntegerField(default=0, verbose_name="测试点数量")
    case_count = models.IntegerField(default=0, verbose_name="用例数量")
    review_status = models.IntegerField(
        choices=[(1, "未评审"), (2, "评审中"), (3, "已评审")],
        default=1,
        verbose_name="评审状态",
    )
    archive_status = models.IntegerField(
        choices=[(1, "未归档"), (2, "已归档")], default=1, verbose_name="归档状态"
    )

    class Meta:
        db_table = "test_design"


TEST_CASE_TYPE_FUNCTIONAL = "functional"
TEST_CASE_TYPE_API = "api"
TEST_CASE_TYPE_PERFORMANCE = "performance"
TEST_CASE_TYPE_SECURITY = "security"
TEST_CASE_TYPE_UI_AUTOMATION = "ui-automation"

TEST_CASE_TYPE_CHOICES = [
    (TEST_CASE_TYPE_FUNCTIONAL, "功能测试"),
    (TEST_CASE_TYPE_API, "API 测试"),
    (TEST_CASE_TYPE_PERFORMANCE, "性能测试"),
    (TEST_CASE_TYPE_SECURITY, "安全测试"),
    (TEST_CASE_TYPE_UI_AUTOMATION, "UI 自动化"),
]


class TestModule(BaseModel):
    project = models.ForeignKey(
        "project.TestProject",
        on_delete=models.CASCADE,
        related_name="modules",
        verbose_name="所属项目",
    )
    name = models.CharField(max_length=100, verbose_name="模块名称")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="父级模块",
    )
    test_type = models.CharField(
        max_length=32,
        choices=TEST_CASE_TYPE_CHOICES,
        default=TEST_CASE_TYPE_FUNCTIONAL,
        verbose_name="测试类型",
    )

    class Meta:
        db_table = "test_module"


class TestEnvironment(BaseModel):
    """
    测试环境实体：
    - base_url 供接口执行拼接或覆盖
    - db_config 保存数据库连通信息（JSON）
    """

    TYPE_DEV = "dev"
    TYPE_TEST = "test"
    TYPE_STAGING = "staging"
    TYPE_PROD = "prod"
    TYPE_CUSTOM = "custom"
    ENV_TYPE_CHOICES = [
        (TYPE_DEV, "开发环境"),
        (TYPE_TEST, "测试环境"),
        (TYPE_STAGING, "预发环境"),
        (TYPE_PROD, "生产镜像"),
        (TYPE_CUSTOM, "自定义"),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="环境名称")
    env_type = models.CharField(
        max_length=16,
        choices=ENV_TYPE_CHOICES,
        default=TYPE_TEST,
        verbose_name="环境类型",
    )
    base_url = models.CharField(
        max_length=2048, blank=True, default="", verbose_name="基础地址"
    )
    health_check_path = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="健康检查路径",
        help_text="相对路径，如 health、api/health；留空则对 Base URL 根路径发 GET",
    )
    db_config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="数据库配置(JSON)",
        help_text="示例：{host, port, user, password, db_name}",
    )
    description = models.TextField(blank=True, default="", verbose_name="环境描述")

    class Meta:
        db_table = "test_environment"
        ordering = ("-create_time",)


class EnvironmentHealthCheck(BaseModel):
    """环境健康检查记录。"""

    CHECK_DB = "db"
    CHECK_API = "api"
    CHECK_REDIS = "redis"
    CHECK_TYPE_CHOICES = [
        (CHECK_DB, "DB"),
        (CHECK_API, "API"),
        (CHECK_REDIS, "Redis"),
    ]

    STATUS_HEALTHY = "healthy"
    STATUS_UNHEALTHY = "unhealthy"
    STATUS_CHOICES = [
        (STATUS_HEALTHY, "Healthy"),
        (STATUS_UNHEALTHY, "Unhealthy"),
    ]

    check_type = models.CharField(
        max_length=16, choices=CHECK_TYPE_CHOICES, verbose_name="检查类型"
    )
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, verbose_name="健康状态"
    )
    response_time_ms = models.PositiveIntegerField(
        default=0, verbose_name="响应时间(ms)"
    )
    error_log = models.TextField(blank=True, default="", verbose_name="错误日志")
    target = models.CharField(
        max_length=255, blank=True, default="", verbose_name="检查目标"
    )
    dimension = models.JSONField(default=dict, blank=True, verbose_name="维度信息")

    class Meta:
        db_table = "environment_health_check"
        ordering = ("-create_time",)
        indexes = [
            models.Index(fields=["check_type", "status", "-create_time"]),
        ]


class EnvironmentVariable(BaseModel):
    """
    环境变量：
    - is_secret=True 时 value 按对称加密保存
    """

    ENV_VALUE_PREFIX = "enc::"

    environment = models.ForeignKey(
        TestEnvironment,
        on_delete=models.CASCADE,
        related_name="variables",
        verbose_name="所属环境",
    )
    key = models.CharField(max_length=128, verbose_name="变量名")
    value = models.TextField(blank=True, default="", verbose_name="变量值")
    is_secret = models.BooleanField(default=False, verbose_name="是否敏感变量")
    description = models.CharField(
        max_length=255, blank=True, default="", verbose_name="变量说明"
    )

    class Meta:
        db_table = "environment_variable"
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(
                fields=["environment", "key"], name="uniq_env_var_key"
            )
        ]

    @classmethod
    def encrypt_text(cls, plain_text: str) -> str:
        token = _ENV_CIPHER.encrypt((plain_text or "").encode("utf-8")).decode("utf-8")
        return f"{cls.ENV_VALUE_PREFIX}{token}"

    @classmethod
    def decrypt_text(cls, encrypted_text: str, *, errors: str = "ignore") -> str:
        """
        errors:
        - ignore: 解密失败时记录日志并返回空串（兼容旧行为）
        - raise: 解密失败抛出 EnvironmentVariableDecryptionError
        """
        if not encrypted_text:
            return ""
        if not encrypted_text.startswith(cls.ENV_VALUE_PREFIX):
            return encrypted_text
        token = encrypted_text[len(cls.ENV_VALUE_PREFIX) :]
        try:
            return _ENV_CIPHER.decrypt(token.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            logger.exception("环境变量解密失败：token 非法")
            if errors == "raise":
                raise EnvironmentVariableDecryptionError(
                    "环境变量解密失败：密文无效或密钥不匹配"
                ) from None
            return ""
        except Exception:
            logger.exception("环境变量解密失败：未知异常")
            if errors == "raise":
                raise EnvironmentVariableDecryptionError(
                    "环境变量解密失败：未知错误"
                ) from None
            return ""

    def get_decrypted_value(self) -> str:
        """返回可用于运行态注入的明文值；敏感变量解密失败时抛出 EnvironmentVariableDecryptionError。"""
        if not self.is_secret:
            return self.value or ""
        return self.decrypt_text(self.value or "", errors="raise")

    def save(self, *args, **kwargs):
        """
        敏感值自动加密：
        - 仅 is_secret=True 且当前非密文格式时执行加密
        """
        raw_value = self.value or ""
        if (
            self.is_secret
            and raw_value
            and not raw_value.startswith(self.ENV_VALUE_PREFIX)
        ):
            try:
                self.value = self.encrypt_text(raw_value)
            except Exception:
                logger.exception("环境变量加密失败")
                raise
        super().save(*args, **kwargs)


class TestCase(BaseModel):
    TEST_TYPE_FUNCTIONAL = TEST_CASE_TYPE_FUNCTIONAL
    TEST_TYPE_API = TEST_CASE_TYPE_API
    TEST_TYPE_PERFORMANCE = TEST_CASE_TYPE_PERFORMANCE
    TEST_TYPE_SECURITY = TEST_CASE_TYPE_SECURITY
    TEST_TYPE_UI_AUTOMATION = TEST_CASE_TYPE_UI_AUTOMATION
    TEST_TYPE_CHOICES = TEST_CASE_TYPE_CHOICES

    module = models.ForeignKey(
        TestModule,
        on_delete=models.SET_NULL,
        null=True,
        related_name="testcases",
        verbose_name="所属模块",
    )
    ai_run = models.ForeignKey(
        "assistant.AiCaseGenerationRun",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="imported_testcases",
        verbose_name="AI 生成批次（可选）",
    )
    case_name = models.CharField(max_length=255, verbose_name="用例名称")
    case_number = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="业务编号",
    )
    test_type = models.CharField(
        max_length=32,
        choices=TEST_CASE_TYPE_CHOICES,
        default=TEST_CASE_TYPE_FUNCTIONAL,
        verbose_name="测试类型",
    )
    level = models.CharField(
        max_length=10,
        choices=[("P0", "P0"), ("P1", "P1"), ("P2", "P2"), ("P3", "P3")],
        default="P2",
        verbose_name="用例等级",
    )
    is_valid = models.BooleanField(default=True, verbose_name="是否有效")
    exec_count = models.IntegerField(default=0, verbose_name="执行次数")
    review_status = models.IntegerField(
        choices=[(1, "未评审"), (2, "评审中"), (3, "已评审")],
        default=1,
        verbose_name="评审状态",
    )
    archive_status = models.IntegerField(
        choices=[(1, "未归档"), (2, "已归档")], default=1, verbose_name="归档状态"
    )
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="删除时间")

    class ActiveManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(is_deleted=False)

    class DeletedManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(is_deleted=True)

    objects = ActiveManager()
    all_objects = models.Manager()
    deleted_objects = DeletedManager()

    class Meta:
        db_table = "test_case"
        constraints = [
            models.UniqueConstraint(
                fields=["test_type", "case_number"],
                condition=Q(is_deleted=False),
                name="uniq_active_case_number_per_type",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk is None and self.case_number is None:
            with transaction.atomic():
                # 编号按测试类型独立递增；用 all_objects 取 Max，避免与回收站中仍占用的编号冲突。
                scope = {"test_type": self.test_type}
                scoped_qs = TestCase.all_objects.select_for_update().filter(**scope)
                max_case_number = scoped_qs.aggregate(
                    max_case_number=Max("case_number")
                )["max_case_number"]
                self.case_number = (max_case_number or 0) + 1
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)

    def _get_subtype_snapshot_data(self) -> dict:
        """子类重写：纳入版本快照的 subtype 段。"""
        return {}

    def _apply_subtype_snapshot(self, subtype: dict) -> None:
        """子类重写：从快照 subtype 回填子表字段。"""
        pass

    @property
    def type_sequence(self):
        """兼容业务语义：type_sequence 复用现有 case_number。"""
        return self.case_number

    def delete(self, using=None, keep_parents=False):
        """默认软删除。"""
        if self.is_deleted:
            return
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "update_time"])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at", "update_time"])

    def hard_delete(self):
        """
        物理删除并重排同 test_type 下序列号（case_number/type_sequence）。
        按要求使用事务 + F 表达式批量更新，避免逐条循环更新。
        """
        with transaction.atomic():
            seq = self.case_number
            test_type = self.test_type
            pk = self.pk
            super(TestCase, self).delete()
            if seq is not None:
                TestCase.all_objects.filter(
                    test_type=test_type,
                    case_number__gt=seq,
                    is_deleted=False,
                ).update(case_number=F("case_number") - 1)

    def build_snapshot_payload(self):
        """
        生成用例当前完整快照，供版本回溯使用。
        """
        subtype_data = self._get_subtype_snapshot_data()

        steps = [
            {
                "id": s.id,
                "step_number": s.step_number,
                "step_desc": s.step_desc,
                "expected_result": s.expected_result,
            }
            for s in self.steps.filter(is_deleted=False).order_by("step_number", "id")
        ]

        return {
            "schema_version": "1.0",
            "base": {
                "id": self.id,
                "module_id": self.module_id,
                "case_name": self.case_name,
                "case_number": self.case_number,
                "test_type": self.test_type,
                "level": self.level,
                "is_valid": self.is_valid,
                "exec_count": self.exec_count,
                "review_status": self.review_status,
                "archive_status": self.archive_status,
                "is_deleted": self.is_deleted,
            },
            "subtype": subtype_data,
            "steps": steps,
        }

    def apply_snapshot_payload(self, snapshot: dict):
        """
        根据快照回填当前用例（主字段 + 子类型 + 步骤）。
        """
        base = snapshot.get("base") or {}
        subtype = snapshot.get("subtype") or {}
        steps = snapshot.get("steps") or []

        self.case_name = base.get("case_name", self.case_name)
        self.level = base.get("level", self.level)
        self.is_valid = bool(base.get("is_valid", self.is_valid))
        self.review_status = int(base.get("review_status", self.review_status))
        self.archive_status = int(base.get("archive_status", self.archive_status))
        self.save(
            update_fields=[
                "case_name",
                "level",
                "is_valid",
                "review_status",
                "archive_status",
                "update_time",
            ]
        )

        self._apply_subtype_snapshot(subtype)

        # 使用“软重建”步骤：旧步骤置删，新步骤按快照插入。
        self.steps.filter(is_deleted=False).update(is_deleted=True)
        for idx, st in enumerate(steps, start=1):
            TestCaseStep.objects.create(
                testcase=self,
                step_number=int(st.get("step_number") or idx),
                step_desc=st.get("step_desc") or "",
                expected_result=st.get("expected_result") or "",
            )


class TestCaseVersion(BaseModel):
    """
    用例版本快照：记录用例在某发布计划关联时的完整状态。
    """

    test_case = models.ForeignKey(
        TestCase,
        on_delete=models.CASCADE,
        related_name="versions",
        verbose_name="测试用例",
    )
    release_plan = models.ForeignKey(
        "project.ReleasePlan",
        on_delete=models.CASCADE,
        related_name="case_versions",
        verbose_name="发布计划",
    )
    snapshot_no = models.PositiveIntegerField(default=1, verbose_name="快照序号")
    version_label = models.CharField(max_length=64, verbose_name="版本标签")
    case_snapshot = models.JSONField(default=dict, blank=True, verbose_name="用例快照")
    source_version = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="derived_versions",
        verbose_name="来源快照",
    )

    class Meta:
        db_table = "test_case_version"
        ordering = ("-create_time",)
        indexes = [
            models.Index(fields=["test_case", "release_plan", "-snapshot_no"]),
            models.Index(fields=["release_plan", "-create_time"]),
        ]

    @classmethod
    def create_version(
        cls, *, test_case, release_plan, creator=None, source_version=None
    ):
        """
        生成并保存用例快照版本。
        """
        with transaction.atomic():
            snapshot = test_case.build_snapshot_payload()
            last = (
                cls.objects.select_for_update()
                .filter(test_case=test_case, release_plan=release_plan)
                .order_by("-snapshot_no")
                .first()
            )
            next_no = 1 if not last else last.snapshot_no + 1
            version_label = f"{release_plan.version_no}-S{next_no:03d}"
            create_kwargs = {
                "test_case": test_case,
                "release_plan": release_plan,
                "snapshot_no": next_no,
                "version_label": version_label,
                "case_snapshot": snapshot,
                "source_version": source_version,
            }
            if creator is not None and getattr(creator, "is_authenticated", False):
                create_kwargs["creator"] = creator
                create_kwargs["updater"] = creator
            return cls.objects.create(**create_kwargs)


class ApiTestCase(TestCase):
    """API 测试用例扩展表（多表继承）：请求定义仅在此存储。"""

    api_url = models.CharField(
        max_length=2048, blank=True, default="", verbose_name="API 地址"
    )
    api_method = models.CharField(
        max_length=16, default="GET", verbose_name="HTTP 方法"
    )
    api_headers = models.JSONField(
        default=dict, blank=True, verbose_name="请求头(JSON)"
    )
    api_body = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="请求体(JSON)",
        help_text='JSON 对象或数组；历史纯文本会迁移为 {"_legacy_text": "..."}',
    )
    api_expected_status = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="期望状态码",
        help_text="为空则仅校验 2xx；与步骤里「预期结果」子串断言可同时生效",
    )
    api_source_curl = models.TextField(
        blank=True,
        default="",
        verbose_name="来源 cURL",
        help_text="生成或「从 cURL 填充」时保存的原始命令；执行前可据此还原请求",
    )

    def _get_subtype_snapshot_data(self) -> dict:
        return {
            "api_url": self.api_url,
            "api_method": self.api_method,
            "api_headers": self.api_headers,
            "api_body": self.api_body,
            "api_expected_status": self.api_expected_status,
            "api_source_curl": getattr(self, "api_source_curl", "") or "",
        }

    def _apply_subtype_snapshot(self, subtype: dict) -> None:
        self.api_url = subtype.get("api_url", self.api_url)
        self.api_method = subtype.get("api_method", self.api_method)
        self.api_headers = subtype.get("api_headers", self.api_headers)
        self.api_body = subtype.get("api_body", self.api_body)
        self.api_expected_status = subtype.get(
            "api_expected_status", self.api_expected_status
        )
        self.api_source_curl = subtype.get("api_source_curl", self.api_source_curl)
        self.save()

    class Meta:
        db_table = "testcase_apitestcase"


class PerfTestCase(TestCase):
    """性能测试用例扩展表。"""

    concurrency = models.PositiveIntegerField(default=1, verbose_name="并发数")
    duration_seconds = models.PositiveIntegerField(
        default=60, verbose_name="持续时间(秒)"
    )
    target_rps = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="目标 RPS",
    )

    def _get_subtype_snapshot_data(self) -> dict:
        return {
            "concurrency": self.concurrency,
            "duration_seconds": self.duration_seconds,
            "target_rps": self.target_rps,
        }

    def _apply_subtype_snapshot(self, subtype: dict) -> None:
        self.concurrency = int(subtype.get("concurrency", self.concurrency))
        self.duration_seconds = int(
            subtype.get("duration_seconds", self.duration_seconds)
        )
        self.target_rps = subtype.get("target_rps", self.target_rps)
        self.save()

    class Meta:
        db_table = "testcase_perftestcase"


class SecurityTestCase(TestCase):
    """安全测试用例扩展表。"""

    RISK_LEVEL_CHOICES = [
        ("高", "高"),
        ("中", "中"),
        ("低", "低"),
    ]

    attack_surface = models.CharField(
        max_length=512, blank=True, default="", verbose_name="攻击面/范围说明"
    )
    tool_preset = models.CharField(
        max_length=128, blank=True, default="", verbose_name="工具/扫描模板"
    )
    risk_level = models.CharField(
        max_length=8,
        blank=True,
        default="",
        choices=RISK_LEVEL_CHOICES,
        verbose_name="风险等级",
    )

    def _get_subtype_snapshot_data(self) -> dict:
        return {
            "attack_surface": self.attack_surface,
            "tool_preset": self.tool_preset,
            "risk_level": self.risk_level,
        }

    def _apply_subtype_snapshot(self, subtype: dict) -> None:
        self.attack_surface = subtype.get("attack_surface", self.attack_surface)
        self.tool_preset = subtype.get("tool_preset", self.tool_preset)
        self.risk_level = subtype.get("risk_level", self.risk_level)
        self.save()

    class Meta:
        db_table = "testcase_securitytestcase"


class UITestCase(TestCase):
    """UI 自动化用例扩展表。"""

    app_under_test = models.CharField(
        max_length=255, blank=True, default="", verbose_name="被测应用/包名"
    )
    primary_locator = models.CharField(
        max_length=512, blank=True, default="", verbose_name="主定位符"
    )
    automation_framework = models.CharField(
        max_length=64, blank=True, default="", verbose_name="自动化框架"
    )

    def _get_subtype_snapshot_data(self) -> dict:
        return {
            "app_under_test": self.app_under_test,
            "primary_locator": self.primary_locator,
            "automation_framework": self.automation_framework,
        }

    def _apply_subtype_snapshot(self, subtype: dict) -> None:
        self.app_under_test = subtype.get("app_under_test", self.app_under_test)
        self.primary_locator = subtype.get("primary_locator", self.primary_locator)
        self.automation_framework = subtype.get(
            "automation_framework", self.automation_framework
        )
        self.save()

    class Meta:
        db_table = "testcase_uitestcase"


class ApiTestLog(BaseModel):
    """单条 API 用例一次实际 HTTP 执行记录。"""

    test_case = models.ForeignKey(
        TestCase,
        on_delete=models.CASCADE,
        related_name="api_test_logs",
        verbose_name="测试用例",
    )
    request_url = models.CharField(max_length=2048, verbose_name="请求 URL")
    request_method = models.CharField(max_length=16, verbose_name="请求方法")
    request_headers = models.JSONField(default=dict, blank=True, verbose_name="请求头")
    request_body = models.TextField(blank=True, default="", verbose_name="请求体")
    response_status_code = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="响应状态码"
    )
    response_body = models.TextField(blank=True, default="", verbose_name="响应体")
    response_time_ms = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="耗时(ms)"
    )
    is_passed = models.BooleanField(default=False, verbose_name="是否通过")

    class Meta:
        db_table = "api_test_log"
        ordering = ["-create_time"]


class ExecutionLog(BaseModel):
    """
    API 单次执行完整记录：Request/Response 全文、耗时、执行状态与断言明细。
    与 ApiTestLog 并存：新执行逻辑优先写入本表；ApiTestLog 仍可用于兼容旧接口展示。
    """

    class ExecutionStatus(models.TextChoices):
        SUCCESS = "success", "成功"
        ASSERTION_FAILED = "assertion_failed", "断言未通过"
        REQUEST_ERROR = "request_error", "请求异常"

    test_case = models.ForeignKey(
        TestCase,
        on_delete=models.CASCADE,
        related_name="execution_logs",
        verbose_name="测试用例",
    )
    request_url = models.CharField(max_length=2048, verbose_name="请求 URL")
    request_method = models.CharField(max_length=16, verbose_name="HTTP 方法")
    request_headers = models.JSONField(default=dict, blank=True, verbose_name="请求头")
    request_body_text = models.TextField(
        blank=True, default="", verbose_name="请求体全文"
    )
    response_status_code = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="响应状态码"
    )
    response_headers = models.JSONField(default=dict, blank=True, verbose_name="响应头")
    response_body_text = models.TextField(
        blank=True, default="", verbose_name="响应体全文"
    )
    duration_ms = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="耗时(ms)"
    )
    execution_status = models.CharField(
        max_length=32,
        choices=ExecutionStatus.choices,
        default=ExecutionStatus.REQUEST_ERROR,
        verbose_name="执行状态",
    )
    assertion_results = models.JSONField(
        default=list,
        blank=True,
        verbose_name="断言结果",
        help_text='示例: [{"name":"status","passed":true,"detail":"..."}]',
    )
    is_passed = models.BooleanField(default=False, verbose_name="总是否通过")
    error_message = models.TextField(blank=True, default="", verbose_name="错误信息")
    trace_id = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="执行追踪ID",
        help_text="单次执行唯一标识，用于与测试报告等关联（新记录必有值）",
    )
    request_payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="请求快照(JSON)",
        help_text="执行时真实请求：method/url/headers/body",
    )
    response_payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="响应快照(JSON)",
        help_text="服务端返回原始数据摘要：status_code/headers/body 等",
    )

    class Meta:
        db_table = "api_execution_log"
        ordering = ["-create_time"]
        indexes = [
            models.Index(fields=["test_case", "-create_time"]),
        ]


class TestCaseStep(BaseModel):
    testcase = models.ForeignKey(
        TestCase,
        on_delete=models.CASCADE,
        related_name="steps",
        verbose_name="所属用例",
    )
    step_number = models.IntegerField(verbose_name="步骤编号")
    step_desc = models.TextField(verbose_name="步骤描述")
    expected_result = models.TextField(verbose_name="预期结果")

    class Meta:
        db_table = "test_case_step"
        ordering = ["step_number"]
