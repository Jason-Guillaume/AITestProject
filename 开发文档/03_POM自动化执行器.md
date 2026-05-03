# POM 自动化执行器模块（Case‑01）

## I. 业务深度逻辑 (Business Logic Deep Dive)
1. **七层 POM 结构**
   - **BaseLayer** (`common.models.BaseModel`) 提供 `created_at/updated_at/is_deleted` 字段。
   - **PageLayer** (`assistant.ui_element_models.UIPage`) 保存页面 URL 与所属模块关联。
   - **ElementLayer** (`assistant.ui_element_models.UIPageElement`) 保存 CSS/XPath 选择器。
   - **TestCaseLayer** (`assistant.ui_element_models.UITestCase`) 归属页面，聚合多个 **Step**。
   - **StepLayer** (`assistant.ui_element_models.UIActionStep`) 描述单一步骤：`action_type`（click、input、assert、wait、screenshot），`target`（元素 selector），`value`（输入或期望值）。
   - **ScriptLayer** (`assistant.models.UIScriptUpload`) 保存压缩 UI 脚本包及激活标记。
   - **ExecutionLayer** (`assistant.models.UIScriptExecution`) 记录执行状态、日志、结果。

2. **执行流程**
   - 前端调用 `POST /api/ui/testcase/{id}/execute/`（`UITestCaseViewSet.execute`），后端创建 `UIScriptExecution` 实例并触发 Celery 任务 `run_ui_script_task(exec_id)`。
   - 任务读取对应 `UITestCase`，通过 **PageObjectFactory** 动态生成页面对象（基于 Selenium 或 Playwright），遍历 `steps` 并使用映射表执行：
     ```python
     ACTION_MAP = {
         "click": lambda driver, selector: driver.find_element(*selector).click(),
         "input": lambda driver, selector, val: driver.find_element(*selector).send_keys(val),
         "assert": lambda driver, selector, val: assert driver.find_element(*selector).text == val,
         "wait": lambda driver, sec: time.sleep(sec),
         "screenshot": lambda driver, path: driver.save_screenshot(path),
     }
     ```
   - 每一步完成后写入 `UIScriptExecution.log`，并通过 **Django Channels** 推送至前端 WebSocket（`UIExecutionConsumer`），实现实时日志展示。
   - 任务使用 `@shared_task(bind=True, max_retries=3, default_retry_delay=60)` 捕获 Selenium 异常（如 `NoSuchElementException`、`TimeoutException`），自动重试；最终状态 `success`、`failed` 写回 `status` 字段。

## II. 数据库全解析 (Database Schema & Visibility)

| 表 | 关键字段 | 类型 | 空/默认 | 可见性 |
|---|----------|------|----------|--------|
| `ui_module` | `name` | VARCHAR(100) | 否 | 前端可见 |
| | `description` | TEXT | 可空 | 前端可见 |
| `ui_page` | `module_id` (FK) | INT | 否 | 前端可见 |
| | `url` | URLField | 否 | 前端可见 |
| `ui_page_element` | `page_id` (FK) | INT | 否 | 前端可见 |
| | `selector` | VARCHAR(255) | 否 | 前端可见 |
| `ui_testcase` | `page_id` (FK) | INT | 否 | 前端可见 |
| | `name` | VARCHAR(255) | 否 | 前端可见 |
| `ui_action_step` | `test_case_id` (FK) | INT | 否 | 前端可见 |
| | `action_type` | VARCHAR(50) | 否 | 前端可见 |
| | `target` | VARCHAR(255) | 否 | 前端可见 |
| | `value` | TEXT | 可空 | 前端可见 |
| `ui_script_upload` | `file` | FileField | 否 | 前端可见（上传） |
| | `is_active` | BOOLEAN | False | 前端可见 |
| `ui_script_execution` | `script_id` (FK) | INT | 否 | 前端可见 |
| | `status` | VARCHAR(20) | `pending` | 前端可见 |
| | `log` | TEXT | 可空 | 前端可见 |

> **字段可见性**：业务字段对前端开放；审计字段 `created_at/updated_at/is_deleted` 为只读；`log` 与 `status` 只能通过专属 API 读取或更新。

## III. 交互生命周期 (Interaction Lifecycle)

| 前端动作 | API Endpoint | 请求示例 | 后端处理 | 响应 |
|----------|--------------|----------|----------|------|
| 创建页面 | `POST /api/ui/pages/` | `{ "module":1, "url":"https://example.com/home" }` | `UIPageSerializer.save()` 写库 | `ApiResponse.success(message='页面创建成功')` |
| 添加元素 | `POST /api/ui/elements/` | `{ "page":3, "selector":"#login-btn" }` | `UIPageElementSerializer.save()` | 同上 |
| 编写用例 | `POST /api/ui/testcases/` | `{ "page":3, "name":"登录流程", "steps":[{"action_type":"click","target":"#login-btn"},{"action_type":"input","target":"#username","value":"admin"}] }` | `UITestCaseSerializer` 解析 `steps`，批量创建 `UIActionStep` | `ApiResponse.success(message='用例创建成功')` |
| 执行用例 | `POST /api/ui/testcases/{id}/execute/` | — | 创建 `UIScriptExecution` → 调用 Celery `run_ui_script_task` | `ApiResponse.success({"execution_id": exec_id})` |
| 实时日志 | WebSocket `ws://<host>/ws/ui-execution/<exec_id>/` | — | `UIExecutionConsumer` 订阅对应 group，`channel_layer.group_send` 推送日志行 | 前端实时显示日志 |
| 获取结果 | `GET /api/ui/executions/{exec_id}/` | — | 返回 `status`、`log`、`result`（如截图 URL） | `ApiResponse.success(data={...})` |

## IV. 前端呈现与 UI 规范 (Frontend & UI Spec)
- **页面列表**：Ant Design Table，列 `名称、URL、所属模块、操作（编辑/删除）`，行背景 `#0a0f1f`，选中高亮 `#1f8ef1`。
- **用例编辑器**：卡片式布局，左侧 **步骤树** (`a-tree`)，右侧 **属性表单** (`a-form`)，整体采用 **Cyberpunk Blue** 主题：卡片阴影 `0 0 12px #00bfff`，输入框边框 `1px solid #1f8ef1`。
- **执行面板**：Modal 包含进度条 (`a-progress`) 与实时日志滚动区，日志文字白色、背景 `#001220`，`white-space: pre-wrap` 保持格式。
- **截图预览**：执行成功返回图片 URL，前端使用 `<img :src="url" class="screenshot" />`，图片加 `border: 2px solid #00bfff`。
- **可访问性**：所有交互提供 `aria-label`，键盘可 Tab 导航，对比度 ≥ 4.5:1。

## V. 模块拆分颗粒度 (Module Granularity)

| 子模块 | 职责 |
|--------|------|
| **Model Layer** (`assistant.ui_element_models`) | 定义七层 ORM，必要时使用 `EncryptedFieldsMixin`（如脚本加密） |
| **Serializer Layer** (`assistant.ui_element_serializers`) | 各模型序列化，`UITestCaseSerializer` 包含 `steps` 列表 |
| **ViewSet Layer** (`assistant.ui_element_views`) | 标准 CRUD + 自定义 `tree`、`execute` Action |
| **Executor Service** (`assistant.services.ui_executor`) | PageObjectFactory、步骤映射、异常包装 |
| **Celery Task** (`assistant.tasks`) | `run_ui_script_task`，负责异步执行、日志写入、重试策略 |
| **WebSocket Consumer** (`assistant.consumers`) | `UIExecutionConsumer` 实时推送日志、状态变更 |
| **Frontend Module** (`frontend/src/pages/UIAutomation.vue`) | 页面列表、用例编辑、执行弹窗、实时日志组件 |
