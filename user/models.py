from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

from common.models import BaseModel


class User(AbstractUser, BaseModel):
    real_name = models.CharField(max_length=255, verbose_name="真实姓名/显示用")
    phone_number = models.CharField(
        max_length=32,
        blank=True,
        default="",
        verbose_name="手机号",
    )
    avatar = models.ImageField(
        upload_to="user_avatars/%Y/%m/",
        null=True,
        blank=True,
        verbose_name="头像",
    )
    is_active = models.BooleanField(
        default=True, choices=[(True, "正常"), (False, "禁用")], verbose_name="账号状态"
    )
    is_system_admin = models.BooleanField(
        default=False,
        verbose_name="系统管理员",
        help_text="可访问组织/角色/用户管理；普通用户仅可消息设置",
    )

    groups = models.ManyToManyField(
        Group,
        verbose_name="groups",
        blank=True,
        help_text="The groups this user belongs to.",
        related_name="custom_user_set",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name="user permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        related_name="custom_user_permissions_set",
        related_query_name="user",
    )

    class Meta:
        db_table = "sys_user"
        verbose_name = "系统用户"


class UserChangeRequest(models.Model):
    """
    敏感信息变更申请（用户名 / 登录密码），需管理员在站内消息中审核后生效。
    - username：new_value 存明文目标用户名（审批时写入 User.username）
    - password：new_value 存 Django 密码哈希（make_password 结果），审批时赋给 User.password
    """

    class RequestType(models.TextChoices):
        USERNAME = "username", "用户名"
        PASSWORD = "password", "密码"

    class Status(models.TextChoices):
        PENDING = "pending", "待审批"
        APPROVED = "approved", "已通过"
        REJECTED = "rejected", "已拒绝"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="change_requests",
        verbose_name="申请人",
    )
    request_type = models.CharField(
        max_length=16,
        choices=RequestType.choices,
        verbose_name="申请类型",
    )
    new_value = models.TextField(
        verbose_name="新值（用户名为明文；密码为哈希字符串）",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name="状态",
    )
    approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_change_requests",
        verbose_name="审批人",
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="审批时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "sys_user_change_request"
        verbose_name = "用户敏感信息变更申请"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} {self.get_request_type_display()} {self.status}"


class SystemMessage(models.Model):
    """
    站内系统消息（如：敏感信息变更待审批）。
    按管理员账号逐条下发，recipient 为实际登录处理的用户。
    """

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="inbox_system_messages",
        verbose_name="接收人",
    )
    title = models.CharField(max_length=255, verbose_name="标题")
    content = models.TextField(verbose_name="内容")
    is_read = models.BooleanField(default=False, verbose_name="是否已读")
    related_request = models.ForeignKey(
        UserChangeRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_messages",
        verbose_name="关联的变更申请",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "sys_system_message"
        verbose_name = "系统消息"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["recipient", "-created_at"]),
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self):
        return f"→{self.recipient_id} {self.title[:40]}"


class AIModelConfig(models.Model):
    """
    平台级唯一 AI 接入配置（数据库中至多保留一条业务记录，删除后可重新保存）。
    """

    project = models.ForeignKey(
        "project.TestProject",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ai_configs",
        verbose_name="所属项目",
    )
    model_type = models.CharField(max_length=64, verbose_name="模型标识")
    api_key = models.TextField(verbose_name="API Key")
    base_url = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="Base URL",
    )
    is_connected = models.BooleanField(default=True, verbose_name="是否处于连接状态")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "sys_ai_model_config"
        verbose_name = "AI 模型配置"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "model_type"],
                name="uniq_ai_model_config_per_project_model",
            )
        ]

    def __str__(self):
        return self.model_type


class Organization(BaseModel):
    """
    组织管理（用于“系统管理-组织管理”页面）
    """

    org_name = models.CharField(max_length=255, verbose_name="组织名称")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="organization_memberships",
        verbose_name="组织成员",
        help_text="加入成员后，可共享绑定到本组织的「服务器日志」等资源配置。",
    )
    projects = models.ManyToManyField(
        "project.TestProject",
        blank=True,
        related_name="organizations",
        verbose_name="关联项目",
    )

    class Meta:
        db_table = "sys_org"
        verbose_name = "组织管理"


class AiQuotaPolicy(BaseModel):
    """
    AI 配额策略（企业治理）：
    - scope_type=project：按项目配额
    - scope_type=org：按组织配额
    - scope_type=user：按用户覆盖（优先级最高）
    """

    SCOPE_PROJECT = "project"
    SCOPE_ORG = "org"
    SCOPE_USER = "user"
    SCOPE_CHOICES = [
        (SCOPE_PROJECT, "项目"),
        (SCOPE_ORG, "组织"),
        (SCOPE_USER, "用户"),
    ]

    scope_type = models.CharField(max_length=16, choices=SCOPE_CHOICES, db_index=True)
    project = models.ForeignKey(
        "project.TestProject",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="ai_quota_policies",
    )
    org = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="ai_quota_policies",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="ai_quota_policies",
    )

    # 0 表示不限制（不推荐对 org/project 使用 0）
    daily_requests = models.PositiveIntegerField(default=0, verbose_name="每日调用上限(0=不限制)")
    max_concurrency = models.PositiveIntegerField(default=0, verbose_name="最大并发(0=不限制)")
    concurrency_ttl_seconds = models.PositiveIntegerField(default=180, verbose_name="并发槽 TTL(秒)")

    # 为空表示对全部 action 生效；否则为 action 白名单
    allowed_actions = models.JSONField(default=list, blank=True, verbose_name="允许/生效的 action 列表")
    is_enabled = models.BooleanField(default=True, db_index=True, verbose_name="是否启用")
    notes = models.CharField(max_length=255, blank=True, default="", verbose_name="备注")

    class Meta:
        db_table = "ai_quota_policy"
        indexes = [
            models.Index(fields=["scope_type", "is_enabled", "-create_time"]),
            models.Index(fields=["project", "is_enabled"]),
            models.Index(fields=["org", "is_enabled"]),
            models.Index(fields=["user", "is_enabled"]),
        ]


class SystemMessageSetting(BaseModel):
    """
    消息设置（用于“系统管理-消息设置”页面）
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="message_settings",
        verbose_name="所属用户",
    )
    in_app_enabled = models.BooleanField(default=True, verbose_name="站内消息")
    email_enabled = models.BooleanField(default=False, verbose_name="邮件通知")
    sms_enabled = models.BooleanField(default=False, verbose_name="短信通知")
    digest_enabled = models.BooleanField(default=False, verbose_name="日报汇总")
    digest_time = models.CharField(
        max_length=16, null=True, blank=True, verbose_name="日报汇总时间（HH:mm）"
    )

    class Meta:
        db_table = "sys_message_setting"
        verbose_name = "消息设置"
        constraints = [
            models.UniqueConstraint(
                fields=["recipient"],
                name="unique_user_message_setting",
            )
        ]
