# AI 测试平台 - 模块索引

## 模块总览

| 模块名 | 路径 | 功能描述 | 核心文件 |
|--------|------|----------|----------|
| 项目配置 | `AITestProduct/` | Django 项目核心配置 | settings.py, urls.py, celery.py, asgi.py |
| 用户管理 | `user/` | 用户、组织、权限、消息 | models.py, views.py, sys_views.py |
| 项目管理 | `project/` | 项目、发布计划、测试计划 | models.py, views.py, services/ |
| 测试用例 | `testcase/` | 用例管理、环境、版本控制 | models.py, views.py, services/ |
| 测试执行 | `execution/` | 执行引擎、WebSocket、调度 | engine.py, consumers.py, tasks.py |
| 缺陷管理 | `defect/` | 缺陷追踪与管理 | models.py, views.py |
| AI 助手 | `assistant/` | AI 生成、RAG、知识库 | views.py, services/, rag_*.py |
| 服务器日志 | `server_logs/` | 日志采集、AI 分析、工单 | views.py, es_client.py, ai_*.py |
| 公共模块 | `common/` | 基础模型、公共服务 | models.py, services/ |
| 脚本 | `scripts/` | 自动化脚本 | smoke_test.py |
| 测试 | `tests/` | API 测试 | api/*.py |

---

## 详细文档

1. [01-项目配置.md](./01-项目配置.md) - AITestProduct 目录配置说明
2. [02-user 用户管理模块.md](./02-user 用户管理模块.md) - 用户、组织、权限管理
3. [03-project 项目管理模块.md](./03-project 项目管理模块.md) - 项目、发布计划、测试计划
4. [04-testcase 测试用例模块.md](./04-testcase 测试用例模块.md) - 用例管理、环境、版本
5. [05-execution 测试执行模块.md](./05-execution 测试执行模块.md) - 执行引擎、WebSocket、调度
6. [06-defect 缺陷管理模块.md](./06-defect 缺陷管理模块.md) - 缺陷追踪
7. [07-assistant AI 助手模块.md](./07-assistant AI 助手模块.md) - AI 生成、RAG、知识库
8. [08-server_logs 服务器日志模块.md](./08-server_logs 服务器日志模块.md) - 日志采集、AI 分析
9. [09-common 公共模块.md](./09-common 公共模块.md) - 基础模型、公共服务
10. [10-scripts 脚本目录.md](./10-scripts 脚本目录.md) - 自动化脚本
11. [11-tests 测试目录.md](./11-tests 测试目录.md) - API 测试

---

## 技术栈

- **后端框架**: Django 4.2
- **API 框架**: Django REST Framework
- **WebSocket**: Django Channels + Redis
- **任务队列**: Celery
- **数据库**: MySQL
- **缓存**: Redis
- **向量数据库**: Chroma
- **日志检索**: Elasticsearch / Grafana Loki
- **AI 集成**: OpenAI / 智谱 AI / Ollama
- **前端**: Vue.js + Vite

---

## 核心业务流程

### 1. AI 生成用例流程
```
需求文档 → 知识库 RAG → AI 生成 → 去重 → 人工审核 → 入库
```

### 2. 测试执行流程
```
用例选择 → 环境配置 → 触发执行 → WebSocket 推送 → 结果记录
```

### 3. 日志分析流程
```
SSH 采集/ES 检索 → AI 分析 → 工单草稿 → 人工确认 → 创建缺陷
```

### 4. 性能测试流程
```
API 用例 → AI 转 k6 脚本 → 执行压测 → 指标采集 → 报告生成
```

---

*文档更新时间：2026-04-26*
