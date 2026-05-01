# UI自动化功能 - 5分钟快速上手

## 🚀 快速开始

### 步骤1：准备环境（1分钟）

```bash
# 安装依赖
pip install redis pytest pytest-timeout

# 启动Redis
redis-server

# 执行数据库迁移
python manage.py migrate assistant
```

### 步骤2：创建测试脚本（1分钟）

创建文件 `test_example.py`:

```python
import pytest

def test_simple():
    """简单测试用例"""
    print("Hello UI Automation!")
    assert 1 + 1 == 2
    print("Test passed!")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### 步骤3：上传脚本（1分钟）

```bash
curl -X POST http://localhost:8000/api/assistant/ui-scripts/ \
  -F "name=我的第一个测试" \
  -F "script_type=LINEAR" \
  -F "entry_point=test_example.py" \
  -F "file_path=@test_example.py"
```

响应示例：
```json
{
  "id": 1,
  "name": "我的第一个测试",
  "script_type": "LINEAR",
  "file_path": "/media/ui_scripts/2026/05/01/test_example.py",
  "entry_point": "test_example.py",
  "is_active": true
}
```

### 步骤4：执行脚本（1分钟）

```bash
curl -X POST http://localhost:8000/api/assistant/ui-script-executions/execute/ \
  -H "Content-Type: application/json" \
  -d '{"script_id": 1}'
```

响应示例：
```json
{
  "id": 1,
  "execution_id": "1_1714521600",
  "status": "pending",
  "status_display": "等待执行"
}
```

### 步骤5：查看日志（1分钟）

```bash
# 等待几秒后查询日志
curl http://localhost:8000/api/assistant/ui-script-executions/1/logs/
```

响应示例：
```json
{
  "execution_id": "1_1714521600",
  "logs": [
    {
      "timestamp": "2026-05-01T10:00:01Z",
      "type": "system",
      "message": "开始执行脚本 (ID: 1)"
    },
    {
      "timestamp": "2026-05-01T10:00:02Z",
      "type": "stdout",
      "message": "Hello UI Automation!"
    },
    {
      "timestamp": "2026-05-01T10:00:03Z",
      "type": "stdout",
      "message": "Test passed!"
    }
  ],
  "total": 3
}
```

---

## 🎉 恭喜！

你已经成功完成了第一个UI自动化脚本的上传和执行！

---

## 📖 下一步

### 上传POM模式脚本

1. 创建项目结构：
```
my_test_project/
├── pages/
│   ├── __init__.py
│   └── login_page.py
└── tests/
    ├── __init__.py
    └── test_login.py
```

2. 打包成ZIP：
```bash
zip -r my_test_project.zip my_test_project/
```

3. 上传：
```bash
curl -X POST http://localhost:8000/api/assistant/ui-scripts/ \
  -F "name=POM测试项目" \
  -F "script_type=POM" \
  -F "entry_point=tests/test_login.py" \
  -F "file_path=@my_test_project.zip"
```

---

## 🔍 常用命令

```bash
# 查看所有脚本
curl http://localhost:8000/api/assistant/ui-scripts/

# 查看执行历史
curl http://localhost:8000/api/assistant/ui-script-executions/?script_id=1

# 查看执行状态
curl http://localhost:8000/api/assistant/ui-script-executions/1/status_detail/

# 禁用脚本
curl -X POST http://localhost:8000/api/assistant/ui-scripts/1/toggle_active/
```

---

## 📚 更多文档

- [完整API文档](./38-UI自动化功能快速参考.md)
- [功能总览](./UI_AUTOMATION_README.md)
- [详细设计文档](./35-UI自动化脚本上传功能开发文档.md)
