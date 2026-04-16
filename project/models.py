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
