import uuid

from django.db import models
from common.models import BaseModel


class TestPlan(BaseModel):
    plan_name = models.CharField(max_length=255, verbose_name="计划名称")
    iteration = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="迭代"
    )
    version = models.ForeignKey(
        "project.ReleasePlan",
        on_delete=models.PROTECT,
        related_name="test_plans",
        verbose_name="关联版本",
    )
    environment = models.CharField(max_length=255, verbose_name="测试环境")
    req_count = models.IntegerField(default=0, verbose_name="需求数")
    case_count = models.IntegerField(default=0, verbose_name="用例数")
    coverage_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, verbose_name="覆盖率"
    )
    plan_status = models.IntegerField(
        choices=[(1, "未开始"), (2, "进行中"), (3, "已完成")],
        default=1,
        verbose_name="计划状态",
    )
    pass_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, verbose_name="通过率"
    )
    defect_count = models.IntegerField(default=0, verbose_name="缺陷数")

    testers = models.ManyToManyField(
        "user.User", related_name="participated_plans", verbose_name="测试人员"
    )
    start_date = models.DateTimeField(null=True, blank=True, verbose_name="开始日期")
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="结束日期")

    class Meta:
        db_table = "test_plan"


class TestReport(BaseModel):
    plan = models.ForeignKey(
        TestPlan,
        on_delete=models.PROTECT,
        related_name="reports",
        verbose_name="关联测试计划",
    )
    report_name = models.CharField(max_length=255, verbose_name="报告名称")
    create_method = models.IntegerField(
        choices=[(1, "新建生成"), (2, "定期生成")], default=1, verbose_name="生成方式"
    )
    environment = models.CharField(max_length=255, verbose_name="测试环境")

    req_count = models.IntegerField(default=0, verbose_name="需求数")
    case_count = models.IntegerField(default=0, verbose_name="用例数")
    coverage_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, verbose_name="覆盖率"
    )
    pass_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, verbose_name="通过率"
    )
    defect_count = models.IntegerField(default=0, verbose_name="缺陷数")
    start_time = models.DateTimeField(verbose_name="统计开始时间")
    end_time = models.DateTimeField(verbose_name="统计结束时间")

    trace_id = models.CharField(
        max_length=36,
        blank=True,
        default="",
        verbose_name="关联执行追踪ID",
        help_text="与 api_execution_log.trace_id 对应，便于报告与单次执行闭环",
    )
    execution_log_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="关联执行日志ID",
        help_text="testcase.ExecutionLog 主键（无跨库外键，仅存储引用）",
    )
    request_payload = models.JSONField(
        null=True,
        blank=True,
        verbose_name="请求快照",
        help_text="执行时真实请求 JSON 快照（与日志表一致便于报表展示）",
    )
    response_payload = models.JSONField(
        null=True,
        blank=True,
        verbose_name="响应快照",
        help_text="服务端返回原始数据摘要",
    )
    project = models.ForeignKey(
        "project.TestProject",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="test_reports",
        verbose_name="关联项目(冗余)",
        help_text="用于数据权限与查询加速；值来自 plan.version.project",
    )

    class Meta:
        db_table = "test_report"


class PerfTask(BaseModel):
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_PENDING = "pending"

    STATUS_CHOICES = [
        (STATUS_PENDING, "待执行"),
        (STATUS_RUNNING, "运行中"),
        (STATUS_COMPLETED, "已完成"),
        (STATUS_FAILED, "失败"),
    ]

    SCENARIO_JMETER = "jmeter"
    SCENARIO_LOCUST = "locust"
    SCENARIO_CHOICES = [
        (SCENARIO_JMETER, "JMeter"),
        (SCENARIO_LOCUST, "Locust"),
    ]

    task_id = models.CharField(max_length=32, unique=True, verbose_name="任务ID")
    task_name = models.CharField(max_length=255, verbose_name="任务名称")
    scenario = models.CharField(
        max_length=32, choices=SCENARIO_CHOICES, verbose_name="测试场景"
    )
    concurrency = models.PositiveIntegerField(default=1, verbose_name="并发数")
    duration = models.CharField(max_length=32, default="10m", verbose_name="持续时间")
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="任务状态",
    )
    executor = models.CharField(max_length=64, blank=True, verbose_name="执行人")

    class Meta:
        db_table = "perf_task"
        ordering = ("-create_time",)


class K6LoadTestSession(BaseModel):
    """
    业务链路 API 用例转 k6 压测的一次会话：生成脚本、Celery 异步执行、Channels 实时指标。
    """

    STATUS_PENDING = "pending"
    STATUS_GENERATING = "generating"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "待开始"),
        (STATUS_GENERATING, "生成脚本中"),
        (STATUS_RUNNING, "压测运行中"),
        (STATUS_COMPLETED, "已完成"),
        (STATUS_FAILED, "失败"),
    ]

    run_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="运行 UUID",
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="状态",
    )
    test_case_ids = models.JSONField(
        default=list, verbose_name="API 用例 ID 列表(有序)"
    )
    vus = models.PositiveIntegerField(default=5, verbose_name="虚拟用户数")
    duration = models.CharField(
        max_length=32, default="30s", verbose_name="持续时间(k6 格式)"
    )
    use_ai = models.BooleanField(default=True, verbose_name="是否使用大模型生成脚本")
    target_base_url = models.CharField(
        max_length=2048,
        blank=True,
        default="",
        verbose_name="目标 Base URL",
        help_text="用于拼接相对路径的 API 地址；留空则要求用例中均为绝对 URL",
    )
    script_rel_path = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="脚本相对路径",
        help_text="相对于 MEDIA_ROOT 的 k6 脚本路径",
    )
    script_body = models.TextField(
        blank=True, default="", verbose_name="生成的脚本内容快照"
    )
    summary = models.JSONField(
        null=True, blank=True, verbose_name="k6 summary-export JSON"
    )
    error_message = models.TextField(blank=True, default="", verbose_name="错误信息")
    celery_task_id = models.CharField(
        max_length=64, blank=True, default="", verbose_name="Celery 任务 ID"
    )
    generation_source = models.CharField(
        max_length=32,
        blank=True,
        default="",
        verbose_name="脚本来源",
        help_text="ai / template",
    )

    class Meta:
        db_table = "k6_load_test_session"
        ordering = ("-create_time",)


class ScheduledTask(BaseModel):
    """定时调度任务定义。"""

    STATUS_ACTIVE = "active"
    STATUS_PAUSED = "paused"
    STATUS_DISABLED = "disabled"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "启用"),
        (STATUS_PAUSED, "暂停"),
        (STATUS_DISABLED, "禁用"),
    ]

    LAST_SUCCESS = "success"
    LAST_FAILED = "failed"
    LAST_PARTIAL = "partial"
    LAST_IDLE = "idle"
    LAST_STATUS_CHOICES = [
        (LAST_SUCCESS, "成功"),
        (LAST_FAILED, "失败"),
        (LAST_PARTIAL, "部分成功"),
        (LAST_IDLE, "未执行"),
    ]

    name = models.CharField(max_length=128, verbose_name="任务名称")
    cron_expression = models.CharField(max_length=64, verbose_name="Cron 表达式")
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        verbose_name="任务状态",
    )
    job_id = models.CharField(max_length=128, unique=True, verbose_name="调度器任务ID")
    environment = models.ForeignKey(
        "testcase.TestEnvironment",
        on_delete=models.PROTECT,
        related_name="scheduled_tasks",
        verbose_name="执行环境",
    )
    test_cases = models.ManyToManyField(
        "testcase.TestCase",
        related_name="scheduled_tasks",
        verbose_name="关联用例",
        blank=True,
    )
    next_run_time = models.DateTimeField(
        null=True, blank=True, verbose_name="下次执行时间"
    )
    last_run_time = models.DateTimeField(
        null=True, blank=True, verbose_name="最近执行时间"
    )
    last_status = models.CharField(
        max_length=16,
        choices=LAST_STATUS_CHOICES,
        default=LAST_IDLE,
        verbose_name="最近执行状态",
    )
    last_message = models.CharField(
        max_length=255, blank=True, default="", verbose_name="最近执行摘要"
    )

    class Meta:
        db_table = "scheduled_task"
        ordering = ("-create_time",)


class ScheduledTaskLog(BaseModel):
    """调度任务执行日志。"""

    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_PARTIAL = "partial"
    STATUS_CHOICES = [
        (STATUS_RUNNING, "执行中"),
        (STATUS_SUCCESS, "成功"),
        (STATUS_FAILED, "失败"),
        (STATUS_PARTIAL, "部分成功"),
    ]

    scheduled_task = models.ForeignKey(
        ScheduledTask,
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name="调度任务",
    )
    trigger_time = models.DateTimeField(verbose_name="触发时间")
    start_time = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="结束时间")
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_RUNNING,
        verbose_name="执行状态",
    )
    message = models.CharField(
        max_length=255, blank=True, default="", verbose_name="执行摘要"
    )
    detail = models.JSONField(default=dict, blank=True, verbose_name="执行明细")

    class Meta:
        db_table = "scheduled_task_log"
        ordering = ("-create_time",)


class ExecutionTask(BaseModel):
    """API 测试执行任务。"""

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "待执行"),
        (STATUS_RUNNING, "执行中"),
        (STATUS_COMPLETED, "执行完成"),
        (STATUS_FAILED, "执行失败"),
    ]

    task_name = models.CharField(max_length=255, verbose_name="任务名称")
    method = models.CharField(max_length=16, default="GET", verbose_name="请求方法")
    url = models.CharField(max_length=2048, verbose_name="请求URL")
    headers = models.JSONField(default=dict, blank=True, verbose_name="请求头")
    body = models.JSONField(null=True, blank=True, verbose_name="请求体")
    timeout_seconds = models.PositiveIntegerField(
        default=30, verbose_name="请求超时(秒)"
    )
    expected_status = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="期望HTTP状态码"
    )
    expected_body_contains = models.CharField(
        max_length=512, blank=True, default="", verbose_name="期望响应体包含"
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="执行状态",
    )
    started_at = models.DateTimeField(
        null=True, blank=True, verbose_name="开始执行时间"
    )
    finished_at = models.DateTimeField(
        null=True, blank=True, verbose_name="结束执行时间"
    )
    duration_ms = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="执行耗时(ms)"
    )
    celery_task_id = models.CharField(
        max_length=64, blank=True, default="", verbose_name="Celery任务ID"
    )
    error_message = models.TextField(blank=True, default="", verbose_name="错误信息")
    report = models.JSONField(default=dict, blank=True, verbose_name="执行报告")
    project = models.ForeignKey(
        "project.TestProject",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="execution_tasks",
        verbose_name="关联项目(冗余)",
        help_text="用于数据权限控制；独立任务可为空或由创建时指定",
    )

    class Meta:
        db_table = "execution_task"
        ordering = ("-create_time",)


class TestQualityMetric(BaseModel):
    """测试质量指标快照。"""

    METRIC_DEFECT_DENSITY = "defect_density"
    METRIC_PASS_RATE = "pass_rate"
    METRIC_REQUIREMENT_COVERAGE = "requirement_coverage"
    METRIC_CHOICES = [
        (METRIC_DEFECT_DENSITY, "缺陷密度"),
        (METRIC_PASS_RATE, "用例通过率"),
        (METRIC_REQUIREMENT_COVERAGE, "需求覆盖率"),
    ]

    metric_date = models.DateField(verbose_name="指标日期")
    metric_type = models.CharField(
        max_length=64, choices=METRIC_CHOICES, verbose_name="指标类型"
    )
    metric_value = models.DecimalField(
        max_digits=12, decimal_places=4, verbose_name="指标值"
    )
    dimension = models.JSONField(default=dict, blank=True, verbose_name="维度信息")

    class Meta:
        db_table = "test_quality_metric"
        ordering = ("-metric_date", "-id")
        indexes = [
            models.Index(fields=["metric_date", "metric_type"]),
        ]


class ApiScenario(BaseModel):
    """
    API 场景（业务链路）：
    - 作为“编排单位”，由多个 TestCase 组成，运行时共享同一变量上下文与 trace_id
    - 绑定 project 以复用数据权限隔离（BaseModelViewSet member scope）
    """

    STRATEGY_ABORT = "abort"
    STRATEGY_CONTINUE = "continue"
    FAILURE_STRATEGY_CHOICES = [
        (STRATEGY_ABORT, "失败中止"),
        (STRATEGY_CONTINUE, "失败继续"),
    ]

    project = models.ForeignKey(
        "project.TestProject",
        on_delete=models.CASCADE,
        related_name="api_scenarios",
        verbose_name="所属项目",
    )
    name = models.CharField(max_length=255, verbose_name="场景名称")
    environment = models.ForeignKey(
        "testcase.TestEnvironment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="api_scenarios",
        verbose_name="默认执行环境",
    )
    default_variables = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="默认变量上下文",
        help_text="场景级初始变量池（可在运行时 overrides 覆盖）",
    )
    failure_strategy = models.CharField(
        max_length=16,
        choices=FAILURE_STRATEGY_CHOICES,
        default=STRATEGY_ABORT,
        verbose_name="失败策略",
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = "api_scenario"
        ordering = ("-create_time",)
        indexes = [
            models.Index(fields=["project", "-create_time"]),
        ]


class ApiScenarioStep(BaseModel):
    """
    场景步骤：引用 TestCase（通常为 API 用例）。
    - 可配置 step_overrides：运行时覆盖 url/headers/body/environment_id/variables/extraction_rules 等
    - extraction_rules：默认提取规则（可被 overrides 覆盖）
    """

    scenario = models.ForeignKey(
        ApiScenario,
        on_delete=models.CASCADE,
        related_name="steps",
        verbose_name="所属场景",
    )
    order = models.PositiveIntegerField(default=1, verbose_name="顺序")
    name = models.CharField(max_length=255, blank=True, default="", verbose_name="步骤名称")
    test_case = models.ForeignKey(
        "testcase.TestCase",
        on_delete=models.PROTECT,
        related_name="scenario_steps",
        verbose_name="关联用例",
    )
    is_enabled = models.BooleanField(default=True, verbose_name="是否启用")
    failure_strategy = models.CharField(
        max_length=16,
        choices=ApiScenario.FAILURE_STRATEGY_CHOICES,
        blank=True,
        default="",
        verbose_name="失败策略(可选覆盖)",
        help_text="留空则继承场景 failure_strategy",
    )
    extraction_rules = models.JSONField(
        default=list,
        blank=True,
        verbose_name="变量提取规则",
        help_text='示例: [{"var_name":"token","source":"body","expression":"$.data.token"}]',
    )
    step_overrides = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="步骤执行覆盖参数",
        help_text="可覆盖 url/method/headers/body/environment_id/variables/extraction_rules 等",
    )

    class Meta:
        db_table = "api_scenario_step"
        ordering = ("order", "id")
        indexes = [
            models.Index(fields=["scenario", "order"]),
            models.Index(fields=["test_case"]),
        ]


class ApiScenarioRun(BaseModel):
    """场景运行记录（一次跑批）。"""

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_PARTIAL = "partial"
    STATUS_CHOICES = [
        (STATUS_PENDING, "待执行"),
        (STATUS_RUNNING, "执行中"),
        (STATUS_SUCCESS, "成功"),
        (STATUS_FAILED, "失败"),
        (STATUS_PARTIAL, "部分失败"),
    ]

    scenario = models.ForeignKey(
        ApiScenario,
        on_delete=models.CASCADE,
        related_name="runs",
        verbose_name="所属场景",
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="运行状态",
    )
    trace_id = models.CharField(
        max_length=36,
        blank=True,
        default="",
        db_index=True,
        verbose_name="trace_id",
    )
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="结束时间")
    duration_ms = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="耗时(ms)"
    )
    environment_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="执行环境ID(快照)",
        help_text="testcase.TestEnvironment 主键（避免跨 app 迁移依赖）",
    )
    initial_variables = models.JSONField(
        default=dict, blank=True, verbose_name="初始变量上下文快照"
    )
    final_variables = models.JSONField(
        default=dict, blank=True, verbose_name="最终变量上下文快照"
    )
    summary = models.JSONField(default=dict, blank=True, verbose_name="汇总")
    celery_task_id = models.CharField(
        max_length=64, blank=True, default="", verbose_name="Celery 任务 ID"
    )
    error_message = models.TextField(blank=True, default="", verbose_name="错误信息")

    class Meta:
        db_table = "api_scenario_run"
        ordering = ("-create_time",)
        indexes = [
            models.Index(fields=["scenario", "-create_time"]),
            models.Index(fields=["trace_id"]),
        ]


class ApiScenarioStepRun(BaseModel):
    """场景步骤运行记录。"""

    STATUS_SKIPPED = "skipped"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_COMPLETED, "执行完成"),
        (STATUS_FAILED, "执行失败"),
        (STATUS_SKIPPED, "已跳过"),
    ]

    run = models.ForeignKey(
        ApiScenarioRun,
        on_delete=models.CASCADE,
        related_name="step_runs",
        verbose_name="所属运行",
    )
    step = models.ForeignKey(
        ApiScenarioStep,
        on_delete=models.PROTECT,
        related_name="runs",
        verbose_name="所属步骤",
    )
    order = models.PositiveIntegerField(default=1, verbose_name="顺序快照")
    test_case_id = models.PositiveIntegerField(verbose_name="用例ID快照")
    execution_log_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="关联 ExecutionLog ID",
        help_text="testcase.ExecutionLog 主键",
    )
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_COMPLETED, verbose_name="状态"
    )
    passed = models.BooleanField(default=False, verbose_name="是否通过")
    extracted_variables = models.JSONField(
        default=dict, blank=True, verbose_name="本步骤提取出的变量"
    )
    message = models.CharField(max_length=255, blank=True, default="", verbose_name="摘要")

    class Meta:
        db_table = "api_scenario_step_run"
        ordering = ("order", "id")
        indexes = [
            models.Index(fields=["run", "order"]),
            models.Index(fields=["test_case_id"]),
        ]
