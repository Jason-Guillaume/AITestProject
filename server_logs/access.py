"""
远程日志主机访问控制：平台管理员、创建人、绑定组织的创建人/成员。
"""

from __future__ import annotations

from django.db.models import Q


def user_is_platform_log_admin(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and (
            getattr(user, "is_superuser", False)
            or getattr(user, "is_staff", False)
            or bool(getattr(user, "is_system_admin", False))
        )
    )


def user_can_access_remote_log_server(user, server) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user_is_platform_log_admin(user):
        return True
    if server.creator_id == user.id:
        return True
    org_id = getattr(server, "organization_id", None)
    if not org_id:
        return False
    org = getattr(server, "organization", None)
    if org is None:
        from user.models import Organization

        try:
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return False
    if getattr(org, "creator_id", None) == user.id:
        return True
    return org.members.filter(pk=user.pk).exists()


def remote_log_server_queryset_for_user(user):
    """未认证返回空查询集。"""
    from server_logs.models import RemoteLogServer

    qs = RemoteLogServer.objects.filter(is_deleted=False).select_related("organization")
    if not user or not user.is_authenticated:
        return qs.none()
    if user_is_platform_log_admin(user):
        return qs
    return qs.filter(
        Q(creator=user)
        | (
            Q(organization_id__isnull=False)
            & (Q(organization__members=user) | Q(organization__creator=user))
        )
    ).distinct()
