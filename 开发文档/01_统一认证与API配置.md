# 统一认证与 API 配置模块（Core‑01）

## I. 业务深度逻辑 (Business Logic Deep Dive)
1. **登录 / 注册**
   - 前端 `POST /api/user/login/` → `UserLoginAPIView`。
   - 使用 `UserLoginSerializer` 校验后调用 `django.contrib.auth.authenticate`。
   - 成功后 `Token.objects.get_or_create(user=user)` 生成 DRF Token，写入 **HttpOnly Cookie** `access_token`，并在响应体返回 `{"token": token.key}`，前端在后续请求中通过 `Authorization: Bearer <token>` 发送。
   - 注册 `UserRegisterAPIView` 调用 `UserRegisterSerializer.create()`，内部使用 `User.objects.create_user` 完成密码哈希并写入审计字段 `created_at/updated_at`（继承自 `BaseModel`）。
2. **统一 API Key / Base URL 配置**
   - `AIModelConfig`（`user/models.py`）持有 `api_key`（TextField） 与 `base_url`（URLField），属于系统配置子模块 `sys`。
   - 通过 `AIModelConfigAPIView`（`user/sys_views.py`）提供 **GET/POST/PUT**：
     - **GET** 返回 `model_type`、`base_url`、`is_connected`（不返回 `api_key`）。
     - **POST** 创建新配置，`api_key` 必填，后端写库后标记 `is_connected=True`。
     - **PUT** 更新 `base_url` 或 **断开/重连**（`/disconnect/`、`/reconnect/`），`disconnect` 仅将 `is_connected=False`，不删除密钥；`reconnect` 重新标记为已连接。
   - 所有外部 LLM 调用统一走 `services/ai_engine.py`，内部检索 `AIModelConfig` 实例并检查 `is_connected`，若为 `False` 抛 `PermissionDenied` 防止密钥泄漏。
3. **会话 / Token 生命周期**
   - 默认 DRF Token 永久有效；可在 `settings.py` 中配置 `TOKEN_EXPIRE_DAYS`，`UserLoginAPIView` 在生成 Token 时写入自定义 `expires_at` 字段并在每次请求中检查过期。
   - 前端 axios 实例 `withCredentials:true` 自动携带 Cookie，若使用 Header 则在拦截器加入 `Authorization: Bearer <token>`。

## II. 数据库全解析 (Database Schema & Visibility)

| 表 & 字段 | 类型 | 空/默认 | 可见性 |
|-----------|------|----------|--------|
| **auth_user** (`User`) | | | |
| &nbsp;&nbsp;`id` | INTEGER PK | 否 | 后端私有 |
| &nbsp;&nbsp;`username` | VARCHAR(150) | 否 | 前端可写（注册） |
| &nbsp;&nbsp;`password` | VARCHAR(128) | 否 | **后端私有** |
| &nbsp;&nbsp;`email` | VARCHAR(254) | 是 | 前端可见 |
| &nbsp;&nbsp;`is_active` | BOOLEAN | 否, True | 前端可见 |
| &nbsp;&nbsp;`date_joined` | DATETIME | 否, 自动 | 前端只读 |
| **user_ai_modelconfig** | | | |
| &nbsp;&nbsp;`id` | INTEGER PK | 否 | 后端私有 |
| &nbsp;&nbsp;`model_type` | VARCHAR(50) | 否 | 前端只读 |
| &nbsp;&nbsp;`api_key` | TEXT | 否 | **后端私有** |
| &nbsp;&nbsp;`base_url` | VARCHAR(255) | 是 | 前端只读 |
| &nbsp;&nbsp;`is_connected` | BOOLEAN | 否, True | 前端只读 |

> **可见性约定**
> - **[前端可见]**：通过公开 API 返回，可在 UI 中展示或编辑。
> - **[后端私有]**：永不返回给前端（如 `api_key`、`password`）。
> - **[只读]**：API 只返回，不接受写入；修改需走专属管理接口（如 `AIModelConfigReconnect`）。

## III. 交互生命周期 (Interaction Lifecycle)

| 前端动作 | 请求示例 | 后端处理 | 响应 |
|----------|----------|----------|------|
| **登录** | `POST /api/user/login/` `{ "username":"admin","password":"pwd" }` | 序列化 → `authenticate` → `Token.get_or_create` → 设置 Cookie | `{ "code":0, "msg":"成功", "data":{"token":"<key>","username":"admin"} }` |
| **获取 API 配置** | `GET /api/sys/ai-config/` | 读取最新 `AIModelConfig`，过滤掉 `api_key` | `ApiResponse.success({"model_type":"openai","base_url":"https://api.openai.com/v1","is_connected":true})` |
| **更新 Base URL** | `PUT /api/sys/ai-config/` `{ "base_url":"https://new.api/v1" }` | `serializer.save()` → 更新 DB | `ApiResponse.success(message="已更新")` |
| **断开连接** | `POST /api/sys/ai-config/disconnect/` | `instance.is_connected=False` → `save()` | `ApiResponse.success(message="已断开")` |
| **重新连接** | `POST /api/sys/ai-config/reconnect/` | `instance.is_connected=True` → `save()` | `ApiResponse.success(message="已连接")` |

## IV. 前端呈现与 UI 规范 (Frontend & UI Spec)
- **登录页**：Ant Design Vue `a-form`，`username`、`password` 必填，提交后调用 `api/userLogin`，成功后 `router.push('/')`。输入框使用 `type="password"` 并提供显示/隐藏切换。
- **系统设置 – AI 配置**：卡片式布局，采用 **Cyberpunk Blue** 主题：背景 `#0a0f1f`，卡片边框 `#1f8ef1`，文字 `#e0f0ff`，按钮渐变 `linear-gradient(45deg, #1f8ef1, #00bfff)`。`api_key` 输入框为密码类型，仅在管理员页面解密后展示。
- **可访问性**：所有交互元素对比度 ≥ 4.5:1，提供键盘焦点样式 `outline: 2px solid #00bfff`。

## V. 模块拆分颗粒度 (Module Granularity)
| 子模块 | 说明 |
|--------|------|
| **Auth（登录/注册）** | 负责凭证校验、Token 发放、Cookie 写入。
| **API Key Management** | 独立系统配置（增删改查、断开/重连），不与业务模型混合。
| **Permission & Role** | `permissions.py` 中的 `IsSystemAdmin`、`IsApprovalAdmin`，保持职责单一。
| **Audit** | `common/models.AuditEvent` 与 `user/models.AiUsageEvent` 记录业务操作与 AI 调用。
