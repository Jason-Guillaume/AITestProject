# 28-AI 导入后批量预检（API Preview-Run）开发文档

## 0. 需求来源与开发动因

- **业务价值摘要**：降低“AI 导入后执行全红”的返工成本，在导入完成后立刻做静态预检（不发请求）。
- **现状痛点**
  - AI 生成的 API 用例可能包含未替换变量（如 `${token}`）、URL 非法、Headers/Body 结构不合法等问题。
  - 这些问题通常在真正执行时才暴露，导致大量回滚/重改。
- **建设目标**
  - 提供批量预检接口：复用 `preview-run-api` 的“合并环境 base_url + 变量替换”能力
  - 在 AI 批量导入成功后自动触发预检，并在前端展示报告

---

## 1. 能力范围（本期）

### 1.1 后端：批量预检接口

- 新增接口：`POST /api/testcase/cases/batch-preview-run-api/`
- 特性：
  - 仅对 **API 测试类型**用例生效
  - 只做请求预览与变量替换，不发网络请求
  - 输出每条用例的最终请求（method/url/headers/body）与 `unresolved_vars`（检测仍存在 `${...}` 的片段）

### 1.2 前端：导入后自动触发 + 报告弹窗

- 在 `AI 生成测试用例` 弹窗中：
  - 批量导入成功后，若测试类型为 `api`，自动调用批量预检接口
  - 弹出“导入后预检报告（API）”对话框，展示：
    - 通过/有问题
    - 未替换变量列表
    - 请求预览（method + url）
    - 错误信息（若存在）

补充：导入后预检将复用同一套 overrides（可选）：

- `environment_id`：用于拼接 base_url
- `variables`：用于预先填充运行时变量，减少 `${...}` 未替换告警

---

## 2. 接口说明

### 2.1 `POST /api/testcase/cases/batch-preview-run-api/`

请求体：

```json
{
  "ids": [10001, 10002],
  "overrides": {
    "environment_id": 1,
    "variables": {
      "token": "xxx"
    }
  }
}
```

说明：
- `ids`：必填，用例 id 数组（单次最多 500）
- `overrides`：可选，透传给 `preview_resolved_request`（例如环境、运行时变量）

响应体：

```json
{
  "success": true,
  "results": [
    {
      "id": 10001,
      "case_name": "登录接口-正常",
      "ok": true,
      "request": {
        "method": "POST",
        "url": "https://example.com/v1/login",
        "headers": {},
        "body": {},
        "expected_status": 200,
        "environment_id": 1
      },
      "unresolved_vars": []
    },
    {
      "id": 10002,
      "case_name": "登录接口-token 缺失",
      "ok": false,
      "unresolved_vars": ["${token}"]
    }
  ]
}
```

---

## 3. 代码变更清单

- 后端：
  - `testcase/views.py`
    - `TestCaseViewSet.batch_preview_run_api`：新增批量预检 action
    - 复用：`testcase/services/api_execution.py: preview_resolved_request`
- 前端：
  - `frontend/src/api/testcase.js`：新增 `batchPreviewRunApiCaseApi`
  - `frontend/src/components/TestCaseModal.vue`：
    - 导入成功后自动调用批量预检
    - 新增预检报告弹窗与表格展示

---

## 4. 验收清单（最小）

- [x] AI 导入 API 用例成功后自动弹出预检报告
- [x] 报告中能展示每条用例的 method/url
- [x] 存在 `${var}` 未替换时，`unresolved_vars` 能正确提示
- [x] `overrides.environment_id/variables` 生效（可手工调用接口验证）

最小复测路径：按 `开发文档/31` §5 步骤 5（P4）走一遍即可。

---

## 5. 回滚方案

- 回滚前端：移除导入后预检调用与弹窗即可（不影响导入主流程）
- 回滚后端：移除 `batch-preview-run-api` action（不影响单条 `preview-run-api`）

---

## 6. 实现状态与全链路索引

- **结论**：已按设计落地（`batch-preview-run-api`、导入成功后报告弹窗）。
- **在本全链路中的优先级**：**P4**（依赖落库用例 id）。
- **总览**：`开发文档/31-AI用例导入全链路-优先级与实现状态.md`。

