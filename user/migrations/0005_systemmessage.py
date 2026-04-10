# Generated manually for SystemMessage

from django.conf import settings
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0004_user_phone_avatar_image_userchangerequest"),
    ]

    operations = [
        migrations.CreateModel(
            name="SystemMessage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=255, verbose_name="标题")),
                ("content", models.TextField(verbose_name="内容")),
                (
                    "is_read",
                    models.BooleanField(default=False, verbose_name="是否已读"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="创建时间"
                    ),
                ),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inbox_system_messages",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="接收人",
                    ),
                ),
                (
                    "related_request",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="system_messages",
                        to="user.userchangerequest",
                        verbose_name="关联的变更申请",
                    ),
                ),
            ],
            options={
                "verbose_name": "系统消息",
                "db_table": "sys_system_message",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="systemmessage",
            index=models.Index(
                fields=["recipient", "-created_at"],
                name="sys_system__recipie_f99508_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="systemmessage",
            index=models.Index(
                fields=["recipient", "is_read"],
                name="sys_system__recipie_7b0fcb_idx",
            ),
        ),
    ]
