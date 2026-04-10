from django.shortcuts import render
from rest_framework import viewsets
from django.db.models import Q

# Create your views here.


class BaseModelViewSet(viewsets.ModelViewSet):
    """
    全局基础视图集,封装通用的增删改查逻辑
    """

    enable_data_scope = True

    def _is_admin_user(self, user):
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.is_staff
                or bool(getattr(user, "is_system_admin", False))
            )
        )

    def _has_field(self, field_name: str) -> bool:
        return any(f.name == field_name for f in self.queryset.model._meta.get_fields())

    def _apply_member_scope(self, qs, user):
        """
        普通用户数据隔离：
        - 优先按项目成员关系放行（project/module/release/version/plan/testcase 等链路）
        - 兜底：仅可见自己创建的数据
        """
        if self._has_field("project"):
            return qs.filter(Q(project__members=user) | Q(creator=user)).distinct()
        if self._has_field("module"):
            return qs.filter(Q(module__project__members=user) | Q(creator=user)).distinct()
        if self._has_field("testcase"):
            return qs.filter(
                Q(testcase__module__project__members=user) | Q(creator=user)
            ).distinct()
        if self._has_field("test_case"):
            return qs.filter(
                Q(test_case__module__project__members=user) | Q(creator=user)
            ).distinct()
        if self._has_field("release_version"):
            return qs.filter(
                Q(release_version__project__members=user) | Q(creator=user)
            ).distinct()
        if self._has_field("version"):
            return qs.filter(Q(version__project__members=user) | Q(creator=user)).distinct()
        if self._has_field("plan"):
            return qs.filter(
                Q(plan__version__project__members=user)
                | Q(plan__testers=user)
                | Q(creator=user)
            ).distinct()
        if self._has_field("members"):
            return qs.filter(Q(members=user) | Q(creator=user)).distinct()
        if self._has_field("assignee"):
            return qs.filter(Q(assignee=user) | Q(creator=user)).distinct()
        if self._has_field("handler"):
            return qs.filter(Q(handler=user) | Q(creator=user)).distinct()
        return qs.filter(creator=user)

    def get_queryset(self):
        """重写查询集,默认只查未被逻辑删除的数据"""
        qs = self.queryset.filter(is_deleted=False)
        user = getattr(self.request, "user", None)
        if not self.enable_data_scope:
            return qs
        if not user or not user.is_authenticated or self._is_admin_user(user):
            return qs
        return self._apply_member_scope(qs, user)

    def perform_create(self, serializer):
        """创建时,自动填充ceator"""
        # 假设前端请求带有token.且通过了认证
        user = self.request.user
        if user.is_authenticated:
            serializer.save(creator=user)
        else:
            serializer.save()

    def perform_update(self, serializer):
        """更新时,自动填充updater"""
        user = self.request.user
        if user.is_authenticated:
            serializer.save(updater=user)
        else:
            serializer.save()

    def perform_destroy(self, instance):
        """重写删除逻辑,实现软删除"""
        instance.is_deleted = True
        instance.save()
