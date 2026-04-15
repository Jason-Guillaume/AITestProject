# Generated manually: organization scope + audit events.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("server_logs", "0001_initial"),
        ("user", "0008_organization_members"),
    ]

    operations = [
        migrations.AddField(
            model_name="remotelogserver",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                help_text="绑定后，组织创建人与成员均可使用该主机配置（含实时日志）。不绑定则仅创建人可见。",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="remote_log_servers",
                to="user.organization",
                verbose_name="所属组织",
            ),
        ),
        migrations.CreateModel(
            name="ServerLogAuditEvent",
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
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("ws_connect", "实时日志连接"),
                            ("ws_disconnect", "实时日志断开"),
                            ("ws_stop", "停止 tail"),
                            ("analyze", "AI 诊断"),
                            ("search", "历史检索"),
                            ("host_create", "新增主机"),
                            ("host_update", "更新主机"),
                            ("host_delete", "删除主机"),
                        ],
                        db_index=True,
                        max_length=40,
                        verbose_name="动作",
                    ),
                ),
                (
                    "meta",
                    models.JSONField(blank=True, default=dict, verbose_name="扩展信息"),
                ),
                (
                    "client_ip",
                    models.CharField(
                        blank=True, default="", max_length=64, verbose_name="客户端 IP"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, verbose_name="时间"
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="server_log_audit_events",
                        to="user.organization",
                        verbose_name="关联组织",
                    ),
                ),
                (
                    "remote_log_server",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_events",
                        to="server_logs.remotelogserver",
                        verbose_name="关联主机",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="server_log_audit_events",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="操作人",
                    ),
                ),
            ],
            options={
                "verbose_name": "服务器日志审计",
                "verbose_name_plural": "服务器日志审计",
                "db_table": "server_logs_audit_event",
                "ordering": ("-created_at",),
            },
        ),
    ]
