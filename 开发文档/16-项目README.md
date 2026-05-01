# SmartTest（AITestProduct）

SmartTest 是一个面向软件测试全流程的 AI 辅助平台，覆盖测试设计、用例管理、执行报告、缺陷跟踪与性能任务管理，并集成大模型能力用于测试用例生成与分析。

---

## 1. 核心能力

- 测试资产管理：测试方法、测试设计、测试用例、测试步骤
- 执行与质量闭环：测试计划、测试报告、缺陷管理
- 性能任务：JMeter/Locust 场景任务管理与状态追踪
- API 执行引擎：基于 requests + Celery 的异步执行、基础断言与 JSON 执行报告
- 测试资产版本快照：用例关联 ReleasePlan 时自动生成 JSON 快照，支持版本回溯
- 测试质量分析：提供模块缺陷分布、通过率趋势、需求覆盖率等 ECharts 聚合接口
- 测试质量统计：新增 `TestQualityMetric` 指标快照与最近30天趋势分析接口
- 环境健康检查：任务执行前自动校验 DB/API/Redis，异常自动取消并邮件告警
- RAG 测试知识库：文章向量索引、语义检索与相似用例模板推荐
- AI 助手：模型连通性校验、同步/流式用例生成、RAG 检索
- 组织协作：用户、角色、组织、系统消息、敏感信息审批流程

---

## 2. 快速启动

### 2.0 一键启动（Windows 推荐）

在项目根目录双击：

- `start-all.bat`：同时启动后端 + 前端（会打开两个终端窗口）
- `start-backend.bat`：只启动后端
- `start-frontend.bat`：只启动前端

> 说明：后端会从项目根目录的 `.env` 读取 `DB_*` 等环境变量（`.env` 已加入 `.gitignore` 不会提交）。首次使用请先 `Copy-Item .env.example .env` 并填好数据库账号密码。

补充（与实时/异步能力相关）：

- **WebSocket（如 k6 实时指标、服务器日志实时 tail）需要 ASGI**：开发环境请用 `daphne` 启动（详见 `开发文档/99-项目全局扫描对账索引.md` §3/§6）。
- **异步任务（Celery）**：需要额外启动 worker（见本页 §4.2 与 `开发文档/99-项目全局扫描对账索引.md` §7.4）。

### 2.1 后端

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

后端默认地址：`http://127.0.0.1:8000`

### 2.2 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：`http://localhost:5173`

---

## 3. 文档导航

### 3.1 开发主文档（推荐阅读顺序）

| 文档 | 说明 |
|------|------|
| [开发文档/99-项目全局扫描对账索引.md](./开发文档/99-项目全局扫描对账索引.md) | **全局对账索引（路由树/WS/环境变量总表/脚本与 CI）**，建议作为单一事实源 |
| [开发文档/01-项目概述与快速启动.md](./开发文档/01-项目概述与快速启动.md) | 项目定位、技术栈、安装启动 |
| [开发文档/02-目录结构与架构设计.md](./开发文档/02-目录结构与架构设计.md) | 目录结构与前后端架构分层 |
| [开发文档/03-核心业务逻辑与模块说明.md](./开发文档/03-核心业务逻辑与模块说明.md) | 核心模型、流程与模块逻辑 |
| [开发文档/04-API接口与数据交互.md](./开发文档/04-API接口与数据交互.md) | 路由、认证、接口与数据约定 |
| [开发文档/05-测试指南与性能评测.md](./开发文档/05-测试指南与性能评测.md) | 测试体系、CI、性能评测现状 |
| [开发文档/06-部署与配置指南.md](./开发文档/06-部署与配置指南.md) | 环境变量、部署步骤、上线检查 |
| [开发文档/07-安全与权限基线.md](./开发文档/07-安全与权限基线.md) | 认证授权、数据隔离、配置安全 |
| [开发文档/08-故障排查与应急手册.md](./开发文档/08-故障排查与应急手册.md) | 典型故障、诊断流程、应急策略 |
| [开发文档/09-AI开发指南.md](./开发文档/09-AI开发指南.md) | AI 生成链路、Prompt/RAG、扩展与测试规范 |
| [开发文档/10-AI扩展开发模板.md](./开发文档/10-AI扩展开发模板.md) | 新增 AI 能力的实施清单与代码模板 |

### 3.2 专题文档

| 文档 | 说明 |
|------|------|
| [DEVELOPMENT.md](./DEVELOPMENT.md) | 代码结构与开发要点总览 |
| [README_API.md](./README_API.md) | 性能任务 API 专题 |
| [开发文档/13-API测试执行引擎开发文档.md](./开发文档/13-API测试执行引擎开发文档.md) | 执行引擎异步执行、重试、幂等与脱敏 |
| [开发文档/14-测试资产版本快照开发文档.md](./开发文档/14-测试资产版本快照开发文档.md) | 快照多版本策略与版本回溯 |
| [开发文档/15-测试质量分析接口开发文档.md](./开发文档/15-测试质量分析接口开发文档.md) | 质量分析口径、公式与缓存策略 |
| [开发文档/16-测试质量统计开发文档.md](./开发文档/16-测试质量统计开发文档.md) | 指标模型、计算公式、错误码、缓存策略与测试覆盖 |
| [开发文档/17-环境健康检查系统开发文档.md](./开发文档/17-环境健康检查系统开发文档.md) | 任务前环境校验、告警与扩展机制 |
| [开发文档/18-RAG测试知识库开发文档.md](./开发文档/18-RAG测试知识库开发文档.md) | 向量模型、检索过滤阈值、自动索引与重建命令 |
| [tests/api/README.md](./tests/api/README.md) | API 自动化测试说明 |
| [frontend/README.md](./frontend/README.md) | 前端开发与联调说明 |

---

## 4. 常用命令

```bash
# 运行 API 集成测试
pytest tests/api

# 仅冒烟测试
pytest -m smoke tests/api

# 生成前端生产包
cd frontend && npm run build

# 重建所有知识文章向量（并回填处理状态）
python manage.py reindex_knowledge_articles

# 仅重试失败文章任务
python manage.py reindex_knowledge_articles --failed-only
```

### 4.1 全项目一键冒烟测试（Windows，含 UI）

该冒烟会依次执行：

- 后端启动（`manage.py runserver`）并等待端口 `8000`
- 后端 API 冒烟：`pytest -m smoke tests/api`（生成 HTML 报告）
- 前端安装/构建：`npm ci` + `npm run build`
- 前端预览：`vite preview` 并等待端口 `4173`
- UI 冒烟：Playwright（登录 + 打开关键页面）

#### 4.1.1 前置条件

- 已准备好可登录账号（用于 API + UI）：必须设置环境变量 `TEST_API_USERNAME` / `TEST_API_PASSWORD`
- 后端依赖与前端依赖可安装（首次运行会较慢）
- 数据库/Redis 等服务已就绪（如果你的后端配置依赖它们）

#### 4.1.2 运行命令（PowerShell）

```powershell
# 在项目根目录运行
$env:TEST_API_USERNAME="admin"
$env:TEST_API_PASSWORD="your-password"

powershell -ExecutionPolicy Bypass -File .\scripts\smoke_all.ps1
```

可选参数：

- `-SkipFrontendBuild`：跳过 `npm ci + npm run build`
- `-SkipUi`：跳过 Playwright UI 冒烟（只跑后端 API 冒烟）

#### 4.1.3 报告产物

- `reports/api-test-report.html`：pytest HTML 报告
- `reports/playwright-report/`：Playwright HTML 报告

#### 4.1.4 常见失败原因

- 端口被占用：`127.0.0.1:8000`（后端）或 `127.0.0.1:4173`（前端预览）
- 未安装 Playwright 浏览器：执行 `cd frontend; npm run e2e:install`
- 缺少测试账号环境变量：未设置 `TEST_API_USERNAME` / `TEST_API_PASSWORD`

### 4.2 Celery Worker（Windows）

```powershell
# 标准 worker
powershell -ExecutionPolicy Bypass -File .\scripts\start-celery.ps1

# Windows 兼容模式（进程池问题时使用）
powershell -ExecutionPolicy Bypass -File .\scripts\start-celery-solo.ps1
```

---

## 5. 知识库文件上传（新增）

- 新增文章弹窗支持两种模式：`直接输入文本` / `上传文件提取文本`
- 上传格式：`.txt`、`.md`、`.pdf`、`.docx`
- 后端大小限制：默认 `10MB`（可通过环境变量 `KNOWLEDGE_UPLOAD_MAX_SIZE` 调整，单位字节）

### 5.1 接口

- `POST /api/assistant/knowledge/extract-text/`
  - `multipart/form-data`，字段：`file`
  - 作用：仅解析并返回纯文本，便于前端预览回填内容框
- `POST /api/assistant/knowledge-articles/`
  - 支持 `application/json` 与 `multipart/form-data`
  - `multipart` 模式字段示例：`title`、`category`、`tags`、`text_source=upload`、`source_file`
- `POST /api/assistant/knowledge/documents/ingest/`
  - 作用：知识文档入库（PDF/MD 上传或 URL 导入），异步向量化
  - 关键字段：`mode=upload|url`、`file|url`、`module_id?`、`category?`、`tags?`
- `GET /api/assistant/knowledge/documents/`
  - 作用：文档列表（支持 `page/page_size` 与 `status/category/module_id/tag/q` 过滤）
- `POST /api/assistant/knowledge/artifacts/`
  - 作用：保存“生成测试资产”（结构化测试计划/测试点/用例草稿等），便于追溯与复用
- `POST /api/ai/knowledge/ask/`
  - 作用：知识库问答（返回 `citations` 引用来源，可追溯）

### 5.2 依赖

知识库文件解析新增依赖：

- `pdfplumber`（PDF 文本提取）
- `python-docx`（Word 文本提取）

安装：

```bash
pip install -r requirements.txt
```

---

## 6. AI 生成用例参数（Agentic Workflow）

以下参数可通过环境变量调整（Django `settings.py` 已内置默认值）：

- `RAG_TOP_K`：RAG 检索召回条数，默认 `5`
- `RAG_MAX_CONTEXT_CHARS`：每条检索片段拼接到 Prompt 的最大长度，默认 `1200`
- `AI_GENERATE_CASES_MAX_TOKENS`：Phase 2 生成最大 token，默认 `8192`（最小不低于 `4096`）
- `AI_GENERATE_MIN_CASES`：最小期望用例条数，低于该值触发补生成，默认 `4`
- `AI_GENERATE_MAX_CASES`：最终最多保留条数，默认 `20`
- `AI_GENERATE_RETRY_ROUNDS`：补生成最大轮次，默认 `2`

### 6.1 调优建议

- 结果偏少：优先提高 `AI_GENERATE_MIN_CASES`（如 `6`），必要时提高 `AI_GENERATE_RETRY_ROUNDS`
- 响应偏慢：降低 `RAG_TOP_K` 或 `RAG_MAX_CONTEXT_CHARS`
- 输出过长：降低 `AI_GENERATE_MAX_CASES`
- 内容被截断：确认 `AI_GENERATE_CASES_MAX_TOKENS >= 4096`

### 6.2 PowerShell 示例

```powershell
$env:RAG_TOP_K="8"
$env:RAG_MAX_CONTEXT_CHARS="1800"
$env:AI_GENERATE_MIN_CASES="6"
$env:AI_GENERATE_MAX_CASES="24"
$env:AI_GENERATE_RETRY_ROUNDS="2"
$env:AI_GENERATE_CASES_MAX_TOKENS="8192"
python manage.py runserver
```

---

*文档版本：v1.0 | 最后更新：2026-04-09*
