# execution 测试执行模块

## 模块概述
负责测试任务的执行引擎、WebSocket 实时推送、性能测试执行、任务调度等。

## 文件列表

### __init__.py
- **作用**: Python 包初始化

### admin.py
- **作用**: Django Admin 后台配置

### apps.py
- **作用**: 应用配置
- **业务功能**: 定义 ExecutionConfig

### models.py
- **作用**: 数据模型定义
- **业务功能**: 定义执行相关的模型（部分在 project 模块中）
  - `K6LoadTestSession`: k6 压测会话
  - `ScheduledTask`: 定时调度任务
  - `ScheduledTaskLog`: 调度任务日志
  - `ExecutionTask`: 执行任务
  - `ApiScenario`: API 场景
  - `ApiScenarioStep`: 场景步骤
  - `ApiScenarioRun`: 场景运行记录
  - `ApiScenarioStepRun`: 场景步骤运行记录

### consumers.py
- **作用**: WebSocket 消费者
- **业务功能**:
  - 处理 WebSocket 连接
  - 实时推送执行进度
  - 推送日志流

### engine.py
- **作用**: 执行引擎核心
- **业务功能**:
  - 测试任务执行调度
  - 用例执行逻辑
  - 结果收集与反馈

### middleware_ws.py
- **作用**: WebSocket 中间件
- **业务功能**: 处理 WebSocket 请求的中间逻辑

### routing.py
- **作用**: WebSocket 路由配置
- **业务功能**: 定义 WebSocket 连接路由

### scheduler.py
- **作用**: 定时调度器
- **业务功能**:
  - 管理定时任务
  - 执行周期性的测试任务

### serialize.py
- **作用**: 序列化器定义
- **业务功能**: 执行相关数据序列化

### tasks.py
- **作用**: Celery 异步任务
- **业务功能**:
  - 异步执行测试任务
  - 任务状态管理

### tasks_k6.py
- **作用**: k6 性能测试任务
- **业务功能**: 执行 k6 压测任务

### views.py
- **作用**: 执行视图
- **业务功能**:
  - 触发测试执行
  - 查询执行状态
  - 获取执行结果

### views_k6.py
- **作用**: k6 执行视图
- **业务功能**: k6 性能测试相关 API

### perf_urls.py
- **作用**: 性能测试路由
- **业务功能**: 性能测试相关 API 路径

### urls.py
- **作用**: 执行模块路由
- **业务功能**: 测试执行相关 API 路径

### services/__init__.py
- **作用**: 服务层初始化

### services/health_checker.py
- **作用**: 健康检查服务
- **业务功能**: 检查环境和系统健康状态

### services/k6_ai_generator.py
- **作用**: k6 AI 脚本生成器
- **业务功能**: 使用 AI 生成 k6 压测脚本

### services/k6_chain_builder.py
- **作用**: k6 请求链构建器
- **业务功能**: 构建 k6 测试请求链

### services/k6_stderr_parser.py
- **作用**: k6 错误解析器
- **业务功能**: 解析 k6 执行错误信息

### services/k6_template_generator.py
- **作用**: k6 模板生成器
- **业务功能**: 生成 k6 测试脚本模板

### services/metric_calculator.py
- **作用**: 指标计算器
- **业务功能**: 计算性能测试指标

### services/scenario_generator.py
- **作用**: 场景生成器
- **业务功能**: 生成测试场景

### services/scenario_runner.py
- **作用**: 场景运行器
- **业务功能**: 执行测试场景

---
