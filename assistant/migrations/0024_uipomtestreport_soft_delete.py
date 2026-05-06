# Generated manually for UI POM report soft delete / recycle bin

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0023_ui_pom_test_report"),
    ]

    operations = [
        migrations.AddField(
            model_name="uipomtestreport",
            name="is_deleted",
            field=models.BooleanField(default=False, db_index=True, verbose_name="已删除"),
        ),
        migrations.AddField(
            model_name="uipomtestreport",
            name="deleted_at",
            field=models.DateTimeField(null=True, blank=True, verbose_name="删除时间"),
        ),
    ]
