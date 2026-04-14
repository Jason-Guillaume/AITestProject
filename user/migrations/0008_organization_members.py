# Generated manually for organization membership (server logs sharing).

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0007_alter_organization_is_deleted_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="members",
            field=models.ManyToManyField(
                blank=True,
                help_text="加入成员后，可共享绑定到本组织的「服务器日志」等资源配置。",
                related_name="organization_memberships",
                to=settings.AUTH_USER_MODEL,
                verbose_name="组织成员",
            ),
        ),
    ]
