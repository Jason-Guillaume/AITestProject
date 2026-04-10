# Generated manually for per-type module trees + ui-automation case type

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("testcase", "0005_add_testcase_test_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="testmodule",
            name="test_type",
            field=models.CharField(
                choices=[
                    ("functional", "功能测试"),
                    ("api", "API 测试"),
                    ("performance", "性能测试"),
                    ("security", "安全测试"),
                    ("ui-automation", "UI 自动化"),
                ],
                default="functional",
                max_length=32,
                verbose_name="测试类型",
            ),
        ),
        migrations.AlterField(
            model_name="testcase",
            name="test_type",
            field=models.CharField(
                choices=[
                    ("functional", "功能测试"),
                    ("api", "API 测试"),
                    ("performance", "性能测试"),
                    ("security", "安全测试"),
                    ("ui-automation", "UI 自动化"),
                ],
                default="functional",
                max_length=32,
                verbose_name="测试类型",
            ),
        ),
    ]
