# 26-AI生成用例：Run 追溯与批量导入开发文档

## 0. 需求来源与开发动因

- **业务价值摘要**：让“AI 生成 → 导入用例 → 后续维护/执行”形成可追溯闭环，减少导入失败与联调成本。
- **现状痛点**
  - 导入依赖前端逐条创建模块/用例/步骤，**慢、易半成功**，失败原因不集中。
  - 导入后缺少“这条用例来自哪次 AI 生成”的关联，**无法复盘 prompt/参数/模型回归**。
- **建设目标**
  - 引入 “AI 生成批次 Run” 作为追溯主键（run_id）
  - 新增后端事务型批量导入接口，一次请求导入 N 条并返回逐条结果
  - 审计事件补齐 `run_id/prompt_version` 等关键 meta

---

## 1. 能力范围（本期）

### 1.1 新增 Run 模型（后端）

- 新增模型：`assistant.models.AiCaseGenerationRun`
- **记录内容**（重点）
  - `user/action/test_type/module_id/streamed/model_used`
  - `prompt_version`
  - `requirement_sha256`（哈希）+ `requirement_preview`（脱敏摘要）
  - `phase1_analysis`、`phase1_override`
  - `success/all_covered/cases_count/latency_ms/prompt_chars/output_chars`
  - `meta`（脱敏 JSON）
- **安全约束**
  - 不保存完整敏感原文（仅 hash + 少量摘要 + 结构化结果）
  - `ext_config/params` 仅保存 key 列表与长度统计（避免 spec/长文本落库）

### 1.2 用例与 Run 关联（后端）

- `testcase.models.TestCase` 新增字段：
  - `ai_run`：`ForeignKey(assistant.AiCaseGenerationRun, null=True, on_delete=SET_NULL)`

### 1.3 生成接口回传 run_id（前后端）

- 同步生成：`POST /api/ai/generate-cases/`
  - 响应新增 `run_id`
- 流式生成：`POST /api/ai/generate-cases-stream/`
  - SSE `done` 事件新增 `run_id`

### 1.4 批量导入接口（后端）

- 新增接口：`POST /api/testcase/cases/ai-import/`
- 特性：
  - 外层事务 + 每条 savepoint：**成功的保留，失败的回滚**，并返回逐条错误
  - 支持 `run_id` 写入到导入用例的 `ai_run`
  - 支持 `module_name` 自动复用/创建模块；缺失时可用 `default_module_id` 兜底

### 1.5 前端导入改造

- `frontend/src/components/TestCaseModal.vue`
  - 导入由“逐条 create 模块/用例/步骤”改为调用 `ai-import` 一次完成
  - 从 SSE `done.run_id` 保存到本地，导入时带给后端

---

## 2. 代码变更清单

### 2.1 后端

- `assistant/models.py`
  - 新增 `AiCaseGenerationRun`
- `assistant/migrations/0010_aicasegenerationrun.py`
  - 新增表 `ai_case_generation_run`
- `assistant/views.py`
  - 同步/流式生成落库 Run，并将 `run_id` 回传给前端
  - `AiUsageEvent.meta` 补齐 `run_id/prompt_version`
- `testcase/models.py`
  - `TestCase` 新增 `ai_run` 外键
- `testcase/migrations/0026_testcase_ai_run_fk.py`
  - 为 `test_case` 表新增 `ai_run_id`
- `testcase/views.py`
  - `TestCaseViewSet.ai_import` 新增批量导入动作

### 2.2 前端

- `frontend/src/api/testcase.js`
  - 新增 `aiImportCasesApi`
- `frontend/src/components/TestCaseModal.vue`
  - 导入逻辑改造：调用 `aiImportCasesApi`
  - 从 SSE `done.run_id` 绑定导入请求

---

## 3. 接口说明

### 3.1 `POST /api/ai/generate-cases/`（响应新增 run_id）

- 新增字段：`run_id: number | null`

### 3.2 `POST /api/ai/generate-cases-stream/`（SSE done 新增 run_id）

- `done` 事件新增字段：`run_id`

### 3.3 `POST /api/testcase/cases/ai-import/`

请求体：

```json
{
  "project_id": 1,
  "test_type": "api",
  "run_id": 123,
  "default_module_id": 456,
  "items": [
    {
      "case_name": "xxx",
      "level": "P1",
      "module_name": "用户登录",
      "precondition": "…",
      "steps": "…",
      "expected_result": "…",
      "api_url": "/v1/login",
      "api_method": "POST",
      "api_headers": {"Content-Type": "application/json"},
      "api_body": {"a": 1},
      "api_expected_status": 200
    }
  ]
}
```

响应体：

```json
{
  "success": true,
  "imported": [{"index": 0, "case_id": 10001, "case_name": "xxx"}],
  "failed": [{"index": 3, "error": "..."}],
  "skipped": 1
}
```

---

## 4. 迁移与上线步骤

1. 执行迁移：

```bash
python manage.py migrate
```

注意：数据库密码从环境变量 `DB_PASSWORD` 读取；未设置会导致无法连接 MySQL 从而迁移失败。

2. 前端构建验证：

```bash
npm -s run -C frontend build
```

---

## 5. 验收清单（最小）

- [ ] 调用 `POST /api/ai/generate-cases/` 成功，响应包含 `run_id`
- [ ] 调用 `POST /api/ai/generate-cases-stream/` 成功，`done` 事件包含 `run_id`
- [ ] 调用 `POST /api/testcase/cases/ai-import/` 可一次导入多条，返回逐条 `imported/failed`
- [ ] 导入后的 `TestCase.ai_run_id` 可追溯到对应 Run
- [ ] `AiUsageEvent.meta` 中包含 `run_id`（同步/流式）

---

## 6. 回滚方案

- 代码回滚：回退相关提交。
- 数据库回滚：
  - 删除 `test_case.ai_run_id` 字段
  - 删除 `ai_case_generation_run` 表
  - 回滚迁移：按 Django migration 依赖顺序回退对应 migration。

