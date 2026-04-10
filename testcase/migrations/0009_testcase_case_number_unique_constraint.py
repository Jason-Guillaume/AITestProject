from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("testcase", "0008_testcase_case_number"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="testcase",
            constraint=models.UniqueConstraint(
                fields=("module", "test_type", "case_number"),
                name="uniq_case_number_per_module_type",
            ),
        ),
    ]
