# Generated manually for Pipeline Jenkins-style project kinds.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("project", "0008_pipeline_pipelinelog"),
    ]

    operations = [
        migrations.AddField(
            model_name="pipeline",
            name="build_definition",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Shell 脚本。流水线类型可用行首「# stage: 阶段名」分段执行。",
                verbose_name="构建定义",
            ),
        ),
        migrations.AddField(
            model_name="pipeline",
            name="kind",
            field=models.IntegerField(
                choices=[(0, "自由风格"), (1, "流水线脚本")],
                default=0,
                verbose_name="项目类型",
            ),
        ),
        migrations.AlterField(
            model_name="pipeline",
            name="repo_url",
            field=models.URLField(
                blank=True,
                max_length=512,
                null=True,
                verbose_name="代码仓库地址",
            ),
        ),
    ]
