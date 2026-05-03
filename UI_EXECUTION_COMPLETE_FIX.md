# UI 脚本执行完整修复方案

## 问题汇总

### 1. URL 路由错误（404）
**现象**：前端请求 `/api/api/assistant/ui-script-executions/execute/`
**原因**：前端代码中重复添加了 `/api/` 前缀
**状态**：✅ 已修复

### 2. 框架识别错误
**现象**：线性 Selenium 脚本被识别为 unittest，导致执行失败
**原因**：框架检测器扫描整个工作空间，而不是单个入口文件
**状态**：✅ 已修复

### 3. Selenium 版本兼容性问题
**现象**：执行时报错 `ValueError: Timeout value connect was <object object>`
**原因**：Selenium 4.43.0 与 urllib3 2.6.3 不兼容
**状态**：✅ 已修复

### 4. Chrome 浏览器崩溃
**现象**：`selenium.common.exceptions.WebDriverException: Message: tab crashed`
**原因**：Chrome 147 版本需要额外的稳定性选项
**状态**：⚠️ 需要修改脚本

## 已完成的修复

### 1. 前端 URL 修复
**文件**：`frontend/src/store/modules/uiExecution.ts`

```typescript
// 修改前
const { data } = await request.post('/api/assistant/ui-script-executions/execute/', ...)

// 修改后
const { data } = await request.post('/assistant/ui-script-executions/execute/', ...)
```

### 2. 框架检测增强
**文件**：`assistant/utils/framework_detector.py`

- 新增 `_detect_linear_script()` 方法
- 检测特征：有自动化库（selenium/playwright）但无测试框架

### 3. 多框架执行器增强
**文件**：`assistant/utils/multi_framework_runner.py`

- 新增 `_is_linear_script_file()` 方法，检查单个文件
- 新增 `_build_linear_command()` 方法，直接用 Python 运行
- 优先检查入口点文件本身的类型

### 4. 依赖版本修复
```bash
# 已执行的命令
pip install "selenium==4.20.0"
pip install "urllib3<2.3.0"
```

**当前版本**：
- selenium: 4.20.0 ✓
- urllib3: 2.2.3 ✓

## 需要用户操作的步骤

### 步骤 1：清除浏览器缓存
1. 在浏览器中按 `Ctrl + Shift + Delete`
2. 选择"缓存的图片和文件"
3. 点击"清除数据"
4. 刷新页面（`Ctrl + F5` 强制刷新）

### 步骤 2：修改现有脚本（推荐）
将 `login.py` 修改为添加 Chrome 稳定性选项：

```python
from selenium.webdriver.chrome.options import Options

# 添加这些选项
chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--disable-software-rasterizer')
chrome_options.add_argument('--disable-extensions')

# 使用选项创建 driver
driver = webdriver.Chrome(options=chrome_options)
```

**或者**：使用已创建的稳定版本脚本 `login_stable.py`

### 步骤 3：测试执行
1. 刷新浏览器页面
2. 选择脚本（login.py 或 login_stable.py）
3. 选择执行模式（有头/无头）
4. 点击"开始执行"
5. 观察日志输出

## 预期行为

### 正常执行流程
```
1. 用户点击"开始执行"
   ↓
2. 前端发送: POST /api/assistant/ui-script-executions/execute/
   ↓
3. 后端创建执行记录，返回 execution_id
   ↓
4. 后端在后台线程中执行脚本
   ↓
5. 前端开始轮询日志（每2秒）
   ↓
6. 日志实时显示在界面上
   ↓
7. 执行完成后显示结果统计
```

### 日志示例
```
[system] 开始执行脚本 (ID: 4)
[system] 脚本信息: A3mall登录线性脚本 (线性脚本)
[system] 工作空间: D:\AITestProduct\media\ui_scripts\2026\05\01
[system] 执行命令: python -u login.py
[system] 测试框架: UNITTEST
[system] 开始执行测试
[stdout] 正在打开163邮箱...
[stdout] 正在定位iframe...
[stdout] 正在输入账号密码...
[stdout] cookie保存成功
[system] 执行完成 (返回码: 0)
```

## 故障排查

### 问题：页面显示"等待执行..."
**原因**：浏览器缓存了旧的前端代码
**解决**：清除浏览器缓存并强制刷新（Ctrl + F5）

### 问题：Chrome 崩溃
**原因**：缺少稳定性选项
**解决**：使用 `login_stable.py` 或修改脚本添加 Chrome 选项

### 问题：执行失败，返回码 1
**原因**：脚本本身的错误（如元素定位失败）
**解决**：查看详细日志，检查网页结构是否变化

### 问题：离开页面后执行停止
**原因**：这是正常行为，组件卸载时会清理轮询
**解决**：保持在执行页面直到完成，或使用后台任务功能

## 技术细节

### 支持的脚本类型
1. **LINEAR（线性脚本）**
   - 执行方式：`python -u script.py`
   - 特征：有 selenium/playwright，无测试框架

2. **PYTEST**
   - 执行方式：`pytest -v -s script.py`
   - 特征：使用 pytest 框架

3. **UNITTEST**
   - 执行方式：`python -m unittest script.py`
   - 特征：继承 unittest.TestCase

4. **其他**：NOSE、ROBOT、BEHAVE

### 日志存储
- 使用 Redis 存储执行日志
- 键名格式：`ui_script_execution:{execution_id}:logs`
- 过期时间：24 小时
- 日志类型：stdout、stderr、system

### 状态管理
- 使用 Pinia Store 管理执行状态
- 轮询间隔：2 秒
- 状态：pending、running、success、failed、timeout

## 相关文件清单

### 后端
- `assistant/views.py` - API 视图
- `assistant/urls.py` - URL 路由
- `assistant/serialize.py` - 序列化器
- `assistant/models.py` - 数据模型
- `assistant/utils/script_runner.py` - 脚本执行引擎
- `assistant/utils/multi_framework_runner.py` - 多框架执行器
- `assistant/utils/framework_detector.py` - 框架检测器

### 前端
- `frontend/src/store/modules/uiExecution.ts` - 执行状态管理
- `frontend/src/views/script/WebUIWorkbench.vue` - 工作台页面
- `frontend/src/utils/request.js` - HTTP 请求配置

### 测试脚本
- `media/ui_scripts/2026/05/01/login.py` - 原始脚本
- `media/ui_scripts/2026/05/01/login_stable.py` - 稳定版脚本（推荐）

## 下一步建议

1. **添加无头模式支持**
   - 前端已收集 headless 配置
   - 需要将配置传递给脚本执行环境
   - 在 Chrome 选项中添加 `--headless` 参数

2. **添加浏览器选择支持**
   - 前端已支持选择 Chrome/Firefox/Edge
   - 需要在后端根据选择创建对应的 WebDriver

3. **改进错误处理**
   - 捕获更详细的错误信息
   - 提供更友好的错误提示

4. **添加执行历史**
   - 保存执行记录到数据库
   - 提供历史查询和回放功能
