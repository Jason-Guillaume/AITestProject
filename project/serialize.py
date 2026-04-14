from django.contrib.auth import get_user_model
from rest_framework import serializers

from project.models import *
from common.serialize import BaseModelSerializers
from user.models import User


class _EmptyAsNullPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """multipart/form-data 中空字符串表示清空外键（等价 null）。"""

    def to_internal_value(self, data):
        if data in ("", None):
            if self.allow_null:
                return None
            self.fail("invalid")
        return super().to_internal_value(data)


class TestProjectSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)
    parent_name = serializers.SerializerMethodField()
    project_status_display = serializers.SerializerMethodField()

    # 列表/详情只读返回已保存路径；上传走 write_only 的 cover_image，避免与 icon 重复映射同一字段
    icon = serializers.ImageField(read_only=True)
    # 前端使用 FormData 上传文件时字段名为 cover_image
    cover_image = serializers.ImageField(
        source="icon",
        write_only=True,
        required=False,
        allow_null=True,
    )
    parent = _EmptyAsNullPrimaryKeyRelatedField(
        queryset=TestProject.objects.filter(is_deleted=False),
        allow_null=True,
        required=False,
    )
    members = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.filter(is_deleted=False),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = TestProject
        fields = [
            "id",
            "project_name",
            "parent",
            "description",
            "icon",
            "cover_image",
            "project_status",
            "project_status_display",
            "progress",
            "members",
            "creator",
            "updater",
            "create_time",
            "update_time",
            "is_deleted",
            "creator_name",
            "parent_name",
        ]
        read_only_fields = (
            "creator",
            "updater",
            "create_time",
            "update_time",
            "creator_name",
            "parent_name",
            "project_status_display",
        )

    def get_project_status_display(self, obj):
        return obj.get_project_status_display()

    def get_parent_name(self, obj):
        if obj.parent_id and obj.parent:
            return obj.parent.project_name
        return None

    def validate_cover_image(self, value):
        if value is None:
            return value
        max_size = 5 * 1024 * 1024
        if int(getattr(value, "size", 0) or 0) > max_size:
            raise serializers.ValidationError("封面图大小不能超过 5MB")
        ext = (str(getattr(value, "name", "")).rsplit(".", 1)[-1] or "").lower()
        if ext not in {"jpg", "jpeg", "png", "webp", "gif"}:
            raise serializers.ValidationError("封面图仅支持 jpg/jpeg/png/webp/gif")
        return value

    def validate_parent(self, value):
        """
        防止 parent 自引用/循环引用。
        """
        if value is None:
            return value

        # 更新时 self.instance 可能存在；创建时 instance 为 None
        current_id = getattr(self.instance, "id", None)
        if current_id and value.id == current_id:
            raise serializers.ValidationError("项目不能将自己设为父项目")

        # 循环检查：沿 parent 链向上追溯
        seen = {current_id} if current_id else set()
        p = value
        while p is not None:
            if p.id in seen:
                raise serializers.ValidationError("项目不能形成循环引用")
            seen.add(p.id)
            p = p.parent
        return value


class TestTaskSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)
    assignee_name = serializers.CharField(source="assignee.real_name", read_only=True)

    assignee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_deleted=False),
        required=True,
    )

    class Meta:
        model = TestTask
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")


class ReleasePlanSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)
    updater_name = serializers.CharField(source="updater.real_name", read_only=True, allow_null=True)
    project_name = serializers.CharField(
        source="project.project_name", read_only=True, allow_null=True
    )

    class Meta:
        model = ReleasePlan
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")
