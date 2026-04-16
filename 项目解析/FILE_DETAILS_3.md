# 完整 Python 文件业务说明 - 续 2

## 六、defect 缺陷管理模块 (8 个文件)

### defect/__init__.py
```
位置：/d/AITestProduct/defect/__init__.py
业务角色：Python 包初始化
```

### defect/admin.py
```
位置：/d/AITestProduct/defect/admin.py
业务角色：Admin 注册
注册模型：TestDefect
```

### defect/apps.py
```
位置：/d/AITestProduct/defect/apps.py
业务角色：应用配置
配置类：DefectConfig
```

### defect/models.py
```
位置：/d/AITestProduct/defect/models.py
业务角色：缺陷领域模型
数据库表:

test_defect (TestDefect)
  字段:
    - defect_no: 缺陷编号 (唯一)
    - defect_name: 缺陷标题
    - release_version: 关联版本 (FK)
    - severity: 严重程度 (1 致命/2 严重/3 一般/4 建议)
    - priority: 优先级 (1 高/2 中/3 低)
    - status: 状态 (1 新缺陷/2 处理中/3 已拒绝/4 已关闭)
    - handler: 当前处理人 (FK)
    - module: 所属模块 (FK)
    - defect_content: 缺陷内容
    - reproduction_steps: 复现步骤 (JSON)
    - attachments: 附件列表 (JSON)
    - environment: 发生环境
  约束：defect_no + is_deleted 唯一
  用途：缺陷主表
```

### defect/serialize.py
```
位置：/d/AITestProduct/defect/serialize.py
业务角色：缺陷序列化器
包含：TestDefectSerializer
```

### defect/urls.py
```
位置：/d/AITestProduct/defect/urls.py
业务角色：缺陷路由
路径：
  - /api/defect/defects/            -> 缺陷管理
  - /api/defect/defects/<id>/       -> 缺陷详情
```

### defect/views.py
```
位置：/d/AITestProduct/defect/views.py
业务角色：缺陷视图
功能:
  - 缺陷 CRUD
  - 缺陷状态流转
  - 缺陷关联版本和模块
  - 缺陷列表查询与筛选
  - 缺陷统计
```

### defect/tests.py
```
位置：/d/AITestProduct/defect/tests.py
业务角色：单元测试
```

---

## 七、assistant AI 助手模块 (24 个文件)

### assistant/__init__.py
```
位置：/d/AITestProduct/assistant/__init__.py
业务角色：Python 包初始化
```

### assistant/admin.py
```
位置：/d/AITestProduct/assistant/admin.py
业务角色：Admin 注册
注册模型：知识库、AI 相关模型
```

### assistant/apps.py
```
位置：/d/AITestProduct/assistant/apps.py
业务角色：应用配置
配置类：AssistantConfig
```

### assistant/models.py
```
位置：/d/AITestProduct/assistant/models.py
业务角色：AI 领域模型
数据库表:

1. knowledge_article (KnowledgeArticle)
   字段：org, visibility_scope, category, title, markdown_content, tags
   分类：template/best_practice/faq/functional_test/api_test/
         performance_test/security_test/ui_automation_test
   用途：知识库文章

2. knowledge_document (KnowledgeDocument)
   字段：org, visibility_scope, title, file_name, module, category,
         document_type, tags, source_type, article, file_path, 
         source_url, status, vector_db_id, semantic_summary, 
         semantic_chunks, error_message
   状态：pending/processing/completed/failed
   用途：知识库文档

3. generated_test_artifact (GeneratedTestArtifact)
   字段：org, project, module, source_document, source_question,
         artifact_type, title, content, citations, model_used
   类型：test_plan/test_points/case_draft/api_scenario
   用途：生成的测试资产

4. ai_usage_event (AiUsageEvent)
   字段：user, action, endpoint, success, status_code, error_code,
         error_message, model_used, test_type, module_id, streamed,
         all_covered, cases_count, latency_ms, prompt_chars, 
         output_chars, meta, created_at
   动作：generate_cases/generate_cases_stream/phase1_preview/
         test_connection/verify_connection/knowledge_autofill/
         knowledge_ask/security_generate/security_analyze
   用途：AI 调用审计

5. ai_patch (AiPatch)
   字段：creator, target_type, target_id, source_execution_log_id,
         status, risk_level, summary, risks, before, after, changes,
         applied_at, rolled_back_at, created_at, updated_at
   状态：draft/applied/rolled_back/cancelled
   风险：low/medium/high
   用途：AI 变更补丁

6. ai_case_generation_run (AiCaseGenerationRun)
   字段：user, action, test_type, module_id, streamed, model_used,
         prompt_version, params, requirement_sha256, requirement_preview,
         ext_config, phase1_analysis, phase1_override, success,
         all_covered, cases_count, prompt_chars, output_chars,
         latency_ms, error_code, error_message, meta, created_at
   用途：AI 生成用例批次记录
```

### assistant/urls.py
```
位置：/d/AITestProduct/assistant/urls.py
业务角色：AI 助手路由
路径：
  - /api/assistant/knowledge/articles/    -> 知识文章
  - /api/assistant/knowledge/documents/   -> 知识文档
  - /api/assistant/generate/              -> AI 生成
  - /api/assistant/config/                -> AI 配置
```

### assistant/ai_urls.py
```
位置：/d/AITestProduct/assistant/ai_urls.py
业务角色：AI 功能路由
路径：
  - /api/ai/generate-cases/               -> 生成用例
  - /api/ai/knowledge/ask/                -> 知识库问答
  - /api/ai/config/test/                  -> 配置测试
```

### assistant/views.py
```
位置：/d/AITestProduct/assistant/views.py
业务角色：AI 助手视图
功能:
  - 知识库管理 (文章/文档)
  - AI 用例生成
  - 知识库问答
  - AI 配置管理
  - 生成资产查看
```

### assistant/tests.py
```
位置：/d/AITestProduct/assistant/tests.py
业务角色：单元测试
```

### assistant/tasks.py
```
位置：/d/AITestProduct/assistant/tasks.py
业务角色：Celery AI 任务
功能:
  - 异步 AI 生成用例
  - 异步文档解析
  - 异步向量入库
```

### assistant/signals.py
```
位置：/d/AITestProduct/assistant/signals.py
业务角色：信号处理器
监听：知识库文档上传
动作：触发向量入库任务
```

### assistant/permissions.py
```
位置：/d/AITestProduct/assistant/permissions.py
业务角色：AI 权限控制
功能：AI 功能访问权限检查
```

### assistant/serialize.py
```
位置：/d/AITestProduct/assistant/serialize.py
业务角色：AI 数据序列化
包含：知识库、生成资产、审计事件等序列化器
```

### assistant/ai_errors.py
```
位置：/d/AITestProduct/assistant/ai_errors.py
业务角色：AI 错误定义
功能：定义 AI 相关错误类型
```

### assistant/ai_prompts.py
```
位置：/d/AITestProduct/assistant/ai_prompts.py
业务角色：AI 提示词模板
功能：定义各种 AI 交互的提示词模板
```

### assistant/ai_generate_strategies.py
```
位置：/d/AITestProduct/assistant/ai_generate_strategies.py
业务角色：AI 生成策略
功能：定义 AI 生成用例的策略逻辑
```

### assistant/api_case_generation.py
```
位置：/d/AITestProduct/assistant/api_case_generation.py
业务角色：API 用例生成
功能：使用 AI 生成 API 测试用例
```

### assistant/error_parser.py
```
位置：/d/AITestProduct/assistant/error_parser.py
业务角色：错误解析
功能：解析测试执行错误信息
```

### assistant/generated_case_dedup.py
```
位置：/d/AITestProduct/assistant/generated_case_dedup.py
业务角色：生成用例去重
功能：对 AI 生成的用例进行去重处理
```

### assistant/knowledge_rag.py
```
位置：/d/AITestProduct/assistant/knowledge_rag.py
业务角色：知识库 RAG
功能：实现知识库检索增强生成
```

### assistant/embeddings_zhipu.py
```
位置：/d/AITestProduct/assistant/embeddings_zhipu.py
业务角色：智谱 Embedding 服务
功能：调用智谱 AI 的 Embedding API
```

### assistant/rag_chroma.py
```
位置：/d/AITestProduct/assistant/rag_chroma.py
业务角色：Chroma 向量数据库
功能：实现向量数据库的存储与检索
```

### assistant/rag_pipeline.py
```
位置：/d/AITestProduct/assistant/rag_pipeline.py
业务角色：RAG 流水线
功能：实现 RAG 完整流程 (检索->生成)
```

### assistant/management/__init__.py
```
位置：/d/AITestProduct/assistant/management/__init__.py
业务角色：Management 命令
```

### assistant/services/__init__.py
```
位置：/d/AITestProduct/assistant/services/__init__.py
业务角色：服务层初始化
```

### assistant/services/ai_engine.py
```
位置：/d/AITestProduct/assistant/services/ai_engine.py
业务角色：AI 引擎核心
功能：AI 生成核心引擎
```

### assistant/services/ai_governance.py
```
位置：/d/AITestProduct/assistant/services/ai_governance.py
业务角色：AI 治理服务
功能：实现 AI 配额、并发控制、审计
```

### assistant/services/case_batch_generation.py
```
位置：/d/AITestProduct/assistant/services/case_batch_generation.py
业务角色：批量用例生成
功能：批量生成测试用例
```

### assistant/services/case_fix_from_execution.py
```
位置：/d/AITestProduct/assistant/services/case_fix_from_execution.py
业务角色：基于执行修复用例
功能：根据执行失败自动修复用例
```

### assistant/services/document_parser.py
```
位置：/d/AITestProduct/assistant/services/document_parser.py
业务角色：文档解析服务
功能：解析知识库文档
```

### assistant/services/rag_service.py
```
位置：/d/AITestProduct/assistant/services/rag_service.py
业务角色：RAG 服务
功能：RAG 检索与生成服务
```

### assistant/services/security_rules.py
```
位置：/d/AITestProduct/assistant/services/security_rules.py
业务角色：安全规则服务
功能：AI 安全规则检查
```

### assistant/services/semantic_dedup.py
```
位置：/d/AITestProduct/assistant/services/semantic_dedup.py
业务角色：语义去重服务
功能：基于语义的用例去重
```

---

## 八、server_logs 服务器日志模块 (18 个文件)

### server_logs/__init__.py
```
位置：/d/AITestProduct/server_logs/__init__.py
业务角色：Python 包初始化
```

### server_logs/admin.py
```
位置：/d/AITestProduct/server_logs/admin.py
业务角色：Admin 注册
```

### server_logs/apps.py
```
位置：/d/AITestProduct/server_logs/apps.py
业务角色：应用配置
配置类：ServerLogsConfig
```

### server_logs/models.py
```
位置：/d/AITestProduct/server_logs/models.py
业务角色：日志领域模型
数据库表:

1. server_logs_remote_host (RemoteLogServer)
   字段：name, host, port, username, password_enc, private_key_enc,
         server_type, default_log_path, organization
   加密：password/private_key 使用 Fernet 加密
   用途：远程 SSH 日志主机配置

2. server_logs_audit_event (ServerLogAuditEvent)
   字段：user, action, remote_log_server, organization, meta, 
         client_ip, created_at
   动作：ws_connect/ws_disconnect/ws_stop/analyze/auto_ticket/search/
         host_create/host_update/host_delete
   用途：日志操作审计

3. server_logs_auto_ticket_job (LogAutoTicketJob)
   字段：user, remote_log_server, anchor_text, anchor_ts, 
         window_seconds, es_limit, status, celery_task_id,
         error_message, draft, meta, create_defect_requested,
         defect_handler, defect_release_version, defect_module,
         created_defect, created_at, updated_at
   状态：pending/processing/success/failed
   用途：AI 工单草稿任务
```

### server_logs/urls.py
```
位置：/d/AITestProduct/server_logs/urls.py
业务角色：日志路由
路径：
  - /api/server-logs/hosts/             -> 主机管理
  - /api/server-logs/tail/              -> 实时日志
  - /api/server-logs/search/            -> 历史检索
  - /api/server-logs/analyze/           -> AI 分析
  - /api/server-logs/tickets/           -> 工单管理
```

### server_logs/views.py
```
位置：/d/AITestProduct/server_logs/views.py
业务角色：日志视图
功能:
  - 远程主机管理
  - 实时日志采集
  - 历史日志检索
  - AI 日志分析
  - 工单自动生成
```

### server_logs/tests.py
```
位置：/d/AITestProduct/server_logs/tests.py
业务角色：单元测试
```

### server_logs/tasks.py
```
位置：/d/AITestProduct/server_logs/tasks.py
业务角色：Celery 日志任务
功能：日志分析异步任务
```

### server_logs/routing.py
```
位置：/d/AITestProduct/server_logs/routing.py
业务角色：WebSocket 路由
路径：
  - ws/logs/tail/<host_id>/             -> 实时日志推送
```

### server_logs/consumers.py
```
位置：/d/AITestProduct/server_logs/consumers.py
业务角色：WebSocket 消费者
功能：实时日志推送
```

### server_logs/serializers.py
```
位置：/d/AITestProduct/server_logs/serializers.py
业务角色：日志序列化
```

### server_logs/access.py
```
位置：/d/AITestProduct/server_logs/access.py
业务角色：日志访问控制
功能：控制日志访问权限
```

### server_logs/audit.py
```
位置：/d/AITestProduct/server_logs/audit.py
业务角色：审计服务
功能：记录日志模块的操作审计
```

### server_logs/crypto.py
```
位置：/d/AITestProduct/server_logs/crypto.py
业务角色：加密服务
功能：SSH 凭据的加密/解密
```

### server_logs/es_client.py
```
位置：/d/AITestProduct/server_logs/es_client.py
业务角色：Elasticsearch 客户端
功能：ES 查询与写入
```

### server_logs/log_context.py
```
位置：/d/AITestProduct/server_logs/log_context.py
业务角色：日志上下文
功能：管理日志查询上下文
```

### server_logs/ssh_tail.py
```
位置：/d/AITestProduct/server_logs/ssh_tail.py
业务角色：SSH 日志 tail
功能：通过 SSH 远程 tail 日志文件
```

### server_logs/validators.py
```
位置：/d/AITestProduct/server_logs/validators.py
业务角色：数据验证
功能：SSH 配置等数据验证
```

### server_logs/ai_analyze.py
```
位置：/d/AITestProduct/server_logs/ai_analyze.py
业务角色：AI 日志分析
功能：使用 AI 分析日志中的问题
```

### server_logs/ai_ticket.py
```
位置：/d/AITestProduct/server_logs/ai_ticket.py
业务角色：AI 工单生成
功能：基于日志自动生成工单草稿
```

### server_logs/defect_create.py
```
位置：/d/AITestProduct/server_logs/defect_create.py
业务角色：缺陷创建服务
功能：基于日志分析自动创建缺陷
```

---

## 九、common 公共模块 (7 个文件)

### common/__init__.py
```
位置：/d/AITestProduct/common/__init__.py
业务角色：Python 包初始化
```

### common/admin.py
```
位置：/d/AITestProduct/common/admin.py
业务角色：Admin 配置
注册模型：AuditEvent
```

### common/apps.py
```
位置：/d/AITestProduct/common/apps.py
业务角色：应用配置
配置类：CommonConfig
```

### common/models.py
```
位置：/d/AITestProduct/common/models.py
业务角色：基础模型定义
数据库表:

1. (抽象) BaseModel
   字段：creator, updater, create_time, update_time, is_deleted
   用途：所有业务模型基类，提供通用字段

2. audit_event (AuditEvent)
   字段：action, object_app, object_model, object_id, object_repr,
         request_path, ip, user_agent, before, after, extra,
         creator, create_time
   动作：create/update/delete/export/execute
   用途：审计事件记录
```

### common/serialize.py
```
位置：/d/AITestProduct/common/serialize.py
业务角色：公共序列化器
功能：通用数据序列化模板
```

### common/views.py
```
位置：/d/AITestProduct/common/views.py
业务角色：公共视图
功能：BaseModelViewSet 基类，提供通用 CRUD 视图
```

### common/tests.py
```
位置：/d/AITestProduct/common/tests.py
业务角色：单元测试
```

### common/services/__init__.py
```
位置：/d/AITestProduct/common/services/__init__.py
业务角色：服务层初始化
```

### common/services/audit.py
```
位置：/d/AITestProduct/common/services/audit.py
业务角色：审计服务
功能：实现审计事件的记录逻辑
```

---

## 十、scripts 脚本目录 (2 个文件)

### scripts/smoke_test.py
```
位置：/d/AITestProduct/scripts/smoke_test.py
业务角色：Smoke 测试脚本
功能：执行基本的冒烟测试验证
```

### scripts/smoke_batch_ops.py
```
位置：/d/AITestProduct/scripts/smoke_batch_ops.py
业务角色：批量操作冒烟测试
功能：执行批量操作的冒烟测试
```

---

## 十一、tests 测试目录 (13 个文件)

### tests/api/__init__.py
```
位置：/d/AITestProduct/tests/api/__init__.py
业务角色：API 测试包初始化
```

### tests/api/conftest.py
```
位置：/d/AITestProduct/tests/api/conftest.py
业务角色：pytest 配置
功能：定义测试 fixture 和配置
```

### tests/api/_helpers.py
```
位置：/d/AITestProduct/tests/api/_helpers.py
业务角色：测试辅助函数
功能：提供测试用的辅助函数和工具
```

### tests/api/test_user.py
```
位置：/d/AITestProduct/tests/api/test_user.py
业务角色：用户 API 测试
功能：测试用户相关 API
```

### tests/api/test_project.py
```
位置：/d/AITestProduct/tests/api/test_project.py
业务角色：项目 API 测试
功能：测试项目相关 API
```

### tests/api/test_testcase.py
```
位置：/d/AITestProduct/tests/api/test_testcase.py
业务角色：用例 API 测试
功能：测试用例相关 API
```

### tests/api/test_execution.py
```
位置：/d/AITestProduct/tests/api/test_execution.py
业务角色：执行 API 测试
功能：测试执行相关 API
```

### tests/api/test_defect.py
```
位置：/d/AITestProduct/tests/api/test_defect.py
业务角色：缺陷 API 测试
功能：测试缺陷相关 API
```

### tests/api/test_ai_assistant.py
```
位置：/d/AITestProduct/tests/api/test_ai_assistant.py
业务角色：AI 助手 API 测试
功能：测试 AI 相关 API
```

### tests/api/test_sys_ai_config.py
```
位置：/d/AITestProduct/tests/api/test_sys_ai_config.py
业务角色：AI 配置 API 测试
功能：测试 AI 配置相关 API
```

### tests/api/test_00_access_control.py
```
位置：/d/AITestProduct/tests/api/test_00_access_control.py
业务角色：访问控制测试
功能：测试 API 权限控制
```

### tests/api/test_comprehensive.py
```
位置：/d/AITestProduct/tests/api/test_comprehensive.py
业务角色：综合测试
功能：综合场景测试
```

### tests/server_logs/test_ssh_host_key_policy.py
```
位置：/d/AITestProduct/tests/server_logs/test_ssh_host_key_policy.py
业务角色：SSH 主机密钥策略测试
功能：测试 SSH 主机密钥策略配置
```

---

*文档生成时间：2026-04-26*
