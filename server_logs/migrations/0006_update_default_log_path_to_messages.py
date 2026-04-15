from django.db import migrations


def forwards(apps, schema_editor):
    RemoteLogServer = apps.get_model("server_logs", "RemoteLogServer")
    # 仅将历史默认的 syslog 替换为 messages（更符合 CentOS/RHEL 环境）
    RemoteLogServer.objects.filter(default_log_path="/var/log/syslog").update(
        default_log_path="/var/log/messages"
    )


def backwards(apps, schema_editor):
    RemoteLogServer = apps.get_model("server_logs", "RemoteLogServer")
    RemoteLogServer.objects.filter(default_log_path="/var/log/messages").update(
        default_log_path="/var/log/syslog"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("server_logs", "0005_log_auto_ticket_defect_options"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
