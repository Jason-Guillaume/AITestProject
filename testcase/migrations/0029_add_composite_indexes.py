from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("testcase", "0028_testenvironment_auth_config"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="testcase",
            index=models.Index(
                fields=["module", "test_type", "is_deleted"],
                name="tc_module_type_del_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="testcase",
            index=models.Index(
                fields=["module", "is_deleted", "-create_time"],
                name="tc_module_del_ctime_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="executionlog",
            index=models.Index(
                fields=["test_case", "-create_time"],
                name="exlog_case_ctime_idx",
            ),
        ),
    ]
