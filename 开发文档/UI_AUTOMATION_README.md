# UI自动化脚本上传与执行功能

## 📋 功能概述

本功能实现了完整的UI自动化脚本管理和执行能力，支持：

- ✅ 脚本上传（单文件/ZIP包）
- ✅ 脚本执行（LINEAR/POM模式）
- ✅ 实时日志收集
- ✅ 执行状态管理
- ✅ 执行历史记录

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install redis pytest pytest-timeout
```

### 2. 启动Redis

```bash
redis-server
```

### 3. 执行数据库迁移

```bash
python manage.py migrate assistant
```

### 4. 测试功能

```bash
# 运行测试脚本
python 开发文档/test_ui_script_upload_execution.py
```

---

## 📁 项目结构

```
assistant/
├── models.py                    # 数据模型
│   ├── UIScriptUpload          # 脚本上传模型
│   └── UIScriptExecution       # 执行记录模型
├── serialize.py                 # 序列化器
│   ├── UIScriptUploadSerializer
│   ├── UIScriptExecutionSerializer
│   └── UIScriptExecutionListSerializer
├── views.py                     # 视图集
│   ├── UIScriptUploadViewSet
│   └── UIScriptExecutionViewSet
├── urls.py                      # URL路由
├── signals.py                   # 信号处理
└── utils/
    ├── script_runner.py        # 执行引擎
    └── script_handler.py       # 文件处理

开发文档/
├── 35-UI自动化脚本上传功能开发文档.md
├── 36-UI自动化脚本执行引擎开发文档.md
├── 37-UI自动化脚本上传与执行功能实现总结.md
├── 38-UI自动化功能快速参考.md
├── test_ui_script_upload_execution.py
└── UI_AUTOMATION_README.md (本文件)
```

---

## 🔧 核心组件

### 1. 脚本上传 (UIScriptUpload)

**支持的脚本类型**:
- **LINEAR**: 线性脚本，单文件执行
- **POM**: Page Object Model，支持多文件项目

**上传流程**:
1. 用户上传文件（.py 或 .zip）
2. 系统验证文件类型和大小
3. 保存文件到 `media/ui_scripts/`
4. 如果是ZIP，解压到 `media/workspaces/{id}/`
5. 验证入口点文件存在

### 2. 脚本执行 (ScriptRunner)

**执行流程**:
1. 创建执行记录（pending）
2. 启动异步执行线程
3. 构建执行环境（PYTHONPATH）
4. 启动pytest子进程
5. 流式读取stdout/stderr → Redis
6. 更新执行状态（success/failed）

**技术栈**:
- **执行框架**: pytest
- **进程管理**: subprocess.Popen
- **日志存储**: Redis List
- **状态存储**: Redis String + MySQL

---

## 📡 API接口

### 脚本管理

```bash
# 上传脚本
POST /api/assistant/ui-scripts/

# 获取脚本列表
GET /api/assistant/ui-scripts/

# 获取脚本详情
GET /api/assistant/ui-scripts/{id}/

# 切换启用状态
POST /api/assistant/ui-scripts/{id}/toggle_active/

# 获取工作空间信息
GET /api/assistant/ui-scripts/{id}/workspace_info/
```

### 脚本执行

```bash
# 执行脚本
POST /api/assistant/ui-script-executions/execute/

# 获取执行记录列表
GET /api/assistant/ui-script-executions/

# 获取执行日志
GET /api/assistant/ui-script-executions/{id}/logs/

# 获取执行状态详情
GET /api/assistant/ui-script-executions/{id}/status_detail/
```

---

## 💾 数据存储

### MySQL表

**ui_script_upload**: 脚本元数据
- id, name, script_type, file_path, entry_point
- workspace_path, git_repo_url, is_active
- created_at, updated_at

**ui_script_execution**: 执行记录
- id, execution_id, script_id, status
- return_code, started_at, completed_at, duration
- error_message, triggered_by

### Redis数据

**日志存储** (List):
```
ui_script_execution:{execution_id}:logs
```

**状态存储** (String):
```
ui_script_execution:{execution_id}:status
```

---

## 🎯 使用示例

### Python代码

```python
from assistant.utils.script_runner import execute_ui_script

# 执行脚本
result = execute_ui_script(
    script_upload_instance_id=1,
    execution_id='custom_id',
    timeout=1800
)

print(result)
# {'success': True, 'execution_id': 'custom_id', 'return_code': 0, 'duration': 12.34}
```

### cURL命令

```bash
# 1. 上传脚本
curl -X POST http://localhost:8000/api/assistant/ui-scripts/ \
  -F "name=登录测试" \
  -F "script_type=LINEAR" \
  -F "entry_point=test_login.py" \
  -F "file_path=@test_login.py"

# 2. 执行脚本
curl -X POST http://localhost:8000/api/assistant/ui-script-executions/execute/ \
  -H "Content-Type: application/json" \
  -d '{"script_id": 1}'

# 3. 查询日志
curl http://localhost:8000/api/assistant/ui-script-executions/1/logs/
```

---

## ⚙️ 配置说明

### settings.py

```python
# Redis配置
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

# 脚本执行超时（秒）
UI_SCRIPT_TIMEOUT = 3600  # 1小时

# 文件上传配置
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB

# 媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

---

## 🔍 监控与调试

### 查看Redis日志

```bash
redis-cli
> LRANGE ui_script_execution:1_1714521600:logs 0 -1
> GET ui_script_execution:1_1714521600:status
```

### 查看数据库记录

```python
from assistant.models import UIScriptExecution

# 查询执行记录
executions = UIScriptExecution.objects.filter(script_id=1)
for exe in executions:
    print(f"{exe.execution_id}: {exe.status} ({exe.duration}s)")
```

### 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 🛡️ 安全考虑

1. **脚本隔离**: 每个脚本在独立工作空间执行
2. **资源限制**: 执行超时限制（默认1小时）
3. **文件验证**: 仅支持.py和.zip文件，限制50MB
4. **权限控制**: 仅启用的脚本可执行

---

## 📈 性能优化

1. **异步执行**: 使用threading避免阻塞API
2. **流式输出**: 并发读取stdout/stderr
3. **日志过期**: Redis日志24小时自动清理
4. **数据库索引**: 关键字段已建立索引

---

## 🐛 常见问题

### Q: 脚本执行超时？
**A**: 修改 `settings.UI_SCRIPT_TIMEOUT` 或传入 `timeout` 参数

### Q: 日志丢失？
**A**: Redis日志保留24小时，建议及时查询

### Q: 如何查看工作空间文件？
**A**: 调用 `/api/assistant/ui-scripts/{id}/workspace_info/`

### Q: 支持并发执行吗？
**A**: 支持，但建议控制并发数量

---

## 🚧 后续计划

### 阶段3：前端界面
- [ ] 脚本上传表单
- [ ] 脚本列表展示
- [ ] 执行按钮和状态显示
- [ ] 实时日志展示（WebSocket）

### 阶段4：高级功能
- [ ] 定时执行任务
- [ ] 并发执行控制
- [ ] 执行结果报告
- [ ] 失败重试机制
- [ ] Docker容器隔离

---

## 📚 相关文档

- [35-UI自动化脚本上传功能开发文档.md](./35-UI自动化脚本上传功能开发文档.md) - 阶段1详细设计
- [36-UI自动化脚本执行引擎开发文档.md](./36-UI自动化脚本执行引擎开发文档.md) - 阶段2详细设计
- [37-UI自动化脚本上传与执行功能实现总结.md](./37-UI自动化脚本上传与执行功能实现总结.md) - 完整实现总结
- [38-UI自动化功能快速参考.md](./38-UI自动化功能快速参考.md) - API快速参考

---

## 👥 贡献者

- 开发团队
- 创建日期: 2026-05-01

---

## 📄 许可证

本项目遵循项目整体许可证。
