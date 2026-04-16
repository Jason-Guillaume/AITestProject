# project 项目管理模块

## 模块概述
负责项目管理、发布计划、测试计划、性能测试任务、定时调度等功能。

## 文件列表

### __init__.py
- **作用**: Python 包初始化

### admin.py
- **作用**: Django Admin 后台配置
- **业务功能**: 配置后台管理界面中显示的项目相关模型

### apps.py
- **作用**: 应用配置
- **业务功能**: 定义 ProjectConfig

### models.py
- **作用**: 数据模型定义
- **业务功能**:
  - `TestProject`: 项目主模型，支持父子项目层级结构
  - `TestTask`: 任务看板
  - `ReleasePlan`: 发布计划，关联版本和测试用例
  - `ReleasePlanTestCase`: 发布计划与用例的关联中间表
  - `TestPlan`: 测试计划，关联版本、环境、测试人员
  - `TestReport`: 测试报告，关联执行日志
  - `PerfTask`: 性能测试任务（JMeter/Locust）
  - `K6LoadTestSession`: k6 压测会话，支持 AI 生成脚本
  - `ScheduledTask`: 定时调度任务定义
  - `ScheduledTaskLog`: 调度任务执行日志
  - `ExecutionTask`: API 测试执行任务
  - `TestQualityMetric`: 测试质量指标快照
  - `ApiScenario`: API 场景（业务链路编排）
  - `ApiScenarioStep`: 场景步骤，引用 TestCase
  - `ApiScenarioRun`: 场景运行记录
  - `ApiScenarioStepRun`: 场景步骤运行记录

### services/__init__.py
- **作用**: 服务层初始化

### services/release_risk_brief.py
- **作用**: 发布风险评估服务
- **业务功能**: 生成发布风险评估简报

### tests.py
- **作用**: 单元测试入口

### urls.py
- **作用**: 项目模块路由
- **业务功能**: 定义项目管理相关 API 路径

### views.py
- **作用**: 项目视图
- **业务功能**:
  - 项目 CRUD
  - 发布计划管理
  - 测试计划管理
  - 测试报告生成
  - API 场景编排与执行

---
