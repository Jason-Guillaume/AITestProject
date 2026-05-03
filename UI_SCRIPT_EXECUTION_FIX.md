# UI 脚本执行问题修复总结

## 问题描述

用户在执行 UI 自动化脚本时遇到以下问题：
1. **有头模式报错**：前端发送的请求 URL 错误（`/api/api/...` 重复）
2. **无头模式无法运行**：线性 Selenium 脚本被错误识别为 unittest 框架

## 根本原因分析

### 1. URL 重复问题
- **位置**：`frontend/src/store/modules/uiExecution.ts`
- **原因**：前端 axios 实例已配置 `baseURL: "/api"`，但在 Pinia store 中又手动添加了 `/api/` 前缀
- **结果**：实际请求变成 `/api/api/assistant/ui-script-executions/execute/`，导致 404 错误

### 2. 框架识别问题
- **位置**：框架检测逻辑
- **原因**：
  - 工作空间中存在多个脚本文件（`login.py` 是线性脚本，`testcase01.py` 是 unittest 脚本）
  - 框架检测器扫描整个工作空间，发现 `testcase01.py` 包含 unittest，就将整个工作空间标记为 unittest 项目
  - 执行 `login.py` 时，系统尝试用 `python -m unittest login.py` 运行，但 `login.py` 不是 unittest 格式，导致失败

## 修复方案

### 1. 修复 URL 重复问题

**文件**：`frontend/src/store/modules/uiExecution.ts`

**修改**：
```typescript
// 修改前
const { data } = await request.post('/api/assistant/ui-script-executions/execute/', ...)

// 修改后
const { data } = await request.post('/assistant/ui-script-executions/execute/', ...)
```

同样修复了日志和状态查询的 URL。

### 2. 支持线性脚本执行

#### 2.1 增强框架检测器

**文件**：`assistant/utils/framework_detector.py`

**新增功能**：
- 添加 `_detect_linear_script()` 方法，检测纯线性自动化脚本
- 特征：包含 selenium/playwright 导入，但不包含测试框架类或装饰器
- 在框架检测优先级中添加 LINEAR 类型

#### 2.2 增强多框架执行器

**文件**：`assistant/utils/multi_framework_runner.py`

**新增功能**：
1. 添加 `_is_linear_script_file()` 方法，检查单个文件是否是线性脚本
2. 在 `_build_python_command()` 中优先检查入口点文件本身
3. 添加 `_build_linear_command()` 方法，直接用 Python 解释器运行脚本

**执行逻辑**：
```python
# 对于线性脚本
cmd = [sys.executable, '-u', target_file]

# 而不是
cmd = ['pytest', target_file]  # 或 python -m unittest
```

## 执行流程

### 修复前
```
用户点击执行
  ↓
前端发送: POST /api/api/assistant/ui-script-executions/execute/
  ↓
Django 404 错误（路由不匹配）
```

### 修复后
```
用户点击执行
  ↓
前端发送: POST /api/assistant/ui-script-executions/execute/
  ↓
后端接收请求，创建执行记录
  ↓
MultiFrameworkRunner 检查入口点文件
  ↓
检测到 login.py 是线性脚本（有 selenium，无 unittest）
  ↓
构建命令: python -u login.py
  ↓
在工作空间中执行脚本
  ↓
实时收集日志到 Redis
  ↓
前端轮询获取日志和状态
```

## 支持的脚本类型

现在系统支持以下 Python 脚本类型：

1. **线性脚本**（LINEAR）
   - 特征：直接编写的自动化脚本，不使用测试框架
   - 执行方式：`python -u script.py`
   - 示例：`login.py`

2. **Pytest 脚本**（PYTEST）
   - 特征：使用 pytest 框架，函数名以 `test_` 开头
   - 执行方式：`pytest -v -s script.py`

3. **Unittest 脚本**（UNITTEST）
   - 特征：继承 `unittest.TestCase`
   - 执行方式：`python -m unittest script.py`

4. **其他框架**
   - NOSE、ROBOT、BEHAVE 等

## 测试建议

1. **测试线性脚本**：
   - 上传 `login.py` 类型的纯 Selenium 脚本
   - 选择有头模式或无头模式
   - 验证能够正常执行

2. **测试 unittest 脚本**：
   - 上传 `testcase01.py` 类型的 unittest 脚本
   - 验证能够正常执行

3. **测试混合工作空间**：
   - 工作空间包含多种类型的脚本
   - 验证每个脚本都能按其自身类型正确执行

## 注意事项

1. **框架检测优先级**：
   - 首先检查入口点文件本身
   - 如果入口点是线性脚本，直接运行
   - 否则使用工作空间级别的框架检测结果

2. **有头模式 vs 无头模式**：
   - 这个配置目前在前端收集，但后端尚未使用
   - 需要在脚本中通过 ChromeOptions 等方式配置
   - 建议后续将此配置传递给脚本执行环境

3. **日志收集**：
   - 使用 Redis 存储执行日志
   - 日志保留 24 小时
   - 前端每 2 秒轮询一次

## 相关文件

- `frontend/src/store/modules/uiExecution.ts` - 前端执行状态管理
- `assistant/utils/framework_detector.py` - 框架检测器
- `assistant/utils/multi_framework_runner.py` - 多框架执行器
- `assistant/utils/script_runner.py` - 脚本执行引擎
- `assistant/views.py` - API 视图（UIScriptExecutionViewSet）
- `assistant/urls.py` - URL 路由配置
