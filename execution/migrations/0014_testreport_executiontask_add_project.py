# Generated manually: add project cache fields for data scope.

from django.db import migrations, models
import django.db.models.deletion


def backfill_testreport_project(apps, schema_editor):
    TestReport = apps.get_model("execution", "TestReport")
    for r in TestReport.objects.select_related("plan__version").iterator():
        proj_id = None
        try:
            proj_id = getattr(getattr(r.plan, "version", None), "project_id", None)
        except Exception:
            proj_id = None
        if proj_id and r.project_id != proj_id:
            TestReport.objects.filter(pk=r.pk).update(project_id=proj_id)


class Migration(migrations.Migration):
    dependencies = [
        ("project", "0001_initial"),
        ("execution", "0013_alter_k6loadtestsession_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="testreport",
            name="project",
            field=models.ForeignKey(
                blank=True,
                help_text="用于数据权限与查询加速；值来自 plan.version.project",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="test_reports",
                to="project.testproject",
                verbose_name="关联项目(冗余)",
            ),
        ),
        migrations.AddField(
            model_name="executiontask",
            name="project",
            field=models.ForeignKey(
                blank=True,
                help_text="用于数据权限控制；独立任务可为空或由创建时指定",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="execution_tasks",
                to="project.testproject",
                verbose_name="关联项目(冗余)",
            ),
        ),
        migrations.RunPython(backfill_testreport_project, migrations.RunPython.noop),
    ]
