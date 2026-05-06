"""
CI 执行引擎数据模型（与 ``project`` 应用中的流水线构建记录解耦，供 engine 任务专用）。
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class BuildRecord(models.Model):
    """一次构建执行记录：项目元数据、执行状态与产物引用。"""

    class Status(models.IntegerChoices):
        PENDING = 0, "Pending"
        RUNNING = 1, "Running"
        SUCCESS = 2, "Success"
        FAILED = 3, "Failed"
        CANCELLED = 4, "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="engine_build_records",
        verbose_name="触发用户",
    )
    project_name = models.CharField(max_length=255, verbose_name="项目名")
    git_url = models.URLField(max_length=512, verbose_name="Git 仓库 URL")
    branch_name = models.CharField(max_length=255, verbose_name="分支名")

    celery_task_id = models.CharField(
        max_length=128,
        blank=True,
        default="",
        db_index=True,
        verbose_name="Celery 任务 ID",
    )
    status = models.IntegerField(
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name="构建状态",
    )
    start_time = models.DateTimeField(
        default=timezone.now,
        verbose_name="开始时间",
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="结束时间",
    )
    duration = models.DurationField(
        null=True,
        blank=True,
        verbose_name="构建持续时间",
        help_text="由 save() 根据开始/结束时间自动计算。",
    )

    docker_image = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="构建镜像名称",
        help_text="例如 registry.example.com/app:1.0.0；无则留空。",
    )
    artifact_download_url = models.URLField(
        max_length=1024,
        blank=True,
        null=True,
        verbose_name="产物下载地址",
        help_text="包或制品的 HTTP(S) 下载链接；无则留空。",
    )

    class Meta:
        db_table = "engine_build_record"
        verbose_name = "引擎构建记录"
        verbose_name_plural = "引擎构建记录"
        ordering = ("-start_time", "-pk")

    def __str__(self) -> str:
        return f"{self.project_name} #{self.pk} ({self.get_status_display()})"

    def save(self, *args, **kwargs) -> None:
        if self.start_time is not None and self.end_time is not None:
            if self.end_time >= self.start_time:
                self.duration = self.end_time - self.start_time
            else:
                self.duration = None
        else:
            self.duration = None
        super().save(*args, **kwargs)
