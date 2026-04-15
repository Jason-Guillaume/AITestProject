from rest_framework.permissions import BasePermission


class IsSystemAdmin(BasePermission):
    """仅系统管理员（ User.is_system_admin ）可访问组织/角色/用户等管理接口。"""

    message = "仅系统管理员可操作"

    def has_permission(self, request, view):
        u = request.user
        if not u or not u.is_authenticated:
            return False
        return bool(getattr(u, "is_system_admin", False))


class IsApprovalAdmin(BasePermission):
    """
    可处理敏感变更审批：Django staff / superuser / 本系统 is_system_admin。
    与站内信收件人范围对齐，避免仅有 staff 却无 is_system_admin 时无法操作。
    """

    message = "仅管理员可审批"

    def has_permission(self, request, view):
        u = request.user
        if not u or not u.is_authenticated:
            return False
        return bool(
            u.is_superuser or u.is_staff or getattr(u, "is_system_admin", False)
        )
