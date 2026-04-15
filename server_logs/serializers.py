from rest_framework import serializers

from server_logs.access import user_is_platform_log_admin
from server_logs.models import LogAutoTicketJob, RemoteLogServer, ServerLogAuditEvent
from server_logs.validators import validate_remote_log_path
from project.models import ReleasePlan
from testcase.models import TestModule
from user.models import Organization, User

_UNSET = object()


class RemoteLogServerSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(is_deleted=False),
        required=False,
        allow_null=True,
    )
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={"input_type": "password"},
    )
    private_key = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        trim_whitespace=False,
    )

    class Meta:
        model = RemoteLogServer
        fields = (
            "id",
            "name",
            "host",
            "port",
            "username",
            "password",
            "private_key",
            "server_type",
            "default_log_path",
            "organization",
            "create_time",
            "update_time",
        )
        read_only_fields = ("id", "create_time", "update_time")

    def validate_organization(self, org):
        if org is None:
            return org
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            raise serializers.ValidationError("未登录")
        if user_is_platform_log_admin(user):
            return org
        if org.creator_id == user.id:
            return org
        if org.members.filter(pk=user.pk).exists():
            return org
        raise serializers.ValidationError("只能绑定您负责或是成员的组织")

    def validate(self, attrs):
        raw_pw = attrs.pop("password", _UNSET)
        raw_pk = attrs.pop("private_key", _UNSET)
        instance = getattr(self, "instance", None)

        if raw_pw is _UNSET:
            pw_plain = _UNSET
        elif raw_pw is None:
            pw_plain = ""
        else:
            pw_plain = (raw_pw or "").strip()

        if raw_pk is _UNSET:
            pk_plain = _UNSET
        elif raw_pk is None:
            pk_plain = ""
        else:
            pk_plain = str(raw_pk or "")

        if instance is None:
            if raw_pw is _UNSET:
                pw_plain = ""
            else:
                pw_plain = (raw_pw or "").strip()
            if raw_pk is _UNSET:
                pk_plain = ""
            else:
                pk_plain = str(raw_pk or "")
            if not pw_plain and not pk_plain.strip():
                raise serializers.ValidationError(
                    {"password": "请至少填写密码或私钥之一用于 SSH 认证。"}
                )
            attrs["_password_plain"] = pw_plain
            attrs["_private_key_plain"] = pk_plain
        else:
            attrs["_password_plain"] = pw_plain
            attrs["_private_key_plain"] = pk_plain

        dpath = attrs.get("default_log_path")
        if dpath is None and instance is not None:
            dpath = instance.default_log_path
        dpath = dpath or "/var/log/messages"
        stype = attrs.get("server_type")
        if stype is None and instance is not None:
            stype = instance.server_type
        stype = stype or "linux"
        perr = validate_remote_log_path(dpath, stype)
        if perr:
            raise serializers.ValidationError({"default_log_path": perr})

        return attrs

    def create(self, validated_data):
        pw = validated_data.pop("_password_plain", "")
        pk_plain = validated_data.pop("_private_key_plain", "")
        obj = RemoteLogServer(**validated_data)
        obj.set_password(pw)
        obj.set_private_key(pk_plain)
        obj.save()
        return obj

    def update(self, instance, validated_data):
        pw = validated_data.pop("_password_plain", _UNSET)
        pk_plain = validated_data.pop("_private_key_plain", _UNSET)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if pw is not _UNSET:
            if pw:
                instance.set_password(pw)
            else:
                instance.password_enc = ""
        if pk_plain is not _UNSET:
            if (pk_plain or "").strip():
                instance.set_private_key(pk_plain)
            else:
                instance.private_key_enc = ""
        instance.save()
        return instance


class RemoteLogServerListSerializer(serializers.ModelSerializer):
    """列表不含敏感字段。"""

    organization_name = serializers.SerializerMethodField()

    class Meta:
        model = RemoteLogServer
        fields = (
            "id",
            "name",
            "host",
            "port",
            "username",
            "server_type",
            "default_log_path",
            "organization",
            "organization_name",
            "update_time",
        )

    def get_organization_name(self, obj):
        if obj.organization_id and obj.organization:
            return obj.organization.org_name
        return None


class LogAnalyzeRequestSerializer(serializers.Serializer):
    log_text = serializers.CharField(
        required=True, allow_blank=False, max_length=120_000
    )
    model = serializers.CharField(required=False, allow_blank=True, max_length=128)
    api_key = serializers.CharField(required=False, allow_blank=True)
    api_base_url = serializers.CharField(
        required=False, allow_blank=True, max_length=512
    )


class LogAnalyzeWithContextRequestSerializer(serializers.Serializer):
    server_id = serializers.IntegerField(required=True, min_value=1)
    anchor_text = serializers.CharField(
        required=True, allow_blank=False, max_length=80_000
    )
    anchor_ts = serializers.IntegerField(required=False, min_value=0)
    window_seconds = serializers.IntegerField(
        required=False, min_value=10, max_value=3600, default=300
    )
    limit = serializers.IntegerField(
        required=False, min_value=10, max_value=500, default=200
    )
    model = serializers.CharField(required=False, allow_blank=True, max_length=128)
    api_key = serializers.CharField(required=False, allow_blank=True)
    api_base_url = serializers.CharField(
        required=False, allow_blank=True, max_length=512
    )


class LogAutoTicketEnqueueSerializer(serializers.Serializer):
    """异步工单草稿入队（凭据不落库，由 Celery 任务参数携带）。"""

    server_id = serializers.IntegerField(required=True, min_value=1)
    anchor_text = serializers.CharField(
        required=True, allow_blank=False, max_length=80_000
    )
    anchor_ts = serializers.IntegerField(required=False, min_value=0)
    window_seconds = serializers.IntegerField(
        required=False, min_value=10, max_value=3600, default=300
    )
    es_limit = serializers.IntegerField(
        required=False, min_value=10, max_value=500, default=200
    )
    model = serializers.CharField(required=False, allow_blank=True, max_length=128)
    api_key = serializers.CharField(required=False, allow_blank=True)
    api_base_url = serializers.CharField(
        required=False, allow_blank=True, max_length=512
    )
    create_defect = serializers.BooleanField(required=False, default=False)
    defect_handler = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_deleted=False),
        required=False,
        allow_null=True,
    )
    defect_release_version = serializers.PrimaryKeyRelatedField(
        queryset=ReleasePlan.objects.filter(is_deleted=False),
        required=False,
        allow_null=True,
    )
    defect_module = serializers.PrimaryKeyRelatedField(
        queryset=TestModule.objects.filter(is_deleted=False),
        required=False,
        allow_null=True,
    )


class LogAutoTicketCreateDefectSerializer(serializers.Serializer):
    """从已成功任务补建缺陷：字段均可选；未传的项沿用任务入队时保存的偏好。"""

    defect_handler = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_deleted=False),
        required=False,
        allow_null=True,
    )
    defect_release_version = serializers.PrimaryKeyRelatedField(
        queryset=ReleasePlan.objects.filter(is_deleted=False),
        required=False,
        allow_null=True,
    )
    defect_module = serializers.PrimaryKeyRelatedField(
        queryset=TestModule.objects.filter(is_deleted=False),
        required=False,
        allow_null=True,
    )


class LogSearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    limit = serializers.IntegerField(
        required=False, min_value=1, max_value=500, default=50
    )


class ServerLogAuditEventSerializer(serializers.ModelSerializer):
    user_display = serializers.SerializerMethodField()
    action_display = serializers.SerializerMethodField()

    class Meta:
        model = ServerLogAuditEvent
        fields = (
            "id",
            "action",
            "action_display",
            "user_display",
            "remote_log_server",
            "organization",
            "meta",
            "client_ip",
            "created_at",
        )

    def get_action_display(self, obj):
        return obj.get_action_display()

    def get_user_display(self, obj):
        u = obj.user
        if not u:
            return ""
        return (getattr(u, "real_name", None) or u.username or str(u.pk))[:64]


class LogAutoTicketJobSerializer(serializers.ModelSerializer):
    """任务状态查询（不含任何 API Key）。"""

    remote_server_name = serializers.CharField(
        source="remote_log_server.name", read_only=True
    )
    created_defect = serializers.SerializerMethodField()

    class Meta:
        model = LogAutoTicketJob
        fields = (
            "id",
            "status",
            "celery_task_id",
            "error_message",
            "draft",
            "meta",
            "remote_log_server",
            "remote_server_name",
            "anchor_text",
            "anchor_ts",
            "window_seconds",
            "es_limit",
            "create_defect_requested",
            "defect_handler",
            "defect_release_version",
            "defect_module",
            "created_defect",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_created_defect(self, obj: LogAutoTicketJob):
        d = getattr(obj, "created_defect", None)
        if d is None:
            return None
        return {"id": d.id, "defect_no": d.defect_no, "defect_name": d.defect_name}
