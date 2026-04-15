from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("execution", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PerfTask",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "create_time",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "update_time",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "is_deleted",
                    models.BooleanField(default=False, verbose_name="逻辑删除标识"),
                ),
                (
                    "task_id",
                    models.CharField(max_length=32, unique=True, verbose_name="任务ID"),
                ),
                (
                    "task_name",
                    models.CharField(max_length=255, verbose_name="任务名称"),
                ),
                (
                    "scenario",
                    models.CharField(
                        choices=[("jmeter", "JMeter"), ("locust", "Locust")],
                        max_length=32,
                        verbose_name="测试场景",
                    ),
                ),
                (
                    "concurrency",
                    models.PositiveIntegerField(default=1, verbose_name="并发数"),
                ),
                (
                    "duration",
                    models.CharField(
                        default="10m", max_length=32, verbose_name="持续时间"
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "待执行"),
                            ("running", "运行中"),
                            ("completed", "已完成"),
                            ("failed", "失败"),
                        ],
                        default="pending",
                        max_length=16,
                        verbose_name="任务状态",
                    ),
                ),
                (
                    "executor",
                    models.CharField(blank=True, max_length=64, verbose_name="执行人"),
                ),
                (
                    "creator",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="创建人",
                    ),
                ),
                (
                    "updater",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="更新人",
                    ),
                ),
            ],
            options={
                "db_table": "perf_task",
                "ordering": ("-create_time",),
            },
        ),
    ]
