"""
UI自动化脚本序列化器
"""
from rest_framework import serializers
from assistant.models import UIScriptUpload, UIScriptExecution


class UIScriptUploadSerializer(serializers.ModelSerializer):
    """UI脚本上传序列化器（详细）"""

    script_type_display = serializers.CharField(source='get_script_type_display', read_only=True)
    language_display = serializers.CharField(source='get_language_display', read_only=True)
    framework_display = serializers.CharField(source='get_framework_display', read_only=True)
    file_extension = serializers.CharField(read_only=True)
    is_zip = serializers.BooleanField(read_only=True)

    class Meta:
        model = UIScriptUpload
        fields = [
            'id', 'name', 'script_type', 'script_type_display',
            'language', 'language_display', 'framework', 'framework_display',
            'file_path', 'online_content', 'git_repo_url', 'entry_point',
            'workspace_path', 'dependencies', 'build_config',
            'created_at', 'updated_at', 'is_active',
            'file_extension', 'is_zip'
        ]
        read_only_fields = ['id', 'workspace_path', 'created_at', 'updated_at']


class UIScriptUploadListSerializer(serializers.ModelSerializer):
    """UI脚本上传序列化器（列表）"""

    script_type_display = serializers.CharField(source='get_script_type_display', read_only=True)
    language_display = serializers.CharField(source='get_language_display', read_only=True)
    framework_display = serializers.CharField(source='get_framework_display', read_only=True)

    class Meta:
        model = UIScriptUpload
        fields = [
            'id', 'name', 'script_type', 'script_type_display',
            'language', 'language_display', 'framework', 'framework_display',
            'entry_point', 'is_active', 'created_at', 'updated_at'
        ]


class UIScriptExecutionSerializer(serializers.ModelSerializer):
    """UI脚本执行序列化器（详细）"""

    script_name = serializers.CharField(source='script.name', read_only=True)
    script_type = serializers.CharField(source='script.script_type', read_only=True)
    script_language = serializers.CharField(source='script.language', read_only=True)
    script_framework = serializers.CharField(source='script.framework', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_running = serializers.BooleanField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)
    is_success = serializers.BooleanField(read_only=True)

    class Meta:
        model = UIScriptExecution
        fields = [
            'id', 'execution_id', 'script', 'script_name', 'script_type',
            'script_language', 'script_framework',
            'status', 'status_display', 'return_code',
            'started_at', 'completed_at', 'duration',
            'error_message', 'log_file_path', 'triggered_by',
            'created_at', 'updated_at',
            'is_running', 'is_completed', 'is_success'
        ]
        read_only_fields = [
            'id', 'execution_id', 'status', 'return_code',
            'started_at', 'completed_at', 'duration',
            'error_message', 'log_file_path', 'created_at', 'updated_at'
        ]


class UIScriptExecutionListSerializer(serializers.ModelSerializer):
    """UI脚本执行序列化器（列表）"""

    script_name = serializers.CharField(source='script.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = UIScriptExecution
        fields = [
            'id', 'execution_id', 'script', 'script_name',
            'status', 'status_display', 'return_code',
            'started_at', 'completed_at', 'duration',
            'triggered_by', 'created_at'
        ]
