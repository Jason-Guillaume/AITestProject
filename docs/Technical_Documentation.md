# AITestProject 技术文档（逆向还原）

本文档遵循需求中规定的 **五大维度**，对项目的每个业务子模块进行 **底层运行逻辑、数据模型、前后端交互、UI 表现与逻辑、异常处理** 的深度剖析。

---

## 1. AITestProduct（Django 主后端）

### 1.1 底层运行逻辑
- `manage.py` 启动入口，调用 `django.core.management.execute_from_command_line`。
- `AITestProduct/settings.py` 完成全局配置：数据库（`sqlite3`）、缓存（本地 `redis`）、Celery broker、已安装的 APP 列表等。
- `urls.py` 按模块 (`defect`, `execution`, `project`, `user`, `assistant` 等) 挂载 `DefaultRouter`，生成 RESTful 路由。
- 中间件 `common.middleware` 实现统一异常捕获、请求日志、跨域、身份认证（基于 JWT）。
- Celery worker (`celery.py`) 使用 `redis` 作为 broker/结果后端，负责异步任务（如 RAG 向量索引、报告生成）。

### 1.2 数据模型定义 (示例)
| 表名 | 关键字段 | 说明 |
|------|----------|------|
| `auth_user`（在 `user/models.py`） | `id`, `username`, `password`, `is_staff`, `is_superuser` | 用户身份、权限控制 |
| `test_defect`（在 `defect/models.py`） | `defect_no`, `defect_name`, `severity`, `priority`, `status`, `handler_id`, `module_id` | 缺陷基本信息 |
| `project_releaseplan`（在 `project/models.py`） | `version_no`, `status` | 版本计划 |

> **显式前端展示字段**：`defect_no`, `defect_name`, `severity`, `priority`, `status`, `handler_name` 等。
> **后端静默维护字段**：`id`, `is_deleted`, `create_time`, `update_time` 等。

### 1.3 前后端交互 (API Interaction)
| 前端动作 | 方法 | URL | 请求体 | 响应结构 |
|----------|------|-----|--------|----------|
| 创建缺陷 | POST | `/api/defects/` | `{defect_no, defect_name, severity, priority, handler, module, ...}` | `{id, defect_no, ...}`（`201 Created`） |
| 查询缺陷列表 | GET | `/api/defects/` | `?status=1&page=1&page_size=20` | `{count, next, previous, results:[{...}]}` |

### 1.4 UI 表现与逻辑
- 前端 Vue 组件位于 `frontend/src/views/DefectList.vue`、`DefectEdit.vue`。
- 使用 Element‑Plus `el-table`、`el-dialog` 实现列表展示与编辑弹窗。
- 主题采用 **赛博朋克蓝**：全局 CSS 变量 `--primary:#0ff`, `--bg:#111`。

### 1.5 异常处理
- **后端**：`common.exception.ApiException` 捕获业务错误，统一返回 `{code, message, detail}` 并写入 `server_logs/`。
- **前端**：`api.interceptors.response` 统一拦截错误码，使用 `ElMessage.error(msg)` 展示；401 时自动跳转登录页。

---

## 2. frontend（Vue 3 SPA）

### 2.1 底层运行逻辑
- 使用 Vite 构建，入口 `main.ts` 挂载根组件 `App.vue`，注册路由 `router/index.ts` 与 Pinia 状态管理。
- 所有业务页面通过 `router` 按模块懒加载 (`defineAsyncComponent`)。
- UI 组件库为 Element‑Plus v2，主题在 `src/styles/theme.scss` 中覆盖实现 **赛博朋克蓝** 风格。

### 2.2 前端状态模型
| Store | 关键状态字段 | 说明 |
|-------|--------------|------|
| `defectStore` | `list`, `total`, `currentPage`, `filters` | 缺陷列表分页、过滤 |
| `userStore`   | `profile`, `token`, `permissions` | 登录用户信息 |

### 2.3 前后端交互
- `src/api/index.ts` 使用 `axios.create({ baseURL: '/api/' })`，在请求拦截器加入 `Authorization: Bearer <token>`。
- 示例：`defectStore.fetchList` 调用 `api.get('/defects/', { params: filters })`，返回分页结构直接映射到 Pinia 状态。

### 2.4 UI 表现与逻辑
- **列表页** `DefectList.vue` 使用 `el-table` 展示缺陷字段，`el-button` 触发新增/编辑弹窗。
- **编辑弹窗** `DefectForm.vue` 包含 `el-form` 表单验证，提交后调用 `defectStore.save(form)`，成功后关闭弹窗并刷新列表。

### 2.5 异常处理
- `api.interceptors.response` 捕获非 2xx 响应，统一弹出错误信息；401 时调用 `userStore.logout()` 并路由至 `/login`。

---

## 3. common（公共库）

### 3.1 底层运行逻辑
- `common/models.py` 定义 `BaseModel`（`id`, `is_deleted`, `create_time`, `update_time`），所有业务模型继承该基类。
- `common/serialize.py` 提供 `BaseModelSerializers`，统一 `create_time`, `update_time` 为只读字段。
- `common/middleware.py` 实现统一异常捕获、请求日志、跨域、限流等功能。

### 3.2 数据模型定义
| 类名 | 字段 | 说明 |
|------|------|------|
| `BaseModel` | `id`, `is_deleted`, `create_time`, `update_time` | 公共基类 |

### 3.3 前后端交互
- 此层不直接提供 API，后端模型/序列化器被各业务模块使用，前端通过业务模块的 API 间接访问。

### 3.4 UI 表现与逻辑
- 前端无 UI，唯一 UI 相关是 `common/components/Loading.vue`（全局加载指示器），在路由守卫中统一显示/隐藏。

### 3.5 异常处理
- `common.exception.ApiException` 继承 `rest_framework.exceptions.APIException`，返回统一结构 `{code, message, detail}`，中间件捕获后记录至 `server_logs/common_exception.log`。

---

## 4. defect（缺陷管理）

### 4.1 底层运行逻辑
1. **视图路由**：`defect/views.py` 中的 `TestDefectViewSet` 通过 `router.register('defects', TestDefectViewSet)` 注册 RESTful 路由。
2. **ViewSet 方法**：默认实现 `list`, `retrieve`, `create`, `update`, `partial_update`, `destroy`；自定义操作 `recycle`, `restore`, `bulk_soft_delete`, `bulk_hard_delete` 通过 `@action` 暴露为 `/defects/recycle/` 等端点。
3. **权限校验**：`permission_classes = [IsAuthenticated, DefectPermission]`，检查用户是否拥有 `defect.manage` 权限。
4. **事务管理**：创建/更新使用 `@transaction.atomic` 确保外键一致性。

### 4.2 数据模型定义
```python
class TestDefect(BaseModel):
    defect_no = models.CharField(max_length=255, verbose_name="缺陷编号")
    defect_name = models.CharField(max_length=255, verbose_name="缺陷标题")
    release_version = models.ForeignKey('project.ReleasePlan', on_delete=models.SET_NULL, null=True, related_name='defects')
    severity = models.IntegerField(choices=[(1,"致命"),(2,"严重"),(3,"一般"),(4,"建议")], default=3)
    priority = models.IntegerField(choices=[(1,"高"),(2,"中"),(3,"低")], default=2)
    status = models.IntegerField(choices=[(1,"新缺陷"),(2,"处理中"),(3,"已拒绝"),(4,"已关闭")], default=1)
    handler = models.ForeignKey('user.User', on_delete=models.PROTECT, related_name='handled_defects')
    module = models.ForeignKey('testcase.TestModule', on_delete=models.SET_NULL, null=True, blank=True, related_name='defects')
    defect_content = models.TextField(null=True, blank=True)
    reproduction_steps = models.JSONField(default=list, blank=True)
    attachments = models.JSONField(default=list, blank=True)
    environment = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        db_table = 'test_defect'
        constraints = [UniqueConstraint(fields=['defect_no','is_deleted'], name='uniq_test_defect_no_is_deleted')]
```

### 4.3 前后端交互 (API Interaction)
| 动作 | 方法 | URL | 请求体 | 响应 |
|------|------|-----|--------|------|
| 创建缺陷 | POST | `/api/defects/` | `{defect_no, defect_name, severity, priority, handler, module, ...}` | `201 Created` 返回完整对象 |
| 查询列表 | GET | `/api/defects/` | `?page=1&page_size=20&status=1` | `200` 分页结构 |
| 更新缺陷 | PATCH | `/api/defects/{id}/` | `{status, handler, ...}` | `200` 更新后对象 |
| 软删除 | POST | `/api/defects/{id}/recycle/` | – | `204 No Content` |
| 批量软删 | POST | `/api/defects/bulk_soft_delete/` | `{ids:[1,2,3]}` | `204` |

### 4.4 UI 表现与逻辑
- **列表页面** `frontend/src/views/DefectList.vue` 使用 `el-table` 展示缺陷，复选框支持批量操作。
- **编辑弹窗** `DefectForm.vue` 包含 `el-form`，字段映射序列化器 `read_only_fields`（如 `creator`, `create_time` 为只读）。
- **全局主题**：通过 CSS 变量 `--primary:#0ff`, `--bg:#111` 实现暗色赛博朋克风格。

### 4.5 异常处理
- **后端**：`TestDefectSerializer.validate_defect_no`、`validate` 抛出 `ValidationError` → 统一返回 `400`，结构 `{field: [msg]}`。
- **前端**：`api.interceptors.response` 捕获错误，使用 `ElMessage.error` 展示；401 时触发登录跳转。

---

## 5. execution（用例执行引擎）

### 5.1 底层运行逻辑
1. **入口 & 调度**：`execution/scheduler.py` 中的 `TestScheduler` 在项目启动时通过 Celery beat 注册，根据 `ScheduledTask` 表的 `cron_expression` 创建/更新调度任务。
2. **任务执行**：`execution/tasks.py`（以及 `tasks_k6.py`）定义了 `run_execution_task`、`run_k6_load_test` 等 Celery 任务。实际执行由 `execution/engine.py` 中的 `APIExecutor` 完成，负责构造请求 payload、清理 headers/body（`_sanitize_*`），并使用 `requests` 发起 HTTP 调用。
3. **实时日志**：`execution/consumers.py` 实现 `K6MetricsConsumer`（基于 `AsyncWebsocketConsumer`），在 WebSocket 建立后接受 Celery 通过 `channel_layer.group_send` 推送的指标，前端通过 `DashboardStreamView`（`views.py`）进行 Server‑Sent Events（SSE）转发。
4. **WebSocket 中间件**：`execution/middleware_ws.py` 提供 `TokenAuthMiddleware`，在握手阶段解析 JWT 并注入 `scope['user']`，供后续权限校验使用。
5. **模型持久化**：所有执行相关模型均继承 `common.models.BaseModel`，统一拥有 `create_time`, `update_time`, `is_deleted` 等字段。

### 5.2 数据模型定义（摘录）
```python
class TestPlan(BaseModel):
    plan_name = models.CharField(max_length=255)
    version = models.ForeignKey('project.ReleasePlan', on_delete=models.PROTECT)
    environment = models.CharField(max_length=255)
    # 统计字段: req_count, case_count, coverage_rate, pass_rate, defect_count

class TestReport(BaseModel):
    plan = models.ForeignKey(TestPlan, on_delete=models.PROTECT, related_name='reports')
    report_name = models.CharField(max_length=255)
    request_payload = models.JSONField(null=True, blank=True)
    response_payload = models.JSONField(null=True, blank=True)
    trace_id = models.CharField(max_length=36, blank=True)
    execution_log_id = models.PositiveIntegerField(null=True, blank=True)

class PerfTask(BaseModel):
    task_id = models.CharField(max_length=32, unique=True)
    scenario = models.CharField(choices=[('jmeter','JMeter'),('locust','Locust')])
    status = models.CharField(choices=[('pending','待执行'),('running','运行中'),('completed','已完成'),('failed','失败')], default='pending')
    concurrency = models.PositiveIntegerField(default=1)
    duration = models.CharField(max_length=32, default='10m')

class K6LoadTestSession(BaseModel):
    run_id = models.UUIDField(default=uuid.uuid4, unique=True)
    status = models.CharField(choices=[('pending','待开始'),('generating','生成脚本中'),('running','压测运行中'),('completed','已完成'),('failed','失败')], default='pending')
    test_case_ids = models.JSONField(default=list)
    script_body = models.TextField(blank=True)
    summary = models.JSONField(null=True, blank=True)

class ScheduledTask(BaseModel):
    name = models.CharField(max_length=128)
    cron_expression = models.CharField(max_length=64)
    status = models.CharField(choices=[('active','启用'),('paused','暂停'),('disabled','禁用')], default='active')
    environment = models.ForeignKey('testcase.TestEnvironment', on_delete=models.PROTECT)
    test_cases = models.ManyToManyField('testcase.TestCase')

class ExecutionTask(BaseModel):
    task_name = models.CharField(max_length=255)
    method = models.CharField(max_length=16, default='GET')
    url = models.CharField(max_length=2048)
    headers = models.JSONField(default=dict)
    body = models.JSONField(null=True, blank=True)
    status = models.CharField(choices=[('pending','待执行'),('running','执行中'),('completed','完成'),('failed','失败')], default='pending')
    report = models.JSONField(default=dict)
    # 关联项目、Celery task id、错误信息等
```

> **前端展示字段**：`plan_name`, `status`, `environment`, `started_at`, `finished_at`（在列表/看板中使用）。
> **后端静默字段**：`id`, `is_deleted`, `create_time`, `update_time`, `celery_task_id`（内部调度使用）。

### 5.3 前后端交互 (API Interaction)
| 动作 | 方法 | URL | 请求体 | 响应 |
|------|------|-----|--------|------|
| 创建执行计划 | POST | `/api/test_plans/` | `{plan_name, version, environment, testers, ...}` | `201` 返回计划对象 |
| 触发一次执行 | POST | `/api/execution_tasks/{id}/run/` | – | `202` 返回任务 ID，Celery 异步执行 |
| 查询执行任务 | GET | `/api/execution_tasks/` | `?status=running&page=1` | 分页结构，包含 `report` 快照 |
| 实时 K6 指标 | WebSocket | `ws://<host>/ws/k6_metrics/<run_id>/` | – | 服务器推送 `{metrics, summary}` JSON |
| 暂停/恢复调度任务 | POST | `/api/scheduled_tasks/{id}/pause/` | – | `200` 返回更新后状态 |

**后端校验（`serialize.py`）**：
- `TestPlanSerializer` 校验 `plan_name` 唯一性、`testers` 必须为有效用户。
- `PerfTaskSerializer.validate_concurrency`、`validate_duration` 确保业务合理范围。
- `ScheduledTaskSerializer.validate_cron_expression` 使用 `croniter` 验证合法性。

### 5.4 UI 表现与逻辑
- 前端页面位于 `frontend/src/views/ExecutionDashboard.vue` 与 `K6Monitor.vue`（基于 Element‑Plus `el-table`、`el-progress`、`el-tabs`）。
- **执行列表**：`ExecutionList.vue` 调用 `executionStore.fetchList`，展示计划、状态、开始/结束时间、进度条。
- **实时监控**：`K6Monitor.vue` 在 `mounted` 时创建 WebSocket 连接到 `ws://.../k6_metrics/<run_id>/`，收到指标后更新 `el-card` 中的 CPU、RPS、Latency 图表（Chart.js）。
- **调度管理**：`ScheduledTaskList.vue` 支持新建、编辑 Cron、立即触发、暂停/恢复，使用 `api.post('/scheduled_tasks/', ...)`。
- **主题**：全局 CSS 变量 `--primary:#0ff`, `--bg:#111` 确保赛博朋克蓝调统一。

### 5.5 异常处理
- **后端**：`APIExecutor` 在网络错误、超时或非 2xx 响应时抛出自定义 `ExecutionError`，捕获后写入 `ExecutionTask.report`，状态设为 `failed` 并记录 `error_message`。Celery 任务若未捕获异常，`@shared_task` 会自动将状态设为 `failed` 并记录堆栈至 `server_logs/execution_error.log`。
- **前端**：`api.interceptors.response` 统一捕获 `500/400`，使用 `ElMessage.error(err.response.data.message || '执行错误')`。WebSocket 在 `onerror` 时弹出提示并尝试指数退避重连。

---

## 6. project（项目/发布计划管理）

（后续章节将在后续补充 `project`、`assistant`、`testcase` 等模块）
