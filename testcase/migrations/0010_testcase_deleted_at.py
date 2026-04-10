from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("testcase", "0009_testcase_case_number_unique_constraint"),
    ]

    operations = [
        migrations.AddField(
            model_name="testcase",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="删除时间"),
        ),
    ]
