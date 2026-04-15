import logging
import time

import requests
from django.conf import settings
from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from common.views import BaseModelViewSet
from server_logs.access import (
    remote_log_server_queryset_for_user,
    user_is_platform_log_admin,
)
from server_logs.es_client import get_elasticsearch_client, get_server_logs_es_index
from server_logs.ai_analyze import (
    analyze_log_markdown,
    analyze_log_markdown_with_context,
)
from server_logs.log_context import fetch_es_context_for_anchor
from server_logs.audit import log_server_log_event
from server_logs.models import (
    LogAutoTicketJob,
    LogAutoTicketJobStatus,
    RemoteLogServer,
    ServerLogAuditEvent,
)
from server_logs.serializers import (
    LogAnalyzeRequestSerializer,
    LogAnalyzeWithContextRequestSerializer,
    LogAutoTicketCreateDefectSerializer,
    LogAutoTicketEnqueueSerializer,
    LogAutoTicketJobSerializer,
    RemoteLogServerListSerializer,
    RemoteLogServerSerializer,
    ServerLogAuditEventSerializer,
)

logger = logging.getLogger(__name__)


class LogServerOrganizationChoicesAPIView(APIView):
    """
    当前用户可绑定到日志主机的组织列表（创建人或成员；平台管理员返回全部）。
    与 /api/user/orgs/ 不同：后者仅系统管理员可访问。
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from user.models import Organization

        u = request.user
        if user_is_platform_log_admin(u):
            qs = Organization.objects.filter(is_deleted=False)
        else:
            qs = (
                Organization.objects.filter(is_deleted=False)
                .filter(Q(creator=u) | Q(members=u))
                .distinct()
            )
        rows = qs.order_by("org_name")[:500]
        return Response([{"id": o.id, "org_name": o.org_name} for o in rows])


class RemoteLogServerViewSet(BaseModelViewSet):
    queryset = RemoteLogServer.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return remote_log_server_queryset_for_user(self.request.user).select_related(
            "organization"
        )

    def get_serializer_class(self):
        if self.action == "list":
            return RemoteLogServerListSerializer
        return RemoteLogServerSerializer

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(creator=user, updater=user)
        log_server_log_event(
            user,
            ServerLogAuditEvent.Action.HOST_CREATE,
            remote_server=serializer.instance,
            request=self.request,
        )

    def perform_update(self, serializer):
        serializer.save(updater=self.request.user)
        log_server_log_event(
            self.request.user,
            ServerLogAuditEvent.Action.HOST_UPDATE,
            remote_server=serializer.instance,
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_server_log_event(
            self.request.user,
            ServerLogAuditEvent.Action.HOST_DELETE,
            remote_server=instance,
            request=self.request,
        )
        super().perform_destroy(instance)


class AnalyzeLogAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "server_logs_analyze"

    def post(self, request):
        ser = LogAnalyzeRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        text = ser.validated_data["log_text"]
        meta = {
            "chars": len(text),
            "model": (ser.validated_data.get("model") or "").strip() or None,
        }
        md, err = analyze_log_markdown(
            text,
            api_key_override=ser.validated_data.get("api_key") or "",
            api_base_override=ser.validated_data.get("api_base_url") or "",
            model_override=ser.validated_data.get("model") or "",
        )
        if err:
            log_server_log_event(
                request.user,
                ServerLogAuditEvent.Action.ANALYZE,
                meta={**meta, "success": False, "error": err[:500]},
                request=request,
            )
            # 返回 200：避免前端拦截器将“上游 AI 错误”误判为后端 5xx 并刷红条
            return Response({"success": False, "error": err, "markdown": None})
        log_server_log_event(
            request.user,
            ServerLogAuditEvent.Action.ANALYZE,
            meta={**meta, "success": True, "reply_chars": len(md or "")},
            request=request,
        )
        return Response({"success": True, "error": None, "markdown": md})


class AnalyzeLogWithContextAPIView(APIView):
    """
    检索增强诊断（ES 上下文）：
    - 入参 server_id + anchor_text（可选 anchor_ts）
    - 先在 ES 里定位锚点，再拉取前后 window_seconds 的上下文日志
    - 将上下文 + anchor_text 一起送入模型，减少断章取义
    - 若 ES 不可用/查询失败：自动降级为原 analyze（仅 anchor_text）
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "server_logs_analyze"

    def post(self, request):
        ser = LogAnalyzeWithContextRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        server_id = int(ser.validated_data["server_id"])
        anchor_text = ser.validated_data["anchor_text"]
        anchor_ts = ser.validated_data.get("anchor_ts")
        window_seconds = int(ser.validated_data.get("window_seconds") or 300)
        limit = int(ser.validated_data.get("limit") or 200)

        # 权限校验：必须能访问该 server_id
        srv = (
            remote_log_server_queryset_for_user(request.user)
            .filter(pk=server_id)
            .first()
        )
        if not srv:
            return Response(
                {
                    "success": False,
                    "error": "无权访问该主机或主机不存在",
                    "markdown": None,
                },
                status=403,
            )

        meta = {
            "server_id": server_id,
            "window_seconds": window_seconds,
            "limit": limit,
            "chars": len(anchor_text or ""),
            "model": (ser.validated_data.get("model") or "").strip() or None,
        }

        context_lines, ctx_meta = fetch_es_context_for_anchor(
            server_id=server_id,
            anchor_text=anchor_text,
            anchor_ts=int(anchor_ts) if anchor_ts is not None else None,
            window_seconds=window_seconds,
            limit=min(limit, 500),
        )
        used_backend = str(ctx_meta.get("backend") or "es")
        if ctx_meta.get("es_error"):
            meta["es_error"] = str(ctx_meta.get("es_error"))[:200]

        # 调用 AI（若 ES 失败/无 anchor，则 context_lines 可能为空）
        md, err = analyze_log_markdown_with_context(
            anchor_text=anchor_text,
            context_lines=context_lines,
            server_name=getattr(srv, "name", None),
            time_window_seconds=window_seconds,
            api_key_override=ser.validated_data.get("api_key") or "",
            api_base_override=ser.validated_data.get("api_base_url") or "",
            model_override=ser.validated_data.get("model") or "",
        )

        meta["backend"] = used_backend
        meta["context_count"] = len(context_lines)
        if err:
            log_server_log_event(
                request.user,
                ServerLogAuditEvent.Action.ANALYZE,
                meta={**meta, "success": False, "error": err[:500]},
                remote_server=srv,
                request=request,
            )
            return Response({"success": False, "error": err, "markdown": None})
        log_server_log_event(
            request.user,
            ServerLogAuditEvent.Action.ANALYZE,
            meta={**meta, "success": True, "reply_chars": len(md or "")},
            remote_server=srv,
            request=request,
        )
        return Response(
            {
                "success": True,
                "error": None,
                "markdown": md,
                "context_count": len(context_lines),
            }
        )


class LogHistorySearchAPIView(APIView):
    """
    历史日志检索（Elasticsearch）：
    - 根据 server_id 与 keyword 做全文检索（match message），按 timestamp 倒序。
    - ES 写入失败不影响实时推送；此接口仅负责检索。
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from rest_framework import serializers

        class _EsSearchSer(serializers.Serializer):
            server_id = serializers.IntegerField(required=False, min_value=1)
            keyword = serializers.CharField(
                required=False, allow_blank=True, max_length=512
            )
            limit = serializers.IntegerField(
                required=False, min_value=1, max_value=500, default=80
            )

        ser = _EsSearchSer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        server_id = ser.validated_data.get("server_id")
        keyword = (ser.validated_data.get("keyword") or "").strip()
        limit = ser.validated_data.get("limit") or 80

        try:
            es = get_elasticsearch_client()
            idx = get_server_logs_es_index()
        except ImportError as e:
            log_server_log_event(
                request.user,
                ServerLogAuditEvent.Action.SEARCH,
                meta={
                    "enabled": False,
                    "backend": "elasticsearch",
                    "error": str(e)[:200],
                },
                request=request,
            )
            # 返回 200：避免前端统一拦截器弹“后端异常”红条
            return Response(
                {
                    "enabled": False,
                    "backend": "elasticsearch",
                    "message": "未安装 elasticsearch Python 客户端，历史检索不可用。",
                    "results": [],
                }
            )
        except Exception as e:
            log_server_log_event(
                request.user,
                ServerLogAuditEvent.Action.SEARCH,
                meta={
                    "enabled": False,
                    "backend": "elasticsearch",
                    "error": str(e)[:300],
                },
                request=request,
            )
            return Response(
                {
                    "enabled": False,
                    "backend": "elasticsearch",
                    "message": "Elasticsearch 未连接或不可用（默认 http://localhost:9200）。",
                    "results": [],
                }
            )

        must = []
        if server_id:
            must.append({"term": {"server_id": int(server_id)}})
        if keyword:
            must.append({"match": {"message": {"query": keyword}}})
        if not must:
            # 防止空查询直接扫全库：要求至少 server_id 或 keyword
            return Response(
                {
                    "enabled": True,
                    "backend": "elasticsearch",
                    "message": "请至少提供 server_id 或 keyword",
                    "results": [],
                }
            )

        body = {
            "size": int(limit),
            "query": {"bool": {"must": must}},
            "sort": [{"timestamp": {"order": "desc"}}],
        }
        try:
            r = es.search(index=idx, body=body)
            hits = (r.get("hits") or {}).get("hits") or []
            rows = []
            for h in hits:
                src = h.get("_source") or {}
                rows.append(
                    {
                        "server_id": src.get("server_id"),
                        "host_name": src.get("host_name"),
                        "message": src.get("message"),
                        "timestamp": src.get("timestamp"),
                    }
                )
            log_server_log_event(
                request.user,
                ServerLogAuditEvent.Action.SEARCH,
                meta={
                    "enabled": True,
                    "backend": "elasticsearch",
                    "count": len(rows),
                    "server_id": server_id,
                    "keyword": keyword[:120],
                },
                request=request,
            )
            return Response(
                {
                    "enabled": True,
                    "backend": "elasticsearch",
                    "message": None,
                    "results": rows,
                }
            )
        except Exception as e:
            log_server_log_event(
                request.user,
                ServerLogAuditEvent.Action.SEARCH,
                meta={
                    "enabled": True,
                    "backend": "elasticsearch",
                    "error": str(e)[:300],
                    "server_id": server_id,
                    "keyword": keyword[:120],
                },
                request=request,
            )
            # ES 查询失败也按“不可用”处理：避免前端红条刷屏
            return Response(
                {
                    "enabled": False,
                    "backend": "elasticsearch",
                    "message": "Elasticsearch 查询失败或不可用，请检查 ES 服务与配置。",
                    "results": [],
                }
            )


class LogErrorTrendAPIView(APIView):
    """
    压测/运维趋势（最小可用版）：
    - 按 server_id + keyword 聚合最近 N 分钟的命中次数趋势（date_histogram）
    - 供前端画“错误率/报错趋势”折线图使用
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from rest_framework import serializers

        class _Ser(serializers.Serializer):
            server_id = serializers.IntegerField(required=False, min_value=1)
            keyword = serializers.CharField(
                required=False, allow_blank=True, max_length=128, default="ERROR"
            )
            minutes = serializers.IntegerField(
                required=False, min_value=1, max_value=1440, default=60
            )
            interval = serializers.CharField(
                required=False, allow_blank=False, max_length=20, default="30s"
            )

        ser = _Ser(data=request.query_params)
        ser.is_valid(raise_exception=True)
        server_id = ser.validated_data.get("server_id")
        keyword = (ser.validated_data.get("keyword") or "ERROR").strip() or "ERROR"
        minutes = int(ser.validated_data.get("minutes") or 60)
        interval = ser.validated_data.get("interval") or "30s"

        try:
            es = get_elasticsearch_client()
            idx = get_server_logs_es_index()
        except ImportError:
            return Response(
                {
                    "enabled": False,
                    "backend": "elasticsearch",
                    "message": "未安装 elasticsearch Python 客户端，趋势不可用。",
                    "points": [],
                }
            )
        except Exception:
            return Response(
                {
                    "enabled": False,
                    "backend": "elasticsearch",
                    "message": "Elasticsearch 未连接或不可用（默认 http://localhost:9200）。",
                    "points": [],
                }
            )

        end_ms = int(time.time() * 1000)
        start_ms = end_ms - minutes * 60 * 1000

        must = [{"range": {"timestamp": {"gte": start_ms, "lte": end_ms}}}]
        if server_id:
            must.append({"term": {"server_id": int(server_id)}})
        if keyword:
            must.append({"match": {"message": {"query": keyword}}})

        body = {
            "size": 0,
            "query": {"bool": {"must": must}},
            "aggs": {
                "trend": {
                    "date_histogram": {
                        "field": "timestamp",
                        "fixed_interval": interval,
                        "min_doc_count": 0,
                        "extended_bounds": {"min": start_ms, "max": end_ms},
                        "format": "epoch_millis",
                    }
                }
            },
        }

        try:
            r = es.search(index=idx, body=body)
            buckets = (
                ((r.get("aggregations") or {}).get("trend") or {}).get("buckets")
            ) or []
            points = [
                {"ts": b.get("key"), "count": b.get("doc_count", 0)} for b in buckets
            ]
            log_server_log_event(
                request.user,
                ServerLogAuditEvent.Action.SEARCH,
                meta={
                    "enabled": True,
                    "backend": "elasticsearch",
                    "agg": "error_trend",
                    "server_id": server_id,
                    "keyword": keyword[:64],
                    "minutes": minutes,
                    "interval": interval,
                },
                request=request,
            )
            return Response(
                {
                    "enabled": True,
                    "backend": "elasticsearch",
                    "message": None,
                    "points": points,
                }
            )
        except Exception as e:
            return Response(
                {
                    "enabled": False,
                    "backend": "elasticsearch",
                    "message": "Elasticsearch 查询失败或不可用，请检查 ES 服务与配置。",
                    "points": [],
                }
            )


class LogAutoTicketEnqueueAPIView(APIView):
    """
    将「日志锚点 + ES 上下文」异步交给 Celery，生成缺陷工单草稿 JSON。
    返回 202 + job_id，前端轮询 LogAutoTicketJobDetailAPIView。
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "server_logs_analyze"

    def post(self, request):
        ser = LogAutoTicketEnqueueSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        server_id = int(ser.validated_data["server_id"])
        srv = (
            remote_log_server_queryset_for_user(request.user)
            .filter(pk=server_id)
            .select_related("organization")
            .first()
        )
        if not srv:
            return Response(
                {"success": False, "error": "无权访问该主机或主机不存在"},
                status=status.HTTP_403_FORBIDDEN,
            )

        job = LogAutoTicketJob.objects.create(
            user=request.user,
            remote_log_server=srv,
            anchor_text=ser.validated_data["anchor_text"],
            anchor_ts=ser.validated_data.get("anchor_ts"),
            window_seconds=int(ser.validated_data.get("window_seconds") or 300),
            es_limit=int(ser.validated_data.get("es_limit") or 200),
            status=LogAutoTicketJobStatus.PENDING,
            meta={},
            create_defect_requested=bool(ser.validated_data.get("create_defect")),
            defect_handler=ser.validated_data.get("defect_handler"),
            defect_release_version=ser.validated_data.get("defect_release_version"),
            defect_module=ser.validated_data.get("defect_module"),
        )

        from server_logs import tasks as sl_tasks

        if not getattr(sl_tasks, "_CELERY_AVAILABLE", False):
            job.status = LogAutoTicketJobStatus.FAILED
            job.error_message = "Celery 未安装或未启用，无法执行异步任务。"
            job.save(update_fields=["status", "error_message", "updated_at"])
            return Response(
                {
                    "success": False,
                    "error": job.error_message,
                    "job": LogAutoTicketJobSerializer(job).data,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        api_key = (ser.validated_data.get("api_key") or "").strip()
        api_base = (ser.validated_data.get("api_base_url") or "").strip()
        model = (ser.validated_data.get("model") or "").strip()

        try:
            async_res = sl_tasks.run_log_auto_ticket_job.delay(
                job.id,
                api_key=api_key,
                api_base_url=api_base,
                model=model,
            )
        except Exception as e:
            logger.exception("auto-ticket enqueue failed job_id=%s", job.id)
            job.status = LogAutoTicketJobStatus.FAILED
            job.error_message = str(e)[:2000]
            job.save(update_fields=["status", "error_message", "updated_at"])
            return Response(
                {
                    "success": False,
                    "error": "任务入队失败，请检查 Celery Broker 与 Worker 是否可用。",
                    "job": LogAutoTicketJobSerializer(job).data,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        tid = getattr(async_res, "id", "") or ""
        if tid:
            job.celery_task_id = tid
            job.save(update_fields=["celery_task_id", "updated_at"])

        log_server_log_event(
            request.user,
            ServerLogAuditEvent.Action.AUTO_TICKET,
            meta={
                "job_id": job.id,
                "phase": "enqueue",
                "server_id": server_id,
                "create_defect": job.create_defect_requested,
            },
            remote_server=srv,
            request=request,
        )
        return Response(
            {
                "success": True,
                "job_id": job.id,
                "task_id": job.celery_task_id,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class LogAutoTicketJobDetailAPIView(APIView):
    """查询异步工单草稿任务状态与结果（仅创建人或平台日志管理员）。"""

    permission_classes = [IsAuthenticated]

    def get(self, request, job_id: int):
        job = (
            LogAutoTicketJob.objects.select_related(
                "remote_log_server",
                "user",
                "created_defect",
                "defect_handler",
                "defect_release_version",
                "defect_module",
            )
            .filter(pk=job_id)
            .first()
        )
        if not job:
            return Response({"detail": "任务不存在"}, status=status.HTTP_404_NOT_FOUND)
        if job.user_id != request.user.id and not user_is_platform_log_admin(
            request.user
        ):
            return Response(
                {"detail": "无权查看该任务"}, status=status.HTTP_403_FORBIDDEN
            )
        return Response(LogAutoTicketJobSerializer(job).data)


class LogAutoTicketCreateDefectAPIView(APIView):
    """
    对已成功的 AI 工单任务，使用当前 draft 补建 TestDefect（幂等：已有关联缺陷则直接返回）。
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "server_logs_analyze"

    def post(self, request, job_id: int):
        from server_logs.defect_create import create_test_defect_from_auto_ticket

        job = (
            LogAutoTicketJob.objects.select_related(
                "remote_log_server",
                "user",
                "created_defect",
                "defect_handler",
                "defect_release_version",
                "defect_module",
            )
            .filter(pk=job_id)
            .first()
        )
        if not job:
            return Response(
                {"success": False, "error": "任务不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if job.user_id != request.user.id and not user_is_platform_log_admin(
            request.user
        ):
            return Response(
                {"success": False, "error": "无权操作该任务"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if job.status != LogAutoTicketJobStatus.SUCCESS:
            return Response(
                {"success": False, "error": "仅成功任务可从草稿创建缺陷。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not job.draft or not isinstance(job.draft, dict):
            return Response(
                {"success": False, "error": "任务无有效草稿数据。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if job.created_defect_id:
            return Response(
                {
                    "success": True,
                    "already_created": True,
                    "job": LogAutoTicketJobSerializer(job).data,
                },
                status=status.HTTP_200_OK,
            )

        ser = LogAutoTicketCreateDefectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        raw = request.data if isinstance(request.data, dict) else {}

        kw: dict = {}
        if "defect_handler" in raw:
            kw["defect_handler"] = ser.validated_data.get("defect_handler")
        if "defect_release_version" in raw:
            kw["defect_release_version"] = ser.validated_data.get(
                "defect_release_version"
            )
        if "defect_module" in raw:
            kw["defect_module"] = ser.validated_data.get("defect_module")

        d_obj, err = create_test_defect_from_auto_ticket(job, job.draft, **kw)
        if err or not d_obj:
            return Response(
                {"success": False, "error": err or "创建缺陷失败"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        meta = dict(job.meta or {})
        meta["defect_create"] = {
            "success": True,
            "defect_id": d_obj.id,
            "defect_no": d_obj.defect_no,
            "source": "manual_rest",
        }
        job.created_defect = d_obj
        job.meta = meta
        job.save(update_fields=["created_defect", "meta", "updated_at"])

        log_server_log_event(
            request.user,
            ServerLogAuditEvent.Action.AUTO_TICKET,
            meta={
                "job_id": job.id,
                "phase": "create_defect_manual",
                "defect_id": d_obj.id,
                "defect_no": d_obj.defect_no,
            },
            remote_server=job.remote_log_server,
            request=request,
        )

        job_out = LogAutoTicketJob.objects.select_related(
            "remote_log_server",
            "user",
            "created_defect",
            "defect_handler",
            "defect_release_version",
            "defect_module",
        ).get(pk=job.id)
        return Response(
            {
                "success": True,
                "already_created": False,
                "job": LogAutoTicketJobSerializer(job_out).data,
            },
            status=status.HTTP_201_CREATED,
        )


class _ServerLogAuditPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 100


class ServerLogAuditViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """审计列表：系统管理员看全部，其余用户仅看自己的操作记录。"""

    permission_classes = [IsAuthenticated]
    serializer_class = ServerLogAuditEventSerializer
    pagination_class = _ServerLogAuditPagination

    def get_queryset(self):
        qs = ServerLogAuditEvent.objects.select_related(
            "user", "remote_log_server", "organization"
        ).order_by("-created_at")
        u = self.request.user
        if user_is_platform_log_admin(u):
            return qs
        return qs.filter(user=u)
