from common.serialize import BaseModelSerializers

from assistant.models import GeneratedTestArtifact, KnowledgeArticle, KnowledgeDocument


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
