# UI自动化工作台 - 快速开始指南

## 功能概述

UI自动化工作台现已支持以下功能：

### 1. 四种脚本来源方式
- **在线编辑** - 直接在浏览器中编写测试脚本
- **AI生成** - 通过AI自动生成测试脚本
- **单文件上传** - 上传单个Python或Java测试文件
- **POM工程导入** - 导入完整的测试工程（ZIP或Git）

### 2. 多语言支持
- **Python** - 支持所有主流Python测试框架
- **Java** - 支持所有主流Java测试框架

### 3. 自动框架检测
系统会自动检测项目使用的测试框架：
- Python: Pytest, Unittest, Nose, Robot Framework, Behave
- Java: JUnit 4/5, TestNG, Cucumber, Spock

### 4. 智能依赖管理
- 自动识别项目依赖（requirements.txt, pom.xml, build.gradle）
- 支持Maven和Gradle构建工具
- 自动配置执行环境

## 快速开始

### 步骤1: 执行数据库迁移

```bash
cd d:/AITestProduct
python manage.py migrate assistant
```

### 步骤2: 启动开发服务器

```bash
# 启动Django后端
python manage.py runserver

# 启动前端（新终端）
cd frontend
npm run dev
```

### 步骤3: 访问工作台

打开浏览器访问：`http://localhost:5173/script-hub/webui`

## 使用示例

### 示例1: 创建在线Python脚本

1. 选择"在线编辑"模式
2. 填写脚本信息：
   - 脚本名称: `登录测试`
   - 脚本语言: `Python`
   - 测试框架: `Pytest`
   - 入口点: `test_login.py`
3. 在编辑器中输入代码
4. 点击"保存并创建"

### 示例2: 上传Java POM工程

1. 选择"POM工程"模式
2. 填写工程信息
3. 上传ZIP文件
4. 点击"导入工程"

## API接口文档

### 创建脚本
**POST** `/assistant/ui-scripts/`

### 获取脚本列表
**GET** `/assistant/ui-scripts/`

### 执行脚本
**POST** `/assistant/ui-script-executions/execute/`

### 获取执行日志
**GET** `/assistant/ui-script-executions/{id}/logs/`

## 配置说明

### Django设置 (settings.py)

```python
# Redis配置（用于日志存储）
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

# 脚本执行超时（秒）
UI_SCRIPT_TIMEOUT = 3600  # 1小时
```

### 环境要求

**Python环境：**
- Python 3.7+
- pip
- virtualenv（推荐）

**Java环境（如果使用Java脚本）：**
- JDK 8+
- Maven 3.6+ 或 Gradle 6.0+
- JAVA_HOME环境变量

**Redis：**
- Redis 5.0+
- 用于存储执行日志和状态

## 测试框架支持

### Python框架
- Pytest ✅
- Unittest ✅
- Nose ✅
- Robot Framework ✅
- Behave ✅

### Java框架
- JUnit 4/5 ✅
- TestNG ✅
- Cucumber ✅
- Spock ✅

## 故障排查

### 问题1: 脚本执行失败
1. 检查执行日志
2. 验证依赖是否安装
3. 确认入口点路径正确

### 问题2: 框架检测不准确
1. 手动指定框架
2. 确保项目包含框架特征文件

### 问题3: Redis连接失败
1. 确认Redis服务运行
2. 检查Redis配置

## 技术支持

如有问题，请查看：
- 实现总结文档：`IMPLEMENTATION_SUMMARY.md`
- Django日志：`logs/django.log`

---

**版本：** 1.0.0  
**更新日期：** 2024-05-01
