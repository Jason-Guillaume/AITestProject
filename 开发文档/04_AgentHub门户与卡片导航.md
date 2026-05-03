# Agent Hub 门户与卡片导航模块（AI‑01）

## I. 业务深度逻辑 (Business Logic Deep Dive)
1. **门户整体结构**
   - 前端为单页面应用，根路由 `/agent` 加载 **AgentHub.vue**。该页面展示若干 **功能卡片**，每张卡片对应一个 AI 子功能（如 `用例生成`、`安全评估`、`报告可视化`）。
   - 卡片数据来源于后端 **AgentCard** 模型（`assistant/models.py`），字段包括 `title`、`icon`、`description`、`entry_api`、`is_enabled`。
   - 点击卡片后路由跳转至对应子页面（`/agent/case-gen`、`/agent/security` 等），子页面通过 `entry_api` 调用统一的 **AgentService**（`assistant/services/ai_engine.py`），完成 Prompt 组装、LLM 调用与结果持久化。
2. **权限与可用性**
   - `AgentCard.is_enabled` 决定卡片是否对普通用户可见。系统管理员可通过 **系统设置**（`POST /api/sys/agent-card/`）开启/关闭功能。
   - 编辑卡片的接口受 `permissions.IsSystemAdmin` 保护，普通用户仅能读取已启用的卡片列表（`GET /api/agent/cards/`）。
3. **前后端交互**
   - 前端 **GET /api/agent/cards/** 获取卡片列表，渲染为 **grid** 布局的卡片组件。
   - 子功能页面 **POST** 相应业务 API（如 `POST /api/ai/generate-case/`），后端在 `AgentService` 中调用 `AIModelConfig` 获取密钥、组装系统 Prompt、调用 LLM、返回生成结果。
   - 所有 LLM 调用统一记录 **AiUsageEvent**（`assistant/models.AiUsageEvent`），供配额与审计使用。

## II. 数据库全解析 (Database Schema & Visibility)

| 表 | 字段 | 类型 | 空/默认 | 可见性 |
|---|------|------|----------|--------|
| `assistant_agentcard` | `id` | INTEGER PK | 否 | 后端私有 |
| | `title` | VARCHAR(100) | 否 | 前端可见 |
| | `icon` | VARCHAR(50) | 否 | 前端可见 |
| | `description` | TEXT | 可空 | 前端可见 |
| | `entry_api` | VARCHAR(100) | 否 | 前端只读 |
| | `is_enabled` | BOOLEAN | True | 前端只读（管理员可写） |

> **可见性说明**：`title`、`icon`、`description` 为 UI 展示字段；`entry_api` 为路由路径，不允许前端修改；`is_enabled` 只能通过管理员 API 修改。

## III. 交互生命周期 (Interaction Lifecycle)

| 前端动作 | API | 请求示例 | 后端处理 | 响应 |
|----------|-----|----------|----------|------|
| 加载门户 | `GET /api/agent/cards/` | — | 查询 `AgentCard`，过滤 `is_enabled=True` → 序列化返回 | `ApiResponse.success([{"title":"用例生成","icon":"code","description":"..."}, …])` |
| 启用/禁用卡片（管理员） | `POST /api/sys/agent-card/` | `{ "id":3, "is_enabled":false }` | `AgentCardSerializer.update()` → 保存 | `ApiResponse.success(message="已更新")` |
| 调用子功能 API | `POST /api/ai/generate-case/` | `{ "requirement":"登录" }` | `AgentService.generate_case()` → LLM 调用 → 结果持久化 `GeneratedTestCase` → 返回 | `ApiResponse.success({"case_id":12,"content":…})` |

## IV. 前端呈现与 UI 规范 (Frontend & UI Spec)
- **卡片布局**：使用 **Ant Design Card**，网格 `a-row`/`a-col`，每张卡片宽度 `calc(33.33% - 16px)`，背景 `#0a0f1f`，边框 `1px solid #1f8ef1`，悬停时 `box-shadow: 0 0 12px #00bfff`。
- **卡片内容**：顶部图标使用 **iconfont**，下方标题 `font-size: 1.2rem; color:#e0f0ff`，描述文字 `font-size: 0.9rem; color:#a0c0ff`。点击卡片触发路由 `router.push(entry_api)`。
- **主题统一**：整体采用 **Cyberpunk Blue** 色调，字体使用 `Roboto Mono`，确保对比度 ≥ 4.5:1。
- **可访问性**：每张卡片 `role="button"`，提供 `aria-label="<title> 功能卡片"`，键盘 `Enter` 可激活。

## V. 模块拆分颗粒度 (Module Granularity)

| 子模块 | 说明 |
|--------|------|
| **AgentCard Model** (`assistant/models.AgentCard`) | 定义卡片元数据，若需要可使用 `EncryptedFieldsMixin` 加密敏感字段 |
| **AgentCard API** (`assistant/views.AgentCardViewSet`) | 只读列表 + 管理员写入/更新接口 |
| **AgentService** (`assistant/services/ai_engine.py`) | 统一 Prompt 组装、LLM 调用、结果处理、记录 `AiUsageEvent` |
| **Permission** (`assistant/permissions.IsSystemAdmin`) | 保护卡片管理接口 |
| **Frontend Module** (`frontend/src/pages/AgentHub.vue`) | 卡片网格渲染、路由跳转、加载状态管理 |
