# common 公共模块

## 模块概述
提供全项目共享的基础模型、公共服务和通用功能。

## 文件列表

### __init__.py
- **作用**: Python 包初始化

### admin.py
- **作用**: Django Admin 配置
- **业务功能**: 公共模型后台配置

### apps.py
- **作用**: 应用配置
- **业务功能**: 定义 CommonConfig

### models.py
- **作用**: 基础模型定义
- **业务功能**:
  - `BaseModel`: 基础模型类
    - 创建人、更新人字段
    - 创建时间、更新时间
    - 软删除标记
  - `AuditEvent`: 审计事件
    - 记录关键业务对象的增删改
    - before/after 快照
    - 操作 IP、User-Agent

### services/audit.py
- **作用**: 审计服务
- **业务功能**: 实现审计事件的记录逻辑

### serialize.py
- **作用**: 公共序列化器
- **业务功能**: 通用数据序列化模板

### tests.py
- **作用**: 单元测试入口

### views.py
- **作用**: 公共视图
- **业务功能**: 通用 API 视图

---
