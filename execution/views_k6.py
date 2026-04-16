import logging
import uuid

from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from execution.models import K6LoadTestSession
from execution.serialize import (
    K6LoadTestSessionCreateSerializer,
    K6LoadTestSessionDetailSerializer,
)

logger = logging.getLogger(__name__)


def _enqueue_k6_task(session_pk: int) -> None:
    from execution.tasks_k6 import run_k6_load_test

    run_k6_load_test.delay(session_pk)


class K6LoadTestSessionViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    创建压测会话并异步执行 k6；通过 WebSocket 订阅 ws/k6/<run_id>/ 获取实时指标。
    """

    queryset = K6LoadTestSession.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated]
    lookup_field = "run_id"

    def get_queryset(self):
        """
        可选筛选参数：
        - status: pending/generating/running/completed/failed
        - run_id: UUID（支持前缀/包含匹配）
        - created_by_me: 1/true/yes
        - created_days: N（仅返回近 N 天内创建的）
        - created_start: ISO 日期/日期时间（含），如 2026-04-01 或 2026-04-01T00:00:00
        - created_end: ISO 日期/日期时间（含），如 2026-04-16 或 2026-04-16T23:59:59
        - ordering: create_time / -create_time / status / -status
        """
        qs = super().get_queryset()
        params = getattr(self.request, "query_params", {}) or {}
        status_value = (params.get("status") or "").strip()
        if status_value:
            allowed = {
                K6LoadTestSession.STATUS_PENDING,
                K6LoadTestSession.STATUS_GENERATING,
                K6LoadTestSession.STATUS_RUNNING,
                K6LoadTestSession.STATUS_COMPLETED,
                K6LoadTestSession.STATUS_FAILED,
            }
            if status_value in allowed:
                qs = qs.filter(status=status_value)
        run_id_kw = (params.get("run_id") or "").strip()
        if run_id_kw:
            qs = qs.filter(run_id__icontains=run_id_kw[:64])
        created_by_me = (params.get("created_by_me") or "").strip().lower()
        if created_by_me in ("1", "true", "yes"):
            user = getattr(self.request, "user", None)
            if user and getattr(user, "is_authenticated", False):
                qs = qs.filter(creator=user)
            else:
                qs = qs.none()
        created_days_raw = (params.get("created_days") or "").strip()
        if created_days_raw:
            try:
                days = int(created_days_raw)
            except (TypeError, ValueError):
                days = 0
            if days > 0:
                cutoff = timezone.now() - timedelta(days=days)
                qs = qs.filter(create_time__gte=cutoff)

        def _parse_dt(raw: str):
            s = (raw or "").strip()
            if not s:
                return None
            # 允许 YYYY-MM-DD
            if len(s) == 10 and s[4] == "-" and s[7] == "-":
                try:
                    d = timezone.datetime.fromisoformat(s)
                    return timezone.make_aware(
                        timezone.datetime(d.year, d.month, d.day, 0, 0, 0)
                    )
                except Exception:
                    return None
            try:
                dt = timezone.datetime.fromisoformat(s.replace("Z", "+00:00"))
            except Exception:
                return None
            if timezone.is_naive(dt):
                try:
                    dt = timezone.make_aware(dt)
                except Exception:
                    return None
            return dt

        created_start = _parse_dt(params.get("created_start") or "")
        if created_start is not None:
            qs = qs.filter(create_time__gte=created_start)
        created_end = _parse_dt(params.get("created_end") or "")
        if created_end is not None:
            # 若为纯日期（00:00:00），则扩展到当日 23:59:59
            if (
                created_end.hour == 0
                and created_end.minute == 0
                and created_end.second == 0
                and (params.get("created_end") or "").strip()[:10].count("-") == 2
                and len((params.get("created_end") or "").strip()) == 10
            ):
                created_end = created_end + timedelta(days=1) - timedelta(seconds=1)
            qs = qs.filter(create_time__lte=created_end)

        ordering = (params.get("ordering") or "").strip()
        if ordering in ("create_time", "-create_time", "status", "-status"):
            # 二级排序保证稳定
            if ordering.startswith("-"):
                return qs.order_by(ordering, "-id")
            return qs.order_by(ordering, "-id")
        return qs.order_by("-create_time", "-id")

    def get_serializer_class(self):
        if self.action == "create":
            return K6LoadTestSessionCreateSerializer
        return K6LoadTestSessionDetailSerializer

    def perform_create(self, serializer):
        user = self.request.user
        instance = serializer.save(
            creator=user if user.is_authenticated else None,
            updater=user if user.is_authenticated else None,
            status=K6LoadTestSession.STATUS_PENDING,
        )
        try:
            _enqueue_k6_task(instance.pk)
        except Exception as exc:
            logger.exception("投递 Celery 任务失败")
            instance.status = K6LoadTestSession.STATUS_FAILED
            instance.error_message = f"无法启动异步任务: {exc}"
            instance.save(update_fields=["status", "error_message", "update_time"])

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        instance = serializer.instance
        out = K6LoadTestSessionDetailSerializer(
            instance, context={"request": request}
        ).data
        return Response(
            {
                **out,
                "websocket_path": f"/ws/k6/{instance.run_id}/",
                "websocket_url_hint": "开发环境经 Vite 代理: ws://<前端host>/ws/k6/<run_id>/?token=<Token>",
            },
            status=status.HTTP_201_CREATED,
        )

    def _parse_id_list(self, raw_ids):
        if raw_ids is None:
            raise ValidationError({"detail": "ids 必填"})
        if not isinstance(raw_ids, list):
            raise ValidationError({"detail": "ids 必须为数组"})
        ids = []
        for x in raw_ids:
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                continue
        ids = [i for i in ids if i > 0]
        if not ids:
            raise ValidationError({"detail": "ids 不能为空"})
        seen = set()
        uniq = []
        for i in ids:
            if i in seen:
                continue
            seen.add(i)
            uniq.append(i)
        return uniq

    @action(detail=False, methods=["post"], url_path="batch-delete")
    def batch_delete(self, request):
        """
        批量软删除 k6 会话。
        POST /api/perf/k6-sessions/batch-delete/
        body: { ids: number[] }
        """
        if not isinstance(request.data, dict):
            raise ValidationError({"detail": "请求体必须为 JSON 对象"})
        ids = self._parse_id_list(request.data.get("ids"))
        qs = self.get_queryset().filter(id__in=ids, is_deleted=False)
        found_ids = list(qs.values_list("id", flat=True))
        if not found_ids:
            return Response({"success": True, "deleted": 0, "skipped": len(ids), "missing_ids": ids})
        with transaction.atomic():
            updated = qs.update(is_deleted=True)
        missing = [i for i in ids if i not in set(found_ids)]
        return Response(
            {
                "success": True,
                "deleted": int(updated),
                "skipped": len(missing),
                "missing_ids": missing,
            }
        )

    @action(detail=False, methods=["post"], url_path="batch-copy")
    def batch_copy(self, request):
        """
        批量复制 k6 会话（仅复制配置字段；不会拷贝脚本/summary；新会话会入队执行）。
        POST /api/perf/k6-sessions/batch-copy/
        body: { ids: number[] }
        """
        if not isinstance(request.data, dict):
            raise ValidationError({"detail": "请求体必须为 JSON 对象"})
        ids = self._parse_id_list(request.data.get("ids"))
        src_qs = self.get_queryset().filter(id__in=ids, is_deleted=False)
        src_list = list(src_qs)
        src_ids = {int(o.id) for o in src_list}
        missing = [i for i in ids if i not in src_ids]
        if not src_list:
            return Response({"success": True, "created": 0, "created_ids": [], "missing_ids": ids})

        created_ids = []
        errors = []
        user = request.user
        with transaction.atomic():
            for src in src_list:
                try:
                    new_obj = K6LoadTestSession.objects.create(
                        run_id=uuid.uuid4(),
                        status=K6LoadTestSession.STATUS_PENDING,
                        test_case_ids=list(src.test_case_ids or []),
                        vus=int(src.vus or 5),
                        duration=str(src.duration or "30s"),
                        use_ai=bool(src.use_ai),
                        target_base_url=str(src.target_base_url or ""),
                        generation_source="",
                        script_rel_path="",
                        script_body="",
                        summary=None,
                        error_message="",
                        celery_task_id="",
                        creator=user if user.is_authenticated else None,
                        updater=user if user.is_authenticated else None,
                    )
                    try:
                        _enqueue_k6_task(new_obj.pk)
                    except Exception as exc:
                        logger.exception("投递 Celery 任务失败")
                        new_obj.status = K6LoadTestSession.STATUS_FAILED
                        new_obj.error_message = f"无法启动异步任务: {exc}"
                        new_obj.save(update_fields=["status", "error_message", "update_time"])
                    created_ids.append(int(new_obj.id))
                except Exception as e:
                    errors.append({"id": int(src.id), "error": str(e)})
        return Response(
            {
                "success": len(errors) == 0,
                "created": len(created_ids),
                "created_ids": created_ids,
                "missing_ids": missing,
                "errors": errors,
            }
        )
