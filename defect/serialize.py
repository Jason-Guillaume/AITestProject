from rest_framework import serializers
from defect.models import *
from common.serialize import BaseModelSerializers
from user.models import User


class TestDefectSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)
    release_version_no = serializers.CharField(
        source="release_version.version_no", read_only=True, allow_null=True
    )
    handler_name = serializers.CharField(
        source="handler.real_name", read_only=True, allow_null=True
    )
    defect_no = serializers.CharField(
        max_length=255, required=False, allow_blank=True, write_only=True
    )
    handler = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_deleted=False),
        required=False,
    )

    def validate_defect_no(self, value):
        value = (value or "").strip()
        if not value:
            return value
        qs = TestDefect.objects.filter(defect_no=value, is_deleted=False)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("缺陷编号已存在")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        severity = attrs.get("severity", getattr(self.instance, "severity", 3))
        priority = attrs.get("priority", getattr(self.instance, "priority", 2))

        if severity == 1 and priority != 1:
            raise serializers.ValidationError({"priority": "致命缺陷的优先级必须为高"})
        if severity == 4 and priority != 3:
            raise serializers.ValidationError(
                {"priority": "建议类缺陷的优先级必须为低"}
            )

        # 业务要求：缺陷必须归属模块（创建时强制，更新时不强制补齐历史数据）
        if not self.instance and not attrs.get("module"):
            raise serializers.ValidationError({"module": "缺陷必须指定所属模块"})

        return attrs

    class Meta:
        model = TestDefect
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")
