from django.db.models import Q
from rest_framework.pagination import PageNumberPagination

from common.views import *
from defect.models import *
from defect.serialize import *


class DefectPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 500


class TestDefectViewSet(BaseModelViewSet):
    queryset = TestDefect.objects.all()
    serializer_class = TestDefectSerializer
    pagination_class = DefectPagination

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("release_version", "handler", "creator", "module")
        )
        p = self.request.query_params
        if p.get("severity"):
            try:
                severity = int(p["severity"])
            except (TypeError, ValueError):
                return qs.none()
            qs = qs.filter(severity=severity)
        if p.get("status"):
            try:
                defect_status = int(p["status"])
            except (TypeError, ValueError):
                return qs.none()
            qs = qs.filter(status=defect_status)
        if p.get("priority"):
            try:
                priority = int(p["priority"])
            except (TypeError, ValueError):
                return qs.none()
            qs = qs.filter(priority=priority)
        rv = p.get("release_version")
        if rv:
            try:
                release_version_id = int(rv)
            except (TypeError, ValueError):
                return qs.none()
            qs = qs.filter(release_version_id=release_version_id)
        q = p.get("search")
        if q:
            qs = qs.filter(Q(defect_no__icontains=q) | Q(defect_name__icontains=q))
        return qs.order_by("-create_time")

    def perform_create(self, serializer):
        from django.db import IntegrityError, transaction
        from rest_framework.exceptions import ValidationError

        user = self.request.user
        vd = serializer.validated_data

        defect_no = (vd.get("defect_no") or "").strip()

        handler = vd.get("handler")

        if handler is None:
            if user.is_authenticated:
                handler = user
            else:
                raise ValidationError({"handler": "创建缺陷必须指定处理人"})

        # 检测重复缺陷（同版本+模块+标题+严重程度）
        duplicate = (
            TestDefect.objects.filter(
                is_deleted=False,
                release_version=vd.get("release_version"),
                module=vd.get("module"),
                defect_name=vd.get("defect_name"),
                severity=vd.get("severity"),
            )
            .order_by("-id")
            .first()
        )
        if duplicate:
            raise ValidationError(
                {
                    "defect_name": "可能存在重复缺陷：已存在相同标题和严重程度的缺陷",
                    "duplicate_id": duplicate.id,
                }
            )

        # 并发安全的编号生成：事务锁 + 唯一约束冲突重试
        if not defect_no:
            for _ in range(5):
                try:
                    with transaction.atomic():
                        last = (
                            TestDefect.objects.select_for_update()
                            .order_by("-id")
                            .first()
                        )
                        next_id = 1 if not last else last.id + 1
                        defect_no = f"DEF-{next_id:05d}"
                        kwargs = {"defect_no": defect_no, "handler": handler}
                        if user.is_authenticated:
                            return serializer.save(creator=user, **kwargs)
                        return serializer.save(**kwargs)
                except IntegrityError:
                    defect_no = ""
            raise ValidationError({"defect_no": "缺陷编号生成冲突，请重试"})

        # 手工编号/外部传入时：验证唯一性（同时靠数据库约束兜底）
        if TestDefect.objects.filter(defect_no=defect_no, is_deleted=False).exists():
            raise ValidationError({"defect_no": "缺陷编号已存在"})

        kwargs = {"defect_no": defect_no, "handler": handler}
        if user.is_authenticated:
            serializer.save(creator=user, **kwargs)
        else:
            serializer.save(**kwargs)

    def perform_update(self, serializer):
        from rest_framework.exceptions import ValidationError

        instance = serializer.instance
        old_status = instance.status
        new_status = serializer.validated_data.get("status", old_status)

        # 状态流转验证：只有处理人可以关闭；且仅允许“处理中” -> “已关闭”
        if new_status == 4:
            if old_status != 2:
                raise ValidationError({"status": "已关闭只能从“处理中”状态流转"})
            if getattr(self.request.user, "pk", None) != instance.handler_id:
                raise ValidationError({"status": "只有处理人可以将缺陷标记为已关闭"})

        user = self.request.user
        if user and user.is_authenticated:
            serializer.save(updater=user)
        else:
            serializer.save()
