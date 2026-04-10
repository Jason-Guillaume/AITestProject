# Generated manually: TestReport 与执行日志闭环字段

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("execution", "0004_alter_testreport_create_method"),
    ]

    operations = [
        migrations.AddField(
            model_name="testreport",
            name="trace_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="与 api_execution_log.trace_id 对应，便于报告与单次执行闭环",
                max_length=36,
                verbose_name="关联执行追踪ID",
            ),
        ),
        migrations.AddField(
            model_name="testreport",
            name="execution_log_id",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="testcase.ExecutionLog 主键（无跨库外键，仅存储引用）",
                null=True,
                verbose_name="关联执行日志ID",
            ),
        ),
        migrations.AddField(
            model_name="testreport",
            name="request_payload",
            field=models.JSONField(
                blank=True,
                help_text="执行时真实请求 JSON 快照（与日志表一致便于报表展示）",
                null=True,
                verbose_name="请求快照",
            ),
        ),
        migrations.AddField(
            model_name="testreport",
            name="response_payload",
            field=models.JSONField(
                blank=True,
                help_text="服务端返回原始数据摘要",
                null=True,
                verbose_name="响应快照",
            ),
        ),
    ]
