import logging

from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from execution.models import K6LoadTestSession
from execution.serialize import K6LoadTestSessionCreateSerializer, K6LoadTestSessionDetailSerializer

logger = logging.getLogger(__name__)


def _enqueue_k6_task(session_pk: int) -> None:
    from execution.tasks_k6 import run_k6_load_test

    run_k6_load_test.delay(session_pk)


class K6LoadTestSessionViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    创建压测会话并异步执行 k6；通过 WebSocket 订阅 ws/k6/<run_id>/ 获取实时指标。
    """

    queryset = K6LoadTestSession.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated]
    lookup_field = "run_id"

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
        out = K6LoadTestSessionDetailSerializer(instance, context={"request": request}).data
        return Response(
            {
                **out,
                "websocket_path": f"/ws/k6/{instance.run_id}/",
                "websocket_url_hint": "开发环境经 Vite 代理: ws://<前端host>/ws/k6/<run_id>/?token=<Token>",
            },
            status=status.HTTP_201_CREATED,
        )
