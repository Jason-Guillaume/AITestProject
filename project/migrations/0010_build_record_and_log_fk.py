# BuildRecord + PipelineLog.build_record (logs no longer on Pipeline directly).

from django.db import migrations, models
import django.db.models.deletion


def forwards_migrate_logs_to_build_records(apps, schema_editor):
    Pipeline = apps.get_model("project", "Pipeline")
    BuildRecord = apps.get_model("project", "BuildRecord")
    PipelineLog = apps.get_model("project", "PipelineLog")

    for p in Pipeline.objects.all().iterator():
        qs = PipelineLog.objects.filter(pipeline_id=p.id)
        if not qs.exists():
            continue
        br = BuildRecord.objects.create(
            pipeline_id=p.id,
            build_number=1,
            status=2,  # Success — 历史占位，仅用于挂载旧日志
        )
        qs.update(build_record_id=br.id)


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("project", "0009_pipeline_kind_build_definition_alter_repo_url"),
    ]

    operations = [
        migrations.CreateModel(
            name="BuildRecord",
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
                    "build_number",
                    models.PositiveIntegerField(verbose_name="构建号"),
                ),
                (
                    "status",
                    models.IntegerField(
                        choices=[
                            (0, "Pending"),
                            (1, "Running"),
                            (2, "Success"),
                            (3, "Fail"),
                            (4, "Cancelled"),
                        ],
                        default=0,
                        verbose_name="构建状态",
                    ),
                ),
                (
                    "start_time",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="开始时间"
                    ),
                ),
                (
                    "end_time",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="结束时间"
                    ),
                ),
                (
                    "workspace_path",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=512,
                        verbose_name="工作区路径",
                        help_text="本次构建临时目录（如 /tmp/workspace/build_<id>），由任务写入。",
                    ),
                ),
                (
                    "celery_task_id",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=128,
                        verbose_name="Celery 任务 ID",
                    ),
                ),
                (
                    "pipeline",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="builds",
                        to="project.pipeline",
                        verbose_name="流水线",
                    ),
                ),
            ],
            options={
                "verbose_name": "流水线构建记录",
                "verbose_name_plural": "流水线构建记录",
                "db_table": "pipeline_build_record",
                "ordering": ["-build_number", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="buildrecord",
            constraint=models.UniqueConstraint(
                fields=("pipeline", "build_number"),
                name="uniq_pipeline_build_number",
            ),
        ),
        migrations.AddField(
            model_name="pipelinelog",
            name="build_record",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="logs",
                to="project.buildrecord",
                verbose_name="构建记录",
            ),
        ),
        migrations.RunPython(forwards_migrate_logs_to_build_records, backwards_noop),
        migrations.RemoveField(
            model_name="pipelinelog",
            name="pipeline",
        ),
        migrations.AlterField(
            model_name="pipelinelog",
            name="build_record",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="logs",
                to="project.buildrecord",
                verbose_name="构建记录",
            ),
        ),
    ]
