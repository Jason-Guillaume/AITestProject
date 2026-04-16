# 30-AI 导入前批量预检（草稿 API 用例）开发文档

## 0. 需求来源与开发动因

- **业务价值摘要**：在“导入之前”就发现 API 用例的明显问题（URL 非法、未替换变量），让质量闸门更准确。
- **与导入后预检的区别**
  - 导入后预检：针对已落库用例 id（`batch-preview-run-api`）
  - 导入前预检：针对 AI 生成的草稿 items（无需落库）

---

## 1. 能力范围（本期）

### 1.1 后端：草稿 items 预检接口

- 新增接口：`POST /api/testcase/cases/ai-import-precheck/`
- 当前覆盖：
  - `test_type=api`：计算最终 URL（含 environment base_url 拼接）、变量替换、URL/method 合法性校验
  - 提取 `unresolved_vars`：检测最终请求中仍存在 `${...}` 占位符

### 1.2 前端：生成完成自动预检并回填到预览表

- AI 流式生成收到 `done` 后自动调用 `ai-import-precheck`
- 将返回的 `unresolved_vars/error/final_url` 回填到 `aiPreviewCases` 行对象
- 质量闸门（标红/阻断）因此能实时识别“未替换变量”等问题

补充：前端支持传入 overrides（用于预检拼接环境 base_url 与填充变量）：

- `environment_id`：从环境列表选择（可选）
- `variables`：JSON 输入（可选），例如 `{"token":"xxx"}`

---

## 2. 接口说明

### 2.1 `POST /api/testcase/cases/ai-import-precheck/`

请求体示例：

```json
{
  "test_type": "api",
  "overrides": {
    "environment_id": 1,
    "variables": {"token": "xxx"}
  },
  "items": [
    {
      "case_name": "登录-正常",
      "api_url": "/v1/login",
      "api_method": "POST",
      "api_headers": {"Content-Type": "application/json"},
      "api_body": {"username": "a", "password": "b"}
    }
  ]
}
```

响应体示例：

```json
{
  "success": true,
  "results": [
    {
      "index": 0,
      "case_name": "登录-正常",
      "ok": true,
      "error": "",
      "unresolved_vars": [],
      "request": {
        "method": "POST",
        "url": "https://example.com/v1/login",
        "headers": {},
        "body": {},
        "environment_id": 1
      }
    }
  ]
}
```

---

## 3. 代码变更清单

- 后端：
  - `testcase/views.py`
    - `TestCaseViewSet.ai_import_precheck`
  - 复用组件：
    - `testcase/services/api_execution.py`（URL 拼接、headers/body 规范化、校验）
    - `testcase/services/variable_runtime.py`（变量替换）
- 前端：
  - `frontend/src/api/testcase.js`：新增 `aiImportPrecheckApi`
  - `frontend/src/components/TestCaseModal.vue`
    - `runPreImportPrecheck()`：生成结束后自动预检并回填行字段

---

## 4. 验收清单（最小）

- [x] API 生成完成后，预览表能自动识别 `${var}` 未替换并标红/阻断
- [x] URL 非法时，`row._precheck_error` 有值，导入前可见提示
- [x] 预检不要求用例已落库

最小复测路径：按 `开发文档/31` §5 步骤 4（P3）走一遍即可。

---

## 5. 回滚方案

- 回滚前端：移除生成完成后的预检调用，不影响生成与导入主流程
- 回滚后端：移除 `ai-import-precheck` action，不影响导入后预检接口

---

## 6. 实现状态与全链路索引

- **结论**：已按设计落地（`POST .../ai-import-precheck/`、`runPreImportPrecheck` 与预览表回填）。
- **在本全链路中的优先级**：**P3**（与 P2 互补，建议验收在 P2 之后）。
- **总览**：`开发文档/31-AI用例导入全链路-优先级与实现状态.md`。

