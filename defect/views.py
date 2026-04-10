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
        user = self.request.user
        vd = serializer.validated_data
        defect_no = (vd.get("defect_no") or "").strip()
        if not defect_no:
            last = TestDefect.objects.order_by("-id").first()
            next_id = 1 if not last else last.id + 1
            defect_no = f"DEF-{next_id:05d}"
        handler = vd.get("handler")
        if handler is None and user.is_authenticated:
            handler = user
        kwargs = {"defect_no": defect_no, "handler": handler}
        if user.is_authenticated:
            serializer.save(creator=user, **kwargs)
        else:
            serializer.save(**kwargs)