from django.shortcuts import render
from rest_framework import viewsets
from django.db.models import Q
from django.db import models

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

    def _has_rel_field(self, field_name: str) -> bool:
        """
        是否存在“关系字段”（FK/O2O/M2M）。

        重要：避免字段同名但类型不匹配导致的错误 join。
        例如 TestApproach.version 是 CharField，但其他模型的 version 常为 FK，
        若误按 FK 链路拼接 version__project 会触发 FieldError。
        """
        try:
            f = self.queryset.model._meta.get_field(field_name)
        except Exception:
            return False
        if isinstance(
            f, (models.ForeignKey, models.OneToOneField, models.ManyToManyField)
        ):
            return True
        return False

    def _apply_member_scope(self, qs, user):
        """
        普通用户数据隔离：
        - 优先按项目成员关系放行（project/module/release/version/plan/testcase 等链路）
        - 兜底：仅可见自己创建的数据
        """
        if self._has_rel_field("project"):
            return qs.filter(Q(project__members=user) | Q(creator=user)).distinct()
        # 同时存在 module/release_version 的模型（如缺陷）需要两条链路都覆盖，避免仅按 module 过滤导致“按版本关联项目”的权限漏掉
        if self._has_rel_field("module") and self._has_rel_field("release_version"):
            return qs.filter(
                Q(module__project__members=user)
                | Q(release_version__project__members=user)
                | Q(creator=user)
            ).distinct()
        if self._has_rel_field("module"):
            return qs.filter(
                Q(module__project__members=user) | Q(creator=user)
            ).distinct()
        if self._has_rel_field("testcase"):
            return qs.filter(
                Q(testcase__module__project__members=user) | Q(creator=user)
            ).distinct()
        if self._has_rel_field("test_case"):
            return qs.filter(
                Q(test_case__module__project__members=user) | Q(creator=user)
            ).distinct()
        if self._has_rel_field("release_version"):
            return qs.filter(
                Q(release_version__project__members=user) | Q(creator=user)
            ).distinct()
        if self._has_rel_field("version"):
            return qs.filter(
                Q(version__project__members=user) | Q(creator=user)
            ).distinct()
        if self._has_rel_field("plan"):
            return qs.filter(
                Q(plan__version__project__members=user)
                | Q(plan__testers=user)
                | Q(creator=user)
            ).distinct()
        if self._has_rel_field("members"):
            return qs.filter(Q(members=user) | Q(creator=user)).distinct()
        if self._has_rel_field("assignee"):
            return qs.filter(Q(assignee=user) | Q(creator=user)).distinct()
        if self._has_rel_field("handler"):
            return qs.filter(Q(handler=user) | Q(creator=user)).distinct()
        return qs.filter(creator=user)

    def get_queryset(self):
        """重写查询集,默认只查未被逻辑删除的数据"""
        qs = self.queryset
        user = getattr(self.request, "user", None)
        active = qs.filter(is_deleted=False)
        if (
            not self.enable_data_scope
            or not user
            or not user.is_authenticated
            or self._is_admin_user(user)
        ):
            return active
        return self._apply_member_scope(active, user)

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
