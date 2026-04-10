import json

from rest_framework import serializers

from testcase.models import *
from common.serialize import BaseModelSerializers
from testcase.services.case_subtypes import (
    create_typed_case,
    inject_typed_read_representation,
    split_typed_payload_create,
    split_typed_payload_update,
    sync_typed_children,
)


class ApiBodyField(serializers.JSONField):
    """接受 JSON 对象/数组；兼容前端传入 JSON 字符串。"""

    def __init__(self, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("allow_null", True)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if data is None:
            return {}
        if isinstance(data, str):
            t = data.strip()
            if not t:
                return {}
            try:
                v = json.loads(t)
            except json.JSONDecodeError:
                return {"_legacy_text": t}
            if isinstance(v, (dict, list)):
                return v
            return {"_legacy_scalar": v}
        return super().to_internal_value(data)


class TestApproachImageSerializer(BaseModelSerializers):
    """
    方案图片序列化：返回可直接在前端展示的绝对 URL。
    """

    image_url = serializers.SerializerMethodField()

    class Meta:
        model = TestApproachImage
        fields = ("id", "approach_id", "image_url", "sort_order", "create_time")
        read_only_fields = fields

    def get_image_url(self, obj):
        request = self.context.get("request")
        if not obj.image:
            return None
        url = obj.image.url
        if request:
            return request.build_absolute_uri(url)
        return url


class TestModuleSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)

    class Meta:
        model = TestModule
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")


class TestEnvironmentSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)

    class Meta:
        model = TestEnvironment
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")


class EnvironmentVariableSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)
    display_value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EnvironmentVariable
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")

    def get_display_value(self, obj: EnvironmentVariable):
        """敏感变量默认返回脱敏值，避免前端误展示明文。"""
        if obj.is_secret:
            return "******"
        return obj.value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["display_value"] = self.get_display_value(instance)
        return data

class TestCaseSerializer(BaseModelSerializers):
    """
    多表继承统一出口：通用字段落在 TestCase，类型专属字段读写子表，API 仍为扁平 JSON。
    """

    creator_name = serializers.CharField(source="creator.real_name", read_only=True)

    api_url = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default=""
    )
    api_method = serializers.CharField(
        write_only=True, required=False, default="GET", max_length=16
    )
    api_headers = serializers.JSONField(write_only=True, required=False, default=dict)
    api_body = ApiBodyField(write_only=True, required=False, default=dict)
    api_expected_status = serializers.IntegerField(
        write_only=True, required=False, allow_null=True, default=None
    )

    concurrency = serializers.IntegerField(
        write_only=True, required=False, default=1, min_value=1
    )
    duration_seconds = serializers.IntegerField(
        write_only=True, required=False, default=60, min_value=1
    )
    target_rps = serializers.IntegerField(
        write_only=True, required=False, allow_null=True, min_value=1
    )

    attack_surface = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default=""
    )
    tool_preset = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default=""
    )
    risk_level = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default="", max_length=8
    )

    app_under_test = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default=""
    )
    primary_locator = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default=""
    )
    automation_framework = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default=""
    )

    class Meta:
        model = TestCase
        fields = (
            "id",
            "module",
            "case_name",
            "case_number",
            "test_type",
            "level",
            "is_valid",
            "exec_count",
            "review_status",
            "archive_status",
            "deleted_at",
            "is_deleted",
            "creator",
            "updater",
            "create_time",
            "update_time",
            "creator_name",
            "api_url",
            "api_method",
            "api_headers",
            "api_body",
            "api_expected_status",
            "concurrency",
            "duration_seconds",
            "target_rps",
            "attack_surface",
            "tool_preset",
            "risk_level",
            "app_under_test",
            "primary_locator",
            "automation_framework",
        )
        read_only_fields = (
            "creator",
            "updater",
            "create_time",
            "update_time",
            "creator_name",
            "deleted_at",
        )
        validators = []
        extra_kwargs = {
            "case_number": {"required": False, "allow_null": True},
        }

    def validate_test_type(self, value):
        if value is None:
            return value
        return str(value).strip()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        inject_typed_read_representation(instance, data)
        return data

    def create(self, validated_data):
        initial = self.initial_data if isinstance(self.initial_data, dict) else {}
        api, perf, sec, ui = split_typed_payload_create(validated_data, initial)
        tt = validated_data.get("test_type", TEST_CASE_TYPE_FUNCTIONAL)
        return create_typed_case(tt, validated_data, api, perf, sec, ui)

    def update(self, instance, validated_data):
        api, perf, sec, ui = split_typed_payload_update(validated_data)
        instance = super().update(instance, validated_data)
        sync_typed_children(
            instance,
            instance.test_type,
            api,
            perf,
            sec,
            ui,
            partial=self.partial,
        )
        return instance

    def validate(self, attrs):
        module = attrs.get("module", getattr(self.instance, "module", None))
        test_type = attrs.get("test_type", getattr(self.instance, "test_type", None))
        case_number = attrs.get("case_number", getattr(self.instance, "case_number", None))
        case_name = (
            attrs.get("case_name", getattr(self.instance, "case_name", "")) or ""
        ).strip()
        if module is not None and test_type and module.test_type != test_type:
            raise serializers.ValidationError(
                {"module": "所选模块的测试类型与用例测试类型不一致，请重新选择。"}
            )
        if self.instance is None and case_name and test_type:
            conflict = (
                TestCase.deleted_objects.filter(
                    case_name=case_name,
                    test_type=test_type,
                )
                .order_by("-deleted_at", "-id")
                .first()
            )
            if conflict:
                raise serializers.ValidationError(
                    {
                        "code": "RECYCLE_CONFLICT",
                        "msg": "回收站中已存在同名同类型用例，请先恢复或彻底删除后再创建。",
                        "recycle_case_id": conflict.id,
                    }
                )
        if test_type and case_number is not None:
            dup_qs = TestCase.objects.filter(test_type=test_type, case_number=case_number)
            if self.instance is not None:
                dup_qs = dup_qs.exclude(pk=self.instance.pk)
            if dup_qs.exists():
                raise serializers.ValidationError(
                    {"case_number": "该测试类型下业务编号已存在，请更换编号或留空自动生成。"}
                )
        return attrs


class ApiTestLogSerializer(BaseModelSerializers):
    """执行报告：对外统一暴露 created_at（即 create_time）。"""

    created_at = serializers.DateTimeField(source="create_time", read_only=True)

    class Meta:
        model = ApiTestLog
        fields = (
            "id",
            "test_case",
            "request_url",
            "request_method",
            "request_headers",
            "request_body",
            "response_status_code",
            "response_body",
            "response_time_ms",
            "is_passed",
            "created_at",
        )
        read_only_fields = fields


class ExecutionLogSerializer(BaseModelSerializers):
    """完整执行日志；兼容旧字段名 request_body / response_body / response_time_ms。"""

    created_at = serializers.DateTimeField(source="create_time", read_only=True)
    request_body = serializers.CharField(source="request_body_text", read_only=True)
    response_body = serializers.CharField(source="response_body_text", read_only=True)
    response_time_ms = serializers.IntegerField(source="duration_ms", read_only=True)

    class Meta:
        model = ExecutionLog
        fields = (
            "id",
            "test_case",
            "trace_id",
            "request_url",
            "request_method",
            "request_headers",
            "request_body",
            "request_body_text",
            "request_payload",
            "response_status_code",
            "response_headers",
            "response_body",
            "response_body_text",
            "response_payload",
            "response_time_ms",
            "duration_ms",
            "execution_status",
            "assertion_results",
            "is_passed",
            "error_message",
            "created_at",
        )
        read_only_fields = fields


class TestCaseStepSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)

    class Meta:
        model = TestCaseStep
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")


class TestCaseVersionSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)
    release_version_no = serializers.CharField(
        source="release_plan.version_no", read_only=True
    )
    snapshot_case_name = serializers.SerializerMethodField()
    snapshot_step_count = serializers.SerializerMethodField()
    snapshot_api_url = serializers.SerializerMethodField()

    class Meta:
        model = TestCaseVersion
        fields = (
            "id",
            "test_case",
            "release_plan",
            "release_version_no",
            "snapshot_no",
            "version_label",
            "source_version",
            "creator_name",
            "create_time",
            "snapshot_case_name",
            "snapshot_step_count",
            "snapshot_api_url",
            "case_snapshot",
        )
        read_only_fields = fields

    def _snapshot(self, obj):
        return obj.case_snapshot if isinstance(obj.case_snapshot, dict) else {}

    def get_snapshot_case_name(self, obj):
        snapshot = self._snapshot(obj)
        base = snapshot.get("base") if isinstance(snapshot.get("base"), dict) else {}
        return base.get("case_name") or snapshot.get("case_name") or ""

    def get_snapshot_step_count(self, obj):
        steps = self._snapshot(obj).get("steps")
        return len(steps) if isinstance(steps, list) else 0

    def get_snapshot_api_url(self, obj):
        subtype = self._snapshot(obj).get("subtype") or {}
        if not isinstance(subtype, dict):
            return ""
        return subtype.get("api_url") or ""


class TestApproachSerializer(BaseModelSerializers):
    creator_name = serializers.SerializerMethodField()
    # 方案历史上传图片
    images = TestApproachImageSerializer(many=True, read_only=True)
    test_category_display = serializers.SerializerMethodField()

    class Meta:
        model = TestApproach
        fields = [
            "id",
            "scheme_name",
            "version",
            "cover_image",
            "test_goal",
            "test_category",
            "test_category_display",
            "creator",
            "updater",
            "create_time",
            "update_time",
            "is_deleted",
            "creator_name",
            "images",
        ]
        read_only_fields = (
            "creator",
            "updater",
            "create_time",
            "update_time",
            "creator_name",
            "images",
            "test_category_display",
        )

    def get_creator_name(self, obj):
        u = getattr(obj, "creator", None)
        if not u:
            return None
        return getattr(u, "real_name", None) or getattr(u, "username", None) or None

    def get_test_category_display(self, obj):
        return obj.get_test_category_display()


class TestDesignSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)
    updater_name = serializers.CharField(source="updater.real_name", read_only=True)

    class Meta:
        model = TestDesign
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")
