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
    defect_no = serializers.CharField(max_length=255, required=False, allow_blank=True)
    handler = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_deleted=False),
        required=False,
    )

    class Meta:
        model = TestDefect
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")
