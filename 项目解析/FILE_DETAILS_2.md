# 完整 Python 文件业务说明 - 续

## 三、project 项目管理模块 (10 个文件)

### project/__init__.py
```
位置：/d/AITestProduct/project/__init__.py
业务角色：Python 包初始化
```

### project/admin.py
```
位置：/d/AITestProduct/project/admin.py
业务角色：Admin 后台注册
注册模型：
  - TestProject: 项目管理
  - TestTask: 任务看板
  - ReleasePlan: 发布计划
  - ReleasePlanTestCase: 发布计划 - 用例关联
  - TestPlan: 测试计划
  - TestReport: 测试报告
  - PerfTask: 性能测试任务
  - K6LoadTestSession: k6 压测会话
  - ScheduledTask: 定时任务
  - ScheduledTaskLog: 定时任务日志
  - ExecutionTask: 执行任务
  - TestQualityMetric: 质量指标
  - ApiScenario: API 场景
  - ApiScenarioStep: 场景步骤
  - ApiScenarioRun: 场景运行
  - ApiScenarioStepRun: 步骤运行
```

### project/apps.py
```
位置：/d/AITestProduct/project/apps.py
业务角色：应用配置
配置类：ProjectConfig
```

### project/models.py
```
位置：/d/AITestProduct/project/models.py
业务角色：项目领域模型
数据库表:

1. test_project (TestProject)
   字段：project_name, parent (自关联), description, 
         icon, project_status, progress, members (M2M)
   方法：update_progress() - 根据测试计划完成率计算进度
   用途：项目主表，支持父子层级

2. test_task (TestTask)
   字段：task_title, task_desc, status, assignee
   用途：任务看板

3. release_plan (ReleasePlan)
   字段：project, release_name, version_no, release_date, status
   约束：project + version_no 唯一 (is_deleted 参与)
   用途：发布计划管理

4. release_plan_test_case (ReleasePlanTestCase)
   字段：release_plan, test_case, is_deleted
   约束：release_plan + test_case 唯一 (is_deleted 参与)
   用途：发布计划与用例关联中间表

5. test_plan (TestPlan)
   字段：plan_name, iteration, version (FK), environment,
         req_count, case_count, coverage_rate, plan_status,
         pass_rate, defect_count, testers (M2M), start_date, end_date
   用途：测试计划

6. test_report (TestReport)
   字段：plan, report_name, create_method, environment,
         req_count, case_count, coverage_rate, pass_rate,
         defect_count, start_time, end_time, trace_id,
         execution_log_id, request_payload, response_payload, project
   用途：测试报告

7. perf_task (PerfTask)
   字段：task_id, task_name, scenario(jmeter/locust),
         concurrency, duration, status, executor
   用途：性能测试任务

8. k6_load_test_session (K6LoadTestSession)
   字段：run_id, status, test_case_ids, vus, duration,
         use_ai, target_base_url, script_rel_path, script_body,
         summary, error_message, celery_task_id, generation_source
   用途：k6 压测会话，支持 AI 生成脚本

9. scheduled_task (ScheduledTask)
   字段：name, cron_expression, status, job_id, environment,
         test_cases (M2M), next_run_time, last_run_time,
         last_status, last_message
   用途：定时调度任务

10. scheduled_task_log (ScheduledTaskLog)
    字段：scheduled_task, trigger_time, start_time, end_time,
          status, message, detail
    用途：定时任务执行日志

11. execution_task (ExecutionTask)
    字段：task_name, method, url, headers, body, timeout_seconds,
          expected_status, expected_body_contains, status,
          started_at, finished_at, duration_ms, celery_task_id,
          error_message, report, project
    用途：API 执行任务

12. test_quality_metric (TestQualityMetric)
    字段：metric_date, metric_type, metric_value, dimension
    用途：质量指标快照

13. api_scenario (ApiScenario)
    字段：project, name, environment, default_variables,
          failure_strategy, is_active
    用途：API 场景编排

14. api_scenario_step (ApiScenarioStep)
    字段：scenario, order, name, test_case (FK), is_enabled,
          failure_strategy, extraction_rules, step_overrides
    用途：场景步骤

15. api_scenario_run (ApiScenarioRun)
    字段：scenario, status, trace_id, started_at, finished_at,
          duration_ms, environment_id, initial_variables,
          final_variables, summary, celery_task_id, error_message
    用途：场景运行记录

16. api_scenario_step_run (ApiScenarioStepRun)
    字段：run, step, order, test_case_id, execution_log_id,
          status, passed, extracted_variables, message
    用途：步骤运行记录
```

### project/serialize.py
```
位置：/d/AITestProduct/project/serialize.py
业务角色：项目数据序列化器
包含：项目、用例、计划、报告等序列化器
```

### project/urls.py
```
位置：/d/AITestProduct/project/urls.py
业务角色：项目路由
路径：
  - /api/project/projects/          -> 项目管理
  - /api/project/release-plans/     -> 发布计划
  - /api/project/test-plans/        -> 测试计划
  - /api/project/reports/           -> 测试报告
  - /api/project/scenarios/         -> API 场景
  - /api/project/scenarios/<id>/run/ -> 场景执行
```

### project/views.py
```
位置：/d/AITestProduct/project/views.py
业务角色：项目视图
功能:
  - 项目 CRUD
  - 发布计划管理
  - 测试计划管理
  - 测试报告生成
  - API 场景编排与执行
  - 定时任务管理
  - 质量指标查询
```

### project/tests.py
```
位置：/d/AITestProduct/project/tests.py
业务角色：单元测试
```

### project/services/__init__.py
```
位置：/d/AITestProduct/project/services/__init__.py
业务角色：服务层初始化
```

### project/services/release_risk_brief.py
```
位置：/d/AITestProduct/project/services/release_risk_brief.py
业务角色：发布风险评估
功能:
  - 分析发布计划的风险点
  - 生成风险评估简报
  - 基于用例覆盖率、缺陷数等指标
```

---

## 四、testcase 测试用例模块 (17 个文件)

### testcase/__init__.py
```
位置：/d/AITestProduct/testcase/__init__.py
业务角色：Python 包初始化
```

### testcase/admin.py
```
位置：/d/AITestProduct/testcase/admin.py
业务角色：Admin 注册
注册模型：用例相关所有模型
```

### testcase/apps.py
```
位置：/d/AITestProduct/testcase/apps.py
业务角色：应用配置
配置类：TestcaseConfig
```

### testcase/models.py
```
位置：/d/AITestProduct/testcase/models.py
业务角色：用例领域模型
数据库表:

1. test_approach (TestApproach)
   字段：scheme_name, version, cover_image, test_goal, test_category
   用途：测试方案

2. test_approach_image (TestApproachImage)
   字段：approach, image, sort_order
   用途：方案图片

3. test_design (TestDesign)
   字段：design_name, req_count, point_count, case_count, 
         review_status, archive_status
   用途：测试设计

4. test_module (TestModule)
   字段：project, name, parent (自关联), test_type
   用途：测试模块 (层级结构)

5. test_environment (TestEnvironment)
   字段：name, env_type, base_url, auth_config, health_check_path,
         db_config, description
   用途：测试环境配置

6. environment_health_check (EnvironmentHealthCheck)
   字段：check_type, status, response_time_ms, error_log, target, dimension
   用途：环境健康检查记录

7. environment_variable (EnvironmentVariable)
   字段：environment, key, value, is_secret, description
   方法：encrypt_text(), decrypt_text(), get_decrypted_value()
   用途：环境变量 (敏感值加密)

8. test_case (TestCase)
   字段：module, ai_run, case_name, case_number, test_type, level,
         is_valid, exec_count, review_status, archive_status, deleted_at
   管理器：objects, all_objects, deleted_objects
   方法：delete() 软删除，restore() 恢复，hard_delete() 物理删除
   用途：用例基类

9. test_case_version (TestCaseVersion)
   字段：test_case, release_plan, snapshot_no, version_label, 
         case_snapshot, source_version
   用途：用例版本快照

10. testcase_apitestcase (ApiTestCase)
    字段：api_url, api_method, api_headers, api_body, 
          api_expected_status, api_source_curl
    用途：API 用例扩展

11. testcase_perftestcase (PerfTestCase)
    字段：concurrency, duration_seconds, target_rps
    用途：性能用例扩展

12. testcase_securitytestcase (SecurityTestCase)
    字段：attack_surface, tool_preset, risk_level
    用途：安全用例扩展

13. testcase_uitestcase (UITestCase)
    字段：app_under_test, primary_locator, automation_framework
    用途：UI 用例扩展

14. test_case_step (TestCaseStep)
    字段：testcase, step_number, step_desc, expected_result, assertions
    用途：用例步骤

15. api_test_log (ApiTestLog)
    字段：test_case, request_url, request_method, request_headers,
          request_body, response_status_code, response_body, 
          response_time_ms, is_passed
    用途：API 执行日志

16. api_execution_log (ExecutionLog)
    字段：test_case, request_url, request_method, request_headers,
          request_body_text, response_status_code, response_headers,
          response_body_text, duration_ms, execution_status,
          assertion_results, is_passed, error_message, trace_id,
          request_payload, response_payload
    用途：完整执行记录
```

### testcase/serialize.py
```
位置：/d/AITestProduct/testcase/serialize.py
业务角色：用例序列化器
包含：用例、模块、环境、变量等序列化器
```

### testcase/signals.py
```
位置：/d/AITestProduct/testcase/signals.py
业务角色：信号处理器
监听：用例创建、更新、删除
动作：审计记录、版本快照
```

### testcase/urls.py
```
位置：/d/AITestProduct/testcase/urls.py
业务角色：用例路由
路径：
  - /api/testcase/modules/          -> 模块管理
  - /api/testcase/cases/            -> 用例管理
  - /api/testcase/cases/import/     -> 用例导入
  - /api/testcase/cases/<id>/execute/ -> 用例执行
```

### testcase/environment_urls.py
```
位置：/d/AITestProduct/testcase/environment_urls.py
业务角色：环境路由
路径：
  - /api/environments/              -> 环境管理
  - /api/environments/<id>/health/  -> 健康检查
```

### testcase/views.py
```
位置：/d/AITestProduct/testcase/views.py
业务角色：用例视图
功能:
  - 用例 CRUD
  - 用例导入 (支持 AI 生成)
  - 用例版本管理
  - 用例执行
  - 模块管理
  - 环境管理
  - 变量管理
```

### testcase/tests.py
```
位置：/d/AITestProduct/testcase/tests.py
业务角色：单元测试
```

### testcase/management/__init__.py
```
位置：/d/AITestProduct/testcase/management/__init__.py
业务角色：Management 命令
```

### testcase/services/__init__.py
```
位置：/d/AITestProduct/testcase/services/__init__.py
业务角色：服务层初始化
```

### testcase/services/ai_case_gate.py
```
位置：/d/AITestProduct/testcase/services/ai_case_gate.py
业务角色：AI 用例生成网关
功能：控制 AI 用例生成入口，参数校验，流量控制
```

### testcase/services/ai_import_precheck_core.py
```
位置：/d/AITestProduct/testcase/services/ai_import_precheck_core.py
业务角色：AI 导入预检查
功能：用例导入前的 AI 预检查，识别潜在问题
```

### testcase/services/ai_openai.py
```
位置：/d/AITestProduct/testcase/services/ai_openai.py
业务角色：OpenAI 接口
功能：调用 OpenAI API 生成用例
```

### testcase/services/api_execution.py
```
位置：/d/AITestProduct/testcase/services/api_execution.py
业务角色：API 执行服务
功能：执行 API 测试用例，处理请求/响应
```

### testcase/services/assertions.py
```
位置：/d/AITestProduct/testcase/services/assertions.py
业务角色：断言服务
功能：实现各种断言逻辑 (状态码、响应体、JSONPath 等)
```

### testcase/services/auth_runtime.py
```
位置：/d/AITestProduct/testcase/services/auth_runtime.py
业务角色：运行时鉴权
功能：处理请求鉴权配置 (Bearer、API Key 等)
```

### testcase/services/case_subtypes.py
```
位置：/d/AITestProduct/testcase/services/case_subtypes.py
业务角色：用例子类型处理
功能：处理不同测试类型的用例逻辑
```

### testcase/services/variable_runtime.py
```
位置：/d/AITestProduct/testcase/services/variable_runtime.py
业务角色：变量运行时
功能：解析和注入环境变量、提取变量
```

---

## 五、execution 测试执行模块 (20 个文件)

### execution/__init__.py
```
位置：/d/AITestProduct/execution/__init__.py
业务角色：Python 包初始化
```

### execution/admin.py
```
位置：/d/AITestProduct/execution/admin.py
业务角色：Admin 注册
```

### execution/apps.py
```
位置：/d/AITestProduct/execution/apps.py
业务角色：应用配置
配置类：ExecutionConfig
```

### execution/models.py
```
位置：/d/AITestProduct/execution/models.py
业务角色：执行模型 (部分与 project 共享)
```

### execution/urls.py
```
位置：/d/AITestProduct/execution/urls.py
业务角色：执行路由
路径：
  - /api/execution/tasks/           -> 执行任务
  - /api/execution/scenarios/<id>/run/ -> 场景执行
  - /api/execution/scheduled-tasks/ -> 定时任务
```

### execution/perf_urls.py
```
位置：/d/AITestProduct/execution/perf_urls.py
业务角色：性能测试路由
路径：
  - /api/perf/k6-sessions/          -> k6 会话
  - /api/perf/k6-sessions/<id>/run/ -> k6 执行
```

### execution/views.py
```
位置：/d/AITestProduct/execution/views.py
业务角色：执行视图
功能：触发执行、查询状态、获取结果
```

### execution/views_k6.py
```
位置：/d/AITestProduct/execution/views_k6.py
业务角色：k6 执行视图
功能：k6 压测相关 API
```

### execution/tests.py
```
位置：/d/AITestProduct/execution/tests.py
业务角色：单元测试
```

### execution/tasks.py
```
位置：/d/AITestProduct/execution/tasks.py
业务角色：Celery 异步任务
功能：异步执行测试任务
```

### execution/tasks_k6.py
```
位置：/d/AITestProduct/execution/tasks_k6.py
业务角色：k6 任务
功能：执行 k6 压测任务
```

### execution/engine.py
```
位置：/d/AITestProduct/execution/engine.py
业务角色：执行引擎核心
功能:
  - 测试任务调度
  - 用例执行逻辑
  - 结果收集与反馈
```

### execution/consumers.py
```
位置：/d/AITestProduct/execution/consumers.py
业务角色：WebSocket 消费者
功能:
  - 处理 WebSocket 连接
  - 实时推送执行进度
  - 推送日志流
```

### execution/routing.py
```
位置：/d/AITestProduct/execution/routing.py
业务角色：WebSocket 路由
路径：
  - ws/execution/<run_id>/          -> 执行进度推送
```

### execution/scheduler.py
```
位置：/d/AITestProduct/execution/scheduler.py
业务角色：定时调度器
功能:
  - 管理定时任务
  - 执行周期性测试任务
  - Cron 表达式解析
```

### execution/middleware_ws.py
```
位置：/d/AITestProduct/execution/middleware_ws.py
业务角色：WebSocket 中间件
功能：处理 WebSocket 请求的中间逻辑
```

### execution/serialize.py
```
位置：/d/AITestProduct/execution/serialize.py
业务角色：执行数据序列化
```

### execution/management/__init__.py
```
位置：/d/AITestProduct/execution/management/__init__.py
业务角色：Management 命令
```

### execution/services/__init__.py
```
位置：/d/AITestProduct/execution/services/__init__.py
业务角色：服务层初始化
```

### execution/services/health_checker.py
```
位置：/d/AITestProduct/execution/services/health_checker.py
业务角色：健康检查服务
功能：检查环境和系统健康状态
```

### execution/services/k6_ai_generator.py
```
位置：/d/AITestProduct/execution/services/k6_ai_generator.py
业务角色：k6 AI 脚本生成
功能：使用 AI 生成 k6 压测脚本
```

### execution/services/k6_chain_builder.py
```
位置：/d/AITestProduct/execution/services/k6_chain_builder.py
业务角色：k6 请求链构建
功能：构建 k6 测试请求链
```

### execution/services/k6_stderr_parser.py
```
位置：/d/AITestProduct/execution/services/k6_stderr_parser.py
业务角色：k6 错误解析
功能：解析 k6 执行错误信息
```

### execution/services/k6_template_generator.py
```
位置：/d/AITestProduct/execution/services/k6_template_generator.py
业务角色：k6 模板生成
功能：生成 k6 测试脚本模板
```

### execution/services/metric_calculator.py
```
位置：/d/AITestProduct/execution/services/metric_calculator.py
业务角色：指标计算
功能：计算性能测试指标 (P50/P90/P99、RPS 等)
```

### execution/services/scenario_generator.py
```
位置：/d/AITestProduct/execution/services/scenario_generator.py
业务角色：场景生成
功能：生成测试场景
```

### execution/services/scenario_runner.py
```
位置：/d/AITestProduct/execution/services/scenario_runner.py
业务角色：场景运行
功能：执行测试场景
```

---

*后续模块说明请参考 FILE_DETAILS.md*
