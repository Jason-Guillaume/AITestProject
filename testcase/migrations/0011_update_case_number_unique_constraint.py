from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("testcase", "0010_testcase_deleted_at"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="testcase",
            name="uniq_case_number_per_module_type",
        ),
        migrations.AddConstraint(
            model_name="testcase",
            constraint=models.UniqueConstraint(
                fields=("test_type", "case_number"),
                condition=Q(is_deleted=False),
                name="uniq_active_case_number_per_type",
            ),
        ),
    ]
