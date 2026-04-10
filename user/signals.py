from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from user.change_request_actions import create_inbox_messages_for_change_request
from user.models import UserChangeRequest


@receiver(post_save, sender=UserChangeRequest)
def user_change_request_notify_admins(sender, instance, created, **kwargs):
    """
    新建的 pending 申请：事务提交后为所有管理员生成站内 SystemMessage。
    不使用邮件。
    """
    if not created:
        return
    if instance.status != UserChangeRequest.Status.PENDING:
        return

    def _create_messages():
        create_inbox_messages_for_change_request(instance)

    transaction.on_commit(_create_messages)
