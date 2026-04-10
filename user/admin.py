from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from user.models import (
    AIModelConfig,
    Organization,
    SystemMessage,
    SystemMessageSetting,
    User,
    UserChangeRequest,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "real_name", "phone_number", "is_system_admin", "is_active")
    search_fields = ("username", "real_name", "email", "phone_number")
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "扩展信息",
            {"fields": ("real_name", "phone_number", "avatar", "is_system_admin")},
        ),
    )


@admin.register(UserChangeRequest)
class UserChangeRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "request_type", "status", "created_at")
    list_filter = ("status", "request_type")
    search_fields = ("user__username",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(SystemMessage)
class SystemMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "title", "is_read", "related_request", "created_at")
    list_filter = ("is_read",)
    search_fields = ("title", "recipient__username")
    readonly_fields = ("created_at",)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "org_name", "create_time")


@admin.register(SystemMessageSetting)
class SystemMessageSettingAdmin(admin.ModelAdmin):
    list_display = ("id", "in_app_enabled", "email_enabled", "create_time")


@admin.register(AIModelConfig)
class AIModelConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "model_type", "is_connected", "updated_at")
    search_fields = ("model_type",)
