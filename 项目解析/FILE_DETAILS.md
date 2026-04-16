# 每个 Python 文件详细业务说明

## 一、项目入口与配置 (6 个文件)

### 1. manage.py
```
位置：/d/AITestProduct/manage.py
业务角色：项目命令行入口
主要职责：
  - Django 管理命令的统一入口
  - 支持命令：runserver, migrate, createsuperuser, shell, celery worker 等
  - 设置环境变量 DJANGO_SETTINGS_MODULE
使用场景：
  - 启动开发服务器：python manage.py runserver
  - 数据库迁移：python manage.py migrate
  - 创建管理员：python manage.py createsuperuser
  - 执行 Celery Worker: python manage.py runworker
```

### 2. AITestProduct/__init__.py
```
位置：/d/AITestProduct/AITestProduct/__init__.py
业务角色：项目包标识
主要职责：使目录成为 Python 包
```

### 3. AITestProduct/asgi.py
```
位置：/d/AITestProduct/AITestProduct/asgi.py
业务角色：异步服务器网关配置
主要职责：
  - 创建 ASGI application
  - 集成 Django Channels
  - 配置 WebSocket 路由
业务场景：
  - 实时日志推送 (WebSocket)
  - 测试执行进度实时通知
  - 服务器日志 tail 实时流
启动方式：daphne -b 0.0.0.0 -p 8000 AITestProduct.asgi:application
```

### 4. AITestProduct/celery.py
```
位置：/d/AITestProduct/AITestProduct/celery.py
业务角色：分布式任务队列配置
主要职责：
  - 初始化 Celery 应用
  - 配置 Broker (Redis/MySQL)
  - 配置结果 Backend
  - 设置任务序列化 (JSON)
  - 配置任务确认机制
业务场景：
  - AI 生成用例 (异步)
  - 测试执行 (异步)
  - k6 压测任务
  - 日志 AI 分析
  - 定时调度任务
启动方式：celery -A AITestProduct worker -l info
或：python manage.py runworker
```

### 5. AITestProduct/settings.py
```
位置：/d/AITestProduct/AITestProduct/settings.py
业务角色：核心配置文件
主要配置模块：
  1. 数据库配置 (DATABASES)
     - MySQL 连接 (host, port, user, password, name)
     - 严格模式 SQL 模式
     - 生产环境密码强校验
  
  2. 缓存配置 (CACHES)
     - Redis 优先，降级到 LocMem
     - 用于验证码、频率限制
  
  3. Channels 配置 (CHANNEL_LAYERS)
     - Redis 通道层 (WebSocket)
     - 降级到 InMemory
  
  4. REST Framework 配置 (REST_FRAMEWORK)
     - 默认认证：TokenAuthentication
     - 默认权限：IsAuthenticated
     - 限流配置：server_logs_analyze: 40/hour
  
  5. Celery 配置
     - Broker: Redis (优先) / MySQL (降级)
     - Backend: django-db / rpc://
     - 序列化：JSON
     - acks_late: True
     - prefetch_multiplier: 1
  
  6. AI 配置
     - RAG_TOP_K: 检索召回数 (默认 5)
     - RAG_MAX_CONTEXT_CHARS: 上下文长度 (默认 1200)
     - KNOWLEDGE_EMBEDDING_PROVIDER: openai/ollama
     - AI_GENERATE_MIN/MAX_CASES: 生成用例数量限制
     - AI_GUARD_DAILY_REQUESTS: 每日配额
     - AI_GUARD_MAX_CONCURRENCY: 最大并发
  
  7. 服务器日志配置
     - SERVER_LOGS_FERNET_KEY: SSH 凭据加密密钥
     - SERVER_LOGS_LOKI_BASE: Grafana Loki 地址
     - ELASTICSEARCH_*: ES 连接配置
     - SERVER_LOGS_SSH_HOST_KEY_POLICY: 主机密钥策略
  
  8. 邮件配置
     - EMAIL_BACKEND: SMTP/Console
     - DEFAULT_FROM_EMAIL: 发件人
     - USER_CENTER_ADMIN_EMAIL: 管理员邮箱
  
  9. 文件存储
     - STATIC_URL: /static/
     - MEDIA_URL: /media/
     - MEDIA_ROOT: media/
  
  10. 安全配置
      - DEBUG: 开发/生产开关
      - SECRET_KEY: 必须环境变量
      - ALLOWED_HOSTS: 允许 hosts
      - 密码兼容性配置 (LEGACY_LOGIN_*)
使用方式：Django 自动加载，通过 os.environ 覆盖
```

### 6. AITestProduct/urls.py
```
位置：/d/AITestProduct/AITestProduct/urls.py
业务角色：主路由分发器
路由映射:
  /admin/                    -> Django 后台管理
  /api/sys/                  -> 系统管理 (用户/组织/角色)
  /api/change-requests/      -> 审批流程
  /api/user/                 -> 用户中心
  /api/project/              -> 项目管理
  /api/testcase/             -> 测试用例管理
  /api/environments/         -> 测试环境管理
  /api/execution/            -> 测试执行
  /api/perf/                 -> 性能测试
  /api/defect/               -> 缺陷管理
  /api/assistant/            -> AI 助手
  /api/ai/                   -> AI 功能
  /api/server-logs/          -> 服务器日志
  /media/                    -> 媒体文件 (DEBUG 模式)
路由机制：include() 分发到各 app 的 urls.py
```

### 7. AITestProduct/wsgi.py
```
位置：/d/AITestProduct/AITestProduct/wsgi.py
业务角色：同步 Web 服务器入口
主要职责：WSGI application 创建
使用场景：
  - Gunicorn/uWSGI 部署
  - 传统 HTTP 请求处理
启动方式：gunicorn AITestProduct.wsgi:application
```

---

## 二、user 用户管理模块 (15 个文件)

### user/__init__.py
```
位置：/d/AITestProduct/user/__init__.py
业务角色：Python 包初始化
```

### user/admin.py
```
位置：/d/AITestProduct/user/admin.py
业务角色：Django Admin 后台注册
注册模型:
  - User: 用户管理
  - UserChangeRequest: 变更申请
  - SystemMessage: 系统消息
  - AIModelConfig: AI 配置
  - Organization: 组织管理
  - AiQuotaPolicy: AI 配额策略
  - SystemMessageSetting: 消息设置
访问路径：/admin/ (需超级管理员登录)
```

### user/apps.py
```
位置：/d/AITestProduct/user/apps.py
业务角色：应用配置
配置类：UserConfig
注册点：在 settings.py INSTALLED_APPS 中注册
```

### user/models.py
```
位置：/d/AITestProduct/user/models.py
业务角色：用户领域模型定义
数据库表：
  1. sys_user (User)
     字段：username, password, real_name, phone_number, 
           avatar, is_active, is_system_admin, email
     继承：AbstractUser + BaseModel
     用途：系统用户账户
  
  2. sys_user_change_request (UserChangeRequest)
     字段：user, request_type(username/password), new_value,
           status(pending/approved/rejected), approver, approved_at
     用途：敏感信息变更审批流程
  
  3. sys_system_message (SystemMessage)
     字段：recipient, title, content, is_read, 
           related_request, created_at
     用途：站内通知消息
  
  4. sys_ai_model_config (AIModelConfig)
     字段：project, model_type, api_key, base_url, is_connected
     约束：project + model_type 唯一
     用途：AI 模型接入配置
  
  5. sys_org (Organization)
     字段：org_name, description, members (M2M), projects (M2M)
     用途：组织管理，用于资源隔离与共享
  
  6. ai_quota_policy (AiQuotaPolicy)
     字段：scope_type(project/org/user), project, org, user,
           daily_requests, max_concurrency, allowed_actions, is_enabled
     用途：AI 调用配额与并发控制
  
  7. sys_message_setting (SystemMessageSetting)
     字段：recipient, in_app_enabled, email_enabled, 
           sms_enabled, digest_enabled, digest_time
     约束：recipient 唯一
     用途：用户通知偏好设置
```

### user/permissions.py
```
位置：/d/AITestProduct/user/permissions.py
业务角色：自定义权限类
权限类:
  1. IsSystemAdmin
     用途：系统管理员权限检查
     适用接口：用户管理、组织管理、角色管理
  
  2. IsApprovalAdmin
     用途：审批管理员权限检查
     适用接口：变更申请审批
实现方式：继承 BasePermission，重写 has_permission()
```

### user/serialize.py
```
位置：/d/AITestProduct/user/serialize.py
业务角色：数据序列化器定义
序列化器:
  1. UserSerializer
     用途：用户信息序列化
     字段：id, username, real_name, phone_number, email, 
           is_active, is_system_admin, avatar
  
  2. UserRegisterSerializer
     用途：用户注册
     字段：username, password, real_name, email
     验证：用户名唯一、密码强度、邮箱格式
  
  3. UserProfileSerializer
     用途：用户资料更新
     字段：real_name, phone_number, email, avatar
  
  4. UserLoginSerializer
     用途：用户登录
     字段：username, password
     验证：密码兼容 (明文/MD5/SHA256/Django Hash)
  
  5. OrganizationSerializer
     用途：组织序列化
     字段：id, org_name, description, members, projects
  
  6. SystemMessageSerializer
     用途：系统消息序列化
     字段：id, title, content, is_read, created_at
  
  7. SystemMessageSettingSerializer
     用途：消息设置序列化
     字段：in_app_enabled, email_enabled, sms_enabled, 
           digest_enabled, digest_time
  
  8. RoleSerializer
     用途：角色 (Group) 序列化
     字段：id, name, permissions
  
  9. UserChangeRequestListSerializer
     用途：变更申请列表
     字段：id, user, request_type, status, created_at
  
  10. UserChangeRequestDecisionSerializer
      用途：变更决策
      字段：decision(approve/reject)
```

### user/signals.py
```
位置：/d/AITestProduct/user/signals.py
业务角色：Django 信号处理器
监听事件:
  1. post_save (User)
     - 用户创建后发送欢迎消息
     - 初始化用户消息设置
  
  2. 其他信号
     - 用户删除后的关联数据处理
触发动作：
  - 发送站内消息
  - 发送通知邮件
  - 审计事件记录
```

### user/tests.py
```
位置：/d/AITestProduct/user/tests.py
业务角色：单元测试入口
测试范围：用户模型、序列化器、视图
```

### user/urls.py
```
位置：/d/AITestProduct/user/urls.py
业务角色：用户中心路由
路径映射:
  register/              -> 用户注册
  login/                 -> 用户登录
  captcha/               -> 验证码
  profile/               -> 用户资料
  password/              -> 修改密码
  me/                    -> 当前用户信息
  me/audit/events/       -> 审计事件
  me/change-request/     -> 提交变更申请
  me/pending-status/     -> 待审批状态
  me/messages/           -> 站内消息列表
  me/messages/<id>/read/ -> 标记已读
路由方式：ViewSet + Router
```

### user/sys_urls.py
```
位置：/d/AITestProduct/user/sys_urls.py
业务角色：系统管理路由
路径映射:
  users/                 -> 用户管理 (CRUD)
  organizations/         -> 组织管理 (CRUD)
  roles/                 -> 角色管理 (CRUD)
  message-settings/      -> 消息设置管理
权限要求：IsSystemAdmin
```

### user/approval_urls.py
```
位置：/d/AITestProduct/user/approval_urls.py
业务角色：审批流程路由
路径映射:
  change-requests/       -> 变更申请列表
  change-requests/<id>/approve/  -> 批准申请
  change-requests/<id>/reject/   -> 拒绝申请
权限要求：IsApprovalAdmin
```

### user/views.py
```
位置：/d/AITestProduct/user/views.py
业务角色：用户中心视图实现
视图类/函数:
  
  1. UserViewSet (viewsets.ModelViewSet)
     路径：/api/sys/users/
     功能：用户 CRUD
     权限：创建/删除需系统管理员
      queryset 过滤：普通用户仅可见项目成员 + 自己
  
  2. OrganizationViewSet
     路径：/api/sys/organizations/
     功能：组织 CRUD
     权限：IsSystemAdmin
  
  3. SystemMessageSettingViewSet
     路径：/api/sys/message-settings/
     功能：消息设置 CRUD
     逻辑：update_or_create 单用户设置
  
  4. RoleViewSet
     路径：/api/sys/roles/
     功能：角色 (Group) CRUD
     权限：IsSystemAdmin
  
  5. CaptchaAPIView
     路径：/api/user/captcha/
     功能：生成验证码图片
     逻辑：IP 频率限制 (10 次/分钟)
           缓存验证码 (5 分钟)
           返回 Base64 图片
  
  6. UserRegisterAPIView
     路径：/api/user/register/
     功能：用户注册
     权限：公开 (无需认证)
  
  7. UserLoginAPIView
     路径：/api/user/login/
     功能：用户登录 + Token 生成
     权限：公开
     返回：token, username, real_name, user_id, is_system_admin
  
  8. CurrentUserAPIView
     路径：/api/user/me/
     功能：获取当前用户信息
  
  9. ChangePasswordAPIView
     路径：/api/user/password/
     功能：修改密码
     验证：旧密码、新密码强度 (8 位 + 大小写 + 数字)
  
  10. UserProfileAPIView
      路径：/api/user/profile/
      功能：更新用户资料 (头像/姓名/手机号)
      支持：multipart 文件上传
  
  11. UserMyPendingSensitiveStatusAPIView
      路径：/api/user/me/pending-sensitive-status/
      功能：查询待审批状态
  
  12. UserSensitiveChangeRequestAPIView
      路径：/api/user/me/change-request/
      功能：提交变更申请
  
  13. SystemMessageListAPIView
      路径：/api/user/me/messages/
      功能：站内消息列表
      过滤：is_read 参数
  
  14. SystemMessageMarkReadAPIView
      路径：/api/user/me/messages/<id>/read/
      功能：标记消息已读
  
  15. UserAuditEventListAPIView
      路径：/api/user/me/audit/events/
      功能：用户审计事件查询
  
  16. AdminUserChangeRequestListAPIView
      路径：/api/change-requests/
      功能：管理员查看变更申请
  
  17. AdminChangeRequestApproveAPIView
      路径：/api/change-requests/<id>/approve/
      功能：批准变更申请
  
  18. AdminChangeRequestRejectAPIView
      路径：/api/change-requests/<id>/reject/
      功能：拒绝变更申请
  
  19. AdminUserChangeRequestDecisionAPIView
      路径：/api/change-requests/<id>/decision/
      功能：兼容旧版决策接口
```

### user/sys_views.py
```
位置：/d/AITestProduct/user/sys_views.py
业务角色：系统管理视图
功能：系统级用户/组织/角色管理逻辑
权限：IsSystemAdmin
```

### user/captcha_image.py
```
位置：/d/AITestProduct/user/captcha_image.py
业务角色：验证码图片生成
功能:
  - CleanTechCaptcha: 科技感验证码
  - 白底蓝字，弱噪声
  - 尺寸：120x40
  - 字体大小：30-38
返回：Base64 编码 PNG 图片
```

### user/change_request_actions.py
```
位置：/d/AITestProduct/user/change_request_actions.py
业务角色：变更申请处理动作
函数:
  1. approve_change_request(cr, approver)
     功能：批准变更申请
     动作：
       - 更新 User.username 或 User.password
       - 更新申请状态为 approved
       - 记录 approver 和 approved_at
       - 标记关联消息已读
  
  2. reject_change_request(cr, approver)
     功能：拒绝变更申请
     动作：
       - 更新申请状态为 rejected
       - 记录 approver 和 approved_at
       - 标记关联消息已读
```

### user/user_center_mail.py
```
位置：/d/AITestProduct/user/user_center_mail.py
业务角色：用户中心邮件服务
功能:
  - 敏感变更通知邮件
  - 审核通知邮件
  - 使用 Django Email Backend
发送场景：
  - 用户提交变更申请 -> 通知管理员
  - 管理员审批 -> 通知申请人
```

---

*由于文档长度限制，剩余模块的详细文件说明请参考主文档 ALL_FILES.md*

*文档持续更新中...*
