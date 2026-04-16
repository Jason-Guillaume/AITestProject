# AI 测试平台 - 完整 Python 文件清单

## 统计
- **总文件数**: 100+ Python 文件
- **业务模块**: 7 个主要应用 (user, project, testcase, execution, defect, assistant, server_logs)
- **公共模块**: 1 个 (common)
- **项目配置**: 6 个文件
- **测试文件**: 12 个

---

## 一、项目根目录 (AITestProduct/)

### manage.py
- **路径**: `/d/AITestProduct/manage.py`
- **业务功能**: Django 命令行工具入口
- **主要功能**:
  - 设置 DJANGO_SETTINGS_MODULE 环境变量
  - 调用 Django 管理命令 (runserver, migrate, createsuperuser 等)
  - 错误处理与提示

### AITestProduct/__init__.py
- **路径**: `/d/AITestProduct/AITestProduct/__init__.py`
- **业务功能**: 项目包初始化

### AITestProduct/asgi.py
- **路径**: `/d/AITestProduct/AITestProduct/asgi.py`
- **业务功能**: ASGI 服务器配置 (Daphne + Channels)
- **主要功能**:
  - 创建 ASGI application 实例
  - 集成 Channels HTTP/WebSocket routing
  - 支持实时日志推送、执行进度 WebSocket 通信

### AITestProduct/celery.py
- **路径**: `/d/AITestProduct/AITestProduct/celery.py`
- **业务功能**: Celery 分布式任务队列配置
- **主要功能**:
  - 初始化 Celery 应用实例
  - 配置 Redis/MySQL 作为 Broker
  - 配置 JSON 序列化
  - 设置任务确认机制 (acks_late)
  - 配置 worker prefetch multiplier = 1

### AITestProduct/settings.py
- **路径**: `/d/AITestProduct/AITestProduct/settings.py`
- **业务功能**: Django 核心配置
- **主要配置项**:
  - **数据库**: MySQL 连接配置
  - **缓存**: Redis/LocMem 自动降级
  - **Channels**: Redis/InMemory 通道层
  - **REST Framework**: Token 认证、权限、限流
  - **Celery**: Broker/Backend 配置
  - **AI 配置**: RAG 参数、配额策略、并发限制
  - **日志配置**: Elasticsearch、Loki、SSH 策略
  - **邮件配置**: SMTP/Console Backend
  - **加密**: Fernet 密钥配置
  - **文件上传**: MEDIA_ROOT 配置

### AITestProduct/urls.py
- **路径**: `/d/AITestProduct/AITestProduct/urls.py`
- **业务功能**: 主路由分发
- **路由映射**:
  - `/admin/` - Django 后台
  - `/api/sys/` - 系统管理 (user.sys_urls)
  - `/api/change-requests/` - 审批流程 (user.approval_urls)
  - `/api/user/` - 用户中心 (user.urls)
  - `/api/project/` - 项目管理 (project.urls)
  - `/api/testcase/` - 测试用例 (testcase.urls)
  - `/api/environments/` - 环境管理 (testcase.environment_urls)
  - `/api/execution/` - 测试执行 (execution.urls)
  - `/api/perf/` - 性能测试 (execution.perf_urls)
  - `/api/defect/` - 缺陷管理 (defect.urls)
  - `/api/assistant/` - AI 助手 (assistant.urls)
  - `/api/ai/` - AI 功能 (assistant.ai_urls)
  - `/api/server-logs/` - 服务器日志 (server_logs.urls)

### AITestProduct/wsgi.py
- **路径**: `/d/AITestProduct/AITestProduct/wsgi.py`
- **业务功能**: WSGI 服务器入口 (传统同步 Web 服务器)

---

## 二、user 用户管理模块

### user/__init__.py
- **业务功能**: Python 包初始化

### user/admin.py
- **业务功能**: Django Admin 后台配置
- **注册模型**: User, UserChangeRequest, SystemMessage, AIModelConfig, Organization, AiQuotaPolicy, SystemMessageSetting

### user/apps.py
- **业务功能**: UserConfig 应用配置类

### user/models.py
- **业务功能**: 数据模型定义
- **模型列表**:
  - `User`: 系统用户模型 (继承 AbstractUser)，包含 real_name, phone_number, avatar, is_active, is_system_admin
  - `UserChangeRequest`: 敏感信息变更申请 (username/password)，需审批
  - `SystemMessage`: 站内系统消息，关联变更申请
  - `AIModelConfig`: 平台级 AI 模型配置 (project + model_type 唯一)
  - `Organization`: 组织管理，成员与项目关联
  - `AiQuotaPolicy`: AI 配额策略 (project/org/user 三维度)
  - `SystemMessageSetting`: 用户消息设置 (站内/邮件/短信/日报)

### user/permissions.py
- **业务功能**: 自定义权限类
- **权限类**:
  - `IsSystemAdmin`: 系统管理员权限
  - `IsApprovalAdmin`: 审批管理员权限

### user/serialize.py
- **业务功能**: DRF 序列化器
- **序列化器**:
  - `UserSerializer`: 用户信息序列化
  - `UserRegisterSerializer`: 注册序列化器
  - `UserProfileSerializer`: 用户资料序列化
  - `UserLoginSerializer`: 登录序列化器
  - `OrganizationSerializer`: 组织序列化
  - `SystemMessageSerializer`: 系统消息序列化
  - `SystemMessageSettingSerializer`: 消息设置序列化
  - `RoleSerializer`: 角色 (Group) 序列化
  - `UserChangeRequestListSerializer`: 变更申请列表
  - `UserChangeRequestDecisionSerializer`: 变更决策序列化

### user/signals.py
- **业务功能**: Django 信号处理器
- **监听事件**:
  - 用户创建后发送欢迎消息
  - 敏感变更审批后发送通知

### user/tests.py
- **业务功能**: 单元测试入口

### user/urls.py
- **业务功能**: 用户模块路由
- **路径**:
  - `/api/user/register/` - 用户注册
  - `/api/user/login/` - 用户登录
  - `/api/user/captcha/` - 验证码
  - `/api/user/profile/` - 用户资料
  - `/api/user/password/` - 修改密码
  - `/api/user/me/` - 当前用户信息
  - `/api/user/me/audit/events/` - 用户审计事件

### user/sys_urls.py
- **业务功能**: 系统管理路由
- **路径**:
  - `/api/sys/users/` - 用户管理
  - `/api/sys/organizations/` - 组织管理
  - `/api/sys/roles/` - 角色管理
  - `/api/sys/message-settings/` - 消息设置

### user/approval_urls.py
- **业务功能**: 审批流程路由
- **路径**:
  - `/api/change-requests/` - 变更申请列表
  - `/api/change-requests/<id>/approve/` - 批准申请
  - `/api/change-requests/<id>/reject/` - 拒绝申请

### user/views.py
- **业务功能**: 用户视图
- **视图类**:
  - `UserViewSet`: 用户 CRUD (RBAC 控制)
  - `OrganizationViewSet`: 组织 CRUD
  - `SystemMessageSettingViewSet`: 消息设置 CRUD
  - `RoleViewSet`: 角色 (Group) CRUD
  - `CaptchaAPIView`: 验证码生成
  - `UserRegisterAPIView`: 用户注册
  - `UserLoginAPIView`: 用户登录 (Token 认证)
  - `CurrentUserAPIView`: 当前用户信息
  - `ChangePasswordAPIView`: 修改密码
  - `UserProfileAPIView`: 用户资料更新
  - `UserMyPendingSensitiveStatusAPIView`: 待审批状态
  - `UserSensitiveChangeRequestAPIView`: 提交变更申请
  - `SystemMessageListAPIView`: 站内消息列表
  - `SystemMessageMarkReadAPIView`: 标记已读
  - `UserAuditEventListAPIView`: 用户审计事件
  - `AdminUserChangeRequestListAPIView`: 管理员查看变更申请
  - `AdminChangeRequestApproveAPIView`: 批准申请
  - `AdminChangeRequestRejectAPIView`: 拒绝申请
  - `AdminUserChangeRequestDecisionAPIView`: 兼容旧版决策接口

### user/sys_views.py
- **业务功能**: 系统管理视图
- **功能**: 系统级用户/组织/角色管理

### user/captcha_image.py
- **业务功能**: 验证码图片生成
- **功能**: 生成科技感验证码图片 (白底蓝字)

### user/change_request_actions.py
- **业务功能**: 变更申请处理逻辑
- **函数**:
  - `approve_change_request()`: 批准变更
  - `reject_change_request()`: 拒绝变更

### user/user_center_mail.py
- **业务功能**: 用户中心邮件服务
- **功能**: 发送敏感变更通知邮件

---

## 三、project 项目管理模块

### project/__init__.py
- **业务功能**: Python 包初始化

### project/admin.py
- **业务功能**: Admin 后台配置
- **注册模型**: TestProject, TestTask, ReleasePlan, ReleasePlanTestCase, TestPlan, TestReport, PerfTask, K6LoadTestSession, ScheduledTask, ScheduledTaskLog, ExecutionTask, TestQualityMetric, ApiScenario, ApiScenarioStep, ApiScenarioRun, ApiScenarioStepRun

### project/apps.py
- **业务功能**: ProjectConfig 应用配置

### project/models.py
- **业务功能**: 项目数据模型
- **模型**:
  - `TestProject`: 项目 (支持父子层级)
  - `TestTask`: 任务看板
  - `ReleasePlan`: 发布计划
  - `ReleasePlanTestCase`: 发布计划 - 用例关联
  - `TestPlan`: 测试计划
  - `TestReport`: 测试报告
  - `PerfTask`: 性能测试任务
  - `K6LoadTestSession`: k6 压测会话
  - `ScheduledTask`: 定时任务
  - `ScheduledTaskLog`: 定时任务日志
  - `ExecutionTask`: 执行任务
  - `TestQualityMetric`: 质量指标
  - `ApiScenario`: API 场景
  - `ApiScenarioStep`: 场景步骤
  - `ApiScenarioRun`: 场景运行记录
  - `ApiScenarioStepRun`: 步骤运行记录

### project/serialize.py
- **业务功能**: 项目数据序列化器

### project/urls.py
- **业务功能**: 项目路由

### project/views.py
- **业务功能**: 项目视图
- **功能**: 项目 CRUD、发布计划、测试计划、报告生成、场景编排

### project/tests.py
- **业务功能**: 单元测试

### project/services/__init__.py
- **业务功能**: 服务层初始化

### project/services/release_risk_brief.py
- **业务功能**: 发布风险评估简报生成

---

## 四、testcase 测试用例模块

### testcase/__init__.py
- **业务功能**: Python 包初始化

### testcase/admin.py
- **业务功能**: Admin 配置

### testcase/apps.py
- **业务功能**: TestcaseConfig 配置

### testcase/models.py
- **业务功能**: 用例数据模型
- **模型**:
  - `TestApproach`: 测试方案
  - `TestApproachImage`: 方案图片
  - `TestDesign`: 测试设计
  - `TestModule`: 测试模块 (层级)
  - `TestEnvironment`: 测试环境
  - `EnvironmentHealthCheck`: 环境健康检查
  - `EnvironmentVariable`: 环境变量 (加密)
  - `TestCase`: 用例基类 (软删除)
  - `TestCaseVersion`: 用例版本快照
  - `ApiTestCase`: API 用例扩展
  - `PerfTestCase`: 性能用例扩展
  - `SecurityTestCase`: 安全用例扩展
  - `UITestCase`: UI 用例扩展
  - `TestCaseStep`: 用例步骤
  - `ApiTestLog`: API 执行日志
  - `ExecutionLog`: 执行完整记录

### testcase/serialize.py
- **业务功能**: 用例序列化器

### testcase/signals.py
- **业务功能**: 信号处理器

### testcase/urls.py
- **业务功能**: 用例路由

### testcase/environment_urls.py
- **业务功能**: 环境路由

### testcase/views.py
- **业务功能**: 用例视图
- **功能**: 用例 CRUD、导入、版本管理、执行、模块管理、环境管理

### testcase/tests.py
- **业务功能**: 单元测试

### testcase/management/__init__.py
- **业务功能**: Django management 命令

### testcase/services/__init__.py
- **业务功能**: 服务层初始化

### testcase/services/ai_case_gate.py
- **业务功能**: AI 用例生成网关

### testcase/services/ai_import_precheck_core.py
- **业务功能**: AI 导入预检查

### testcase/services/ai_openai.py
- **业务功能**: OpenAI API 调用

### testcase/services/api_execution.py
- **业务功能**: API 执行服务

### testcase/services/assertions.py
- **业务功能**: 断言逻辑

### testcase/services/auth_runtime.py
- **业务功能**: 运行时鉴权

### testcase/services/case_subtypes.py
- **业务功能**: 用例子类型处理

### testcase/services/variable_runtime.py
- **业务功能**: 变量运行时解析

---

## 五、execution 测试执行模块

### execution/__init__.py
- **业务功能**: Python 包初始化

### execution/admin.py
- **业务功能**: Admin 配置

### execution/apps.py
- **业务功能**: ExecutionConfig 配置

### execution/models.py
- **业务功能**: 执行相关模型 (部分与 project 共享)

### execution/urls.py
- **业务功能**: 执行路由

### execution/perf_urls.py
- **业务功能**: 性能测试路由

### execution/views.py
- **业务功能**: 执行视图

### execution/views_k6.py
- **业务功能**: k6 执行视图

### execution/tests.py
- **业务功能**: 单元测试

### execution/tasks.py
- **业务功能**: Celery 异步任务

### execution/tasks_k6.py
- **业务功能**: k6 压测任务

### execution/engine.py
- **业务功能**: 执行引擎核心
- **功能**: 任务调度、用例执行、结果收集

### execution/consumers.py
- **业务功能**: WebSocket 消费者
- **功能**: 实时推送执行进度、日志流

### execution/routing.py
- **业务功能**: WebSocket 路由

### execution/scheduler.py
- **业务功能**: 定时调度器

### execution/middleware_ws.py
- **业务功能**: WebSocket 中间件

### execution/serialize.py
- **业务功能**: 执行数据序列化

### execution/management/__init__.py
- **业务功能**: Management 命令

### execution/services/__init__.py
- **业务功能**: 服务层初始化

### execution/services/health_checker.py
- **业务功能**: 健康检查

### execution/services/k6_ai_generator.py
- **业务功能**: k6 AI 脚本生成

### execution/services/k6_chain_builder.py
- **业务功能**: k6 请求链构建

### execution/services/k6_stderr_parser.py
- **业务功能**: k6 错误解析

### execution/services/k6_template_generator.py
- **业务功能**: k6 模板生成

### execution/services/metric_calculator.py
- **业务功能**: 指标计算

### execution/services/scenario_generator.py
- **业务功能**: 场景生成

### execution/services/scenario_runner.py
- **业务功能**: 场景运行

---

## 六、defect 缺陷管理模块

### defect/__init__.py
- **业务功能**: Python 包初始化

### defect/admin.py
- **业务功能**: Admin 配置

### defect/apps.py
- **业务功能**: DefectConfig 配置

### defect/models.py
- **业务功能**: 缺陷模型
- **模型**: `TestDefect` - 缺陷 (编号、标题、版本、严重程度、优先级、状态、处理人、模块、内容、步骤、附件)

### defect/serialize.py
- **业务功能**: 缺陷序列化器

### defect/urls.py
- **业务功能**: 缺陷路由

### defect/views.py
- **业务功能**: 缺陷视图
- **功能**: 缺陷 CRUD、状态流转、关联管理

### defect/tests.py
- **业务功能**: 单元测试

---

## 七、assistant AI 助手模块

### assistant/__init__.py
- **业务功能**: Python 包初始化

### assistant/admin.py
- **业务功能**: Admin 配置

### assistant/apps.py
- **业务功能**: AssistantConfig 配置

### assistant/models.py
- **业务功能**: AI 数据模型
- **模型**:
  - `KnowledgeArticle`: 知识库文章
  - `KnowledgeDocument`: 知识库文档
  - `GeneratedTestArtifact`: 生成的测试资产
  - `AiUsageEvent`: AI 调用审计
  - `AiPatch`: AI 变更补丁
  - `AiCaseGenerationRun`: AI 生成批次

### assistant/urls.py
- **业务功能**: AI 助手路由

### assistant/ai_urls.py
- **业务功能**: AI 功能路由

### assistant/views.py
- **业务功能**: AI 助手视图

### assistant/tests.py
- **业务功能**: 单元测试

### assistant/tasks.py
- **业务功能**: Celery AI 任务

### assistant/signals.py
- **业务功能**: 信号处理器

### assistant/permissions.py
- **业务功能**: AI 权限控制

### assistant/serialize.py
- **业务功能**: AI 数据序列化

### assistant/ai_errors.py
- **业务功能**: AI 错误定义

### assistant/ai_prompts.py
- **业务功能**: AI 提示词模板

### assistant/ai_generate_strategies.py
- **业务功能**: AI 生成策略

### assistant/api_case_generation.py
- **业务功能**: API 用例 AI 生成

### assistant/error_parser.py
- **业务功能**: 错误解析

### assistant/generated_case_dedup.py
- **业务功能**: 生成用例去重

### assistant/knowledge_rag.py
- **业务功能**: 知识库 RAG

### assistant/embeddings_zhipu.py
- **业务功能**: 智谱 Embedding

### assistant/rag_chroma.py
- **业务功能**: Chroma 向量数据库

### assistant/rag_pipeline.py
- **业务功能**: RAG 流水线

### assistant/management/__init__.py
- **业务功能**: Management 命令

### assistant/services/__init__.py
- **业务功能**: 服务层初始化

### assistant/services/ai_engine.py
- **业务功能**: AI 引擎核心

### assistant/services/ai_governance.py
- **业务功能**: AI 治理 (配额、并发、审计)

### assistant/services/case_batch_generation.py
- **业务功能**: 批量用例生成

### assistant/services/case_fix_from_execution.py
- **业务功能**: 基于执行修复用例

### assistant/services/document_parser.py
- **业务功能**: 文档解析

### assistant/services/rag_service.py
- **业务功能**: RAG 服务

### assistant/services/security_rules.py
- **业务功能**: 安全规则检查

### assistant/services/semantic_dedup.py
- **业务功能**: 语义去重

---

## 八、server_logs 服务器日志模块

### server_logs/__init__.py
- **业务功能**: Python 包初始化

### server_logs/admin.py
- **业务功能**: Admin 配置

### server_logs/apps.py
- **业务功能**: ServerLogsConfig 配置

### server_logs/models.py
- **业务功能**: 日志模型
- **模型**:
  - `RemoteLogServer`: 远程 SSH 日志主机
  - `ServerLogAuditEvent`: 日志操作审计
  - `LogAutoTicketJob`: AI 工单草稿任务

### server_logs/urls.py
- **业务功能**: 日志路由

### server_logs/views.py
- **业务功能**: 日志视图

### server_logs/tests.py
- **业务功能**: 单元测试

### server_logs/tasks.py
- **业务功能**: Celery 日志任务

### server_logs/routing.py
- **业务功能**: WebSocket 路由

### server_logs/consumers.py
- **业务功能**: WebSocket 消费者

### server_logs/serializers.py
- **业务功能**: 日志序列化器

### server_logs/access.py
- **业务功能**: 日志访问控制

### server_logs/audit.py
- **业务功能**: 审计服务

### server_logs/crypto.py
- **业务功能**: SSH 凭据加密/解密

### server_logs/es_client.py
- **业务功能**: Elasticsearch 客户端

### server_logs/log_context.py
- **业务功能**: 日志上下文

### server_logs/ssh_tail.py
- **业务功能**: SSH 日志 tail

### server_logs/validators.py
- **业务功能**: 数据验证

### server_logs/ai_analyze.py
- **业务功能**: AI 日志分析

### server_logs/ai_ticket.py
- **业务功能**: AI 工单生成

### server_logs/defect_create.py
- **业务功能**: 自动创建缺陷

---

## 九、common 公共模块

### common/__init__.py
- **业务功能**: Python 包初始化

### common/admin.py
- **业务功能**: Admin 配置

### common/apps.py
- **业务功能**: CommonConfig 配置

### common/models.py
- **业务功能**: 基础模型
- **模型**:
  - `BaseModel`: 基础模型 (creator/updater/create_time/update_time/is_deleted)
  - `AuditEvent`: 审计事件

### common/serialize.py
- **业务功能**: 公共序列化器

### common/views.py
- **业务功能**: 公共视图 (BaseModelViewSet)

### common/tests.py
- **业务功能**: 单元测试

### common/services/__init__.py
- **业务功能**: 服务层初始化

### common/services/audit.py
- **业务功能**: 审计服务

---

## 十、scripts 脚本目录

### scripts/smoke_test.py
- **业务功能**: Smoke 测试脚本

### scripts/smoke_batch_ops.py
- **业务功能**: 批量操作冒烟测试

---

## 十一、tests 测试目录

### tests/api/__init__.py
- **业务功能**: API 测试包初始化

### tests/api/conftest.py
- **业务功能**: pytest 配置与 fixture

### tests/api/_helpers.py
- **业务功能**: 测试辅助函数

### tests/api/test_user.py
- **业务功能**: 用户 API 测试

### tests/api/test_project.py
- **业务功能**: 项目 API 测试

### tests/api/test_testcase.py
- **业务功能**: 用例 API 测试

### tests/api/test_execution.py
- **业务功能**: 执行 API 测试

### tests/api/test_defect.py
- **业务功能**: 缺陷 API 测试

### tests/api/test_ai_assistant.py
- **业务功能**: AI 助手 API 测试

### tests/api/test_sys_ai_config.py
- **业务功能**: AI 配置 API 测试

### tests/api/test_00_access_control.py
- **业务功能**: 访问控制测试

### tests/api/test_comprehensive.py
- **业务功能**: 综合测试

### tests/server_logs/test_ssh_host_key_policy.py
- **业务功能**: SSH 主机密钥策略测试

---

*文档生成时间：2026-04-26*
