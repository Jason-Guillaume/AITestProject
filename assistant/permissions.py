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


class IsAdminOrDocumentCreator(BasePermission):
    """
    Allow access if the user is superuser/staff/system_admin, or created the object.
    Intended for KnowledgeDocument rows (expects ``creator_id`` on ``obj``).
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
            return False
