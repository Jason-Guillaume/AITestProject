# UI自动化脚本上传与执行功能 - 文档索引

## 📚 文档导航

### 🚀 快速开始
- **[5分钟快速上手](./UI_AUTOMATION_QUICK_START.md)** - 最快速的入门指南
- **[功能总览](./UI_AUTOMATION_README.md)** - 完整功能介绍和使用说明

### 📖 详细文档
1. **[阶段1：脚本上传功能](./35-UI自动化脚本上传功能开发文档.md)**
   - Django模型设计
   - 序列化器实现
   - 视图集开发
   - 文件处理工具
   - API接口文档

2. **[阶段2：执行引擎](./36-UI自动化脚本执行引擎开发文档.md)**
   - 执行引擎架构
   - ScriptRunner类详解
   - Redis日志收集
   - 执行状态管理
   - 性能优化

3. **[完整实现总结](./37-UI自动化脚本上传与执行功能实现总结.md)**
   - 已完成工作清单
   - 文件清单
   - 数据库表结构
   - 部署步骤
   - 后续计划

### 🔍 参考文档
- **[API快速参考](./38-UI自动化功能快速参考.md)** - API端点、命令示例、常见问题
- **[测试脚本](./test_ui_script_upload_execution.py)** - 完整的功能测试代码

---

## 🎯 按需求查找文档

### 我想快速上手
👉 [5分钟快速上手](./UI_AUTOMATION_QUICK_START.md)

### 我想了解完整功能
👉 [功能总览](./UI_AUTOMATION_README.md)

### 我想查看API接口
👉 [API快速参考](./38-UI自动化功能快速参考.md)

### 我想了解技术实现
👉 [阶段1文档](./35-UI自动化脚本上传功能开发文档.md) + [阶段2文档](./36-UI自动化脚本执行引擎开发文档.md)

### 我想运行测试
👉 [测试脚本](./test_ui_script_upload_execution.py)

---

## 📊 功能概览

### 核心功能
- ✅ 脚本上传（LINEAR/POM模式）
- ✅ 脚本执行（pytest集成）
- ✅ 实时日志收集（Redis）
- ✅ 执行状态管理
- ✅ 执行历史记录

### 技术栈
- Django + DRF
- MySQL + Redis
- pytest + subprocess
- threading

---

## 🔗 核心文件

- `assistant/models.py` - 数据模型
- `assistant/views.py` - 视图集
- `assistant/utils/script_runner.py` - 执行引擎
- `assistant/utils/script_handler.py` - 文件处理

---

**最后更新**: 2026-05-01
