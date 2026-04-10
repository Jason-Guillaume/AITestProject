# Generated manually: ExecutionLog + ApiTestCase.api_body 文本迁移为 JSON

import json

from django.conf import settings
import django.db.models.deletion
from django.db import migrations, models


def forwards_api_body_to_json(apps, schema_editor):
    ApiTestCase = apps.get_model("testcase", "apitestcase")
    for row in ApiTestCase.objects.all().iterator():
        raw = row.api_body
        if raw is None or (isinstance(raw, str) and not str(raw).strip()):
            parsed = {}
        else:
            s = str(raw).strip()
            try:
                parsed = json.loads(s)
                if not isinstance(parsed, (dict, list)):
                    parsed = {"_legacy_scalar": parsed}
            except json.JSONDecodeError:
                parsed = {"_legacy_text": s}
        row.api_body_json = parsed
        row.save(update_fields=["api_body_json"])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("testcase", "0012_split_testcase_subtype_tables"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExecutionLog",
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
                    models.CharField(max_length=16, verbose_name="HTTP 方法"),
                ),
                (
                    "request_headers",
                    models.JSONField(blank=True, default=dict, verbose_name="请求头"),
                ),
                (
                    "request_body_text",
                    models.TextField(blank=True, default="", verbose_name="请求体全文"),
                ),
                (
                    "response_status_code",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="响应状态码"
                    ),
                ),
                (
                    "response_headers",
                    models.JSONField(blank=True, default=dict, verbose_name="响应头"),
                ),
                (
                    "response_body_text",
                    models.TextField(blank=True, default="", verbose_name="响应体全文"),
                ),
                (
                    "duration_ms",
                    models.PositiveIntegerField(blank=True, null=True, verbose_name="耗时(ms)"),
                ),
                (
                    "execution_status",
                    models.CharField(
                        choices=[
                            ("success", "成功"),
                            ("assertion_failed", "断言未通过"),
                            ("request_error", "请求异常"),
                        ],
                        default="request_error",
                        max_length=32,
                        verbose_name="执行状态",
                    ),
                ),
                (
                    "assertion_results",
                    models.JSONField(blank=True, default=list, verbose_name="断言结果"),
                ),
                (
                    "is_passed",
                    models.BooleanField(default=False, verbose_name="总是否通过"),
                ),
                (
                    "error_message",
                    models.TextField(blank=True, default="", verbose_name="错误信息"),
                ),
                (
                    "creator",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="executionlog_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="创建人",
                    ),
                ),
                (
                    "test_case",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="execution_logs",
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
                        related_name="executionlog_updated",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="更新人",
                    ),
                ),
            ],
            options={
                "db_table": "api_execution_log",
                "ordering": ["-create_time"],
                "indexes": [
                    models.Index(
                        fields=["test_case", "-create_time"],
                        name="api_exec_case_ctime_idx",
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="apitestcase",
            name="api_body_json",
            field=models.JSONField(blank=True, default=dict, verbose_name="请求体JSON临时"),
        ),
        migrations.RunPython(forwards_api_body_to_json, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="apitestcase",
            name="api_body",
        ),
        migrations.RenameField(
            model_name="apitestcase",
            old_name="api_body_json",
            new_name="api_body",
        ),
        migrations.AlterField(
            model_name="apitestcase",
            name="api_body",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='JSON 对象或数组；历史纯文本会迁移为 {"_legacy_text": "..."}',
                verbose_name="请求体(JSON)",
            ),
        ),
    ]
