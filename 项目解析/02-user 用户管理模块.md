# user 用户管理模块

## 模块概述
负责用户账户、权限、组织管理、AI 配额策略、消息通知等核心用户功能。

## 文件列表

### __init__.py
- **作用**: Python 包初始化

### admin.py
- **作用**: Django Admin 后台配置
- **业务功能**: 配置后台管理界面中显示的用户相关模型

### apps.py
- **作用**: 应用配置
- **业务功能**: 定义 UserConfig，设置默认应用类

### models.py
- **作用**: 数据模型定义
- **业务功能**:
  - `User`: 系统用户模型，继承 Django AbstractUser
  - `UserChangeRequest`: 用户敏感信息变更申请（用户名/密码）
  - `SystemMessage`: 站内系统消息
  - `AIModelConfig`: AI 模型配置（平台级唯一）
  - `Organization`: 组织管理
  - `AiQuotaPolicy`: AI 配额策略（项目/组织/用户维度）
  - `SystemMessageSetting`: 消息设置（站内/邮件/短信/日报）

### permissions.py
- **作用**: 权限配置
- **业务功能**: 定义自定义权限类，控制 API 访问权限

### signals.py
- **作用**: Django 信号处理器
- **业务功能**: 监听用户创建、更新等事件，触发相应业务逻辑

### tests.py
- **作用**: 单元测试入口

### urls.py
- **作用**: 用户模块路由
- **业务功能**: 定义用户相关 API 路径

### user_center_mail.py
- **作用**: 用户中心邮件服务
- **业务功能**:
  - 敏感变更通知邮件
  - 审核通知邮件
  - 使用 Django Email Backend 发送

### approval_urls.py
- **作用**: 审批相关路由
- **业务功能**: 用户变更申请审批接口

### sys_urls.py
- **作用**: 系统管理路由
- **业务功能**: 系统管理员相关接口（组织、角色、用户管理）

### sys_views.py
- **作用**: 系统管理视图
- **业务功能**: 实现系统管理 API 逻辑

### views.py
- **作用**: 用户中心视图
- **业务功能**:
  - 用户注册、登录、登出
  - 用户信息 CRUD
  - 头像上传
  - 密码修改
  - 验证码生成

### captcha_image.py
- **作用**: 验证码图片生成
- **业务功能**: 生成图形验证码，防止暴力破解

### change_request_actions.py
- **作用**: 变更申请处理动作
- **业务功能**: 处理用户名/密码变更申请的审批逻辑

### serialize.py
- **作用**: 序列化器定义
- **业务功能**: 用户数据序列化/反序列化，支持 API 数据交换

---
