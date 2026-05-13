from functools import cached_property

from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from django.db.models import Q
from django.db import models
from common.models import AuditEvent
from common.services.audit import record_audit_event

# Create your views here.


class BaseModelViewSet(viewsets.ModelViewSet):
    """
    全局基础视图集,封装通用的增删改查逻辑
    """

    enable_data_scope = True

    def _parse_id_list(self, raw_ids, max_count=500):
        if raw_ids is None:
            raise ValidationError({"msg": "ids 必填", "code": 400, "data": None})
        if not isinstance(raw_ids, list):
            raise ValidationError({"msg": "ids 必须为数组", "code": 400, "data": None})
        ids = []
        for x in raw_ids:
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                continue
        ids = [i for i in ids if i > 0]
        if not ids:
            raise ValidationError({"msg": "ids 不能为空", "code": 400, "data": None})
        if len(ids) > max_count:
            raise ValidationError({"msg": f"单次最多处理 {max_count} 条", "code": 400, "data": None})
        seen = set()
        uniq = []
        for i in ids:
            if i in seen:
                continue
            seen.add(i)
            uniq.append(i)
        return uniq

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

    @cached_property
    def _rel_field_names(self):
        return {
            f.name for f in self.queryset.model._meta.get_fields()
            if isinstance(f, (models.ForeignKey, models.OneToOneField, models.ManyToManyField))
        }

    def _has_rel_field(self, field_name: str) -> bool:
        """
        是否存在"关系字段"（FK/O2O/M2M）。

        重要：避免字段同名但类型不匹配导致的错误 join。
        例如 TestApproach.version 是 CharField，但其他模型的 version 常为 FK，
        若误按 FK 链路拼接 version__project 会触发 FieldError。
        """
        return field_name in self._rel_field_names

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
            instance = serializer.save(creator=user)
        else:
            instance = serializer.save()

        record_audit_event(
            action=AuditEvent.ACTION_CREATE,
            actor=user,
            instance=instance,
            request=self.request,
            before=None,
            after=None,
        )

    def perform_update(self, serializer):
        """更新时,自动填充updater"""
        user = self.request.user
        before = None
        try:
            before = serializer.instance
        except Exception:
            before = None
        if user.is_authenticated:
            instance = serializer.save(updater=user)
        else:
            instance = serializer.save()

        record_audit_event(
            action=AuditEvent.ACTION_UPDATE,
            actor=user,
            instance=instance,
            request=self.request,
            before=before,
            after=None,
        )

    def perform_destroy(self, instance):
        """重写删除逻辑,实现软删除"""
        user = getattr(self.request, "user", None)
        before = instance
        instance.is_deleted = True
        instance.save()

        record_audit_event(
            action=AuditEvent.ACTION_DELETE,
            actor=user,
            instance=instance,
            request=self.request,
            before=before,
            after=None,
        )
