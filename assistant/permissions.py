"""
DRF permissions for assistant resources.
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission


def user_is_knowledge_document_privileged(user) -> bool:
    """Superuser, Django staff, or custom system admin flag."""
    return bool(
        user
        and user.is_authenticated
        and (
            user.is_superuser
            or user.is_staff
            or bool(getattr(user, "is_system_admin", False))
        )
    )


def user_is_org_member(user, org_id: int | None) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    try:
        oid = int(org_id or 0)
    except (TypeError, ValueError):
        return False
    if oid <= 0:
        return False
    try:
        qs = getattr(user, "organization_memberships", None)
        if qs is not None:
            return bool(qs.filter(id=oid, is_deleted=False).exists())
    except Exception:
        return False
    return False


class IsAdminOrKnowledgeResourceAccessible(BasePermission):
    """
    Allow access if the user is superuser/staff/system_admin, or created the object,
    or the object is shared to an organization the user belongs to.

    Intended for KnowledgeDocument / KnowledgeArticle rows.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if user_is_knowledge_document_privileged(request.user):
            return True
        creator_id = getattr(obj, "creator_id", None)
        try:
            return int(creator_id or 0) == int(request.user.id)
        except (TypeError, ValueError):
            pass
        scope = str(getattr(obj, "visibility_scope", "") or "").strip().lower()
        if scope == "org":
            return user_is_org_member(request.user, getattr(obj, "org_id", None))
        # project scope 尚未实现（需要项目成员关系），暂不放行
        return False
