from rest_framework import serializers
from common.serialize import BaseModelSerializers

from assistant.models import (
    GeneratedTestArtifact,
    KnowledgeArticle,
    KnowledgeDocument,
    UIScriptExecution,
    UIScriptUpload,
    UIPomTestReport,
)
import os


class KnowledgeArticleSerializer(BaseModelSerializers):
    class Meta:
        model = KnowledgeArticle
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")


class KnowledgeDocumentSerializer(BaseModelSerializers):
    class Meta:
        model = KnowledgeDocument
        fields = "__all__"
        read_only_fields = (
            "status",
            "error_message",
            "created_at",
            "creator",
            "updater",
            "create_time",
            "update_time",
        )


class GeneratedTestArtifactSerializer(BaseModelSerializers):
    class Meta:
        model = GeneratedTestArtifact
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")


class UIScriptUploadSerializer(serializers.ModelSerializer):
    """UI脚本上传序列化器"""

    file_extension = serializers.ReadOnlyField()
    is_zip = serializers.ReadOnlyField()
    file_size = serializers.SerializerMethodField()

    class Meta:
        model = UIScriptUpload
        fields = [
            'id',
            'name',
            'script_type',
            'language',
            'framework',
            'file_path',
            'online_content',
            'git_repo_url',
            'entry_point',
            'workspace_path',
            'dependencies',
            'build_config',
            'created_at',
            'updated_at',
            'is_active',
            'folder',
            'is_deleted',
            'deleted_at',
            'file_extension',
            'is_zip',
            'file_size',
        ]
        # is_deleted / deleted_at 仅允许通过 soft_delete、restore、empty_trash 等接口变更，禁止客户端在创建/ PATCH 时写入回收站
        read_only_fields = [
            'id',
            'workspace_path',
            'created_at',
            'updated_at',
            'is_deleted',
            'deleted_at',
        ]

    def get_file_size(self, obj):
        """获取文件大小（字节）"""
        try:
            return obj.file_path.size
        except Exception:
            return None

    def validate_file_path(self, value):
        """验证文件类型和大小"""
        if not value:
            return value

        max_size = 50 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"文件大小不能超过50MB，当前大小: {value.size / 1024 / 1024:.2f}MB"
            )

        ext = os.path.splitext(value.name)[1].lower()
        if ext not in ['.py', '.zip']:
            raise serializers.ValidationError(
                f"不支持的文件类型: {ext}，仅支持 .py 和 .zip"
            )

        return value

    def validate(self, attrs):
        """交叉字段验证"""
        script_type = attrs.get('script_type')
        file_path = attrs.get('file_path')
        online_content = attrs.get('online_content')
        git_repo_url = attrs.get('git_repo_url')
        entry_point = attrs.get('entry_point')

        # ONLINE 类型：必须提供在线内容
        if script_type == UIScriptUpload.ScriptType.ONLINE:
            if not online_content:
                raise serializers.ValidationError({
                    'online_content': '在线脚本必须提供脚本内容'
                })
            # ONLINE 类型如果没有 entry_point，使用默认值
            if not entry_point:
                attrs['entry_point'] = 'test_script.py'

        # LINEAR 类型：必须提供文件
        elif script_type == UIScriptUpload.ScriptType.LINEAR:
            if not file_path and not online_content:
                raise serializers.ValidationError({
                    'file_path': '线性脚本必须上传文件或提供在线内容'
                })
            # LINEAR 类型的 entry_point 可以为空，默认使用上传的文件名
            if not entry_point and file_path:
                attrs['entry_point'] = os.path.basename(file_path.name)
            elif not entry_point:
                attrs['entry_point'] = 'test_script.py'

        # POM 类型：必须提供 entry_point，文件或 Git URL 二选一
        elif script_type == UIScriptUpload.ScriptType.POM:
            if not entry_point:
                raise serializers.ValidationError({
                    'entry_point': 'POM 模式必须指定执行入口点'
                })
            if not file_path and not git_repo_url and not online_content:
                raise serializers.ValidationError({
                    'file_path': 'POM 模式必须上传 ZIP 文件、提供 Git 仓库 URL 或在线内容'
                })

        return attrs


class UIScriptUploadListSerializer(serializers.ModelSerializer):
    """列表展示序列化器（精简版）"""

    file_size = serializers.SerializerMethodField()

    class Meta:
        model = UIScriptUpload
        fields = [
            'id',
            'name',
            'script_type',
            'language',
            'framework',
            'entry_point',
            'created_at',
            'updated_at',
            'is_active',
            'folder',
            'is_deleted',
            'deleted_at',
            'file_size',
        ]

    def get_file_size(self, obj):
        """获取文件大小（格式化）"""
        try:
            size = obj.file_path.size
            if size < 1024:
                return f"{size}B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.2f}KB"
            else:
                return f"{size / 1024 / 1024:.2f}MB"
        except Exception:
            return "未知"


class UIScriptExecutionSerializer(serializers.ModelSerializer):
    """UI脚本执行记录序列化器"""

    script_name = serializers.CharField(source='script.name', read_only=True)
    script_type = serializers.CharField(source='script.script_type', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_running = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    is_success = serializers.ReadOnlyField()

    class Meta:
        model = UIScriptExecution
        fields = [
            'id',
            'execution_id',
            'script',
            'script_name',
            'script_type',
            'status',
            'status_display',
            'return_code',
            'started_at',
            'completed_at',
            'duration',
            'error_message',
            'log_file_path',
            'triggered_by',
            'created_at',
            'updated_at',
            'is_running',
            'is_completed',
            'is_success',
        ]
        read_only_fields = [
            'id',
            'execution_id',
            'script_name',
            'script_type',
            'status_display',
            'is_running',
            'is_completed',
            'is_success',
            'created_at',
            'updated_at',
        ]


class UIScriptExecutionListSerializer(serializers.ModelSerializer):
    """UI脚本执行记录列表序列化器（精简版）"""

    script_name = serializers.CharField(source='script.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_display = serializers.SerializerMethodField()

    class Meta:
        model = UIScriptExecution
        fields = [
            'id',
            'execution_id',
            'script',
            'script_name',
            'status',
            'status_display',
            'return_code',
            'started_at',
            'completed_at',
            'duration',
            'duration_display',
            'triggered_by',
            'created_at',
        ]

    def get_duration_display(self, obj):
        """格式化执行时长"""
        if obj.duration is None:
            return None

        duration = obj.duration
        if duration < 60:
            return f"{duration:.2f}秒"
        elif duration < 3600:
            minutes = int(duration // 60)
            seconds = duration % 60
            return f"{minutes}分{seconds:.0f}秒"
        else:
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            return f"{hours}小时{minutes}分"


class UIPomTestReportListSerializer(serializers.ModelSerializer):
    """UI POM 报告列表"""

    script_name = serializers.CharField(source="script.name", read_only=True)
    execution_id_str = serializers.CharField(source="execution.execution_id", read_only=True)
    execution_status = serializers.CharField(source="execution.status", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = UIPomTestReport
        fields = [
            "id",
            "title",
            "script",
            "script_name",
            "execution",
            "execution_id_str",
            "execution_status",
            "source_relative_path",
            "file_size",
            "file_url",
            "created_at",
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        if not obj.report_file:
            return None
        request = self.context.get("request")
        if request is None:
            return obj.report_file.url
        return request.build_absolute_uri(f"/api/assistant/ui-pom-reports/{obj.pk}/download/")


class UIPomTestReportSerializer(serializers.ModelSerializer):
    """UI POM 报告详情"""

    script_name = serializers.CharField(source="script.name", read_only=True)
    execution_id_str = serializers.CharField(source="execution.execution_id", read_only=True)
    execution_status = serializers.CharField(source="execution.status", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = UIPomTestReport
        fields = [
            "id",
            "title",
            "script",
            "script_name",
            "execution",
            "execution_id_str",
            "execution_status",
            "source_relative_path",
            "file_size",
            "file_url",
            "created_at",
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        if not obj.report_file:
            return None
        request = self.context.get("request")
        if request is None:
            return obj.report_file.url
        return request.build_absolute_uri(f"/api/assistant/ui-pom-reports/{obj.pk}/download/")
