---
name: AI 测试平台项目概况
description: SmartTest 全流程 AI 测试平台技术架构与功能模块总览
type: project
---

# SmartTest 全流程 AI 测试平台 — 项目概况

> 🤖 **一句话介绍**：这是一个集「测试管理 +AI 生成 + 缺陷追踪」于一体的企业级测试平台，后端 Django + 前端 Vue3，AI 模型接入智谱/GLM 系列。

---

## 📋 项目基本信息

| 项目 | 信息 |
|------|------|
| **项目名称** | SmartTest 全流程 AI 测试平台 |
| **技术栈** | Django 4.2 + DRF + Vue 3 + Vite + Element Plus |
| **数据库** | MySQL（`django.db.backends.mysql`） |
| **缓存** | Django-Redis（可选，降级为 LocMem） |
| **AI 模型** | 智谱 GLM 系列（glm-4.7-flash）、讯飞 MaaS、OpenAI 兼容接口 |
| **向量库** | ChromaDB（RAG 用例去重与检索） |

---

## 🏗️ 后端架构（5 个核心 App）

### 1️⃣ `user` — 用户与组织管理
**职责**：用户体系、权限控制、消息通知、敏感变更审批

| 模型 | 说明 |
|------|------|
| `User` | 继承 AbstractUser，扩展真实姓名、手机号、头像、系统管理员标识 |
| `UserChangeRequest` | 敏感信息变更申请（用户名/密码），需管理员审核 |
| `SystemMessage` | 站内系统消息，关联变更申请 |
| `AIModelConfig` | 平台级 AI 模型配置（单条记录，存储 API Key/Base URL） |
| `Organization` | 组织管理 |
| `SystemMessageSetting` | 消息通知设置（站内/邮件/短信/日报） |

**核心接口**：
- `POST /api/user/login/` — 登录获取 Token
- `POST /api/user/register/` — 注册（含验证码）
- `GET/PUT /api/user/current-user/` — 获取/更新当前用户
- `GET/POST /api/sys/ai-config/` — 系统级 AI 模型配置

---

### 2️⃣ `project` — 项目管理
**职责**：测试项目、任务看板、发布计划

| 模型 | 说明 |
|------|------|
| `TestProject` | 项目主表，支持父子项目层级，含进度百分比 |
| `TestTask` | 任务看板，关联经办人 |
| `ReleasePlan` | 发布计划，关联项目与版本 |

**核心接口**：
- `GET/POST /api/project/projects/` — 项目列表/创建
- `GET/POST /api/project/tasks/` — 任务看板
- `GET/POST /api/project/releases/` — 发布计划

---

### 3️⃣ `testcase` — 测试资产管理
**职责**：测试方法、测试设计、用例与步骤、测试模块

| 模型 | 说明 |
|------|------|
| `TestApproach` | 测试方案/方法，支持多图上传 |
| `TestDesign` | 测试设计，关联需求/测试点/用例数量 |
| `TestModule` | 测试模块，支持树形结构，按测试类型分类 |
| `TestCase` | 用例主表，支持 5 种类型（功能/API/性能/安全/UI 自动化） |
| `ApiTestCase` | API 用例扩展表（多表继承），含请求/响应定义 |
| `PerfTestCase` | 性能用例扩展表 |
| `SecurityTestCase` | 安全用例扩展表 |
| `UITestCase` | UI 自动化用例扩展表 |
| `TestCaseStep` | 用例步骤表 |
| `ExecutionLog` | API 执行日志，含完整 Request/Response 快照 |
| `ApiTestLog` | 兼容旧表的 API 执行记录 |

**核心接口**：
- `GET/POST /api/testcase/cases/` — 用例管理
- `GET/POST /api/testcase/modules/` — 模块管理
- `GET/POST /api/testcase/designs/` — 测试设计
- `POST /api/ai/generate-cases/` — AI 生成用例（同步）
- `POST /api/ai/generate-cases-stream/` — AI 生成用例（SSE 流式）

---

### 4️⃣ `execution` — 执行与报告
**职责**：测试计划、测试报告、性能任务、仪表盘

| 模型 | 说明 |
|------|------|
| `TestPlan` | 测试计划，关联版本/测试人员，含覆盖率/通过率 |
| `TestReport` | 测试报告，关联计划，含 Request/Response 快照 |
| `PerfTask` | 性能任务（JMeter/Locust），状态机：pending→running→completed/failed |

**核心接口**：
- `GET/POST /api/execution/plans/` — 测试计划
- `GET/POST /api/execution/reports/` — 测试报告
- `GET/POST /api/perf/tasks/` — 性能任务列表
- `POST /api/perf/tasks/{task_id}/run/` — 触发性能任务执行
- `GET /api/execution/dashboard/summary/` — 仪表盘聚合数据

---

### 5️⃣ `defect` — 缺陷管理
**职责**：缺陷列表、看板、发布关联

| 模型 | 说明 |
|------|------|
| `TestDefect` | 缺陷主表，含严重程度/优先级/状态/处理人 |

**核心接口**：
- `GET/POST /api/defect/defects/` — 缺陷列表
- `GET/POST /api/defect/board/` — 缺陷看板

---

## 🎨 前端架构（17 个模块页面）

### 路由结构

| 路径前缀 | 模块 | 说明 |
|----------|------|------|
| `/login` `/register` | 认证 | 登录/注册 |
| `/dashboard` | 仪表盘 | 统计卡片/折线图/活动流 |
| `/user/center` | 用户中心 | 个人信息/头像/密码修改 |
| `/projects` | 项目管理 | 项目列表/详情/任务看板 |
| `/test-approach` | 测试方法 | 测试方案管理 |
| `/test-design` | 测试设计 | 测试设计管理 |
| `/test-plan` | 测试计划 | 计划创建/执行 |
| `/test-case` | 用例管理 | 用例 CRUD/导入/导出 |
| `/test-report` | 测试报告 | 报告查看/分析 |
| `/defect/list` `/defect/board` | 缺陷管理 | 列表/看板视图 |
| `/defect/release` | 缺陷发布 | 版本关联 |
| `/performance/tasks` | 性能任务 | 独立全屏布局 |
| `/ai-assistant` | AI 助手 | 用例生成对话框 |
| `/system/org` `/system/role` `/system/user` | 系统管理 | 组织/角色/用户（仅管理员） |
| `/system/messages` | 消息设置 | 通知配置 |
| `/knowledge` | 知识库 | RAG 向量库管理 |
| `/help` | 帮助中心 | 使用指南 |

### 技术要点

- **状态管理**：Vuex/Pinia（根据实际配置）
- **路由守卫**：未登录重定向 `/login`，系统管理路径校验 `is_system_admin`
- **API 封装**：`src/api/` 下按域拆分（`auth.js`、`user.js`、`project.js`、`testcase.js`、`execution.js`、`perfTask.js`、`assistant.js`）
- **Axios 拦截器**：统一注入 Token，401 自动跳转登录
- **Vite 代理**：`/api` → `http://127.0.0.1:8000`

---

## 🤖 AI 能力集成

### 1. 模型连接测试
- `POST /api/ai/test-connection/` — OpenAI SDK 方式测试
- `POST /api/ai/verify-connection/` — 固定智谱 v4 接口校验
- `POST /api/assistant/test-connection/` — 原生 HTTP 方式测试

### 2. 用例生成（RAG 增强）
- `POST /api/ai/generate-cases/` — 同步生成，返回 JSON 数组
- `POST /api/ai/generate-cases-stream/` — SSE 流式生成，实时展示

**技术亮点**：
- 强制简体中文输出（Prompt 约束）
- RAG 检索现有用例去重（ChromaDB）
- 自动识别 API 用例并补充 `businessId`
- 括号补全容错解析（应对截断）
- 相似度去重（caseName + steps）

---

## 📊 数据模型总览

```
common.BaseModel (抽象基类)
├── creator / updater (FK → User)
├── create_time / update_time
└── is_deleted (软删除)

user.User
├── UserChangeRequest
├── SystemMessage
├── AIModelConfig
├── Organization
└── SystemMessageSetting

project.TestProject
├── TestTask
└── ReleasePlan

testcase.TestApproach
├── TestApproachImage
├── TestDesign
├── TestModule
├── TestCase
│   ├── ApiTestCase (多表继承)
│   ├── PerfTestCase
│   ├── SecurityTestCase
│   └── UITestCase
├── TestCaseStep
├── ExecutionLog
└── ApiTestLog

execution.TestPlan
├── TestReport
└── PerfTask

defect.TestDefect
```

---

## 🚀 快速启动

### 后端
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_perf_tasks  # 可选：初始化演示数据
python manage.py runserver
```

### 前端
```bash
cd frontend
npm install
npm run dev
```

---

## 📌 关键设计决策

1. **软删除优先**：所有业务表通过 `is_deleted` 实现软删除，保留历史数据
2. **用例编号按类型独立递增**：`case_number` 在 `test_type` 维度内唯一，避免跨类型冲突
3. **性能任务 ID 生成**：`PT-0001` 格式，并发冲突时自动重试
4. **AI 输出强制中文**：Prompt 中双重约束（中文 + 英文），确保用例正文全中文
5. **SSE 流式生成**：避免 DRF 内容协商问题，使用原生 Django View + StreamingHttpResponse
6. **仪表盘真实数据**：统计卡片/图表均基于真实数据库聚合，空表返回 0 而非占位符

---

*文档版本：v1.0 | 最后更新：2026-04-09*
