# Web 脚本处理逻辑分析 Spec

## Why
当前 automation-center 的 Web UI 自动化脚本以「直接编辑代码」模式运行——用户上传或在线编写原始 Python/Selenium 脚本，平台通过子进程直接执行。该模式缺乏结构化表示、元素复用、可视化编辑等能力，导致维护成本高、协作困难。需要系统梳理现有脚本中涉及的所有操作类型、元素定位方式，并分析当前模式的局限性，为后续向「结构化步骤编辑」模式演进提供依据。

## What Changes
- 本 spec 为纯分析型，不引入代码变更
- 梳理当前脚本处理全链路：上传 → 解析 → 框架检测 → 命令构建 → 子进程执行 → 日志流 → 前端展示
- 总结所有操作类型（click/input/wait 等）和元素定位方式（ID/XPath/CSS 等）
- 分析「直接编辑代码」模式的 12 项核心局限性

## Impact
- Affected specs: automation-center Web 脚本执行引擎、POM 元素库、AI 脚本生成
- Affected code:
  - 后端: `assistant/utils/script_handler.py`, `assistant/utils/script_runner.py`, `assistant/utils/multi_framework_runner.py`, `assistant/utils/framework_detector.py`, `assistant/runtime/browser_env_patch.py`, `assistant/ui_automation_views.py`, `assistant/ui_element_models.py`
  - 前端: `frontend/src/views/script/WebUIWorkbench.vue`, `frontend/src/views/automation-center/WebAutomationTree.vue`, `frontend/src/components/automation-center/inspector/InspectorWebPanel.vue`, `frontend/src/stores/uiExecutionStore.ts`

---

## ADDED Requirements

### Requirement: 脚本处理全链路梳理

系统 SHALL 提供以下脚本处理链路的完整文档化描述：

#### Scenario: 脚本上传与工作空间创建
- **WHEN** 用户通过「导入脚本」对话框上传 .py 单文件或 .zip 工程包
- **THEN** `script_handler.py` 将文件解压/保存到 `media/workspaces/{id}/` 目录，验证入口点文件存在，并通过 `FrameworkDetector` 自动检测测试框架

#### Scenario: 框架自动检测
- **WHEN** 脚本的 `framework` 字段为 `AUTO`
- **THEN** `FrameworkDetector` 按优先级扫描工作空间：Robot → Behave → Pytest → Nose → Unittest → 线性脚本（含 selenium/playwright/appium 导入但无测试框架特征）→ 默认 Pytest

#### Scenario: 执行命令构建
- **WHEN** 用户点击「开始执行」
- **THEN** `MultiFrameworkRunner` 根据 `script_type`/`framework` 构建命令：
  - LINEAR → `python -u [launch_ui_entry.py] <script.py>`（无头时经启动器注入补丁）
  - PYTEST → `pytest -v -s --capture=no --tb=short --junitxml=...`
  - UNITTEST → `python -m unittest <module> -v` 或 `python -u <script.py>`（路径含非标识符时）
  - 无头 unittest → 经 `launch_ui_unittest.py` 启动器注入补丁

#### Scenario: 浏览器无头补丁注入
- **WHEN** `HEADLESS_MODE=true` 且未设置 `AITESTA_SKIP_BROWSER_PATCH`
- **THEN** `browser_env_patch.py` 在子进程内 monkey-patch `webdriver.Chrome/Edge/Firefox.__init__`，自动添加 `--headless=new`（Chrome/Edge）或 `-headless`（Firefox）参数

#### Scenario: 子进程执行与日志流
- **WHEN** `ScriptRunner.execute_ui_script()` 被调用
- **THEN** 以 `subprocess.Popen` 启动子进程，stdout/stderr 通过线程流式写入 Redis（key: `ui_script_execution:{id}:logs`），状态写入 Redis（key: `ui_script_execution:{id}:status`），PID 注册到 Redis 供用户停止时 kill 进程树

#### Scenario: 前端日志轮询与展示
- **WHEN** `uiExecutionStore.startExecution()` 被调用
- **THEN** 前端以 250ms~600ms 间隔轮询 `/assistant/ui-script-executions/{id}/logs/` 和 `status_detail/`，将 Redis 日志映射为带时间戳/级别的控制台输出，执行结束后显示用例统计

### Requirement: 操作类型与元素定位方式总结

系统 SHALL 明确记录当前脚本中涉及的所有操作类型和元素定位方式。

#### Scenario: 操作类型枚举
- **WHEN** 查阅 `UIActionStep.ACTION_TYPE_CHOICES`
- **THEN** 当前定义的操作类型为：
  | 操作类型 | 常量 | 说明 |
  |---------|------|------|
  | 点击 | `click` | 单击元素 |
  | 输入 | `input` | 向输入框输入文本 |
  | 断言 | `assert` | 验证元素状态或属性 |
  | 悬停 | `hover` | 鼠标悬停在元素上 |
  | 选择 | `select` | 下拉框选项选择 |
  | 等待元素 | `wait` | 显式等待元素出现/可点击 |
  | 休眠 | `sleep` | 固定时间等待 |
  | 导航 | `navigate` | 打开 URL |
  | 切换窗口 | `switch_window` | 切换浏览器窗口/标签页 |
  | 切换 Frame | `switch_frame` | 切换 iframe 上下文 |
  | 滚动 | `scroll` | 页面或元素内滚动 |
  | 执行 JS | `execute_js` | 执行自定义 JavaScript |

#### Scenario: 元素定位方式枚举
- **WHEN** 查阅 `UIPageElement.LOCATOR_TYPE_CHOICES`
- **THEN** 当前定义的定位方式为：
  | 定位方式 | 常量 | Selenium By 映射 |
  |---------|------|-----------------|
  | ID | `id` | `By.ID` |
  | Name | `name` | `By.NAME` |
  | XPath | `xpath` | `By.XPATH` |
  | CSS Selector | `css` | `By.CSS_SELECTOR` |
  | Class Name | `class` | `By.CLASS_NAME` |
  | Tag Name | `tag` | `By.TAG_NAME` |
  | Link Text | `link_text` | `By.LINK_TEXT` |
  | Partial Link Text | `partial_link_text` | `By.PARTIAL_LINK_TEXT` |

#### Scenario: 实际脚本中的定位方式
- **WHEN** 分析 `ui_automation_views.py` 中 AI 生成的 Mock 脚本
- **THEN** 生成代码中使用的定位方式为：
  - `By.TAG_NAME`（`"body"`）— 等待页面加载
  - `By.CSS_SELECTOR`（`"input, button, a"`）— 查找关键元素
  - 直接使用 `self.driver.title`、`self.driver.current_url` — 属性断言
  - 所有定位值均为硬编码字符串，未引用元素库

### Requirement: 「直接编辑代码」模式局限性分析

系统 SHALL 明确记录当前「直接编辑代码」模式的 12 项核心局限性。

#### Scenario: 局限性清单
- **WHEN** 评估当前脚本编辑与执行模式
- **THEN** 存在以下局限性：

  **L1 — 无结构化脚本表示**
  脚本以原始 Python 代码（`online_content` 字段或文件）存储，平台无法理解脚本内部的步骤结构、操作语义和元素引用。`UIActionStep` 模型虽定义了 12 种操作类型，但与实际执行的脚本代码完全脱节。

  **L2 — 硬编码定位器**
  所有元素定位器（XPath、CSS Selector 等）以字符串字面量形式嵌入在代码中。例如 `By.CSS_SELECTOR, "input, button, a"`。当 UI 变更时，需人工在代码中搜索并逐个替换，极易遗漏。

  **L3 — 无元素复用**
  `UIPageElement` 元素库已存在于数据库中（支持 8 种定位方式），但脚本代码不引用元素库 ID。同一元素在不同脚本中重复定义，无法做到「改一处、全局生效」。

  **L4 — 无可视化编辑**
  前端仅提供 Monaco 文本编辑器，用户必须手写 Python 代码。无可拖拽步骤编辑器、无表单化操作配置、无步骤预览。

  **L5 — Inspector 为占位状态**
  `InspectorWebPanel.vue` 中的「元素校验工具」仅有一个输入框和「校验」按钮，后端无对应的元素探测 API。无法在运行时实时拾取页面元素并生成定位器。

  **L6 — AI 生成仅为 Mock**
  `ui_automation_views.py` 的 `UiAutomationGenerateAPIView` 返回硬编码的模板代码，仅使用 `By.TAG_NAME` 和 `By.CSS_SELECTOR` 两种定位方式，未接入真实 AI 模型，无法根据用户描述生成精确的步骤脚本。

  **L7 — 无步骤级调试**
  执行粒度为整个脚本文件，无法单步执行、断点调试、或单独运行某个步骤。出错时只能通过日志定位，无法在 UI 上高亮失败步骤。

  **L8 — 测试数据与代码耦合**
  输入值、断言期望值等测试数据直接写在代码字符串中，无参数化机制。无法通过数据驱动方式运行同一脚本的多组数据。

  **L9 — 无脚本间元素共享**
  每个脚本独立存储，元素定位器在脚本间复制粘贴。POM 模式虽支持上传 ZIP 工程（含 Page Object 类），但平台不管理 Page Object 与元素库的映射关系。

  **L10 — 无预执行验证**
  点击「开始执行」后直接拉起浏览器运行，无法在执行前验证定位器是否有效、脚本语法是否正确、依赖是否满足。

  **L11 — 无录制能力**
  缺少浏览器操作录制功能，无法将用户在浏览器中的交互自动转化为脚本步骤。所有脚本必须手写或从外部导入。

  **L12 — 执行结果与步骤无关联**
  执行结果统计（total/passed/failed/skipped）来自 pytest junit.xml 或进程退出码，与 `UIActionStep` 无映射关系。无法在 UI 上展示「第 N 步失败」的精确信息。

---

## MODIFIED Requirements

（无修改，本 spec 为纯新增分析）

## REMOVED Requirements

（无移除）
