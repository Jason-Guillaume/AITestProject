from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from common.models import AuditEvent
from common.services.audit import record_audit_event


class RecyclableMixin:
    recycle_mode_param = "recycle"
    hard_delete_audit = True

    def _is_recycle_mode(self, params=None):
        params = params or self.request.query_params
        r = params.get(self.recycle_mode_param)
        if r is not None and str(r).strip().lower() in ("1", "true", "yes"):
            return True
        d = params.get("is_deleted")
        if d is not None and str(d).strip().lower() in ("1", "true", "yes"):
            return True
        return False

    def get_recycle_queryset(self):
        model = self.queryset.model
        qs = model.objects.filter(is_deleted=True)
        user = getattr(self.request, "user", None)
        if (
            getattr(self, "enable_data_scope", False)
            and user
            and getattr(user, "is_authenticated", False)
            and not self._is_admin_user(user)
        ):
            qs = self._apply_member_scope(qs, user)
        return qs

    @action(detail=False, methods=["get"], url_path="recycle")
    def recycle(self, request):
        qp = request.query_params.copy()
        qp[self.recycle_mode_param] = "1"
        original_params = self.request.query_params
        self.request._get = qp
        try:
            return self.list(request)
        finally:
            self.request._get = original_params

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        model = self.queryset.model
        obj = get_object_or_404(model.objects.filter(is_deleted=True), pk=pk)
        obj.is_deleted = False
        obj.save(update_fields=["is_deleted", "update_time"])
        return Response({"success": True, "id": int(obj.id)})

    @action(detail=False, methods=["post"], url_path="bulk-soft-delete")
    def bulk_soft_delete(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        qs = self.get_queryset().filter(id__in=ids, is_deleted=False)
        found_ids = list(qs.values_list("id", flat=True))
        if not found_ids:
            return Response({"success": True, "deleted": 0, "skipped": len(ids), "missing_ids": ids})
        with transaction.atomic():
            updated = qs.update(is_deleted=True)
        missing = [i for i in ids if i not in set(found_ids)]
        return Response({"success": True, "deleted": int(updated), "skipped": len(missing), "missing_ids": missing})

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        model = self.queryset.model
        user = getattr(request, "user", None)
        qs = model.objects.filter(id__in=ids, is_deleted=True)
        if (
            getattr(self, "enable_data_scope", False)
            and user
            and getattr(user, "is_authenticated", False)
            and not self._is_admin_user(user)
        ):
            qs = self._apply_member_scope(qs, user)
        found_ids = list(qs.values_list("id", flat=True))
        if not found_ids:
            return Response({"success": True, "restored": 0, "skipped": len(ids), "missing_ids": ids})
        with transaction.atomic():
            updated = qs.update(is_deleted=False)
        missing = [i for i in ids if i not in set(found_ids)]
        return Response({"success": True, "restored": int(updated), "skipped": len(missing), "missing_ids": missing})

    @action(detail=True, methods=["post"], url_path="hard-delete")
    def hard_delete(self, request, pk=None):
        model = self.queryset.model
        obj = get_object_or_404(model.objects.filter(is_deleted=True), pk=pk)
        user = getattr(request, "user", None)
        before = obj
        obj.delete()
        if self.hard_delete_audit:
            try:
                record_audit_event(
                    action=AuditEvent.ACTION_DELETE,
                    actor=user,
                    instance=before,
                    request=request,
                    before=before,
                    after=None,
                )
            except Exception:
                pass
        return Response({"success": True})

    @action(detail=False, methods=["post"], url_path="bulk-hard-delete")
    def bulk_hard_delete(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        model = self.queryset.model
        user = getattr(request, "user", None)
        qs = model.objects.filter(id__in=ids, is_deleted=True).order_by("id")
        if (
            getattr(self, "enable_data_scope", False)
            and user
            and getattr(user, "is_authenticated", False)
            and not self._is_admin_user(user)
        ):
            qs = self._apply_member_scope(qs, user)
        deleted = 0
        errors = []
        for obj in qs.iterator(chunk_size=200):
            try:
                before = obj
                obj.delete()
                deleted += 1
                if self.hard_delete_audit:
                    try:
                        record_audit_event(
                            action=AuditEvent.ACTION_DELETE,
                            actor=user,
                            instance=before,
                            request=request,
                            before=before,
                            after=None,
                        )
                    except Exception:
                        pass
            except Exception as e:
                errors.append({"id": int(getattr(obj, "id", 0) or 0), "error": str(e)})
        return Response({"success": len(errors) == 0, "count": deleted, "errors": errors})


class BatchOperationMixin:
    batch_update_allowed_keys = set()
    batch_copy_name_field = "name"
    batch_copy_name_suffix = "（复制）"

    @action(detail=False, methods=["post"], url_path="batch-delete")
    def batch_delete(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        qs = self.get_queryset().filter(id__in=ids, is_deleted=False)
        found_ids = list(qs.values_list("id", flat=True))
        if not found_ids:
            return Response({"success": True, "deleted": 0, "skipped": len(ids), "missing_ids": ids})
        with transaction.atomic():
            updated = qs.update(is_deleted=True, deleted_at=timezone.now())
        missing = [i for i in ids if i not in set(found_ids)]
        return Response({"success": True, "deleted": int(updated), "skipped": len(missing), "missing_ids": missing})

    @action(detail=False, methods=["post"], url_path="batch-update")
    def batch_update(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        patch = request.data.get("patch")
        if not isinstance(patch, dict) or not patch:
            raise ValidationError({"msg": "patch 必须为非空对象", "code": 400, "data": None})
        if not self.batch_update_allowed_keys:
            raise ValidationError({"msg": "该资源不支持批量更新", "code": 400, "data": None})
        cleaned = {k: v for (k, v) in patch.items() if k in self.batch_update_allowed_keys}
        if not cleaned:
            raise ValidationError({"msg": "patch 未包含可更新字段", "code": 400, "data": None})
        qs = self.get_queryset().filter(id__in=ids, is_deleted=False)
        found = list(qs)
        found_ids = {int(o.id) for o in found}
        missing = [i for i in ids if i not in found_ids]
        updated_ids = []
        errors = []
        with transaction.atomic():
            for obj in found:
                ser = self.get_serializer(obj, data=cleaned, partial=True)
                try:
                    ser.is_valid(raise_exception=True)
                    self.perform_update(ser)
                    updated_ids.append(int(obj.id))
                except Exception as e:
                    errors.append({"id": int(obj.id), "error": str(e)})
        return Response({
            "success": len(errors) == 0,
            "updated": len(updated_ids),
            "updated_ids": updated_ids,
            "missing_ids": missing,
            "errors": errors,
        })

    @action(detail=False, methods=["post"], url_path="batch-copy")
    def batch_copy(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({"msg": "请求体必须为 JSON 对象", "code": 400, "data": None})
        ids = self._parse_id_list(request.data.get("ids"))
        suffix = str(request.data.get("name_suffix") or self.batch_copy_name_suffix).strip()[:32] or self.batch_copy_name_suffix
        src_qs = self.get_queryset().filter(id__in=ids, is_deleted=False)
        src_list = list(src_qs)
        src_ids = {int(o.id) for o in src_list}
        missing = [i for i in ids if i not in src_ids]
        if not src_list:
            return Response({"success": True, "created": 0, "created_ids": [], "missing_ids": ids})
        created_ids = []
        errors = []
        user = request.user if getattr(request, "user", None) is not None else None
        with transaction.atomic():
            for src in src_list:
                try:
                    name_val = str(getattr(src, self.batch_copy_name_field, "") or "")[:220] + suffix
                    kwargs = {self.batch_copy_name_field: name_val}
                    for f in src._meta.concrete_fields:
                        if f.name in ("id", "pk", self.batch_copy_name_field, "is_deleted", "deleted_at", "create_time", "update_time", "creator", "updater"):
                            continue
                        if f.name in ("pass_rate", "plan_status"):
                            continue
                        try:
                            kwargs[f.name] = getattr(src, f.name)
                        except Exception:
                            pass
                    if user and getattr(user, "is_authenticated", False):
                        kwargs["creator"] = user
                        kwargs["updater"] = user
                    new_obj = self.queryset.model.objects.create(**kwargs)
                    created_ids.append(int(new_obj.id))
                except Exception as e:
                    errors.append({"id": int(src.id), "error": str(e)})
        return Response({
            "success": len(errors) == 0,
            "created": len(created_ids),
            "created_ids": created_ids,
            "missing_ids": missing,
            "errors": errors,
        })
