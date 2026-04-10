from django.core.management.base import BaseCommand

from assistant.knowledge_rag import KnowledgeIndexer


class Command(BaseCommand):
    help = "重建测试知识库向量索引"

    def handle(self, *args, **options):
        result = KnowledgeIndexer.reindex_all()
        self.stdout.write(
            self.style.SUCCESS(
                f"知识库重建完成: total={result['total']} success={result['success']} failed={result['failed']}"
            )
        )
