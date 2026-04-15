from django.contrib import admin

from server_logs.models import LogAutoTicketJob, RemoteLogServer, ServerLogAuditEvent


@admin.register(RemoteLogServer)
class RemoteLogServerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "host",
        "port",
        "username",
        "server_type",
        "organization",
        "creator",
        "update_time",
    )
    search_fields = ("name", "host", "username")
    list_filter = ("server_type", "is_deleted")


@admin.register(LogAutoTicketJob)
class LogAutoTicketJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "create_defect_requested",
        "created_defect",
        "user",
        "remote_log_server",
        "celery_task_id",
        "created_at",
    )
    list_filter = ("status", "create_defect_requested")
    search_fields = ("celery_task_id", "error_message")
    readonly_fields = (
        "user",
        "remote_log_server",
        "anchor_text",
        "draft",
        "meta",
        "create_defect_requested",
        "defect_handler",
        "defect_release_version",
        "defect_module",
        "created_defect",
        "created_at",
        "updated_at",
    )


@admin.register(ServerLogAuditEvent)
class ServerLogAuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "action",
        "user",
        "remote_log_server",
        "client_ip",
        "created_at",
    )
    list_filter = ("action",)
    search_fields = ("client_ip",)
    readonly_fields = (
        "user",
        "action",
        "remote_log_server",
        "organization",
        "meta",
        "client_ip",
        "created_at",
    )
