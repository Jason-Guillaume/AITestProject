from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from common.models import BaseModel


class TestProject(BaseModel):
    STATUS_IN_PROGRESS = 1
    STATUS_COMPLETED = 2
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, "进行中"),
        (STATUS_COMPLETED, "已完成"),
    ]

    project_name = models.CharField(max_length=255, verbose_name="项目名称")
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sub_projects",
        verbose_name="父项目",
    )
    description = models.TextField(null=True, blank=True, verbose_name="项目描述")
    icon = models.ImageField(
        upload_to="project_covers/",
        null=True,
        blank=True,
        verbose_name="项目封面图",
    )
    project_status = models.IntegerField(
        choices=STATUS_CHOICES,
        default=STATUS_IN_PROGRESS,
        verbose_name="项目状态",
    )
    progress = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="进度百分比",
        help_text="进行中时展示为 0-100；已完成可忽略",
    )
    members = models.ManyToManyField(
        "user.User", related_name="projects", verbose_name="项目成员"
    )

    class Meta:
        db_table = "test_project"
        verbose_name = "项目管理"

    def clean(self):
        if self.parent_id is None:
            return
        if self.pk and self.parent_id == self.pk:
            raise ValidationError("项目不能将自己设为父项目")

        # 检查循环引用：沿 parent 链向上追溯
        seen = {self.pk} if self.pk else set()
        p = self.parent
        while p is not None:
            if p.pk in seen:
                raise ValidationError("项目不能形成循环引用")
            seen.add(p.pk)
            p = p.parent

    def update_progress(self, save: bool = True) -> int:
        """
        根据该项目下关联测试计划完成率自动计算进度。
        口径：project → release plans → execution.TestPlan(plan_status=3) 完成数 / 总数。
        """
        from execution.models import TestPlan

        plan_qs = TestPlan.objects.filter(version__project=self, is_deleted=False)
        total = plan_qs.count()
        progress = 0
        if total > 0:
            completed = plan_qs.filter(plan_status=3).count()
            progress = int((completed / total) * 100)

        self.progress = progress
        if save:
            self.save(update_fields=["progress", "update_time"])
        return progress


class TestTask(BaseModel):
    task_title = models.CharField(max_length=255, verbose_name="任务标题")
    task_desc = models.TextField(null=True, blank=True, verbose_name="任务描述")
    status = models.IntegerField(
        choices=[(1, "待处理"), (2, "处理中"), (3, "已处理")],
        default=1,
        verbose_name="任务状态",
    )
    assignee = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="assigned_tasks",
        verbose_name="经办人",
    )

    class Meta:
        db_table = "test_task"
        verbose_name = "任务看板"


class ReleasePlan(BaseModel):
    project = models.ForeignKey(
        TestProject,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="release_plans",
        verbose_name="所属项目",
    )
    release_name = models.CharField(max_length=255, verbose_name="发布名称")
    version_no = models.CharField(max_length=255, verbose_name="版本号")
    release_date = models.DateTimeField(verbose_name="计划发布日期")
    status = models.IntegerField(
        choices=[(1, "待发布"), (2, "已发布"), (3, "已取消")],
        default=1,
        verbose_name="发布状态",
    )
    test_cases = models.ManyToManyField(
        "testcase.TestCase",
        related_name="release_plans",
        blank=True,
        through="ReleasePlanTestCase",
        verbose_name="关联测试用例",
    )

    class Meta:
        db_table = "release_plan"
        verbose_name = "发布计划"
        constraints = [
            # 兼容 MySQL：用 is_deleted 参与唯一性，达到“仅对未删除记录唯一”的效果
            models.UniqueConstraint(
                fields=["project", "version_no", "is_deleted"],
                name="uniq_releaseplan_version_per_project_deletedflag",
            )
        ]


class ReleasePlanTestCase(models.Model):
    """
    ReleasePlan 与 TestCase 的关联中间表，用于控制关联关系的软删除。
    """

    release_plan = models.ForeignKey(
        ReleasePlan,
        on_delete=models.CASCADE,
        related_name="release_plan_test_cases",
    )
    test_case = models.ForeignKey(
        "testcase.TestCase",
        on_delete=models.CASCADE,
        related_name="release_plan_test_cases",
    )
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_deleted = models.BooleanField(default=False, verbose_name="是否已删除")

    class Meta:
        db_table = "release_plan_test_case"
        constraints = [
            # 兼容 MySQL：用 is_deleted 参与唯一性，达到“仅对未删除记录唯一”的效果
            models.UniqueConstraint(
                fields=["release_plan", "test_case", "is_deleted"],
                name="uniq_releaseplan_testcase_deletedflag",
            ),
        ]

# ---------------------------------------------------------------------------
# CI/CD Pipeline models
# ---------------------------------------------------------------------------


class Pipeline(BaseModel):
    """CI/CD 构建项目（对齐 Jenkins 概念：自由风格 vs 流水线脚本）。"""

    STATUS_PENDING = 0
    STATUS_RUNNING = 1
    STATUS_SUCCESS = 2
    STATUS_FAIL = 3

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAIL, "Fail"),
    ]

    # 项目类型：自由风格 = 单段 Shell；流水线脚本 = 可用 # stage: 分段依次执行
    KIND_FREESTYLE = 0
    KIND_PIPELINE = 1
    KIND_CHOICES = [
        (KIND_FREESTYLE, "自由风格"),
        (KIND_PIPELINE, "流水线脚本"),
    ]

    name = models.CharField(max_length=255, verbose_name="名称")
    kind = models.IntegerField(
        choices=KIND_CHOICES,
        default=KIND_FREESTYLE,
        verbose_name="项目类型",
    )
    repo_url = models.URLField(
        max_length=512,
        blank=True,
        null=True,
        verbose_name="代码仓库地址",
    )
    build_definition = models.TextField(
        blank=True,
        default="",
        verbose_name="构建定义",
        help_text="Shell 脚本。流水线类型可用行首「# stage: 阶段名」分段执行。",
    )
    status = models.IntegerField(
        choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name="执行状态"
    )

    class Meta:
        db_table = "pipeline"
        verbose_name = "流水线"


class BuildRecord(models.Model):
    """单次流水线构建（挂载日志与 Celery / Docker 执行元数据）。"""

    STATUS_PENDING = 0
    STATUS_RUNNING = 1
    STATUS_SUCCESS = 2
    STATUS_FAIL = 3
    STATUS_CANCELLED = 4

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAIL, "Fail"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        related_name="builds",
        verbose_name="流水线",
    )
    build_number = models.PositiveIntegerField(verbose_name="构建号")
    status = models.IntegerField(
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="构建状态",
    )
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="开始时间")
    end_time = models.DateTimeField(blank=True, null=True, verbose_name="结束时间")
    workspace_path = models.CharField(
        blank=True,
        default="",
        max_length=512,
        verbose_name="工作区路径",
        help_text="本次构建临时目录（如 /tmp/workspace/build_<id>），由任务写入。",
    )
    celery_task_id = models.CharField(
        blank=True,
        default="",
        max_length=128,
        verbose_name="Celery 任务 ID",
    )
    log_key = models.CharField(
        blank=True,
        default="",
        max_length=256,
        verbose_name="Redis 构建日志列表键",
    )
    duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name="耗时（秒）",
        help_text="自开始至结束的 wall-clock 秒数。",
    )

    class Meta:
        db_table = "pipeline_build_record"
        verbose_name = "流水线构建记录"
        verbose_name_plural = "流水线构建记录"
        ordering = ["-build_number", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["pipeline", "build_number"],
                name="uniq_pipeline_build_number",
            ),
        ]


class PipelineLog(models.Model):
    """单次构建的日志行。"""

    build_record = models.ForeignKey(
        BuildRecord,
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name="构建记录",
    )
    log_text = models.TextField(verbose_name="日志内容")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="记录时间")

    class Meta:
        db_table = "pipeline_log"
        verbose_name = "流水线日志"
        ordering = ["-timestamp"]
