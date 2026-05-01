"""
UI元素库序列化器
"""
from rest_framework import serializers
from assistant.ui_element_models import (
    UIModule,
    UIPage,
    UIPageElement,
    UITestCase,
    UIActionStep
)


class UIModuleSerializer(serializers.ModelSerializer):
    """UI模块序列化器"""
    children_count = serializers.SerializerMethodField()
    pages_count = serializers.SerializerMethodField()

    class Meta:
        model = UIModule
        fields = [
            'id', 'project', 'name', 'parent', 'description',
            'order', 'children_count', 'pages_count',
            'create_time', 'update_time'
        ]
        read_only_fields = ['id', 'create_time', 'update_time']

    def get_children_count(self, obj):
        return obj.children.count()

    def get_pages_count(self, obj):
        return obj.pages.count()


class UIPageSerializer(serializers.ModelSerializer):
    """UI页面序列化器"""
    module_name = serializers.CharField(source='module.name', read_only=True)
    elements_count = serializers.SerializerMethodField()

    class Meta:
        model = UIPage
        fields = [
            'id', 'module', 'module_name', 'name', 'url',
            'description', 'order', 'elements_count',
            'create_time', 'update_time'
        ]
        read_only_fields = ['id', 'create_time', 'update_time']

    def get_elements_count(self, obj):
        return obj.elements.count()


class UIPageElementSerializer(serializers.ModelSerializer):
    """UI页面元素序列化器"""
    page_name = serializers.CharField(source='page.name', read_only=True)
    module_name = serializers.CharField(source='page.module.name', read_only=True)

    class Meta:
        model = UIPageElement
        fields = [
            'id', 'page', 'page_name', 'module_name', 'name',
            'locator_type', 'locator_value', 'description', 'order',
            'create_time', 'update_time'
        ]
        read_only_fields = ['id', 'create_time', 'update_time']


class UITestCaseSerializer(serializers.ModelSerializer):
    """UI测试用例序列化器"""
    module_name = serializers.CharField(source='module.name', read_only=True)
    steps_count = serializers.SerializerMethodField()

    class Meta:
        model = UITestCase
        fields = [
            'id', 'module', 'module_name', 'name', 'preconditions',
            'expected_result', 'priority', 'order', 'steps_count',
            'create_time', 'update_time'
        ]
        read_only_fields = ['id', 'create_time', 'update_time']

    def get_steps_count(self, obj):
        return obj.action_steps.count()


class UIActionStepSerializer(serializers.ModelSerializer):
    """UI操作步骤序列化器"""
    test_case_name = serializers.CharField(source='test_case.name', read_only=True)
    element_name = serializers.CharField(source='element.name', read_only=True, allow_null=True)

    class Meta:
        model = UIActionStep
        fields = [
            'id', 'test_case', 'test_case_name', 'sequence',
            'action_type', 'element', 'element_name', 'test_data',
            'description', 'create_time', 'update_time'
        ]
        read_only_fields = ['id', 'create_time', 'update_time']


class UIModuleTreeSerializer(serializers.ModelSerializer):
    """UI模块树形结构序列化器（用于前端Tree组件）"""
    children = serializers.SerializerMethodField()
    pages = UIPageSerializer(many=True, read_only=True)
    label = serializers.CharField(source='name', read_only=True)

    class Meta:
        model = UIModule
        fields = ['id', 'name', 'label', 'parent', 'description', 'order', 'children', 'pages']

    def get_children(self, obj):
        children = obj.children.all()
        return UIModuleTreeSerializer(children, many=True).data
