from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0010_aicasegenerationrun"),
        ("testcase", "0025_normalize_apitestcase_api_body"),
    ]

    operations = [
        migrations.AddField(
            model_name="testcase",
            name="ai_run",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="imported_testcases",
                to="assistant.aicasegenerationrun",
                verbose_name="AI 生成批次（可选）",
            ),
        ),
    ]
