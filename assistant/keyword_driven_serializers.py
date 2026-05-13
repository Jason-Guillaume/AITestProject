"""
关键字驱动框架序列化器

遵循项目现有序列化器风格 (ui_element_serializers.py)：
  - ModelSerializer + 显式 fields 列表
  - 通过 source 参数展开关联字段名称
  - SerializerMethodField 计算派生值
  - read_only_fields 保护自动字段
"""
from rest_framework import serializers
from assistant.keyword_driven_models import (
    KWElementLocator,
    KWTestCase,
    KWActionStep,
)


class KWElementLocatorSerializer(serializers.ModelSerializer):
    """关键字驱动 - 元素定位器序列化器"""

    locator_type_display = serializers.CharField(
        source="get_locator_type_display",
        read_only=True,
    )
    selenium_by = serializers.SerializerMethodField()
    referencing_steps_count = serializers.SerializerMethodField()

    class Meta:
        model = KWElementLocator
        fields = [
            "id",
            "project",
            "name",
            "locator_type",
            "locator_type_display",
            "locator_expression",
            "selenium_by",
            "description",
            "referencing_steps_count",
            "create_time",
            "update_time",
        ]
        read_only_fields = ["id", "create_time", "update_time"]

    def get_selenium_by(self, obj):
        return KWElementLocator.SELENIUM_BY_MAP.get(obj.locator_type, "")

    def get_referencing_steps_count(self, obj):
        return obj.referencing_steps.count()


class KWActionStepReadSerializer(serializers.ModelSerializer):
    """关键字驱动 - 步骤读取序列化器（嵌套展开定位器详情）"""

    action_type_display = serializers.CharField(
        source="get_action_type_display",
        read_only=True,
    )
    element_name = serializers.CharField(
        source="element.name",
        read_only=True,
        allow_null=True,
    )
    element_locator_type = serializers.CharField(
        source="element.locator_type",
        read_only=True,
        allow_null=True,
    )
    element_locator_expression = serializers.CharField(
        source="element.locator_expression",
        read_only=True,
        allow_null=True,
    )
    assert_type_display = serializers.CharField(
        source="get_assert_type_display",
        read_only=True,
    )

    class Meta:
        model = KWActionStep
        fields = [
            "id",
            "test_case",
            "step_order",
            "action_type",
            "action_type_display",
            "element",
            "element_name",
            "element_locator_type",
            "element_locator_expression",
            "action_value",
            "assert_type",
            "assert_type_display",
            "assert_expected",
            "test_data",
            "description",
            "enabled",
            "create_time",
            "update_time",
        ]
        read_only_fields = ["id", "create_time", "update_time"]


class KWActionStepWriteSerializer(serializers.ModelSerializer):
    """关键字驱动 - 步骤写入序列化器（仅接受 FK ID，避免嵌套写入）"""

    class Meta:
        model = KWActionStep
        fields = [
            "id",
            "test_case",
            "step_order",
            "action_type",
            "element",
            "action_value",
            "assert_type",
            "assert_expected",
            "test_data",
            "description",
            "enabled",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        action_type = attrs.get("action_type", getattr(self.instance, "action_type", ""))
        element = attrs.get("element", getattr(self.instance, "element", None))

        if action_type in KWActionStep.ELEMENT_REQUIRED_ACTIONS and element is None:
            raise serializers.ValidationError(
                {"element": f"操作类型 '{action_type}' 必须关联一个页面元素"}
            )

        if action_type == KWActionStep.ACTION_ASSERT:
            assert_type = attrs.get("assert_type", getattr(self.instance, "assert_type", ""))
            if not assert_type:
                raise serializers.ValidationError(
                    {"assert_type": "断言操作必须指定断言类型"}
                )

        return attrs


class KWTestCaseListSerializer(serializers.ModelSerializer):
    """关键字驱动 - 用例列表序列化器（轻量，不含步骤详情）"""

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    steps_count = serializers.SerializerMethodField()

    class Meta:
        model = KWTestCase
        fields = [
            "id",
            "project",
            "name",
            "description",
            "status",
            "status_display",
            "base_url",
            "timeout_seconds",
            "steps_count",
            "create_time",
            "update_time",
        ]
        read_only_fields = ["id", "create_time", "update_time"]

    def get_steps_count(self, obj):
        return obj.steps.count()


class KWTestCaseDetailSerializer(serializers.ModelSerializer):
    """关键字驱动 - 用例详情序列化器（嵌套步骤列表）"""

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    steps = KWActionStepReadSerializer(many=True, read_only=True)

    class Meta:
        model = KWTestCase
        fields = [
            "id",
            "project",
            "name",
            "description",
            "status",
            "status_display",
            "base_url",
            "variables",
            "timeout_seconds",
            "steps",
            "create_time",
            "update_time",
        ]
        read_only_fields = ["id", "create_time", "update_time"]


class KWTestCaseWriteSerializer(serializers.ModelSerializer):
    """关键字驱动 - 用例写入序列化器"""

    class Meta:
        model = KWTestCase
        fields = [
            "id",
            "project",
            "name",
            "description",
            "status",
            "base_url",
            "variables",
            "timeout_seconds",
        ]
        read_only_fields = ["id"]


class KWTestCaseExecutorSerializer(serializers.ModelSerializer):
    """
    关键字驱动 - 用例执行器序列化器

    输出 to_executor_dict() 格式的 JSON，供执行引擎直接消费。
    包含完整的定位器信息，无需执行器二次查询。
    """

    steps = serializers.SerializerMethodField()

    class Meta:
        model = KWTestCase
        fields = ["id", "name", "base_url", "variables", "timeout_seconds", "steps"]

    def get_steps(self, obj):
        steps = obj.steps.select_related("element").order_by("step_order")
        return [step.to_executor_dict() for step in steps]
