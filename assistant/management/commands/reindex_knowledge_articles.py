from django.core.management.base import BaseCommand

from assistant.models import KnowledgeArticle, KnowledgeDocument
from assistant.tasks import process_knowledge_article_task


class Command(BaseCommand):
    help = "重建知识文章向量并回填处理状态"

    def add_arguments(self, parser):
        parser.add_argument(
            "--failed-only",
            action="store_true",
            help="仅重试失败状态的文章任务",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="最多处理多少条文章（0 表示不限制）",
        )

    def handle(self, *args, **options):
        failed_only = bool(options.get("failed_only"))
        limit = int(options.get("limit") or 0)

        qs = KnowledgeArticle.objects.filter(is_deleted=False).order_by("-id")
        total_candidates = 0
        done = 0
        failed = 0
        skipped = 0

        for article in qs:
            existing = KnowledgeDocument.objects.filter(
                article=article,
                is_deleted=False,
            ).order_by("-id").first()
            prev_status = existing.status if existing is not None else None
            if failed_only and prev_status != KnowledgeDocument.STATUS_FAILED:
                skipped += 1
                continue

            doc, _ = KnowledgeDocument.objects.update_or_create(
                article=article,
                defaults={
                    "title": article.title or "",
                    "category": article.category or "",
                    "tags": article.tags if isinstance(article.tags, list) else [],
                    "source_type": KnowledgeDocument.SOURCE_ARTICLE,
                    "status": KnowledgeDocument.STATUS_PENDING,
                    "error_message": "",
                    "creator": article.creator,
                    "updater": article.updater or article.creator,
                },
            )

            total_candidates += 1
            try:
                process_knowledge_article_task(int(article.id), int(doc.id))
                done += 1
            except Exception:
                failed += 1
            if limit > 0 and total_candidates >= limit:
                break

        self.stdout.write(
            self.style.SUCCESS(
                (
                    "知识文章向量重建完成: "
                    f"selected={total_candidates} success={done} failed={failed} skipped={skipped}"
                )
            )
        )
