import uuid
import json
import threading

from rest_framework.decorators import action
from rest_framework.response import Response
from common.views import BaseModelViewSet
from assistant.keyword_driven_models import (
    KWElementLocator,
    KWTestCase,
    KWActionStep,
)
from assistant.keyword_driven_serializers import (
    KWElementLocatorSerializer,
    KWActionStepReadSerializer,
    KWActionStepWriteSerializer,
    KWTestCaseListSerializer,
    KWTestCaseDetailSerializer,
    KWTestCaseWriteSerializer,
    KWTestCaseExecutorSerializer,
)


class KWElementLocatorViewSet(BaseModelViewSet):
    queryset = KWElementLocator.objects.all()
    enable_data_scope = False

    def get_serializer_class(self):
        if self.action == "list":
            return KWElementLocatorSerializer
        return KWElementLocatorSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        project = self.request.query_params.get("project")
        if project:
            qs = qs.filter(project=project)
        return qs


class KWTestCaseViewSet(BaseModelViewSet):
    queryset = KWTestCase.objects.all()
    enable_data_scope = False

    def get_serializer_class(self):
        if self.action == "list":
            return KWTestCaseListSerializer
        if self.action == "retrieve":
            return KWTestCaseDetailSerializer
        if self.action == "executor_blueprint":
            return KWTestCaseExecutorSerializer
        return KWTestCaseWriteSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        project = self.request.query_params.get("project")
        if project:
            qs = qs.filter(project=project)
        return qs

    @action(detail=True, methods=["get"])
    def executor_blueprint(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None):
        instance = self.get_object()
        execution_id = str(uuid.uuid4())
        browser = request.data.get("browser", "chrome")
        headless = request.data.get("headless", True)

        from assistant.utils.kw_executor import execute_kw_test_case

        thread = threading.Thread(
            target=execute_kw_test_case,
            args=(instance.pk, execution_id),
            kwargs={"browser_type": browser, "headless": headless},
            daemon=True,
        )
        thread.start()

        return Response(
            {
                "execution_id": execution_id,
                "test_case_id": instance.pk,
                "status": "running",
            }
        )

    @action(detail=False, methods=["get"], url_path="execution-status")
    def execution_status(self, request):
        execution_id = request.query_params.get("execution_id")
        if not execution_id:
            return Response(
                {"detail": "execution_id is required."}, status=400
            )
        try:
            from django.core.cache import cache

            redis_client = cache.client.get_client()
            status_key = f"kw_execution:{execution_id}:status"
            raw = redis_client.get(status_key)
            if raw is None:
                return Response({"status": "unknown"})
            return Response(json.loads(raw))
        except Exception as e:
            return Response(
                {"detail": f"Redis error: {e}"}, status=500
            )

    @action(detail=False, methods=["get"], url_path="execution-logs")
    def execution_logs(self, request):
        execution_id = request.query_params.get("execution_id")
        if not execution_id:
            return Response(
                {"detail": "execution_id is required."}, status=400
            )
        try:
            start = int(request.query_params.get("start", 0))
            end = int(request.query_params.get("end", -1))
        except (ValueError, TypeError):
            return Response(
                {"detail": "start and end must be integers."}, status=400
            )
        try:
            from django.core.cache import cache

            redis_client = cache.client.get_client()
            logs_key = f"kw_execution:{execution_id}:logs"
            raw_list = redis_client.lrange(logs_key, start, end)
            logs = [json.loads(item) for item in raw_list]
            return Response({"logs": logs, "count": len(logs)})
        except Exception as e:
            return Response(
                {"detail": f"Redis error: {e}"}, status=500
            )

    @action(detail=False, methods=["get"], url_path="execution-steps")
    def execution_steps(self, request):
        execution_id = request.query_params.get("execution_id")
        if not execution_id:
            return Response(
                {"detail": "execution_id is required."}, status=400
            )
        try:
            from django.core.cache import cache

            redis_client = cache.client.get_client()
            steps_key = f"kw_execution:{execution_id}:steps"
            raw_list = redis_client.lrange(steps_key, 0, -1)
            steps = [json.loads(item) for item in raw_list]
            return Response({"steps": steps, "count": len(steps)})
        except Exception as e:
            return Response(
                {"detail": f"Redis error: {e}"}, status=500
            )

    @action(detail=False, methods=["post"], url_path="cancel-execution")
    def cancel_execution(self, request):
        execution_id = request.data.get("execution_id")
        if not execution_id:
            return Response(
                {"detail": "execution_id is required."}, status=400
            )
        try:
            from django.core.cache import cache

            redis_client = cache.client.get_client()
            cancel_key = f"kw_execution:{execution_id}:cancel"
            redis_client.setex(cancel_key, 3600, "1")
            return Response({"execution_id": execution_id, "cancelled": True})
        except Exception as e:
            return Response(
                {"detail": f"Redis error: {e}"}, status=500
            )


class KWActionStepViewSet(BaseModelViewSet):
    queryset = KWActionStep.objects.all().select_related("element")
    enable_data_scope = False

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return KWActionStepReadSerializer
        return KWActionStepWriteSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        test_case = self.request.query_params.get("test_case")
        if test_case:
            qs = qs.filter(test_case=test_case)
        return qs

    @action(detail=False, methods=["put"])
    def batch(self, request):
        from assistant.keyword_driven_serializers import KWActionStepWriteSerializer

        items = request.data
        if not isinstance(items, list):
            return Response({"detail": "Expected a list of items."}, status=400)
        updated = []
        for item in items:
            step_id = item.get("id")
            if step_id is None:
                continue
            try:
                instance = KWActionStep.objects.get(pk=step_id)
            except KWActionStep.DoesNotExist:
                continue
            serializer = KWActionStepWriteSerializer(
                instance, data=item, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            updated.append(serializer.data)
        return Response(updated)
