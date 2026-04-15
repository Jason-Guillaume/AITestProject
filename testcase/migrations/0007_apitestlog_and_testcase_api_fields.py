from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("testcase", "0006_testmodule_test_type_and_ui_automation_case"),
    ]

    operations = [
        migrations.AddField(
            model_name="testcase",
            name="api_body",
            field=models.TextField(blank=True, default="", verbose_name="请求体"),
        ),
        migrations.AddField(
            model_name="testcase",
            name="api_expected_status",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="为空则仅校验 2xx；与步骤里「预期结果」子串断言可同时生效",
                null=True,
                verbose_name="期望状态码",
            ),
        ),
        migrations.AddField(
            model_name="testcase",
            name="api_headers",
            field=models.JSONField(
                blank=True, default=dict, verbose_name="请求头(JSON)"
            ),
        ),
        migrations.AddField(
            model_name="testcase",
            name="api_method",
            field=models.CharField(
                default="GET", max_length=16, verbose_name="HTTP 方法"
            ),
        ),
        migrations.AddField(
            model_name="testcase",
            name="api_url",
            field=models.CharField(
                blank=True, default="", max_length=2048, verbose_name="API 地址"
            ),
        ),
        migrations.CreateModel(
            name="ApiTestLog",
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
                    "request_url",
                    models.CharField(max_length=2048, verbose_name="请求 URL"),
                ),
                (
                    "request_method",
                    models.CharField(max_length=16, verbose_name="请求方法"),
                ),
                (
                    "request_headers",
                    models.JSONField(blank=True, default=dict, verbose_name="请求头"),
                ),
                (
                    "request_body",
                    models.TextField(blank=True, default="", verbose_name="请求体"),
                ),
                (
                    "response_status_code",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="响应状态码"
                    ),
                ),
                (
                    "response_body",
                    models.TextField(blank=True, default="", verbose_name="响应体"),
                ),
                (
                    "response_time_ms",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="耗时(ms)"
                    ),
                ),
                (
                    "is_passed",
                    models.BooleanField(default=False, verbose_name="是否通过"),
                ),
                (
                    "creator",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="apitestlog_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="创建人",
                    ),
                ),
                (
                    "test_case",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="api_test_logs",
                        to="testcase.testcase",
                        verbose_name="测试用例",
                    ),
                ),
                (
                    "updater",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="apitestlog_updated",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="更新人",
                    ),
                ),
            ],
            options={
                "verbose_name": "API 执行记录",
                "db_table": "api_test_log",
                "ordering": ["-create_time"],
            },
        ),
    ]
