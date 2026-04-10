# 后端 API 自动化测试说明

本目录提供基于 `pytest + requests` 的后端 API 自动化测试套件。

## 1. API 路由总览（来自代码路由扫描）

项目主路由：`/api/*`

- `api/user/`
  - `GET /captcha/`
  - `POST /register/`
  - `POST /login/`
  - `GET /me/`
  - `PATCH /me/profile/`
  - `GET /me/change-requests-status/`
  - `POST /me/sensitive-change/`
  - `GET /system-messages/`
  - `PATCH /system-messages/{pk}/read/`
  - `GET /admin/change-requests/`
  - `POST /admin/change-requests/{pk}/decision/`
  - `POST /change-password/`
  - `users/orgs/message-settings/roles`（DRF ViewSet 标准 CRUD）

- `api/sys/`
  - `GET|PUT|DELETE /ai-config/`
  - `POST /ai-config/disconnect/`
  - `POST /ai-config/reconnect/`

- `api/change-requests/`
  - `POST /{pk}/approve/`
  - `POST /{pk}/reject/`

- `api/project/`
  - `projects/tasks/releases`（DRF ViewSet 标准 CRUD）

- `api/testcase/`
  - `cases/modules/approachs/steps/designs`（DRF ViewSet 标准 CRUD）
  - `POST /cases/batch-delete/`
  - `POST /cases/batch-execute/`
  - `POST /cases/{id}/execute-api/`
  - `GET /approachs/{id}/images/`
  - `POST /approachs/{id}/images/upload/`
  - `DELETE /approachs/{id}/images/{image_id}/`

- `api/execution/`
  - `plans/reports/tasks`（DRF ViewSet 标准 CRUD）
  - `POST /tasks/{task_id}/run/`
  - `GET /dashboard/summary/`
  - `GET /dashboard/quality/`

- `api/perf/`
  - `tasks`（同 `execution` 的性能任务 ViewSet）

- `api/defect/`
  - `defects`（DRF ViewSet 标准 CRUD）

- `api/assistant/`
  - `POST /llm/test-connection/`

- `api/ai/`
  - `POST /verify-connection/`
  - `POST /test-connection/`
  - `POST /generate-cases/`
  - `POST /generate-cases-stream/`

---

## 2. 测试覆盖内容

测试文件：`tests/api/test_backend_api_suite.py`

- Happy Path
  - 登录、用户信息、核心资源 CRUD（项目/模块/用例/步骤/设计/方案/发布/计划/报告/性能任务/缺陷）
  - 关键自定义 action（批量执行、批量删除、性能任务 run、仪表盘 summary 等）

- 边界值/边界场景
  - 过滤参数边界（如 project 非数字）
  - 可选字段空值（如手机号空字符串）
  - 自定义接口无文件上传边界

- 非法输入与错误处理
  - 缺少必填、类型错误、错误 method
  - 鉴权缺失（401/403）
  - AI 接口缺少 API key 的错误返回

---

## 3. 本地运行

## 3.1 安装依赖

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## 3.2 启动后端

确保 Django 服务已运行（默认 `http://127.0.0.1:8000`）。

## 3.3 设置环境变量

必须：

- `TEST_API_USERNAME`：可登录测试账号
- `TEST_API_PASSWORD`：对应密码

可选：

- `TEST_API_BASE_URL`（默认 `http://127.0.0.1:8000/api`）
- `TEST_API_ADMIN_USERNAME` / `TEST_API_ADMIN_PASSWORD`（用于管理员接口 happy path）
- `TEST_AI_API_KEY`（用于 AI 连通性 happy path）

PowerShell 示例：

```powershell
$env:TEST_API_BASE_URL="http://127.0.0.1:8000/api"
$env:TEST_API_USERNAME="admin"
$env:TEST_API_PASSWORD="your-password"
$env:TEST_API_ADMIN_USERNAME="admin"
$env:TEST_API_ADMIN_PASSWORD="your-password"
```

## 3.4 执行测试

```bash
pytest -q tests/api
```

查看详细输出：

```bash
pytest -vv tests/api
```

只跑冒烟：

```bash
pytest -m smoke tests/api
```

只跑回归：

```bash
pytest -m regression tests/api
```

---

## 3.5 生成测试报告

HTML 报告：

```bash
pytest tests/api --html=reports/api-test-report.html --self-contained-html
```

Allure 结果：

```bash
pytest tests/api --alluredir=reports/allure-results
```

本地安装了 Allure CLI 后可生成可视化报告：

```bash
allure serve reports/allure-results
```

---

## 3.6 一键脚本（Windows PowerShell）

已提供脚本：`scripts/run_api_tests.ps1`

示例：

```powershell
# 全量 + HTML 报告
powershell -ExecutionPolicy Bypass -File .\scripts\run_api_tests.ps1 -Suite full -HtmlReport

# 冒烟 + HTML + Allure
powershell -ExecutionPolicy Bypass -File .\scripts\run_api_tests.ps1 -Suite smoke -HtmlReport -AllureReport
```

---

## 3.7 CI（GitHub Actions）

已提供工作流：`.github/workflows/api-tests.yml`

默认在 Push / PR / 手动触发时运行（当前配置执行 smoke 集）。

请在仓库 Secrets 配置：

- `TEST_API_USERNAME`
- `TEST_API_PASSWORD`
- `TEST_API_ADMIN_USERNAME`（可选）
- `TEST_API_ADMIN_PASSWORD`（可选）
- `TEST_AI_API_KEY`（可选）

---

## 3.8 用例编号一致性报告（CI Artifact）

工作流会执行：

```bash
python manage.py resequence_case_numbers --dry-run --strict --report-file reports/case-number-check.txt --report-json-file reports/case-number-check.json
```

- `--dry-run`：只检查不落库  
- `--strict`：若发现脏数据（`pending > 0`）则任务失败  
- `--report-file`：文本报告（便于人工查看）  
- `--report-json-file`：JSON 报告（便于平台/脚本消费）

上传的产物：

- `case-number-check-report`
  - `reports/case-number-check.txt`
  - `reports/case-number-check.json`

JSON 字段说明（schema `1.1`）：

- `schema_version`：报告结构版本
- `generated_at`：生成时间（ISO8601）
- `strict_mode`：本次是否启用严格模式
- `status`：`pass` / `fail`
- `pending`：待修复记录总数
- `preview_limit`：预览条数上限
- `preview`：预览数组（元素含 `id`、`test_type`、`old`、`new`）

---

## 4. 注意事项

- 该套件属于**接口集成测试**，会写入测试数据（项目、用例、缺陷等）。
- 建议连接独立测试库运行，不要直接对生产库执行。
- 若账号权限不足，管理员接口用例会失败，请配置管理员凭证环境变量。
