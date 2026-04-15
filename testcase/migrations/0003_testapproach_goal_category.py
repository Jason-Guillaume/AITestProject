from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("testcase", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="testapproach",
            name="test_goal",
            field=models.TextField(blank=True, null=True, verbose_name="测试目标"),
        ),
        migrations.AddField(
            model_name="testapproach",
            name="test_category",
            field=models.IntegerField(
                choices=[
                    (1, "单元测试"),
                    (2, "集成测试"),
                    (3, "系统测试"),
                    (4, "用户测试"),
                ],
                default=1,
                verbose_name="测试类型",
            ),
        ),
    ]
