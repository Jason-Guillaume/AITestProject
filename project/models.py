from django.db import models
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
        verbose_name="关联测试用例",
    )

    class Meta:
        db_table = "release_plan"
        verbose_name = "发布计划"
