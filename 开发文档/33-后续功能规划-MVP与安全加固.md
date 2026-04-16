# 33-后续功能规划（MVP 与安全加固）

## 0. 文档目的

将上一轮讨论中 **可独立排期、边界清晰** 的能力固化为产品/技术条目，便于评审与拆分任务。  
本文档为 **规划 + 落地索引**：**§1 MVP-A**、**§2 MVP-B** 首期已实现；**§3** 仍为加固规划。后续变更请更新 §6 变更记录。

---

## 1. MVP-A：失败执行 → 用例修订建议

### 1.1 需求摘要

- **用户**：测试工程师在计划/API 执行失败后，希望少翻日志、少手写改用例。
- **价值**：缩短「失败 → 定位 → 改用例」闭环；输出必须 **可人工审核**，默认不落库自动覆盖。

### 1.2 已实现能力（首期）

- **接口**：`POST /api/ai/suggest-case-fix/`
  - Body：`{ "execution_log_id": number, "hint"?: string }`
  - 仅当 `ExecutionLog.is_passed == false` 时调用模型；通过记录返回 400 说明无需修订。
- **权限**：`IsAuthenticated` + `can_user_access_execution_log`（与项目成员 / 用例创建者 / 管理员对齐）。
- **治理**：`_guard_ai_request_or_429(..., action="suggest_case_fix")`；`write_ai_usage_event` 记录 `meta.execution_log_id`。
- **输出**：`success`、`summary`、`suggested_steps[]`、`risks`、`model`、`test_case_id`；**不落库**。
- **前端**：用例详情 →「查看测试日志」表格中未通过行可点 **「AI」**，弹窗展示摘要与建议步骤（`TestCase.vue`）。
- **非目标（首期不做）**：自动重跑计划。
- **二期（已落地）**：在建议弹窗内 **「一键替换全部步骤」**（`ElMessageBox` 二次确认 + `confirm_replace_all: true`）；接口 `POST /api/testcase/cases/<id>/apply-ai-suggested-steps/`。

### 1.3 代码入口

- `assistant/services/case_fix_from_execution.py`：提示词、权限判断、用户消息拼装、JSON 解析
- `assistant/views.py`：`AiSuggestCaseFixAPIView`
- `assistant/ai_urls.py`：`suggest-case-fix/`
- `testcase/views.py`：`TestCaseViewSet.apply_ai_suggested_steps`（`apply-ai-suggested-steps/`）
- `frontend/src/api/assistant.js`：`suggestCaseFixFromExecutionLogApi`
- `frontend/src/api/testcase.js`：`applyCaseAiSuggestedStepsApi`

### 1.4 验收清单

- [x] 无权限用户无法对他人的执行记录生成建议（403）。
- [x] 结构化响应含 `risks`；不自动写库。
- [x] 「一键应用」到步骤（二期：`confirm_replace_all` + 前端确认框）。

### 1.5 主要依赖模块

- `testcase/`（`ExecutionLog`、`TestCase`、`TestCaseStep`）
- `assistant/`（OpenAI SDK、治理与审计）

---

## 2. MVP-B：发布风险简报（只读）

### 2.1 需求摘要

- **用户**：测试负责人 / PM 在发布前需要一页 **只读** 汇总，减少跨页统计。
- **价值**：聚合系统内已有指标，**尽量不调用大模型**（首期），避免幻觉与成本。

### 2.2 已实现能力（首期）

- **接口**：`GET /api/project/releases/<id>/risk-brief/?days=7`（`days` 默认 7，范围 1～90）
- **聚合内容**：
  - 发布计划关联用例数（`ReleasePlanTestCase`，`is_deleted=False`）
  - 该版本下 `execution.TestPlan`（`version_id`）按状态：未开始 / 进行中 / 已完成
  - 关联缺陷 `defect.TestDefect`（`release_version`）：总数、未关闭（新缺陷/处理中）、按严重级别与状态计数
  - 关联用例在窗口内 `testcase.ExecutionLog`：总次数、通过（`is_passed`）/ 未通过
- **响应**：`release`、`coverage`、`defects`、`executions`、`markdown`（只读摘要文本）
- **前端**：发布计划详情页右栏（`ReleasePlanDetail.vue`）展示指标 + Markdown，可调窗口天数并刷新。
- **非目标（首期不做）**：根因长文、自动「禁止发布」、未单独统计「计划内用例从未执行」条数（可二期补口径）。

### 2.3 代码入口

- `project/services/release_risk_brief.py`：`build_release_risk_brief`
- `project/views.py`：`ReleasePlanViewSet.risk_brief`
- `frontend/src/api/project.js`：`getReleaseRiskBriefApi`
- `frontend/src/views/defect/ReleasePlanDetail.vue`

### 2.4 验收清单

- [x] 与 `ReleasePlanViewSet` 同源数据范围（`BaseModelViewSet` + `project` 成员链路）
- [x] 指标来自 ORM 聚合（见 `release_risk_brief.py`）
- [x] 只读 GET，不修改缺陷/用例/计划
- [x] 更细的「计划内用例未执行」清单或导出（二期）

#### 2.6 二期增补：计划内用例未执行清单（已落地）

- **接口**：`GET /api/project/releases/<id>/never-executed-cases/?days=7&limit=500`
  - 语义：返回该发布计划关联用例中，在窗口内（近 N 天）**从未产生** `testcase.ExecutionLog` 的用例清单（按关联顺序输出）
  - 响应：`{ success, days, total, items[] }`
- **导出**：`GET /api/project/releases/<id>/never-executed-cases/export.csv?days=7&limit=20000`
- **简报字段增补**：`risk-brief` 的 `executions.never_executed_cases` 与 `never_executed_case_ids`（最多返回前 2000 个 id，避免过大 payload）
- **代码入口**
  - `project/services/release_risk_brief.py`：`_never_executed_case_ids_in_window`、`build_release_risk_brief` 增补字段
  - `project/views.py`：`ReleasePlanViewSet.never_executed_cases`
  - `project/views.py`：`ReleasePlanViewSet.export_never_executed_cases_csv`

> 说明：CSV 为流式输出，避免大结果占用内存；limit 最大 200000。

### 2.5 主要依赖模块

- `project/`（发布计划、关联用例中间表）
- `execution/`（`TestPlan`）
- `defect/`（`TestDefect`）
- `testcase/`（`ExecutionLog`）

---

## 3. 安全加固（与 `32-安全审计记录` 对齐）

### 3.1 SSH 主机密钥策略可配置

- **背景**：Bandit 对 `server_logs/ssh_tail.py` 中 `AutoAddPolicy` 标 High（MITM 风险）。
- **目标**：支持配置项在 **开发**（可 AutoAdd）与 **生产**（Reject + known_hosts 或跳板）之间切换；默认生产偏保守。
- **已实现（首期）**
  - **环境变量**：`SERVER_LOGS_SSH_HOST_KEY_POLICY`（`auto_add` | `warning` | `reject` | `known_hosts`）；未设置时 **`DJANGO_DEBUG=1` 默认 `auto_add`**，**`DJANGO_DEBUG=0` 默认 `reject`**（加载系统 `known_hosts` + `RejectPolicy`）。
  - **自定义指纹文件**：`SERVER_LOGS_SSH_KNOWN_HOSTS_PATH`（仅当策略为 `known_hosts` 时必填）。
  - **代码**：`server_logs/ssh_tail.py` 中 `apply_ssh_host_key_policy`、`ssh_tail_worker` 读取 `settings` 后应用策略。
  - **单测**：`tests/server_logs/test_ssh_host_key_policy.py`（策略分支与 `known_hosts` 缺路径校验）。
- **验收**：配置文档 + 单测或手工矩阵（两种策略下连接行为符合预期）。
  - [x] 配置文档（见 `开发文档/22` §9.5、`AITestProduct/settings.py` 注释）
  - [x] 单测（策略映射）
  - [ ] 手工矩阵（真实 SSH 与系统/自定义 `known_hosts`）可按运维节奏补做

### 3.2 预发跑通 `manage.py check --deploy`

- **背景**：生产向 `DJANGO_DEBUG=0` 时需 `DB_PASSWORD` 等，日常本地未跑全量 deploy 检查。
- **目标**：在 CI 或预发流水线注入最小环境变量集，将 `check --deploy` 告警清单化并逐项关闭或备案。
- **已实现（首期）**：`.github/workflows/api-tests.yml` 在 **Migrate** 之后增加一步 **`python manage.py check --deploy`**，注入与本仓库 `settings.py` 生产校验一致的 **最小变量集**（含 `DJANGO_SECRET_KEY`、`DB_*`、`ELASTICSEARCH_*` 占位等）；日志中保留该步完整输出。
- **验收**：流水线日志中保留 `check --deploy` 输出；严重项为 0 或均有书面备案。
  - [x] CI 中保留 `check --deploy` 输出
  - [ ] 若后续出现新的 deploy 级告警，在审计文档或本文件 §6 备案或跟进修复项

---

## 4. 推荐排期顺序（建议）

| 顺序 | 条目 | 说明 |
|------|------|------|
| 1 | §3.2 `check --deploy` | **首期已落地**（见 §3.2）；后续随 Django 升级关注新告警 |
| 2 | §3.1 SSH 策略 | **首期已落地**（见 §3.1）；Bandit 仍可能命中 `auto_add` 分支代码，属可接受残留 |
| 3 | §2 MVP-B 简报 | **首期已落地**（见 §2.2）；后续可做导出与更细口径 |
| 4 | §1 MVP-A 修订建议 | **首期 + 二期「一键替换步骤」已落地**（见 §1.2、§1.3） |

---

## 5. 关联文档

- [32-安全审计记录.md](./32-安全审计记录.md)
- [31-AI用例导入全链路-优先级与实现状态.md](./31-AI用例导入全链路-优先级与实现状态.md)
- [25-AI治理（用量配额与审计）开发文档.md](./25-AI治理（用量配额与审计）开发文档.md)
- [07-安全与权限基线.md](./07-安全与权限基线.md)
- [34-AI能力路线图（闭环修复-编排-安全-知识库-治理-自动化操作）.md](./34-AI能力路线图（闭环修复-编排-安全-知识库-治理-自动化操作）.md)

---

## 6. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-04-16 | 初版：MVP-A / MVP-B 与 §3 安全加固条目入库。 |
| 2026-04-16 | **MVP-B 首期落地**：`risk-brief` API、详情页展示；API 集成测试 `test_release_risk_brief`。 |
| 2026-04-16 | **MVP-A 首期落地**：`POST /api/ai/suggest-case-fix/`、执行日志入口、集成测试鉴权路由登记。 |
| 2026-04-16 | **§3 安全加固首期**：可配置 SSH 主机密钥策略（`SERVER_LOGS_SSH_*`）、CI 增加 `manage.py check --deploy`；单测 `tests/server_logs/test_ssh_host_key_policy.py`。 |
| 2026-04-16 | **MVP-A 二期**：`POST .../cases/<id>/apply-ai-suggested-steps/`、执行日志建议弹窗「一键替换全部步骤」；鉴权路由登记。 |
| 2026-04-16 | **MVP-A 测试**：`testcase.tests.ApplyAiSuggestedStepsApiTests`（`manage.py test`）；CI `api-tests.yml` 在 migrate 后执行。 |
