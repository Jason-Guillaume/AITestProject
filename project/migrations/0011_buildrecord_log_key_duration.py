# Generated manually for AITesta CI engine (Redis log key + duration).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("project", "0010_build_record_and_log_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="buildrecord",
            name="log_key",
            field=models.CharField(
                blank=True,
                default="",
                max_length=256,
                verbose_name="Redis 构建日志列表键",
            ),
        ),
        migrations.AddField(
            model_name="buildrecord",
            name="duration",
            field=models.FloatField(
                blank=True,
                help_text="自开始至结束的 wall-clock 秒数。",
                null=True,
                verbose_name="耗时（秒）",
            ),
        ),
    ]
