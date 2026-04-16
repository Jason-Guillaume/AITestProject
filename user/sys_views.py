"""系统级接口：全局 AI 模型配置（/api/sys/）"""

from datetime import datetime, timedelta

from django.db.models import Avg, Count, Max
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import AuditEvent
from user.models import AIModelConfig
from user.permissions import IsSystemAdmin
from user.serialize import (
    AIModelConfigReadSerializer,
    AIModelConfigWriteSerializer,
    AiQuotaPolicySerializer,
)
from common.services.audit import record_audit_event, record_export_audit


def _parse_date_yyyymmdd(s: str):
    try:
        return datetime.strptime(str(s).strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def _split_actions(raw: str) -> list[str]:
    text = str(raw or "").strip()
    if not text:
        return []
    parts = [x.strip() for x in text.split(",")]
    return [p for p in parts if p]


def _apply_ai_usage_filters(qs, request, *, allow_multi_action: bool = True):
    """
    统一筛选参数（给 events/export/top-errors/latency-trend 复用）：
    - action: 支持单值或逗号分隔多值（allow_multi_action=True）
    - success: true/false
    - user_id: int
    - error_code: 精确匹配（可选）
    - start_date/end_date: YYYY-MM-DD（可选，包含边界）
    """
    action = (request.query_params.get("action") or "").strip()
    if action:
        if allow_multi_action and "," in action:
            qs = qs.filter(action__in=_split_actions(action))
        else:
            qs = qs.filter(action=action)

    success = request.query_params.get("success")
    if success not in (None, ""):
        s = str(success).strip().lower()
        if s in ("1", "true", "yes"):
            qs = qs.filter(success=True)
        elif s in ("0", "false", "no"):
            qs = qs.filter(success=False)

    user_id = request.query_params.get("user_id")
    if user_id not in (None, ""):
        try:
            qs = qs.filter(user_id=int(user_id))
        except (TypeError, ValueError):
            pass

    error_code = (request.query_params.get("error_code") or "").strip()
    if error_code:
        qs = qs.filter(error_code=error_code)

    start_date = _parse_date_yyyymmdd(request.query_params.get("start_date") or "")
    end_date = _parse_date_yyyymmdd(request.query_params.get("end_date") or "")
    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)
    return qs


def _get_start_end_date_from_request(request):
    start_date = _parse_date_yyyymmdd(request.query_params.get("start_date") or "")
    end_date = _parse_date_yyyymmdd(request.query_params.get("end_date") or "")
    return start_date, end_date


class AIModelConfigAPIView(APIView):
    """
    GET /api/sys/ai-config/ — 任意登录用户可查看当前配置状态（不含明文 Key）
    PUT /api/sys/ai-config/ — 系统管理员保存/更新配置；保存后 is_connected=True
    DELETE /api/sys/ai-config/ — 系统管理员删除配置记录
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSystemAdmin()]

    def get(self, request):
        row = AIModelConfig.objects.order_by("id").first()
        if not row:
            return Response({"code": 200, "msg": "ok", "data": None})
        return Response(
            {
                "code": 200,
                "msg": "ok",
                "data": AIModelConfigReadSerializer(row).data,
            }
        )

    def put(self, request):
        row = AIModelConfig.objects.order_by("id").first()
        ser = AIModelConfigWriteSerializer(instance=row, data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        row = AIModelConfig.objects.order_by("id").first()
        return Response(
            {
                "code": 200,
                "msg": "保存成功",
                "data": AIModelConfigReadSerializer(row).data,
            }
        )

    def delete(self, request):
        deleted, _ = AIModelConfig.objects.all().delete()
        if not deleted:
            return Response(
                {"code": 400, "msg": "当前没有可删除的配置", "data": None},
                status=200,
            )
        return Response({"code": 200, "msg": "已删除", "data": None})


class AIModelConfigDisconnectAPIView(APIView):
    """POST /api/sys/ai-config/disconnect/ — 标记断开，不删除 Key"""

    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def post(self, request):
        row = AIModelConfig.objects.order_by("id").first()
        if not row:
            return Response(
                {"code": 404, "msg": "未配置 AI 模型", "data": None},
                status=200,
            )
        row.is_connected = False
        row.save(update_fields=["is_connected", "updated_at"])
        return Response(
            {
                "code": 200,
                "msg": "已断开连接",
                "data": AIModelConfigReadSerializer(row).data,
            }
        )


class AIModelConfigReconnectAPIView(APIView):
    """POST /api/sys/ai-config/reconnect/ — 在保留 Key 的前提下重新标记为已连接"""

    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def post(self, request):
        row = AIModelConfig.objects.order_by("id").first()
        if not row:
            return Response(
                {"code": 404, "msg": "未配置 AI 模型", "data": None},
                status=200,
            )
        row.is_connected = True
        row.save(update_fields=["is_connected", "updated_at"])
        return Response(
            {
                "code": 200,
                "msg": "已重新连接",
                "data": AIModelConfigReadSerializer(row).data,
            }
        )


# ---------------------------------------------------------------------------
# AI 配额治理（项目/组织/用户）
# ---------------------------------------------------------------------------


class AiQuotaPolicyListCreateAPIView(APIView):
    """
    GET /api/sys/ai-quota/policies/  列表
    POST /api/sys/ai-quota/policies/ 创建
    """

    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def get(self, request):
        from user.models import AiQuotaPolicy

        qs = AiQuotaPolicy.objects.filter(is_deleted=False).order_by("-id")
        scope_type = (request.query_params.get("scope_type") or "").strip()
        if scope_type:
            qs = qs.filter(scope_type=scope_type)
        project_id = request.query_params.get("project_id")
        if project_id not in (None, ""):
            try:
                qs = qs.filter(project_id=int(project_id))
            except Exception:
                pass
        org_id = request.query_params.get("org_id")
        if org_id not in (None, ""):
            try:
                qs = qs.filter(org_id=int(org_id))
            except Exception:
                pass
        user_id = request.query_params.get("user_id")
        if user_id not in (None, ""):
            try:
                qs = qs.filter(user_id=int(user_id))
            except Exception:
                pass

        limit = request.query_params.get("limit")
        try:
            limit_n = max(1, min(500, int(limit))) if limit not in (None, "") else 200
        except Exception:
            limit_n = 200

        items = list(qs[:limit_n])
        return Response(
            {
                "code": 200,
                "msg": "ok",
                "data": AiQuotaPolicySerializer(items, many=True).data,
            }
        )

    def post(self, request):
        ser = AiQuotaPolicySerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        obj = ser.save(creator=request.user, updater=request.user)
        record_audit_event(
            request=request,
            action=AuditEvent.ACTION_CREATE,
            obj=obj,
            before=None,
            after=AiQuotaPolicySerializer(obj).data,
        )
        return Response(
            {"code": 200, "msg": "创建成功", "data": AiQuotaPolicySerializer(obj).data}
        )


class AiQuotaPolicyDetailAPIView(APIView):
    """
    GET /api/sys/ai-quota/policies/<id>/
    PUT /api/sys/ai-quota/policies/<id>/
    DELETE /api/sys/ai-quota/policies/<id>/
    """

    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def get(self, request, policy_id: int):
        from user.models import AiQuotaPolicy

        obj = AiQuotaPolicy.objects.filter(pk=policy_id, is_deleted=False).first()
        if not obj:
            return Response({"code": 404, "msg": "不存在", "data": None}, status=404)
        return Response(
            {"code": 200, "msg": "ok", "data": AiQuotaPolicySerializer(obj).data}
        )

    def put(self, request, policy_id: int):
        from user.models import AiQuotaPolicy

        obj = AiQuotaPolicy.objects.filter(pk=policy_id, is_deleted=False).first()
        if not obj:
            return Response({"code": 404, "msg": "不存在", "data": None}, status=404)
        before = AiQuotaPolicySerializer(obj).data
        ser = AiQuotaPolicySerializer(
            instance=obj,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        ser.is_valid(raise_exception=True)
        obj = ser.save(updater=request.user)
        after = AiQuotaPolicySerializer(obj).data
        record_audit_event(
            request=request,
            action=AuditEvent.ACTION_UPDATE,
            obj=obj,
            before=before,
            after=after,
        )
        return Response({"code": 200, "msg": "保存成功", "data": after})

    def delete(self, request, policy_id: int):
        from user.models import AiQuotaPolicy

        obj = AiQuotaPolicy.objects.filter(pk=policy_id, is_deleted=False).first()
        if not obj:
            return Response({"code": 404, "msg": "不存在", "data": None}, status=404)
        before = AiQuotaPolicySerializer(obj).data
        obj.is_deleted = True
        obj.updater = request.user
        obj.save(update_fields=["is_deleted", "updater", "update_time"])
        record_audit_event(
            request=request,
            action=AuditEvent.ACTION_DELETE,
            obj=obj,
            before=before,
            after=None,
        )
        return Response({"code": 200, "msg": "删除成功", "data": None})


class AiUsageEventListAPIView(APIView):
    """
    GET /api/sys/ai-usage/events/
    系统管理员查看 AI 审计事件（最近 N 条，可筛选）。

    query params:
    - page_size: 默认 50，最大 200
    - action/success/user_id
    """

    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def get(self, request):
        from assistant.models import AiUsageEvent

        page_size = request.query_params.get("page_size", 50)
        try:
            page_size = int(page_size)
        except (TypeError, ValueError):
            page_size = 50
        page_size = max(1, min(page_size, 200))

        qs = _apply_ai_usage_filters(
            AiUsageEvent.objects.all(), request, allow_multi_action=True
        )

        rows = qs.order_by("-created_at")[:page_size]
        results = []
        for r in rows:
            results.append(
                {
                    "id": r.id,
                    "created_at": r.created_at,
                    "user_id": r.user_id,
                    "action": r.action,
                    "endpoint": r.endpoint,
                    "success": r.success,
                    "status_code": r.status_code,
                    "error_code": r.error_code,
                    "error_message": r.error_message,
                    "model_used": r.model_used,
                    "test_type": r.test_type,
                    "module_id": r.module_id,
                    "streamed": r.streamed,
                    "all_covered": r.all_covered,
                    "latency_ms": r.latency_ms,
                    "prompt_chars": r.prompt_chars,
                    "output_chars": r.output_chars,
                    "cases_count": r.cases_count,
                    "meta": r.meta,
                }
            )
        return Response({"success": True, "results": results})


class AiUsageSummaryAPIView(APIView):
    """
    GET /api/sys/ai-usage/summary/
    系统管理员查看近 7 天 AI 调用汇总（按 action）。
    """

    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def get(self, request):
        from assistant.models import AiUsageEvent

        days = request.query_params.get("days", 7)
        try:
            days = int(days)
        except (TypeError, ValueError):
            days = 7
        days = max(1, min(days, 31))
        since = timezone.now() - timedelta(days=days)
        qs = AiUsageEvent.objects.filter(created_at__gte=since)
        rows = (
            qs.values("action", "success")
            .annotate(count=Count("id"))
            .order_by("action", "success")
        )
        # 组装为 action -> {success/failed}
        out = {}
        for r in rows:
            act = r.get("action") or ""
            if act not in out:
                out[act] = {"success": 0, "failed": 0, "total": 0}
            if bool(r.get("success")):
                out[act]["success"] += int(r.get("count") or 0)
            else:
                out[act]["failed"] += int(r.get("count") or 0)
            out[act]["total"] += int(r.get("count") or 0)
        return Response(
            {"success": True, "since": since, "days": days, "by_action": out}
        )


class AiUsageMetricsAPIView(APIView):
    """
    GET /api/sys/ai-usage/metrics/
    返回近 N 天的趋势与耗时分位数（按 action）。

    query params:
    - days: 1..31，默认 7
    - max_samples: 每个 action 用于分位数计算的最大样本数（默认 5000）
    """

    permission_classes = [IsAuthenticated, IsSystemAdmin]

    @staticmethod
    def _quantile(values: list[int], q: float) -> int:
        if not values:
            return 0
        q = max(0.0, min(1.0, float(q)))
        values.sort()
        idx = int(round((len(values) - 1) * q))
        idx = max(0, min(len(values) - 1, idx))
        return int(values[idx])

    def get(self, request):
        from assistant.models import AiUsageEvent

        days = request.query_params.get("days", 7)
        try:
            days = int(days)
        except (TypeError, ValueError):
            days = 7
        days = max(1, min(days, 31))
        since = timezone.now() - timedelta(days=days)

        max_samples = request.query_params.get("max_samples", 5000)
        try:
            max_samples = int(max_samples)
        except (TypeError, ValueError):
            max_samples = 5000
        max_samples = max(200, min(max_samples, 20000))

        qs = AiUsageEvent.objects.filter(created_at__gte=since)

        # 1) 趋势：按天、按 action 统计 total/success/failed
        try:
            from django.db.models.functions import TruncDate

            trend_rows = (
                qs.annotate(day=TruncDate("created_at"))
                .values("day", "action", "success")
                .annotate(count=Count("id"))
                .order_by("day", "action", "success")
            )
        except Exception:
            trend_rows = []

        # 2) 基础耗时指标：avg/max（DB 可聚合）
        latency_rows = (
            qs.values("action")
            .annotate(
                avg_ms=Avg("latency_ms"), max_ms=Max("latency_ms"), total=Count("id")
            )
            .order_by("action")
        )
        latency_map = {
            r.get("action")
            or "": {
                "avg_ms": int(float(r.get("avg_ms") or 0)),
                "max_ms": int(r.get("max_ms") or 0),
                "total": int(r.get("total") or 0),
            }
            for r in latency_rows
        }

        # 3) 分位数：用 Python 在“有限样本”上计算（避免数据库 percentile 函数兼容性）
        p_map: dict[str, dict[str, int]] = {}
        actions = list(latency_map.keys())
        for action in actions:
            vals = list(
                qs.filter(action=action)
                .exclude(latency_ms__lte=0)
                .order_by("-created_at")
                .values_list("latency_ms", flat=True)[:max_samples]
            )
            vals = [int(x) for x in vals if x is not None]
            p_map[action] = {
                "p50_ms": self._quantile(vals, 0.50),
                "p95_ms": self._quantile(vals, 0.95),
            }

        # 4) 组装趋势：xAxis 为日期字符串，series 为每个 action 的 total/success/failed
        day_set = []
        bucket = {}
        for r in trend_rows:
            day = r.get("day")
            act = r.get("action") or ""
            suc = bool(r.get("success"))
            cnt = int(r.get("count") or 0)
            if day not in day_set:
                day_set.append(day)
            key = (day, act)
            if key not in bucket:
                bucket[key] = {"total": 0, "success": 0, "failed": 0}
            bucket[key]["total"] += cnt
            if suc:
                bucket[key]["success"] += cnt
            else:
                bucket[key]["failed"] += cnt

        x_axis = [
            (d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d))
            for d in day_set
        ]
        trend = []
        for act in actions:
            total_series = []
            succ_series = []
            fail_series = []
            for d in day_set:
                row = bucket.get((d, act)) or {"total": 0, "success": 0, "failed": 0}
                total_series.append(int(row["total"]))
                succ_series.append(int(row["success"]))
                fail_series.append(int(row["failed"]))
            trend.append(
                {
                    "action": act,
                    "total": total_series,
                    "success": succ_series,
                    "failed": fail_series,
                }
            )

        # 5) 汇总指标：per action
        metrics = {}
        for act in actions:
            m = latency_map.get(act) or {"avg_ms": 0, "max_ms": 0, "total": 0}
            p = p_map.get(act) or {"p50_ms": 0, "p95_ms": 0}
            metrics[act] = {**m, **p}

        return Response(
            {
                "success": True,
                "since": since,
                "days": days,
                "xAxis": x_axis,
                "trend": trend,
                "metrics": metrics,
            }
        )


class AiUsageTopErrorsAPIView(APIView):
    """
    GET /api/sys/ai-usage/top-errors/
    返回近 N 天失败事件的 Top 错误码/摘要。
    """

    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def get(self, request):
        from assistant.models import AiUsageEvent

        start_date, end_date = _get_start_end_date_from_request(request)
        days = request.query_params.get("days", 7)
        try:
            days = int(days)
        except (TypeError, ValueError):
            days = 7
        days = max(1, min(days, 31))
        since = timezone.now() - timedelta(days=days)

        limit = request.query_params.get("limit", 10)
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 50))

        if start_date or end_date:
            base_qs = AiUsageEvent.objects.filter(success=False)
        else:
            base_qs = AiUsageEvent.objects.filter(created_at__gte=since, success=False)
        qs = _apply_ai_usage_filters(base_qs, request, allow_multi_action=True)
        rows = (
            qs.values("action", "error_code", "error_message")
            .annotate(count=Count("id"), max_latency=Max("latency_ms"))
            .order_by("-count")[: limit * 3]
        )
        results = []
        for r in rows:
            results.append(
                {
                    "action": r.get("action") or "",
                    "error_code": r.get("error_code") or "",
                    "error_message": r.get("error_message") or "",
                    "count": int(r.get("count") or 0),
                    "max_latency_ms": int(r.get("max_latency") or 0),
                }
            )
        return Response(
            {"success": True, "since": since, "days": days, "results": results[:limit]}
        )


class AiUsageLatencyTrendAPIView(APIView):
    """
    GET /api/sys/ai-usage/latency-trend/
    返回近 N 天按天的 P95 趋势（按 action）。

    说明：
    - 由于 MySQL 环境下 percentile 聚合兼容性不稳定，这里采用“每日抽样 + Python 分位数计算”。
    - 每天每个 action 抽样 max_samples 条（按时间倒序），以控制计算量。
    """

    permission_classes = [IsAuthenticated, IsSystemAdmin]

    @staticmethod
    def _quantile(values: list[int], q: float) -> int:
        if not values:
            return 0
        q = max(0.0, min(1.0, float(q)))
        values.sort()
        idx = int(round((len(values) - 1) * q))
        idx = max(0, min(len(values) - 1, idx))
        return int(values[idx])

    def get(self, request):
        from assistant.models import AiUsageEvent

        start_date, end_date = _get_start_end_date_from_request(request)
        days = request.query_params.get("days", 7)
        try:
            days = int(days)
        except (TypeError, ValueError):
            days = 7
        days = max(1, min(days, 31))

        max_samples = request.query_params.get("max_samples", 500)
        try:
            max_samples = int(max_samples)
        except (TypeError, ValueError):
            max_samples = 500
        max_samples = max(50, min(max_samples, 5000))

        now = timezone.now()
        # 以自然日为单位输出 xAxis；若传 start_date/end_date，则优先使用（并限制最大窗口）
        if start_date or end_date:
            if not end_date:
                end_date = now.date()
            if not start_date:
                start_date = end_date - timedelta(days=days - 1)
            # 限制窗口，避免超大计算
            max_days = 62
            if (end_date - start_date).days + 1 > max_days:
                start_date = end_date - timedelta(days=max_days - 1)
            day_list = []
            cur = start_date
            while cur <= end_date:
                day_list.append(cur)
                cur = cur + timedelta(days=1)
        else:
            start_day = (now - timedelta(days=days - 1)).date()
            day_list = [start_day + timedelta(days=i) for i in range(days)]
        x_axis = [d.strftime("%Y-%m-%d") for d in day_list]

        qs = AiUsageEvent.objects.all()
        qs = _apply_ai_usage_filters(qs, request, allow_multi_action=True)
        if not (start_date or end_date):
            # 没有自定义范围时，按 days 控制数据窗口
            start_day = day_list[0]
            qs = qs.filter(created_at__date__gte=start_day)

        actions = list(
            qs.values_list("action", flat=True).distinct().order_by("action")
        )

        series = []
        for act in actions:
            p95_rows = []
            for d in day_list:
                vals = list(
                    qs.filter(action=act, created_at__date=d)
                    .exclude(latency_ms__lte=0)
                    .order_by("-created_at")
                    .values_list("latency_ms", flat=True)[:max_samples]
                )
                vals = [int(v) for v in vals if v is not None]
                p95_rows.append(self._quantile(vals, 0.95))
            series.append({"action": act, "p95_ms": p95_rows})

        return Response(
            {
                "success": True,
                "days": days,
                "xAxis": x_axis,
                "series": series,
            }
        )


class AiUsageExportCsvAPIView(APIView):
    """
    GET /api/sys/ai-usage/export.csv
    按筛选条件导出审计事件 CSV（流式输出，避免大结果占用内存）。

    query params（与 events 列表保持一致）：
    - action / success / user_id
    - limit: 默认 2000，最大 200000
    """

    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def get(self, request):
        from assistant.models import AiUsageEvent
        from django.http import StreamingHttpResponse

        limit = request.query_params.get("limit", 2000)
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 2000
        limit = max(1, min(limit, 200000))

        qs = _apply_ai_usage_filters(
            AiUsageEvent.objects.all(), request, allow_multi_action=True
        )

        qs = qs.order_by("-created_at")[:limit]

        columns = [
            "created_at",
            "action",
            "success",
            "status_code",
            "user_id",
            "model_used",
            "test_type",
            "module_id",
            "latency_ms",
            "prompt_chars",
            "output_chars",
            "cases_count",
            "error_code",
            "error_message",
            "endpoint",
        ]

        def _csv_escape(v):
            s = "" if v is None else str(v)
            s = s.replace("\r", " ").replace("\n", " ")
            if '"' in s:
                s = s.replace('"', '""')
            if any(ch in s for ch in [",", '"']):
                return f'"{s}"'
            return s

        def stream():
            yield ",".join(columns) + "\n"
            for r in qs.iterator(chunk_size=1000):
                row = []
                for c in columns:
                    val = getattr(r, c, None)
                    row.append(_csv_escape(val))
                yield ",".join(row) + "\n"

        resp = StreamingHttpResponse(stream(), content_type="text/csv; charset=utf-8")
        filename = f"ai-usage-events-{timezone.now().strftime('%Y%m%d-%H%M')}.csv"
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        resp["Cache-Control"] = "no-store"
        record_export_audit(
            actor=request.user,
            instance=None,
            request=request,
            extra={"export": "ai_usage_events", "rows": int(limit)},
        )
        return resp


class AuditEventListAPIView(APIView):
    """
    GET /api/sys/audit/events/
    系统审计事件查询（系统管理员）。

    query params:
    - action: create/update/delete/export/execute（可选）
    - object_app/object_model/object_id（可选）
    - start_date/end_date: YYYY-MM-DD（可选，包含边界）
    - page/page_size：默认 1/50，page_size 最大 200
    """

    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def get(self, request):
        try:
            page = int(request.query_params.get("page", "1"))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.query_params.get("page_size", "50"))
        except (TypeError, ValueError):
            page_size = 50
        page = max(1, page)
        page_size = max(1, min(page_size, 200))
        offset = (page - 1) * page_size

        qs = AuditEvent.objects.filter(is_deleted=False)

        action = (request.query_params.get("action") or "").strip()
        if action:
            qs = qs.filter(action=action)
        object_app = (request.query_params.get("object_app") or "").strip()
        if object_app:
            qs = qs.filter(object_app=object_app)
        object_model = (request.query_params.get("object_model") or "").strip()
        if object_model:
            qs = qs.filter(object_model=object_model)
        object_id = (request.query_params.get("object_id") or "").strip()
        if object_id:
            qs = qs.filter(object_id=object_id)

        start_date = _parse_date_yyyymmdd(request.query_params.get("start_date") or "")
        end_date = _parse_date_yyyymmdd(request.query_params.get("end_date") or "")
        if start_date:
            qs = qs.filter(create_time__date__gte=start_date)
        if end_date:
            qs = qs.filter(create_time__date__lte=end_date)

        total = qs.count()
        rows = list(
            qs.order_by("-create_time")
            .values(
                "id",
                "action",
                "object_app",
                "object_model",
                "object_id",
                "object_repr",
                "request_path",
                "ip",
                "user_agent",
                "before",
                "after",
                "extra",
                "creator_id",
                "create_time",
            )[offset : offset + page_size]
        )
        return Response(
            {
                "code": 200,
                "msg": "ok",
                "data": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "items": rows,
                },
            }
        )


class AuditEventExportCsvAPIView(APIView):
    """
    GET /api/sys/audit/export.csv
    按筛选条件导出系统审计 CSV（流式输出）。

    query params:
    - action/object_app/object_model/object_id（可选）
    - start_date/end_date（可选）
    - limit: 默认 5000，最大 200000
    """

    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def get(self, request):
        from django.http import StreamingHttpResponse

        limit = request.query_params.get("limit", 5000)
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 5000
        limit = max(1, min(limit, 200000))

        qs = AuditEvent.objects.filter(is_deleted=False)

        action = (request.query_params.get("action") or "").strip()
        if action:
            qs = qs.filter(action=action)
        object_app = (request.query_params.get("object_app") or "").strip()
        if object_app:
            qs = qs.filter(object_app=object_app)
        object_model = (request.query_params.get("object_model") or "").strip()
        if object_model:
            qs = qs.filter(object_model=object_model)
        object_id = (request.query_params.get("object_id") or "").strip()
        if object_id:
            qs = qs.filter(object_id=object_id)

        start_date = _parse_date_yyyymmdd(request.query_params.get("start_date") or "")
        end_date = _parse_date_yyyymmdd(request.query_params.get("end_date") or "")
        if start_date:
            qs = qs.filter(create_time__date__gte=start_date)
        if end_date:
            qs = qs.filter(create_time__date__lte=end_date)

        qs = qs.order_by("-create_time")[:limit]

        columns = [
            "create_time",
            "action",
            "object_app",
            "object_model",
            "object_id",
            "object_repr",
            "request_path",
            "ip",
            "creator_id",
        ]

        def _csv_escape(v):
            s = "" if v is None else str(v)
            s = s.replace("\r", " ").replace("\n", " ")
            if '"' in s:
                s = s.replace('"', '""')
            if any(ch in s for ch in [",", '"']):
                return f'"{s}"'
            return s

        def stream():
            yield ",".join(columns) + "\n"
            for r in qs.iterator(chunk_size=1000):
                row = [
                    getattr(r, "create_time", None),
                    getattr(r, "action", None),
                    getattr(r, "object_app", None),
                    getattr(r, "object_model", None),
                    getattr(r, "object_id", None),
                    getattr(r, "object_repr", None),
                    getattr(r, "request_path", None),
                    getattr(r, "ip", None),
                    getattr(r, "creator_id", None),
                ]
                yield ",".join(_csv_escape(x) for x in row) + "\n"

        resp = StreamingHttpResponse(stream(), content_type="text/csv; charset=utf-8")
        filename = f"audit-events-{timezone.now().strftime('%Y%m%d-%H%M')}.csv"
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        resp["Cache-Control"] = "no-store"
        record_export_audit(
            actor=request.user,
            instance=None,
            request=request,
            extra={"export": "audit_events", "rows": int(limit)},
        )
        return resp
