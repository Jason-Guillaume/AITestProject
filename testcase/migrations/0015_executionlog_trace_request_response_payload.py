# Generated manually: ExecutionLog trace_id + request/response JSON snapshots

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "testcase",
            "0014_rename_api_exec_case_ctime_idx_api_executi_test_ca_0661b3_idx_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="executionlog",
            name="trace_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="单次执行唯一标识，用于与测试报告等关联（新记录必有值）",
                max_length=36,
                null=True,
                verbose_name="执行追踪ID",
            ),
        ),
        migrations.AddField(
            model_name="executionlog",
            name="request_payload",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="执行时真实请求：method/url/headers/body",
                verbose_name="请求快照(JSON)",
            ),
        ),
        migrations.AddField(
            model_name="executionlog",
            name="response_payload",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="服务端返回原始数据摘要：status_code/headers/body 等",
                verbose_name="响应快照(JSON)",
            ),
        ),
    ]
