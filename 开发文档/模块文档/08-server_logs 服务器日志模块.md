# server_logs 服务器日志模块

## 模块概述
负责服务器日志的实时采集、历史检索、AI 分析、工单自动生成等功能。

## 文件列表

### __init__.py
- **作用**: Python 包初始化

### access.py
- **作用**: 日志访问控制
- **业务功能**: 控制日志访问权限

### admin.py
- **作用**: Django Admin 后台配置

### ai_analyze.py
- **作用**: AI 日志分析
- **业务功能**: 使用 AI 分析日志中的问题

### ai_ticket.py
- **作用**: AI 工单生成
- **业务功能**: 基于日志自动生成工单草稿

### apps.py
- **作用**: 应用配置
- **业务功能**: 定义 ServerLogsConfig

### audit.py
- **作用**: 审计服务
- **业务功能**: 记录日志模块的操作审计

### consumers.py
- **作用**: WebSocket 消费者
- **业务功能**: 实时日志推送

### crypto.py
- **作用**: 加密服务
- **业务功能**: SSH 凭据的加密/解密

### defect_create.py
- **作用**: 缺陷创建服务
- **业务功能**: 基于日志分析自动创建缺陷

### es_client.py
- **作用**: Elasticsearch 客户端
- **业务功能**: ES 查询与写入

### log_context.py
- **作用**: 日志上下文
- **业务功能**: 管理日志查询上下文

### models.py
- **作用**: 数据模型定义
- **业务功能**:
  - `RemoteLogServer`: 远程 SSH 日志主机配置
  - `ServerLogAuditEvent`: 日志操作审计
  - `LogAutoTicketJob`: AI 工单草稿任务

### routing.py
- **作用**: WebSocket 路由
- **业务功能**: 实时日志 WebSocket 路由

### serializers.py
- **作用**: 序列化器定义
- **业务功能**: 日志数据序列化

### ssh_tail.py
- **作用**: SSH 日志 tail
- **业务功能**: 通过 SSH 远程 tail 日志文件

### tasks.py
- **作用**: Celery 异步任务
- **业务功能**: 日志分析异步任务

### urls.py
- **作用**: 日志模块路由
- **业务功能**: 服务器日志相关 API 路径

### validators.py
- **作用**: 数据验证器
- **业务功能**: SSH 配置等数据验证

### views.py
- **作用**: 日志视图
- **业务功能**:
  - 远程主机管理
  - 实时日志采集
  - 历史日志检索
  - AI 日志分析
  - 工单自动生成

---
