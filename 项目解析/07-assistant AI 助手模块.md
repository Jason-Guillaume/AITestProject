# assistant AI 助手模块

## 模块概述
负责 AI 辅助测试生成、知识库 RAG、AI 治理、用例生成、错误分析等 AI 相关功能。

## 文件列表

### __init__.py
- **作用**: Python 包初始化

### ai_errors.py
- **作用**: AI 错误定义
- **业务功能**: 定义 AI 相关错误类型

### ai_generate_strategies.py
- **作用**: AI 生成策略
- **业务功能**: 定义 AI 生成用例的策略逻辑

### ai_prompts.py
- **作用**: AI 提示词模板
- **业务功能**: 定义各种 AI 交互的提示词模板

### ai_urls.py
- **作用**: AI 功能路由
- **业务功能**: 定义 AI 相关 API 路径

### api_case_generation.py
- **作用**: API 用例生成
- **业务功能**: 使用 AI 生成 API 测试用例

### apps.py
- **作用**: 应用配置
- **业务功能**: 定义 AssistantConfig

### embeddings_zhipu.py
- **作用**: 智谱 Embedding 服务
- **业务功能**: 调用智谱 AI 的 Embedding API

### error_parser.py
- **作用**: 错误解析器
- **业务功能**: 解析测试执行错误信息

### generated_case_dedup.py
- **作用**: 生成用例去重
- **业务功能**: 对 AI 生成的用例进行去重处理

### knowledge_rag.py
- **作用**: 知识库 RAG 服务
- **业务功能**: 实现知识库检索增强生成

### models.py
- **作用**: 数据模型定义
- **业务功能**:
  - `KnowledgeArticle`: 知识库文章
  - `KnowledgeDocument`: 知识库文档
  - `GeneratedTestArtifact`: 生成的测试资产
  - `AiUsageEvent`: AI 调用审计事件
  - `AiPatch`: AI 变更补丁
  - `AiCaseGenerationRun`: AI 生成用例批次

### permissions.py
- **作用**: 权限配置
- **业务功能**: AI 功能访问权限控制

### rag_chroma.py
- **作用**: Chroma 向量数据库
- **业务功能**: 实现向量数据库的存储与检索

### rag_pipeline.py
- **作用**: RAG 流水线
- **业务功能**: 实现 RAG 完整流程

### serialize.py
- **作用**: 序列化器定义
- **业务功能**: AI 相关数据序列化

### signals.py
- **作用**: Django 信号处理器
- **业务功能**: 监听相关事件触发 AI 处理

### tasks.py
- **作用**: Celery 异步任务
- **业务功能**: AI 生成的异步任务

### tests.py
- **作用**: 单元测试入口

### urls.py
- **作用**: 助手模块路由
- **业务功能**: AI 助手相关 API 路径

### views.py
- **作用**: 助手视图
- **业务功能**:
  - AI 知识库管理
  - AI 用例生成
  - 知识库问答
  - AI 配置管理

### services/__init__.py
- **作用**: 服务层初始化

### services/ai_engine.py
- **作用**: AI 引擎服务
- **业务功能**: AI 生成核心引擎

### services/ai_governance.py
- **作用**: AI 治理服务
- **业务功能**: 实现 AI 配额、并发控制、审计

### services/case_batch_generation.py
- **作用**: 用例批量生成服务
- **业务功能**: 批量生成测试用例

### services/case_fix_from_execution.py
- **作用**: 基于执行结果修复用例
- **业务功能**: 根据执行失败自动修复用例

### services/document_parser.py
- **作用**: 文档解析服务
- **业务功能**: 解析知识库文档

### services/rag_service.py
- **作用**: RAG 服务
- **业务功能**: RAG 检索与生成服务

### services/security_rules.py
- **作用**: 安全规则服务
- **业务功能**: AI 安全规则检查

### services/semantic_dedup.py
- **作用**: 语义去重服务
- **业务功能**: 基于语义的用例去重

---
