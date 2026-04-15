from common.views import *
from execution.models import *
from execution.serialize import *
from execution.scheduler import TestScheduler, execute_scheduled_task
from execution.services.metric_calculator import MetricCalculator
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.authtoken.models import Token
from django.utils import timezone
from django.core.cache import cache
from django.http import StreamingHttpResponse, JsonResponse
from django.views import View
from datetime import timedelta, datetime, time
from django.db.models import Avg, Count, DateField, Q
from django.db import IntegrityError
from django.db.models.functions import TruncDate

import logging
import uuid
import json
import time as time_module
import asyncio
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class DashboardStreamView(View):
    """
    Dashboard SSE 事件流（推送刷新信号）。
    EventSource 无法自定义 Authorization 头，支持 ?token=<DRF Token>。
    """

    @staticmethod
    def _resolve_user(request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            return user
        token_key = (request.GET.get("token") or "").strip()
        if not token_key:
            auth_header = request.META.get("HTTP_AUTHORIZATION", "")
            if auth_header.lower().startswith("token "):
                token_key = auth_header.split(" ", 1)[1].strip()
        if not token_key:
            return None
        try:
            token = Token.objects.select_related("user").get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            return None

    async def get(self, request, *args, **kwargs):
        """
        重要：SSE 是长连接；在 ASGI 下若用同步 view + time.sleep 会占用线程池，
        当连接数变多时可能导致其它 API（如删除/保存）被“饿死”出现超时/异常。

        这里改为 async + asyncio.sleep，避免占用同步线程池。
        """

        user = await sync_to_async(self._resolve_user)(request)
        if not user:
            return JsonResponse({"detail": "认证失败"}, status=401)

        project_id = request.GET.get("project_id")

        async def event_stream():
            yield "retry: 3000\n\n"
            while True:
                payload = {
                    "type": "dashboard_tick",
                    "ts": timezone.now().isoformat(),
                    "project_id": project_id,
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                await asyncio.sleep(3)

        response = StreamingHttpResponse(
            streaming_content=event_stream(),
            content_type="text/event-stream; charset=utf-8",
        )
        response["Cache-Control"] = "no-cache, no-store, no-transform"
        response["Pragma"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class TestPlanViewSet(BaseModelViewSet):
    queryset = TestPlan.objects.all().prefetch_related("testers")
    serializer_class = TestPlanSerializer


class TestReportViewSet(BaseModelViewSet):
    queryset = TestReport.objects.all()
    serializer_class = TestReportSerializer


class PerfTaskPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class PerfTaskViewSet(BaseModelViewSet):
    queryset = PerfTask.objects.all()
    serializer_class = PerfTaskSerializer
    pagination_class = PerfTaskPagination
    lookup_field = "task_id"

    def get_queryset(self):
        queryset = super().get_queryset()
        request = self.request
        name = request.query_params.get("name")
        status_value = request.query_params.get("status")
        executor = request.query_params.get("executor")

        if name:
            queryset = queryset.filter(task_name__icontains=name)
        if status_value:
            queryset = queryset.filter(status=status_value)
        if executor:
            queryset = queryset.filter(executor__icontains=executor)

        return queryset.order_by("-create_time")

    def perform_create(self, serializer):
        user = self.request.user
        task_id = f"PT-{uuid.uuid4().hex[:8].upper()}"
        if user and user.is_authenticated:
            serializer.save(task_id=task_id, creator=user)
        else:
            serializer.save(task_id=task_id)

    @action(methods=["post"], detail=True, url_path="run")
    def run(self, request, pk=None, task_id=None):
        task = self.get_object()
        if task.status == PerfTask.STATUS_RUNNING:
            return Response(
                {"detail": "任务正在运行中，无需重复触发"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if task.status == PerfTask.STATUS_COMPLETED:
            return Response(
                {"detail": "已完成任务不可直接执行，请复制后重跑"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task.status = PerfTask.STATUS_RUNNING
        if request.user and request.user.is_authenticated:
            task.executor = request.user.real_name or request.user.username
            task.updater = request.user
        task.save(update_fields=["status", "executor", "updater", "update_time"])
        return Response(
            {"detail": "任务已触发执行", "task_id": task.task_id},
            status=status.HTTP_200_OK,
        )


class DashboardSummaryAPIView(APIView):
    """
    首页/工作台仪表盘聚合接口
    返回：统计卡片、折线图（周/月）、饼图、柱状图、最近测试任务列表
    """

    def _humanize_delta(self, dt):
        if not dt:
            return "-"
        now = timezone.now()
        diff = now - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return f"{seconds}秒前" if seconds > 0 else "刚刚"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}分钟前"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}小时前"
        days = hours // 24
        return f"{days}天前"

    def _last_n_days(self, n):
        today = timezone.localdate()
        dates = [today - timedelta(days=i) for i in range(n - 1, -1, -1)]
        return dates

    def _count_by_day(self, model_cls, field_name, dates):
        if not dates:
            return []
        start = timezone.make_aware(datetime.combine(dates[0], time.min))
        end = timezone.make_aware(datetime.combine(dates[-1], time.max))
        day_expr = TruncDate(field_name, output_field=DateField())
        rows = (
            model_cls.objects.filter(
                is_deleted=False,
                **{f"{field_name}__gte": start, f"{field_name}__lte": end},
            )
            .annotate(day=day_expr)
            .values("day")
            .annotate(total=Count("id"))
        )
        day_to_count = {row["day"]: row["total"] for row in rows}
        return [int(day_to_count.get(d, 0)) for d in dates]

    def get(self, request, *args, **kwargs):
        # 统一使用真实数据；如果表为空则返回 0，确保前端不会报错
        from testcase.models import TestCase
        from defect.models import TestDefect

        project_id = (request.query_params.get("project_id") or "").strip()
        user = getattr(request, "user", None)
        is_admin = bool(
            user
            and getattr(user, "is_authenticated", False)
            and (
                getattr(user, "is_superuser", False)
                or getattr(user, "is_staff", False)
                or bool(getattr(user, "is_system_admin", False))
            )
        )

        def _case_scope_qs():
            qs = TestCase.objects.filter(is_deleted=False)
            if project_id:
                try:
                    pid = int(project_id)
                except (TypeError, ValueError):
                    return qs.none()
                return qs.filter(module__project_id=pid)
            if user and getattr(user, "is_authenticated", False) and not is_admin:
                return qs.filter(
                    Q(module__project__members=user) | Q(creator=user)
                ).distinct()
            return qs

        def _defect_scope_qs():
            qs = TestDefect.objects.filter(is_deleted=False)
            if project_id:
                try:
                    pid = int(project_id)
                except (TypeError, ValueError):
                    return qs.none()
                # 缺陷模型不一定有 project 字段：优先走常见链路（用例/模块/项目）
                if hasattr(TestDefect, "project_id"):
                    return qs.filter(project_id=pid)
                if hasattr(TestDefect, "testcase_id"):
                    return qs.filter(testcase__module__project_id=pid)
                if hasattr(TestDefect, "test_case_id"):
                    return qs.filter(test_case__module__project_id=pid)
                return qs
            if user and getattr(user, "is_authenticated", False) and not is_admin:
                if hasattr(TestDefect, "creator_id"):
                    return qs.filter(
                        Q(creator=user)
                        | Q(testcase__module__project__members=user)
                        | Q(test_case__module__project__members=user)
                    ).distinct()
            return qs

        # --------------------------
        # 统计卡片
        # --------------------------
        total_cases = _case_scope_qs().count()

        # 今日“执行用例”近似：今日生成的测试报告数量
        today = timezone.localdate()
        start_today = timezone.make_aware(datetime.combine(today, time.min))
        end_today = start_today + timedelta(days=1)
        today_reports_qs = TestReport.objects.filter(
            is_deleted=False, create_time__gte=start_today, create_time__lt=end_today
        )
        if project_id:
            try:
                pid = int(project_id)
            except (TypeError, ValueError):
                pid = None
            if pid is not None:
                if hasattr(TestReport, "project_id"):
                    today_reports_qs = today_reports_qs.filter(project_id=pid)
                else:
                    today_reports_qs = today_reports_qs.filter(
                        plan__version__project_id=pid
                    )
        today_reports = today_reports_qs.count()

        # 未解决缺陷：状态非“已关闭”(4)
        unresolved_defects = _defect_scope_qs().exclude(status=4).count()

        completed_plans = TestPlan.objects.filter(is_deleted=False, plan_status=3)
        if completed_plans.exists():
            pass_rate = float(
                completed_plans.aggregate(avg_rate=Avg("pass_rate")).get("avg_rate")
                or 0.0
            )
        else:
            pass_rate = 0.0

        # 对比昨日：同样采用“今日/昨日”口径的简单增量（用于前端展示）
        yesterday = today - timedelta(days=1)
        start_yesterday = timezone.make_aware(datetime.combine(yesterday, time.min))
        end_yesterday = start_yesterday + timedelta(days=1)
        yesterday_reports_qs = TestReport.objects.filter(
            is_deleted=False,
            create_time__gte=start_yesterday,
            create_time__lt=end_yesterday,
        )
        if project_id:
            try:
                pid = int(project_id)
            except (TypeError, ValueError):
                pid = None
            if pid is not None:
                if hasattr(TestReport, "project_id"):
                    yesterday_reports_qs = yesterday_reports_qs.filter(project_id=pid)
                else:
                    yesterday_reports_qs = yesterday_reports_qs.filter(
                        plan__version__project_id=pid
                    )
        yesterday_reports = yesterday_reports_qs.count()
        yesterday_unresolved_new = (
            _defect_scope_qs()
            .exclude(status=4)
            .filter(create_time__gte=start_yesterday, create_time__lt=end_yesterday)
            .count()
        )

        # 总用例：对比“昨日新增用例数”
        yesterday_new_cases = (
            _case_scope_qs()
            .filter(create_time__gte=start_yesterday, create_time__lt=end_yesterday)
            .count()
        )
        today_new_cases = (
            _case_scope_qs()
            .filter(create_time__gte=start_today, create_time__lt=end_today)
            .count()
        )

        total_cases_delta = today_new_cases - yesterday_new_cases
        today_reports_delta = today_reports - yesterday_reports
        today_unresolved_new = (
            _defect_scope_qs()
            .exclude(status=4)
            .filter(create_time__gte=start_today, create_time__lt=end_today)
            .count()
        )
        unresolved_defects_delta = today_unresolved_new - yesterday_unresolved_new

        # --------------------------
        # 图表数据
        # --------------------------
        last7 = self._last_n_days(7)
        last30 = self._last_n_days(30)

        week_executed = self._count_by_day(TestReport, "create_time", last7)
        week_defects = self._count_by_day(TestDefect, "create_time", last7)
        month_executed = self._count_by_day(TestReport, "create_time", last30)
        month_defects = self._count_by_day(TestDefect, "create_time", last30)

        week_x = [d.strftime("%m/%d") for d in last7]
        month_x = [d.strftime("%m/%d") for d in last30]

        # 饼图：按缺陷严重程度映射到“安全/合规/性能/功能”
        # 1 致命 -> 安全；2 严重 -> 合规；3 一般 -> 性能；4 建议 -> 功能
        severity_map = {1: "安全", 2: "合规", 3: "性能", 4: "功能"}
        pie_items = []
        for sev in [1, 2, 3, 4]:
            v = TestDefect.objects.filter(is_deleted=False, severity=sev).count()
            pie_items.append({"name": severity_map[sev], "value": v})

        # 柱状图：近 7 天缺陷新增数
        bar_x = week_x
        bar_values = week_defects

        # --------------------------
        # 最近测试任务（统一做成“活动流”）
        # --------------------------
        activities = []
        # 运行中测试计划
        running_plans = TestPlan.objects.filter(
            is_deleted=False, plan_status=2
        ).order_by("-update_time")[:2]
        for p in running_plans:
            activities.append(
                {
                    "id": f"plan-{p.id}",
                    "tag": "进行中",
                    "tagType": "warning",
                    "text": p.plan_name,
                    "time": self._humanize_delta(p.update_time),
                }
            )

        # 新缺陷
        new_defects = TestDefect.objects.filter(is_deleted=False, status=1).order_by(
            "-update_time"
        )[:2]
        for d in new_defects:
            activities.append(
                {
                    "id": f"defect-{d.id}",
                    "tag": "新缺陷",
                    "tagType": "danger",
                    "text": f"{d.defect_name}",
                    "time": self._humanize_delta(d.update_time),
                }
            )

        # 运行中性能任务
        perf_running = PerfTask.objects.filter(
            is_deleted=False, status=PerfTask.STATUS_RUNNING
        ).order_by("-update_time")[:1]
        for t in perf_running:
            activities.append(
                {
                    "id": f"perftask-{t.id}",
                    "tag": "进行中",
                    "tagType": "info",
                    "text": f"性能任务：{t.task_name}",
                    "time": self._humanize_delta(t.update_time),
                }
            )

        # 补齐：用已完成测试计划
        if len(activities) < 6:
            finished = TestPlan.objects.filter(
                is_deleted=False, plan_status=3
            ).order_by("-update_time")[: (6 - len(activities))]
            for p in finished:
                activities.append(
                    {
                        "id": f"plan-done-{p.id}",
                        "tag": "已完成",
                        "tagType": "success",
                        "text": p.plan_name,
                        "time": self._humanize_delta(p.update_time),
                    }
                )

        # --------------------------
        # 返回
        # --------------------------
        return Response(
            {
                "statCards": {
                    "totalCases": {
                        "value": total_cases,
                        "label": "测试用例总数",
                        "delta": total_cases_delta,
                        "barBg": "#e6f4ff",
                        "barColor": "#1677ff",
                        "barWidth": f"{max(10, min(100, 50 + total_cases_delta * 10))}%",
                    },
                    "todayExecuted": {
                        "value": today_reports,
                        "label": "今日执行用例",
                        "delta": today_reports_delta,
                        "barBg": "#e6fffb",
                        "barColor": "#13c2c2",
                        "barWidth": f"{max(10, min(100, 50 + today_reports_delta * 20))}%",
                    },
                    "unresolvedDefects": {
                        "value": unresolved_defects,
                        "label": "未解决缺陷",
                        "delta": unresolved_defects_delta,
                        "barBg": "#fff7e6",
                        "barColor": "#fa8c16",
                        "barWidth": f"{max(10, min(100, 50 + unresolved_defects_delta * 10))}%",
                    },
                    "passRate": {
                        "value": f"{round(pass_rate, 0)}%",
                        "label": "用例通过率",
                        "delta": 0,
                        "barBg": "#f6ffed",
                        "barColor": "#52c41a",
                        "barWidth": f"{min(max(int(pass_rate), 0), 100)}%",
                    },
                },
                "lineChart": {
                    "week": {
                        "x": week_x,
                        "executed": week_executed,
                        "defects": week_defects,
                    },
                    "month": {
                        "x": month_x,
                        "executed": month_executed,
                        "defects": month_defects,
                    },
                },
                "pieChart": {"items": pie_items},
                "barChart": {"x": bar_x, "values": bar_values},
                "activities": activities[:6],
            }
        )


class QualityDashboardView(APIView):
    """
    测试质量分析接口（ECharts 友好结构）：
    - 各模块缺陷分布
    - 用例通过率趋势
    - 需求覆盖率
    """

    def _resolve_dates(self, time_range: str):
        tr = (time_range or "30d").strip().lower()
        days_map = {"7d": 7, "14d": 14, "30d": 30, "90d": 90}
        days = days_map.get(tr, 30)
        end_date = timezone.localdate()
        start_date = end_date - timedelta(days=days - 1)
        start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
        end_dt = timezone.make_aware(datetime.combine(end_date, time.max))
        return start_date, end_date, start_dt, end_dt

    def _fill_daily_rate(self, start_date, end_date, day_rate_map):
        labels = []
        values = []
        cur = start_date
        while cur <= end_date:
            labels.append(cur.strftime("%m/%d"))
            values.append(round(float(day_rate_map.get(cur, 0.0)), 2))
            cur += timedelta(days=1)
        return labels, values

    def get(self, request, *args, **kwargs):
        project_id = request.query_params.get("project_id")
        time_range = (request.query_params.get("time_range") or "30d").strip().lower()
        start_date, end_date, _, _ = self._resolve_dates(time_range)
        pid = None
        if project_id not in (None, ""):
            try:
                pid = int(project_id)
            except (TypeError, ValueError):
                return Response(
                    {"msg": "project_id 必须为整数"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        cache_key = f"quality_dashboard_metric:{pid if pid is not None else 'null'}:{start_date.isoformat()}:{end_date.isoformat()}:{time_range}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        calculator = MetricCalculator()
        days = []
        cur = start_date
        while cur <= end_date:
            days.append(cur)
            calculator.calc_pass_rate(pid, cur)
            calculator.calc_defect_density(pid, cur)
            calculator.calc_requirement_coverage(pid, cur)
            cur += timedelta(days=1)

        metrics_qs = TestQualityMetric.objects.filter(
            is_deleted=False,
            metric_date__gte=start_date,
            metric_date__lte=end_date,
        )
        metrics_qs = metrics_qs.filter(
            dimension__project_id=(pid if pid is not None else None)
        )

        metric_map = {
            TestQualityMetric.METRIC_PASS_RATE: {},
            TestQualityMetric.METRIC_DEFECT_DENSITY: {},
            TestQualityMetric.METRIC_REQUIREMENT_COVERAGE: {},
        }
        for item in metrics_qs:
            metric_map.setdefault(item.metric_type, {})[item.metric_date] = float(
                item.metric_value
            )

        x_axis = [d.strftime("%m/%d") for d in days]
        pass_rate_series = [
            round(metric_map[TestQualityMetric.METRIC_PASS_RATE].get(d, 0.0), 4)
            for d in days
        ]
        defect_density_series = [
            round(metric_map[TestQualityMetric.METRIC_DEFECT_DENSITY].get(d, 0.0), 4)
            for d in days
        ]
        req_cov_series = [
            round(
                metric_map[TestQualityMetric.METRIC_REQUIREMENT_COVERAGE].get(d, 0.0), 4
            )
            for d in days
        ]

        payload = {
            "filters": {
                "project_id": pid,
                "time_range": "30d",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "trendChart": {
                "xAxis": x_axis,
                "series": [
                    {
                        "name": "用例通过率(%)",
                        "type": "line",
                        "smooth": True,
                        "data": pass_rate_series,
                    },
                    {
                        "name": "缺陷密度",
                        "type": "line",
                        "smooth": True,
                        "data": defect_density_series,
                    },
                    {
                        "name": "需求覆盖率(%)",
                        "type": "line",
                        "smooth": True,
                        "data": req_cov_series,
                    },
                ],
            },
            "latestMetrics": {
                "date": end_date.isoformat(),
                "pass_rate": pass_rate_series[-1] if pass_rate_series else 0.0,
                "defect_density": (
                    defect_density_series[-1] if defect_density_series else 0.0
                ),
                "requirement_coverage": req_cov_series[-1] if req_cov_series else 0.0,
            },
            "raw": {
                "pass_rate": {
                    "metric_type": TestQualityMetric.METRIC_PASS_RATE,
                    "points": [
                        {"date": d.isoformat(), "value": pass_rate_series[idx]}
                        for idx, d in enumerate(days)
                    ],
                },
                "defect_density": {
                    "metric_type": TestQualityMetric.METRIC_DEFECT_DENSITY,
                    "points": [
                        {"date": d.isoformat(), "value": defect_density_series[idx]}
                        for idx, d in enumerate(days)
                    ],
                },
                "requirement_coverage": {
                    "metric_type": TestQualityMetric.METRIC_REQUIREMENT_COVERAGE,
                    "points": [
                        {"date": d.isoformat(), "value": req_cov_series[idx]}
                        for idx, d in enumerate(days)
                    ],
                },
            },
            "chartsCompat": {
                "passRateTrend": {
                    "xAxis": x_axis,
                    "series": [
                        {
                            "name": "用例通过率(%)",
                            "type": "line",
                            "smooth": True,
                            "data": pass_rate_series,
                        }
                    ],
                },
                "defectDensityTrend": {
                    "xAxis": x_axis,
                    "series": [
                        {
                            "name": "缺陷密度",
                            "type": "line",
                            "smooth": True,
                            "data": defect_density_series,
                        }
                    ],
                },
                "requirementCoverageTrend": {
                    "xAxis": x_axis,
                    "series": [
                        {
                            "name": "需求覆盖率(%)",
                            "type": "line",
                            "smooth": True,
                            "data": req_cov_series,
                        }
                    ],
                },
            },
        }
        cache.set(cache_key, payload, timeout=60)
        return Response(payload)


class ScheduledTaskViewSet(BaseModelViewSet):
    queryset = ScheduledTask.objects.prefetch_related("test_cases").all()
    serializer_class = ScheduledTaskSerializer

    def perform_create(self, serializer):
        instance = serializer.save(job_id=f"scheduled-task-{uuid.uuid4().hex}")
        try:
            TestScheduler.instance().sync_task(instance)
        except Exception as exc:
            logger.exception("创建调度任务后同步失败: task_id=%s", instance.id)
            raise ValidationError({"msg": f"任务已创建，但调度同步失败: {exc}"})

    def perform_update(self, serializer):
        instance = serializer.save()
        try:
            TestScheduler.instance().sync_task(instance)
        except Exception as exc:
            logger.exception("更新调度任务后同步失败: task_id=%s", instance.id)
            raise ValidationError({"msg": f"任务已更新，但调度同步失败: {exc}"})

    def perform_destroy(self, instance):
        instance.status = ScheduledTask.STATUS_DISABLED
        instance.is_deleted = True
        instance.save(update_fields=["status", "is_deleted", "update_time"])
        TestScheduler.instance().remove_task(instance.id)

    @action(detail=True, methods=["post"], url_path="pause")
    def pause(self, request, pk=None):
        task = self.get_object()
        task.status = ScheduledTask.STATUS_PAUSED
        task.save(update_fields=["status", "update_time"])
        TestScheduler.instance().sync_task(task)
        return Response({"msg": "任务已暂停"})

    @action(detail=True, methods=["post"], url_path="resume")
    def resume(self, request, pk=None):
        task = self.get_object()
        task.status = ScheduledTask.STATUS_ACTIVE
        task.save(update_fields=["status", "update_time"])
        TestScheduler.instance().sync_task(task)
        return Response({"msg": "任务已恢复"})

    @action(detail=True, methods=["post"], url_path="trigger")
    def trigger(self, request, pk=None):
        task = self.get_object()
        execute_scheduled_task(task.id)
        return Response({"msg": "任务已手动触发"})


class ScheduledTaskLogViewSet(BaseModelViewSet):
    queryset = ScheduledTaskLog.objects.select_related("scheduled_task").all()
    serializer_class = ScheduledTaskLogSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        scheduled_task = self.request.query_params.get("scheduled_task")
        status_value = (self.request.query_params.get("status") or "").strip()
        message_kw = (self.request.query_params.get("message") or "").strip()
        if scheduled_task not in (None, ""):
            try:
                task_id = int(scheduled_task)
            except (TypeError, ValueError):
                return qs.none()
            qs = qs.filter(scheduled_task_id=task_id)
        if status_value:
            qs = qs.filter(status=status_value)
        if message_kw:
            qs = qs.filter(message__icontains=message_kw)
        return qs.order_by("-trigger_time", "-id")
