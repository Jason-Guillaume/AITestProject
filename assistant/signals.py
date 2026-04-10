import threading

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from assistant.knowledge_rag import KnowledgeIndexer
from assistant.models import KnowledgeArticle, KnowledgeDocument


def _enqueue_article_vector_task(article_id: int, doc_id: int):
    try:
        from assistant.tasks import process_knowledge_article_task

        process_knowledge_article_task.delay(int(article_id), int(doc_id))
    except Exception:
        from assistant.tasks import process_knowledge_article_task

        threading.Thread(
            target=process_knowledge_article_task,
            args=(int(article_id), int(doc_id)),
            daemon=True,
        ).start()


@receiver(post_save, sender=KnowledgeArticle)
def knowledge_article_post_save(sender, instance, **kwargs):
    doc, _ = KnowledgeDocument.objects.update_or_create(
        article=instance,
        defaults={
            "title": instance.title or "",
            "category": instance.category or "",
            "tags": instance.tags if isinstance(instance.tags, list) else [],
            "source_type": KnowledgeDocument.SOURCE_ARTICLE,
            "status": KnowledgeDocument.STATUS_PENDING,
            "error_message": "",
            "creator": instance.creator,
            "updater": instance.updater or instance.creator,
        },
    )
    _enqueue_article_vector_task(int(instance.id), int(doc.id))


@receiver(post_delete, sender=KnowledgeArticle)
def knowledge_article_post_delete(sender, instance, **kwargs):
    KnowledgeIndexer.delete_article(instance.id)
    KnowledgeDocument.objects.filter(article=instance).update(is_deleted=True)
