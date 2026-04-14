from django.conf import settings
from django.db import models

from common.models import BaseModel


class ServerType(models.TextChoices):
    LINUX = "linux", "Linux"
    WINDOWS = "windows", "Windows"


class RemoteLogServer(BaseModel):
    """
    远程 SSH 日志主机配置；password / private_key 以 Fernet 密文落库。
    """

    name = models.CharField(max_length=128, verbose_name="显示名称")
    host = models.CharField(max_length=255, verbose_name="主机地址")
    port = models.PositiveIntegerField(default=22, verbose_name="SSH 端口")
    username = models.CharField(max_length=128, verbose_name="SSH 用户名")
    password_enc = models.TextField(blank=True, default="", verbose_name="密码密文")
    private_key_enc = models.TextField(blank=True, default="", verbose_name="私钥密文")
    server_type = models.CharField(
        max_length=16,
        choices=ServerType.choices,
        default=ServerType.LINUX,
        verbose_name="系统类型",
    )
    default_log_path = models.CharField(
        max_length=1024,
        default="/var/log/syslog",
        verbose_name="默认日志路径",
    )
    organization = models.ForeignKey(
        "user.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="remote_log_servers",
        verbose_name="所属组织",
        help_text="绑定后，组织创建人与成员均可使用该主机配置（含实时日志）。不绑定则仅创建人可见。",
    )

    class Meta:
        db_table = "server_logs_remote_host"
        verbose_name = "远程日志服务器"
        ordering = ("-update_time",)

    def __str__(self):
        return f"{self.name} ({self.host})"

    def set_password(self, raw: str | None) -> None:
        from server_logs.crypto import encrypt_secret

        self.password_enc = encrypt_secret(raw or "") if (raw or "").strip() else ""

    def set_private_key(self, raw: str | None) -> None:
        from server_logs.crypto import encrypt_secret

        self.private_key_enc = encrypt_secret(raw or "") if (raw or "").strip() else ""

    def get_password(self) -> str:
        from server_logs.crypto import decrypt_secret

        return decrypt_secret(self.password_enc)

    def get_private_key(self) -> str:
        from server_logs.crypto import decrypt_secret

        return decrypt_secret(self.private_key_enc)


class ServerLogAuditEvent(models.Model):
    """服务器日志模块操作审计（不落敏感凭据）。"""

    class Action(models.TextChoices):
        WS_CONNECT = "ws_connect", "实时日志连接"
        WS_DISCONNECT = "ws_disconnect", "实时日志断开"
        WS_STOP = "ws_stop", "停止 tail"
        ANALYZE = "analyze", "AI 诊断"
        AUTO_TICKET = "auto_ticket", "AI 工单草稿"
        SEARCH = "search", "历史检索"
        HOST_CREATE = "host_create", "新增主机"
        HOST_UPDATE = "host_update", "更新主机"
        HOST_DELETE = "host_delete", "删除主机"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="server_log_audit_events",
        verbose_name="操作人",
    )
    action = models.CharField(max_length=40, choices=Action.choices, db_index=True, verbose_name="动作")
    remote_log_server = models.ForeignKey(
        RemoteLogServer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
        verbose_name="关联主机",
    )
    organization = models.ForeignKey(
        "user.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="server_log_audit_events",
        verbose_name="关联组织",
    )
    meta = models.JSONField(default=dict, blank=True, verbose_name="扩展信息")
    client_ip = models.CharField(max_length=64, blank=True, default="", verbose_name="客户端 IP")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="时间", db_index=True)

    class Meta:
        db_table = "server_logs_audit_event"
        verbose_name = "服务器日志审计"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.get_action_display()} @{self.created_at}"


class LogAutoTicketJobStatus(models.TextChoices):
    PENDING = "pending", "排队中"
    PROCESSING = "processing", "处理中"
    SUCCESS = "success", "成功"
    FAILED = "failed", "失败"


class LogAutoTicketJob(models.Model):
    """
    异步 AI 工单草稿：入队后由 Celery 拉 ES 上下文并调用模型，结果写入 draft。
    凭据仅通过任务参数传递，不落库。
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="log_auto_ticket_jobs",
        verbose_name="发起人",
    )
    remote_log_server = models.ForeignKey(
        RemoteLogServer,
        on_delete=models.CASCADE,
        related_name="auto_ticket_jobs",
        verbose_name="关联主机",
    )
    anchor_text = models.TextField(verbose_name="锚点文本")
    anchor_ts = models.BigIntegerField(null=True, blank=True, verbose_name="锚点时间戳(ms)")
    window_seconds = models.PositiveIntegerField(default=300, verbose_name="上下文窗口(秒)")
    es_limit = models.PositiveIntegerField(default=200, verbose_name="ES 最大行数")
    status = models.CharField(
        max_length=16,
        choices=LogAutoTicketJobStatus.choices,
        default=LogAutoTicketJobStatus.PENDING,
        db_index=True,
        verbose_name="状态",
    )
    celery_task_id = models.CharField(max_length=128, blank=True, default="", verbose_name="Celery 任务 ID")
    error_message = models.TextField(blank=True, default="", verbose_name="错误信息")
    draft = models.JSONField(null=True, blank=True, verbose_name="草稿 JSON")
    meta = models.JSONField(default=dict, blank=True, verbose_name="诊断元信息")
    # 可选：AI 成功后自动落库 TestDefect（凭据仍不入库）
    create_defect_requested = models.BooleanField(default=False, verbose_name="是否请求创建缺陷")
    defect_handler = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="log_auto_ticket_jobs_as_handler",
        verbose_name="缺陷处理人",
        help_text="留空则使用任务发起人作为处理人。",
    )
    defect_release_version = models.ForeignKey(
        "project.ReleasePlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="log_auto_ticket_jobs",
        verbose_name="缺陷关联版本",
    )
    defect_module = models.ForeignKey(
        "testcase.TestModule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="log_auto_ticket_jobs",
        verbose_name="缺陷所属模块",
    )
    created_defect = models.ForeignKey(
        "defect.TestDefect",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_log_auto_ticket_jobs",
        verbose_name="已创建的缺陷",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "server_logs_auto_ticket_job"
        verbose_name = "日志 AI 工单草稿任务"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"AutoTicketJob#{self.pk} {self.status}"
