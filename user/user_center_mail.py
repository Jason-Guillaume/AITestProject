import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def get_user_center_admin_recipients():
    """
    管理员收件人列表。
    优先 settings.USER_CENTER_ADMIN_EMAIL（可逗号分隔），否则用 settings.ADMINS 邮箱。
    """
    raw = getattr(settings, "USER_CENTER_ADMIN_EMAIL", "") or ""
    if raw.strip():
        return [e.strip() for e in raw.split(",") if e.strip()]
    admins = getattr(settings, "ADMINS", ()) or ()
    return [a[1] for a in admins if len(a) > 1 and a[1]]


def notify_admins_new_change_request(change_request):
    """
    新建敏感变更申请时通知管理员（失败仅记日志，不影响主流程）。
    """
    from user.models import UserChangeRequest

    recipients = get_user_center_admin_recipients()
    if not recipients:
        logger.warning(
            "未配置 USER_CENTER_ADMIN_EMAIL 或 ADMINS，跳过发送用户变更申请邮件"
        )
        return

    prefix = (getattr(settings, "EMAIL_SUBJECT_PREFIX", "") or "").strip()
    subject = (
        f"{prefix} 用户敏感信息变更待审批 #{change_request.id}".strip()
        if prefix
        else f"用户敏感信息变更待审批 #{change_request.id}"
    )

    body_lines = [
        f"申请编号: {change_request.id}",
        f"用户ID: {change_request.user_id}",
        f"当前用户名: {change_request.user.username}",
        f"申请类型: {change_request.get_request_type_display()}",
        f"状态: {change_request.get_status_display()}",
    ]
    if change_request.request_type == UserChangeRequest.RequestType.USERNAME:
        body_lines.append(f"目标用户名: {change_request.new_value}")
    else:
        body_lines.append(
            "目标密码: 已以 Django 哈希形式保存，审核「通过」后将写入该用户。"
        )

    body = "\n".join(body_lines)

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
    except Exception:
        logger.exception("发送用户变更申请通知邮件失败")
