"""
用户敏感变更：站内信通知与审批执行逻辑。
"""

from django.db.models import Q

from django.utils import timezone

from user.models import SystemMessage, User, UserChangeRequest


def admin_recipients_queryset():
    """
    接收待审批站内信的管理员账号。
    规范：is_staff OR is_superuser；并包含本项目的 is_system_admin，避免漏发。
    """
    return User.objects.filter(
        Q(is_staff=True) | Q(is_superuser=True) | Q(is_system_admin=True)
    ).distinct()


def create_inbox_messages_for_change_request(change_request):
    """为每位管理员创建一条关联 SystemMessage（bulk_create）。"""
    recipients = admin_recipients_queryset()
    if not recipients.exists():
        return

    u = change_request.user
    title = (
        f"【待审批】{u.username} 申请修改{change_request.get_request_type_display()}"
    )
    if change_request.request_type == UserChangeRequest.RequestType.USERNAME:
        content = (
            f"申请人：{u.username}（ID {u.pk}）\n"
            f"申请类型：{change_request.get_request_type_display()}\n"
            f"目标用户名：{change_request.new_value}\n"
            f"申请编号：{change_request.pk}\n"
            f"请在系统中审核通过或拒绝。"
        )
    else:
        content = (
            f"申请人：{u.username}（ID {u.pk}）\n"
            f"申请类型：{change_request.get_request_type_display()}\n"
            f"新密码已以安全哈希形式保存，审批通过后将写入该用户。\n"
            f"申请编号：{change_request.pk}\n"
            f"请在系统中审核通过或拒绝。"
        )

    rows = [
        SystemMessage(
            recipient=adm,
            title=title[:255],
            content=content,
            related_request=change_request,
        )
        for adm in recipients
    ]
    SystemMessage.objects.bulk_create(rows)


def mark_messages_for_request(change_request, *, is_read=True):
    """将某条申请关联的全部站内信标记为已读（审批处理后清理待办）。"""
    SystemMessage.objects.filter(related_request=change_request).update(is_read=is_read)


def approve_change_request(cr, *, approver=None):
    """
    通过申请：写回 User，更新状态，标记关联站内信已读。
    Raises ValueError：[reason] 业务失败（便于视图返回 400）。
    """
    if cr.status != UserChangeRequest.Status.PENDING:
        raise ValueError("该申请已处理")

    u = cr.user
    if cr.request_type == UserChangeRequest.RequestType.USERNAME:
        if User.objects.filter(username=cr.new_value).exclude(pk=u.pk).exists():
            raise ValueError("目标用户名已被占用")
        u.username = cr.new_value
        u.save(update_fields=["username"])
    elif cr.request_type == UserChangeRequest.RequestType.PASSWORD:
        u.password = cr.new_value
        u.save(update_fields=["password"])
    else:
        raise ValueError("未知申请类型")

    cr.status = UserChangeRequest.Status.APPROVED
    if approver is not None:
        cr.approver = approver
    cr.approved_at = timezone.now()
    cr.save(update_fields=["status", "approver", "approved_at", "updated_at"])
    mark_messages_for_request(cr, is_read=True)


def reject_change_request(cr, *, approver=None):
    """拒绝申请：更新状态并标记关联站内信已读。"""
    if cr.status != UserChangeRequest.Status.PENDING:
        raise ValueError("该申请已处理")

    cr.status = UserChangeRequest.Status.REJECTED
    if approver is not None:
        cr.approver = approver
    cr.approved_at = timezone.now()
    cr.save(update_fields=["status", "approver", "approved_at", "updated_at"])
    mark_messages_for_request(cr, is_read=True)
