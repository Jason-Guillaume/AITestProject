# testcase 测试用例模块

## 模块概述
负责测试用例管理、测试模块、测试环境、用例版本控制、用例执行等核心功能。

## 文件列表

### __init__.py
- **作用**: Python 包初始化

### admin.py
- **作用**: Django Admin 后台配置
- **业务功能**: 配置后台管理界面中显示的用例相关模型

### apps.py
- **作用**: 应用配置
- **业务功能**: 定义 TestcaseConfig

### models.py
- **作用**: 数据模型定义
- **业务功能**:
  - `TestApproach`: 测试方案
  - `TestApproachImage`: 方案图片
  - `TestDesign`: 测试设计
  - `TestModule`: 测试模块，支持层级结构
  - `TestEnvironment`: 测试环境，支持多环境配置
  - `EnvironmentHealthCheck`: 环境健康检查记录
  - `EnvironmentVariable`: 环境变量，支持敏感值加密
  - `TestCase`: 测试用例基类，支持软删除
  - `TestCaseVersion`: 用例版本快照
  - `ApiTestCase`: API 测试用例扩展表
  - `PerfTestCase`: 性能测试用例扩展表
  - `SecurityTestCase`: 安全测试用例扩展表
  - `UITestCase`: UI 自动化用例扩展表
  - `TestCaseStep`: 用例步骤
  - `ApiTestLog`: API 测试执行日志
  - `ExecutionLog`: API 单次执行完整记录

### services/__init__.py
- **作用**: 服务层初始化

### services/ai_case_gate.py
- **作用**: AI 用例生成网关
- **业务功能**: 控制 AI 用例生成的入口逻辑

### services/ai_import_precheck_core.py
- **作用**: AI 导入预检查核心
- **业务功能**: 用例导入前的 AI 预检查

### services/ai_openai.py
- **作用**: OpenAI 接口服务
- **业务功能**: 调用 OpenAI API 生成用例

### services/api_execution.py
- **作用**: API 执行服务
- **业务功能**: 执行 API 测试用例

### services/assertions.py
- **作用**: 断言服务
- **业务功能**: 实现各种断言逻辑

### services/auth_runtime.py
- **作用**: 运行时鉴权服务
- **业务功能**: 处理请求鉴权配置

### services/case_subtypes.py
- **作用**: 用例子类型服务
- **业务功能**: 处理不同测试类型的用例逻辑

### services/variable_runtime.py
- **作用**: 变量运行时服务
- **业务功能**: 处理用例执行时的变量解析与注入

### signals.py
- **作用**: Django 信号处理器
- **业务功能**: 监听用例创建、更新等事件

### tests.py
- **作用**: 单元测试入口

### urls.py
- **作用**: 用例模块路由
- **业务功能**: 定义测试用例相关 API 路径

### environment_urls.py
- **作用**: 环境管理路由
- **业务功能**: 测试环境相关 API 路径

### views.py
- **作用**: 用例视图
- **业务功能**:
  - 用例 CRUD
  - 用例导入（支持 AI 生成）
  - 用例版本管理
  - 用例执行
  - 模块管理
  - 环境管理

### serialize.py
- **作用**: 序列化器定义
- **业务功能**: 用例数据序列化/反序列化

---
