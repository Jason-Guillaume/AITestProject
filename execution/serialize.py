from rest_framework import serializers
from execution.models import *
from common.serialize import BaseModelSerializers
from user.models import User
from testcase.models import TestCase
import re

from apscheduler.triggers.cron import CronTrigger


class TestPlanSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)
    testers = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.filter(is_deleted=False),
        required=False,
        allow_empty=True,
    )
    testers_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TestPlan
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")

    def get_testers_display(self, obj):
        return ", ".join(
            (u.real_name or u.username or str(u.pk)) for u in obj.testers.all()
        )

    def create(self, validated_data):
        testers = validated_data.pop("testers", [])
        instance = super().create(validated_data)
        if testers:
            instance.testers.set(testers)
        return instance

    def update(self, instance, validated_data):
        testers = validated_data.pop("testers", serializers.empty)
        instance = super().update(instance, validated_data)
        if testers is not serializers.empty:
            instance.testers.set(testers)
        return instance


class TestReportSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)

    class Meta:
        model = TestReport
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")


class PerfTaskSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)
    created_at = serializers.DateTimeField(
        source="create_time", format="%Y-%m-%d %H:%M:%S", read_only=True
    )

    class Meta:
        model = PerfTask
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")
        extra_kwargs = {
            "task_id": {"read_only": True},
        }

    def validate_concurrency(self, value):
        if value <= 0:
            raise serializers.ValidationError("并发数必须大于 0")
        if value > 100000:
            raise serializers.ValidationError("并发数过大，请控制在 100000 以内")
        return value

    def validate_duration(self, value):
        # 支持: 30s / 10m / 2h
        if not re.match(r"^\d+[smh]$", value):
            raise serializers.ValidationError("持续时间格式错误，应为如 30s、10m、2h")
        return value


class ScheduledTaskSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)
    test_case_ids = serializers.PrimaryKeyRelatedField(
        source="test_cases",
        many=True,
        queryset=TestCase.objects.filter(is_deleted=False),
        required=False,
    )

    class Meta:
        model = ScheduledTask
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")

    def validate_cron_expression(self, value):
        try:
            CronTrigger.from_crontab(value)
        except Exception:
            raise serializers.ValidationError("Cron 表达式不合法，请使用标准五段格式")
        return value

    def create(self, validated_data):
        test_cases = validated_data.pop("test_cases", [])
        instance = super().create(validated_data)
        if test_cases:
            instance.test_cases.set(test_cases)
        return instance

    def update(self, instance, validated_data):
        test_cases = validated_data.pop("test_cases", serializers.empty)
        instance = super().update(instance, validated_data)
        if test_cases is not serializers.empty:
            instance.test_cases.set(test_cases)
        return instance


class ScheduledTaskLogSerializer(BaseModelSerializers):
    class Meta:
        model = ScheduledTaskLog
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")


class K6LoadTestSessionCreateSerializer(serializers.ModelSerializer):
    test_case_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )

    class Meta:
        model = K6LoadTestSession
        fields = ("test_case_ids", "vus", "duration", "use_ai", "target_base_url")

    def validate_duration(self, value):
        if not re.match(r"^\d+[smh]$", (value or "").strip()):
            raise serializers.ValidationError("持续时间格式错误，应为如 30s、10m、2h")
        return value.strip()

    def validate_vus(self, value):
        if value < 1:
            raise serializers.ValidationError("vus 至少为 1")
        if value > 500:
            raise serializers.ValidationError("vus 请控制在 500 以内")
        return value


class K6LoadTestSessionDetailSerializer(BaseModelSerializers):
    class Meta:
        model = K6LoadTestSession
        fields = (
            "id",
            "run_id",
            "status",
            "test_case_ids",
            "vus",
            "duration",
            "use_ai",
            "target_base_url",
            "script_rel_path",
            "script_body",
            "summary",
            "error_message",
            "generation_source",
            "celery_task_id",
            "create_time",
            "update_time",
        )
        read_only_fields = fields


class ApiScenarioSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)

    class Meta:
        model = ApiScenario
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")


class ApiScenarioStepSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)

    class Meta:
        model = ApiScenarioStep
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")


class ApiScenarioRunSerializer(BaseModelSerializers):
    class Meta:
        model = ApiScenarioRun
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")


class ApiScenarioStepRunSerializer(BaseModelSerializers):
    class Meta:
        model = ApiScenarioStepRun
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")
