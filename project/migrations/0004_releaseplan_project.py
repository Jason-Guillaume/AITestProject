# Generated manually for ReleasePlan.project FK

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("project", "0003_testproject_progress_testproject_project_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="releaseplan",
            name="project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="release_plans",
                to="project.testproject",
                verbose_name="所属项目",
            ),
        ),
    ]
