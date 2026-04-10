from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("testcase", "0007_apitestlog_and_testcase_api_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="testcase",
            name="case_number",
            field=models.IntegerField(
                blank=True, db_index=True, null=True, verbose_name="业务编号"
            ),
        ),
    ]
