# 04-API接口与数据交互

## 0. 需求来源与开发动因

- 业务价值摘要：稳定接口契约，缩短联调周期并降低对接风险。
- 业务背景：前后端并行开发与第三方接入场景增加，接口契约需要长期稳定且可查询。
- 现状痛点：字段、鉴权规则和错误码口径不统一，导致联调反复、线上误用和兼容问题。
- 建设目标：建立可维护的 API 规范与数据交互约定，统一对接标准。
- 预期收益：缩短联调周期，降低接口变更带来的回归与兼容风险。

## 1. 接口体系总览

项目后端基于 Django REST Framework（DRF）实现，以 `AITestProduct/urls.py` 为统一入口，将业务按模块拆分到不同子应用。前端通过 `frontend/src/utils/request.js` 统一发起请求，默认 `baseURL="/api"`，并使用 Vite 代理转发到 Django 服务。

### 1.1 主路由映射

| 路由前缀 | 子路由文件 | 说明 |
|------|------|------|
| `/api/user/` | `user/urls.py` | 登录注册、用户中心、组织/角色/用户管理 |
| `/api/project/` | `project/urls.py` | 测试项目、任务、发布计划 |
| `/api/testcase/` | `testcase/urls.py` | 测试模块、用例、步骤、测试方案、测试设计 |
| `/api/environments/` | `testcase/environment_urls.py` | 环境管理独立挂载入口（与 testcase 中 environments ViewSet 对齐） |
| `/api/execution/` | `execution/urls.py` | 测试计划、测试报告、仪表盘聚合 |
| `/api/perf/` | `execution/perf_urls.py` | 性能任务专用入口（按 `task_id` 操作） |
| `/api/defect/` | `defect/urls.py` | 缺陷管理 |
| `/api/assistant/` | `assistant/urls.py` | 助手兼容接口（旧路径） |
| `/api/ai/` | `assistant/ai_urls.py` | AI 连接测试、用例生成（同步/流式） |
| `/api/sys/` | `user/sys_urls.py` | 系统级配置与系统管理员能力（AI 模型配置、系统审计等） |
| `/api/change-requests/` | `user/approval_urls.py` | 敏感信息审批动作接口 |
| `/api/server-logs/` | `server_logs/urls.py` | 服务器日志主机管理、实时查看、AI 诊断、审计、（可选）历史检索与工单 |

补充（全局对账索引）：

- 路由树、扩展 action、前端调用侧入口、以及 WebSocket 路由与鉴权方式，统一以 `开发文档/99-项目全局扫描对账索引.md` 为准。

### 1.3 WebSocket 路由与鉴权（统一约定）

部分模块使用 WebSocket（如 k6 实时指标、服务器日志实时 tail）。当前约定：

- **WS 前缀**：`/ws/*`（开发模式由 `frontend/vite.config.js` 代理到后端）
- **鉴权方式**：querystring 传 token：`?token=<DRF Token>`
- 具体 WS 路由清单见：`开发文档/99-项目全局扫描对账索引.md` §3

### 1.2 前端 API 分层

前端采用“按业务域封装”的 API 模式：

- `frontend/src/api/auth.js`：登录、注册、验证码
- `frontend/src/api/user.js`：用户中心、敏感信息审批流
- `frontend/src/api/project.js`：项目/任务/发布计划（含发布计划「从未执行用例」清单与 CSV 导出）
- `frontend/src/api/testcase.js`：用例与扩展动作（回收站、执行、导入等）
- `frontend/src/api/execution.js`、`perfTask.js`：测试执行与性能任务
- `frontend/src/api/defect.js`：缺陷管理
- `frontend/src/api/assistant.js`、`sysAiConfig.js`：AI 能力与系统配置
- `frontend/src/api/audit.js`：审计事件查询与 CSV 导出（系统管理员）
- `frontend/src/utils/downloadAuthedGet.js`：带 Token 的 GET blob 下载（CSV 等）

---

## 2. 认证、权限与路由守卫

### 2.1 后端认证与权限

`settings.py` 中全局 DRF 配置：

- 默认认证：`TokenAuthentication`
- 默认权限：`IsAuthenticated`

因此，除显式开放接口外（如登录、注册、验证码），所有接口都要求请求头携带：

```http
Authorization: Token <token>
```

### 2.2 前端 Token 注入与失效处理

`request.js` 使用 Axios 拦截器统一处理：

1. 请求前从 `localStorage.token` 注入 `Authorization`
2. 响应 `401` 时清理本地 Token，并跳转 `/login`
3. `5xx` 统一提示“服务异常，请稍后重试”

### 2.3 页面级访问控制

`frontend/src/router/index.js` 的 `beforeEach` 守卫实现：

- 未登录访问非公开路由，重定向到登录页
- 已登录访问登录页，重定向到 `/dashboard`
- 非系统管理员访问系统管理路由（`/system/org`、`/system/role`、`/system/user`、`/system/messages`、`/system/ai-usage`、`/system/audit`）时，重定向到 `/system/message`

---

## 3. 数据交互约定

### 3.1 URL 与方法约定

项目以 DRF `DefaultRouter + ViewSet` 为主，遵循标准 REST 资源风格：

- 列表：`GET /resource/`
- 新建：`POST /resource/`
- 详情：`GET /resource/{id}/`
- 更新：`PATCH /resource/{id}/`
- 删除：`DELETE /resource/{id}/`
- 扩展动作：`POST/GET /resource/{id}/{action}/` 或 `/resource/{action}/`

---

## 9. AI 与用例模块交互（补充）

### 9.1 AI 生成接口回传 run_id

- 同步：`POST /api/ai/generate-cases/` 响应新增 `run_id`
- 流式：`POST /api/ai/generate-cases-stream/` 的 SSE `done` 事件新增 `run_id`

### 9.2 发布计划风险简报（只读）

- `GET /api/project/releases/<id>/risk-brief/?days=7`
  - 用途：按发布计划聚合关联用例数、测试计划状态、缺陷分布、近 N 天关联用例的 `ExecutionLog` 通过/失败；返回 `markdown` 摘要
  - 权限：与 `ReleasePlan` 列表一致的数据范围（项目成员）
- `GET /api/project/releases/<id>/never-executed-cases/?days=7&limit=500`
  - 用途：列出近 N 天窗口内「从未执行」的关联用例（分页上限由 `limit` 控制，最大 5000）
  - 返回：`{ success, days, total, items[] }`（`items` 含 `id/case_name/test_type/module_id/module_name`）
- `GET /api/project/releases/<id>/never-executed-cases/export.csv?days=7&limit=20000`
  - 用途：导出同上窗口的 CSV（流式）；前端下载须使用 blob + `Authorization: Token ...`（参考 `frontend/src/utils/downloadAuthedGet.js`、`frontend/src/api/project.js`）

参考：`开发文档/33-后续功能规划-MVP与安全加固.md` §2

### 9.3 AI 批量导入用例

- `POST /api/testcase/cases/ai-import/`
  - 用途：将 AI 预览结果一次性导入到用例库（事务 + 逐条结果）
  - 关键参数：`project_id/test_type/run_id/default_module_id/items[]`；可选 `strict`、`precheck_overrides`（API+strict 预检与环境变量）
  - 返回：`imported[]/failed[]/skipped`

参考开发文档：
- `开发文档/26-AI生成用例-Run追溯与批量导入开发文档.md`

### 9.4 AI 导入后批量预检（API）

- `POST /api/testcase/cases/batch-preview-run-api/`
  - 用途：导入后对 API 用例做静态预检（最终请求预览 + 未替换变量检测），不发网络请求

参考开发文档：
- `开发文档/28-AI导入后批量预检（API Preview-Run）开发文档.md`

### 9.5 AI 导入前质量闸门（前端）与 strict（后端）

- 前端：AI 生成预览表会对问题行标红，并可选择是否阻断导入
- 后端：`POST /api/testcase/cases/ai-import/` 支持 `strict=true`，对关键字段做严格校验
- **strict + API**：后端对每条 item 执行与 `ai-import-precheck` 相同的静态预检（`testcase/services/ai_import_precheck_core.py`），请求体可带 **`precheck_overrides`**（`environment_id`、`variables`），与前端预检面板一致，避免绕过 UI 直连导入坏数据

参考开发文档：
- `开发文档/29-AI导入前质量闸门开发文档.md`

### 9.6 AI 导入前批量预检（草稿 items）

- `POST /api/testcase/cases/ai-import-precheck/`
  - 用途：对 AI 生成的草稿 API items 做静态预检（URL 拼接 + 变量替换 + 未替换变量检测），不要求落库

参考开发文档：
- `开发文档/30-AI导入前批量预检（草稿 API 用例）开发文档.md`

### 9.7 失败执行 → 用例修订建议（AI，不落库）

- `POST /api/ai/suggest-case-fix/`
  - Body：`{ "execution_log_id": number, "hint"?: string }`
  - 用途：基于未通过的 `testcase.ExecutionLog` 与当前用例步骤，调用大模型生成 `summary` / `suggested_steps` / `risks`（仅建议，不写库）
  - 权限：登录 + 与用例相同的数据范围；**通过**的执行记录返回 400

参考：`开发文档/33-后续功能规划-MVP与安全加固.md` §1

### 9.8 应用 AI 建议步骤（写库）

- `POST /api/testcase/cases/<id>/apply-ai-suggested-steps/`
  - Body：`{ "execution_log_id": number, "suggested_steps": [{ "step_desc", "expected_result"? }, ...], "confirm_replace_all": true }`
  - 行为：校验该 `ExecutionLog` 属于该用例且 **未通过**、调用方数据权限与 `suggest-case-fix` 一致后，**软删除**现有步骤并按数组顺序 **新建**步骤（最多 60 条；`step_desc` / `expected_result` 长度与 AI 导入对齐截断）。
  - `confirm_replace_all` 必须为 JSON 布尔 **`true`**，否则 400。
  - 自动化：`python manage.py test testcase.tests.ApplyAiSuggestedStepsApiTests`（需可连 MySQL；与 CI `api-tests` 中该步一致）。

### 3.2 请求体格式

| 场景 | Content-Type | 说明 |
|------|------|------|
| 普通 JSON CRUD | `application/json` | 默认场景 |
| 图片上传（头像、项目封面、方案图片） | `multipart/form-data` | 由前端使用 FormData 提交 |
| AI 流式生成 | `application/json` | 使用 `fetch` + SSE 读取服务端分块数据 |

### 3.3 分页约定

多数列表接口使用 DRF `PageNumberPagination`：

- 查询参数：`page`、`page_size`
- 典型响应字段：`count`、`next`、`previous`、`results`

已明确设置分页类的典型资源：

- 组织管理（`OrganizationViewSet`）
- 用例列表（`TestCaseViewSet`）
- 缺陷列表（`TestDefectViewSet`）
- 性能任务列表（`PerfTaskViewSet`）
- 测试计划（`TestPlanViewSet`）：`/api/execution/plans/`
  - 批量删除：`POST /api/execution/plans/batch-delete/`，Body `{ "ids": number[] }`
  - 批量更新：`POST /api/execution/plans/batch-update/`，Body `{ "ids": number[], "patch": object }`
  - 批量复制：`POST /api/execution/plans/batch-copy/`，Body `{ "ids": number[], "name_suffix"?: string }`
- 测试报告（`TestReportViewSet`）：`/api/execution/reports/`
  - 批量删除：`POST /api/execution/reports/batch-delete/`，Body `{ "ids": number[] }`
  - 批量更新：`POST /api/execution/reports/batch-update/`，Body `{ "ids": number[], "patch": object }`
  - 批量复制：`POST /api/execution/reports/batch-copy/`，Body `{ "ids": number[], "name_suffix"?: string }`
- 定时任务（`ScheduledTaskViewSet`）：`/api/execution/scheduled-tasks/`
  - 批量删除：`POST /api/execution/scheduled-tasks/batch-delete/`，Body `{ "ids": number[] }`
  - 批量更新：`POST /api/execution/scheduled-tasks/batch-update/`，Body `{ "ids": number[], "patch": object }`
  - 批量复制：`POST /api/execution/scheduled-tasks/batch-copy/`，Body `{ "ids": number[], "name_suffix"?: string }`
- 调度日志（`ScheduledTaskLogViewSet`）：`/api/execution/scheduled-task-logs/`
  - 批量删除：`POST /api/execution/scheduled-task-logs/batch-delete/`，Body `{ "ids": number[] }`
  - 按筛选清理：`POST /api/execution/scheduled-task-logs/batch-delete-by-filter/`，Body `{ "scheduled_task"?, "status"?, "message"?, "before_days"?, "max_delete"? }`
- 性能任务（`PerfTaskViewSet`）：`/api/perf/tasks/`
  - 批量删除：`POST /api/perf/tasks/batch-delete/`，Body `{ "task_ids": string[] }`
  - 批量更新：`POST /api/perf/tasks/batch-update/`，Body `{ "task_ids": string[], "patch": object }`
  - 批量复制：`POST /api/perf/tasks/batch-copy/`，Body `{ "task_ids": string[], "name_suffix"?: string }`
- k6 压测会话（`K6LoadTestSessionViewSet`）：`/api/perf/k6-sessions/`
  - 列表：`GET /api/perf/k6-sessions/`（分页；支持 query: `status`、`run_id`、`created_by_me`、`created_days`、`created_start`、`created_end`、`ordering`）
  - 批量删除：`POST /api/perf/k6-sessions/batch-delete/`，Body `{ "ids": number[] }`
  - 批量复制并执行：`POST /api/perf/k6-sessions/batch-copy/`，Body `{ "ids": number[] }`

### 3.4 筛选与搜索约定

接口普遍采用 Query 参数组合筛选，例如：

- 缺陷：`severity`、`status`、`priority`、`release_version`、`search`
- 用例：`project`、`module`、`testType`、`search`、`recycle`
- 发布计划：`project`
- 性能任务：`name`、`status`、`executor`

---

## 4. 响应格式与错误语义

### 4.1 响应风格现状

当前项目存在“两种并行响应风格”：

1. **业务包装风格**（常见于 `APIView`）：`{ code, msg, data }`
2. **DRF 原生风格**（常见于 `ModelViewSet`）：直接返回资源对象或分页结构

这属于历史演进结果，前端通过分模块封装规避了调用差异，但在新增接口时应保持“同一业务域内部风格一致”。

### 4.2 常见成功响应示例

**登录成功（包装风格）**

```json
{
  "code": 200,
  "msg": "登录成功",
  "data": {
    "token": "xxxxx",
    "username": "admin",
    "real_name": "管理员",
    "user_id": 1,
    "is_system_admin": true
  }
}
```

**缺陷列表（分页风格）**

```json
{
  "count": 36,
  "next": "http://127.0.0.1:8000/api/defect/defects/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "defect_no": "DEF-00001",
      "defect_name": "登录页按钮样式错乱"
    }
  ]
}
```

### 4.3 错误码与异常处理约定

- `400`：参数错误、业务校验失败（如批量 ids 非法）
- `401`：未认证或 Token 失效
- `403`：无权限（如非管理员审批操作）
- `404`：资源不存在
- `409`：冲突（如创建用例时命中回收站同名冲突）
- `500/502/504`：服务内部或上游模型服务异常

`BaseModelSerializers` 会将校验异常统一格式化为 `{ msg, code, data }` 结构抛出，便于前端直接展示友好提示。

---

## 5. 核心模块接口清单

### 5.1 用户与系统管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/user/captcha/` | GET | 获取验证码（Base64 图片 + UUID） |
| `/api/user/register/` | POST | 用户注册（开放） |
| `/api/user/login/` | POST | 用户登录并返回 Token |
| `/api/user/me/` | GET | 获取当前登录用户 |
| `/api/user/me/profile/` | GET/PATCH | 个人资料查询/更新（支持头像） |
| `/api/user/change-password/` | POST | 修改密码 |
| `/api/user/me/change-requests-status/` | GET | 查询敏感变更待审批状态 |
| `/api/user/me/sensitive-change/` | POST | 提交用户名/密码变更申请 |
| `/api/user/system-messages/` | GET | 当前用户系统消息 |
| `/api/user/system-messages/{id}/read/` | PATCH | 消息标记已读 |
| `/api/change-requests/{id}/approve/` | POST | 审批通过 |
| `/api/change-requests/{id}/reject/` | POST | 审批拒绝 |

### 5.2 项目管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/project/projects/` | GET/POST | 项目列表/创建（支持封面图上传） |
| `/api/project/projects/{id}/` | GET/PATCH/DELETE | 项目详情与维护 |
| `/api/project/tasks/` | GET/POST | 测试任务列表/创建 |
| `/api/project/tasks/{id}/` | GET/PATCH/DELETE | 任务详情与维护 |
| `/api/project/releases/` | GET/POST | 发布计划列表/创建 |
| `/api/project/releases/{id}/` | GET/PATCH/DELETE | 发布计划详情与维护 |

### 5.3 测试用例管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/testcase/modules/` | GET/POST | 模块管理 |
| `/api/testcase/cases/` | GET/POST | 用例列表/创建（支持多类型扁平字段） |
| `/api/testcase/cases/{id}/` | GET/PATCH/DELETE | 用例详情、更新、软删除 |
| `/api/testcase/cases/batch-delete/` | POST | 批量逻辑删除 |
| `/api/testcase/cases/recycle-bin/` | GET | 回收站列表 |
| `/api/testcase/cases/{id}/restore/` | POST | 回收站恢复 |
| `/api/testcase/cases/{id}/hard-delete/` | DELETE | 物理删除 |
| `/api/testcase/cases/batch-execute/` | POST | 批量执行计数 +1 |
| `/api/testcase/cases/{id}/execute-api/` | POST | 执行 API 用例（含兼容日志） |
| `/api/testcase/cases/{id}/run-api/` | POST | 覆盖参数执行 API 用例 |
| `/api/testcase/cases/{id}/execution-logs/` | GET | 执行日志分页 |
| `/api/testcase/ai-fill-test-data/` | POST | AI 按字段结构生成测试数据 |
| `/api/testcase/import-api-spec/` | POST | Swagger/cURL 导入 API 用例 |

### 5.4 测试执行与性能任务

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/execution/plans/` | GET/POST | 测试计划 |
| `/api/execution/reports/` | GET/POST | 测试报告 |
| `/api/execution/dashboard/summary/` | GET | 仪表盘聚合数据 |
| `/api/perf/tasks/` | GET/POST | 性能任务列表/创建 |
| `/api/perf/tasks/{task_id}/` | GET/PATCH/DELETE | 性能任务详情（主键为 task_id） |
| `/api/perf/tasks/{task_id}/run/` | POST | 触发性能任务运行 |

### 5.5 缺陷管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/defect/defects/` | GET/POST | 缺陷列表/创建 |
| `/api/defect/defects/{id}/` | GET/PATCH/DELETE | 缺陷详情与维护 |

### 5.6 AI 助手与模型配置

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/ai/verify-connection/` | POST | 固定模型快速连通性验证 |
| `/api/ai/test-connection/` | POST | 自定义模型/地址连通性测试 |
| `/api/ai/generate-cases/` | POST | 同步生成测试用例 |
| `/api/ai/generate-cases-stream/` | POST | SSE 流式生成测试用例 |
| `/api/assistant/llm/test-connection/` | POST | 兼容旧路径测试接口 |
| `/api/sys/ai-config/` | GET/PUT/DELETE | 系统级 AI 模型配置读取/更新/删除 |
| `/api/sys/ai-config/disconnect/` | POST | 断开模型配置 |
| `/api/sys/ai-config/reconnect/` | POST | 重连模型配置 |

---

## 6. 典型交互链路

### 6.1 登录与令牌续用链路

```
前端 Login.vue 提交用户名/密码
  ↓
POST /api/user/login/
  ↓
后端校验 + Token.objects.get_or_create()
  ↓
返回 token 与用户信息
  ↓
前端保存 localStorage.token
  ↓
后续 request.js 自动注入 Authorization 头
```

### 6.2 API 用例执行链路

```
前端调用 POST /api/testcase/cases/{id}/run-api/
  ↓
后端校验用例类型与 API 扩展字段
  ↓
run_api_case() 发起真实 HTTP 请求
  ↓
写入 ExecutionLog（可选兼容写入 ApiTestLog）
  ↓
返回 execution_log + 执行结果消息
```

### 6.3 AI 流式生成链路（SSE）

```
前端 fetch("/api/ai/generate-cases-stream/")
  ↓
TokenAuthentication 校验身份
  ↓
后端分块推送 data: {type, ...}
  ↓
前端按 \n\n 切块并 JSON.parse 每个 event
  ↓
收到 done 事件后结束流式渲染
```

### 6.4 AI 生成接口（新增约束）

`/api/ai/generate-cases/` 与 `/api/ai/generate-cases-stream/` 当前统一遵循：

1. 批量生成：单次请求默认至少生成 5 条用例（可配置）
2. 覆盖要求：正向、逆向、边界场景必须同时覆盖
3. 生成前规避：自动注入当前模块已有用例标题，约束模型避免重复意图
4. 解析策略：JSON Mode 优先，兼容端不支持时回退到容错 JSON 解析
5. 去重策略：字符串去重 + 语义去重双层过滤后再返回

常用请求体字段（示例）：

```json
{
  "requirement": "请生成登录模块测试用例",
  "test_type": "functional",
  "module_id": 101,
  "module_name": "登录模块",
  "api_key": "sk-xxx",
  "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
  "model": "glm-4.7-flash"
}
```

---

## 10. 审计事件查询与导出（补充）

### 10.1 个人审计（当前用户）

- **接口**：`GET /api/user/me/audit/events/`
- **权限**：登录即可
- **用途**：查询“由当前用户触发/产生”的 `AuditEvent`（后端过滤 `creator=request.user`）
- **分页参数**：
  - `page`：默认 `1`
  - `page_size`：默认 `50`，最大 `200`
- **筛选参数（可选）**：
  - `action` / `object_app` / `object_model` / `object_id`
- **响应**（统一 `{code,msg,data}`）：

```json
{
  "code": 200,
  "msg": "ok",
  "data": {
    "page": 1,
    "page_size": 50,
    "total": 123,
    "items": [
      {
        "id": 1,
        "action": "export",
        "object_app": "project",
        "object_model": "ReleasePlan",
        "object_id": "12",
        "object_repr": "ReleasePlan#12",
        "request_path": "/api/project/releases/12/never-executed-cases/export.csv",
        "ip": "127.0.0.1",
        "extra": {},
        "create_time": "2026-04-16T10:00:00+08:00"
      }
    ]
  }
}
```

### 10.2 系统审计（系统管理员）

- **列表接口**：`GET /api/sys/audit/events/`
- **权限**：系统管理员（`IsSystemAdmin`）
- **分页参数**：同 10.1
- **筛选参数（可选）**：
  - `action` / `object_app` / `object_model` / `object_id`
  - `start_date` / `end_date`：`YYYY-MM-DD`（按 `create_time` 的日期包含边界过滤）
- **响应**（统一 `{code,msg,data}`）：`data` 结构同 10.1，但 `items` 额外包含 `user_agent`、`before`、`after`、`creator_id` 等字段（以实际 `values()` 为准）。

### 10.3 系统审计 CSV 导出（系统管理员）

- **接口**：`GET /api/sys/audit/export.csv`
- **权限**：系统管理员
- **筛选参数（可选）**：同 10.2 的文本筛选 + 日期筛选
- **额外参数**：
  - `limit`：默认 `5000`，最大 `200000`
- **响应**：`text/csv` 文件下载（流式输出）
- **前端注意**：CSV 下载不要用 `<a href="/api/...">` 裸链（浏览器请求不会自动带 `Authorization`），应使用 Axios `responseType: "blob"` 并手动注入 `Authorization: Token ...`（通用封装：`frontend/src/utils/downloadAuthedGet.js`；业务封装示例：`frontend/src/api/audit.js`）。`downloadAuthedGet` 在 4xx/JSON 错误体时会解析 Blob 中的 `detail`/`msg` 并 `throw new Error(…)`，前端可直接 `ElMessage.error(e.message)`。
- **同类端点**：`GET /api/sys/ai-usage/export.csv`（AI 用量审计导出）同样适用上述约定，参考 `frontend/src/api/sysAiUsage.js`。

---

## 7. 前后端联调注意事项

1. **路径拼接**
   - `request.js` 已设置 `baseURL="/api"`，业务 API 文件中应使用相对路径（如 `/user/me/`），避免重复写成 `/api/user/me/`。

2. **统一 token 存储键**
   - 当前约定为 `localStorage.token`；若变更存储键需同步修改请求拦截器与登录页逻辑。

3. **混合响应风格处理**
   - 登录、用户中心等接口常返回 `{code,msg,data}`；
   - ViewSet 列表接口常返回 DRF 原生分页结构。前端调用处需按域解包。

4. **上传接口必须使用 FormData**
   - 头像、项目封面、方案图片等场景需设置 `multipart/form-data`，并匹配后端字段名（如 `avatar`、`cover_image`、`images`）。

5. **回收站语义**
   - 测试用例“删除”默认是软删除；前端若要展示回收站数据，应传 `recycle=1` 或调用回收站专用接口。

6. **性能任务主键差异**
   - `/api/perf/tasks/{task_id}/` 使用业务主键 `task_id`（如 `PT-0001`），而非数据库自增 `id`。

---

## 8. 与后续文档关系

本章定义了“接口如何被调用以及数据如何流转”的基础约定。后续文档将继续说明：

- [05-测试指南与性能评测.md](./05-测试指南与性能评测.md)：如何围绕接口进行自动化测试与性能验证
- [06-部署与配置指南.md](./06-部署与配置指南.md)：不同环境下接口可用性的配置保障与部署细节

---

*文档版本：v1.2 | 最后更新：2026-04-16*
