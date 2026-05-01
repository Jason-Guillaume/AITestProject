# UI Automation Implementation Guide - POM Architecture with Element Library

## 架构概述

AITesta 的 UI 自动化模块基于 **Page Object Model (POM)** 架构设计，采用三层结构：

```
UIModule (模块层)
    └── UIPage (页面层)
            └── UIPageElement (元素层)
```

这种架构将页面元素的定位信息与测试逻辑分离，提高了代码的可维护性和可复用性。

---

## 数据模型

### 1. UIModule - 模块管理
用于组织和分类页面，支持树形结构（父子模块）。

**字段：**
- `project`: 所属项目（外键）
- `name`: 模块名称
- `parent`: 父模块（自关联外键，可为空）
- `description`: 模块描述
- `order`: 排序序号

**示例：**
```
电商系统
  ├── 用户模块
  │   ├── 登录注册
  │   └── 个人中心
  └── 商品模块
      ├── 商品列表
      └── 商品详情
```

### 2. UIPage - 页面管理
表示一个具体的页面，包含该页面的所有元素。

**字段：**
- `module`: 所属模块（外键）
- `name`: 页面名称
- `url`: 页面URL
- `description`: 页面描述
- `order`: 排序序号

**示例：**
```python
{
    "name": "登录页面",
    "url": "https://example.com/login",
    "module": 1,
    "description": "用户登录页面"
}
```

### 3. UIPageElement - 页面元素
存储页面元素的定位信息，这是 POM 架构的核心。

**字段：**
- `page`: 所属页面（外键）
- `name`: 元素名称（用于代码中引用）
- `locator_type`: 定位方式（id, xpath, css, name, class, tag, link_text, partial_link_text）
- `locator_value`: 定位表达式
- `description`: 元素描述
- `order`: 排序序号

**示例：**
```python
{
    "name": "username_input",
    "page": 1,
    "locator_type": "id",
    "locator_value": "username",
    "description": "用户名输入框"
}
```

### 4. UITestCase - 测试用例
基于模块的测试用例定义。

**字段：**
- `module`: 所属模块（外键）
- `name`: 用例名称
- `preconditions`: 前置条件
- `expected_result`: 预期结果
- `priority`: 优先级
- `order`: 排序序号

### 5. UIActionStep - 操作步骤
测试用例的具体执行步骤。

**字段：**
- `test_case`: 所属测试用例（外键）
- `sequence`: 执行顺序
- `action_type`: 操作类型（click, input, assert, hover, select, wait, sleep, navigate, switch_window, switch_frame, scroll, execute_js）
- `element`: 关联元素（外键，可为空）
- `test_data`: 测试数据
- `description`: 步骤描述

---

## API 接口

### 模块管理
- `GET /api/ai/ui-modules/` - 获取模块列表
- `GET /api/ai/ui-modules/tree/` - 获取模块树形结构
- `POST /api/ai/ui-modules/` - 创建模块
- `PUT /api/ai/ui-modules/{id}/` - 更新模块
- `DELETE /api/ai/ui-modules/{id}/` - 删除模块

### 页面管理
- `GET /api/ai/ui-pages/?module_id={id}` - 获取页面列表
- `POST /api/ai/ui-pages/` - 创建页面
- `PUT /api/ai/ui-pages/{id}/` - 更新页面
- `DELETE /api/ai/ui-pages/{id}/` - 删除页面

### 元素管理
- `GET /api/ai/ui-elements/?page_id={id}` - 获取元素列表
- `GET /api/ai/ui-elements/by_name/?name={name}&page_id={id}` - 根据名称查找元素
- `POST /api/ai/ui-elements/` - 创建元素
- `PUT /api/ai/ui-elements/{id}/` - 更新元素
- `DELETE /api/ai/ui-elements/{id}/` - 删除元素

### 测试用例管理
- `GET /api/ai/ui-test-cases/?module_id={id}` - 获取测试用例列表
- `POST /api/ai/ui-test-cases/` - 创建测试用例
- `PUT /api/ai/ui-test-cases/{id}/` - 更新测试用例
- `DELETE /api/ai/ui-test-cases/{id}/` - 删除测试用例

### 操作步骤管理
- `GET /api/ai/ui-action-steps/?test_case_id={id}` - 获取操作步骤列表
- `POST /api/ai/ui-action-steps/` - 创建操作步骤
- `PUT /api/ai/ui-action-steps/{id}/` - 更新操作步骤
- `DELETE /api/ai/ui-action-steps/{id}/` - 删除操作步骤

---

## AI 脚本生成器集成

### 原有方式（硬编码）
```python
# 旧方式：直接在代码中硬编码定位器
element = driver.find_element(By.ID, "username")
element.send_keys("test_user")
```

**问题：**
- 元素定位信息分散在代码中
- 页面变化时需要修改多处代码
- 难以复用和维护

### 新方式（元素库查找）

#### 1. AI 生成脚本时查询元素库

当用户在 UI 自动化生成器中输入测试场景时，AI 应该：

1. **解析场景描述**，识别需要操作的元素（如"点击登录按钮"）
2. **调用元素查找 API**，从元素库中获取定位信息
3. **生成使用元素库的代码**

**示例流程：**

用户输入：
```
1. 打开登录页面
2. 输入用户名 "admin"
3. 输入密码 "123456"
4. 点击登录按钮
```

AI 处理逻辑：
```python
# 伪代码
for step in user_steps:
    if "输入用户名" in step:
        # 查询元素库
        element = api.get_element_by_name("username_input", page_id=login_page_id)
        # 生成代码
        code += f"driver.find_element(By.{element.locator_type.upper()}, '{element.locator_value}').send_keys('admin')\n"
```

#### 2. 生成的代码示例

**使用元素库的代码：**
```python
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class LoginTestCase(unittest.TestCase):
    """登录功能测试用例 - 基于元素库"""
    
    # 元素库定义（从 API 获取）
    ELEMENTS = {
        "username_input": ("id", "username"),
        "password_input": ("id", "password"),
        "login_button": ("xpath", "//button[@type='submit']"),
        "error_message": ("css", ".error-message")
    }
    
    @classmethod
    def setUpClass(cls):
        cls.driver = webdriver.Chrome()
        cls.driver.maximize_window()
        cls.wait = WebDriverWait(cls.driver, 10)
    
    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
    
    def find_element(self, element_name):
        """从元素库中查找元素"""
        locator_type, locator_value = self.ELEMENTS[element_name]
        by_type = getattr(By, locator_type.upper())
        return self.wait.until(
            EC.presence_of_element_located((by_type, locator_value))
        )
    
    def test_login_success(self):
        """测试成功登录"""
        self.driver.get("https://example.com/login")
        
        # 使用元素库中的定位信息
        self.find_element("username_input").send_keys("admin")
        self.find_element("password_input").send_keys("123456")
        self.find_element("login_button").click()
        
        # 验证登录成功
        self.assertIn("dashboard", self.driver.current_url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

#### 3. AI Prompt 指导

在 AI 脚本生成时，应该包含以下指导：

```
你是一个 UI 自动化测试脚本生成专家。在生成脚本时，请遵循以下规则：

1. **优先使用元素库**：
   - 在生成定位器之前，先调用 `/api/ai/ui-elements/by_name/` 接口查询元素库
   - 如果元素库中存在该元素，使用元素库中的定位信息
   - 如果元素库中不存在，再生成新的定位器，并建议用户将其添加到元素库

2. **代码结构**：
   - 在测试类中定义 `ELEMENTS` 字典，存储从元素库获取的定位信息
   - 实现 `find_element(element_name)` 方法，统一处理元素查找
   - 测试方法中使用 `self.find_element("element_name")` 而不是直接使用定位器

3. **元素命名规范**：
   - 使用小写字母和下划线：`username_input`, `login_button`
   - 命名应该描述元素的功能，而不是位置
   - 保持命名的一致性

4. **注释说明**：
   - 在生成的代码中注释说明哪些元素来自元素库
   - 如果某个元素不在元素库中，添加 TODO 注释提醒用户添加
```

---

## 前端使用指南

### 元素库管理页面

访问路径：`智能体中心` → `元素库管理`

**功能：**
1. **左侧树形结构**：展示模块和页面的层级关系
2. **右侧元素表格**：显示选中页面的所有元素
3. **CRUD 操作**：支持创建、编辑、删除模块、页面和元素

**操作流程：**
1. 创建模块（如"用户模块"）
2. 在模块下创建页面（如"登录页面"）
3. 在页面下添加元素（如"用户名输入框"）
4. 为每个元素配置定位方式和定位表达式

### 在 AI 脚本生成器中使用

1. 用户在 `AI Web UI Automation` 页面输入测试场景
2. AI 自动查询元素库，匹配场景中提到的元素
3. 生成的代码使用元素库中的定位信息
4. 如果元素不存在，AI 会提示用户先在元素库中添加

---

## 最佳实践

### 1. 元素命名规范
- **输入框**：`{field}_input` (如 `username_input`)
- **按钮**：`{action}_button` (如 `login_button`, `submit_button`)
- **链接**：`{target}_link` (如 `forgot_password_link`)
- **文本**：`{content}_text` (如 `welcome_text`, `error_message`)
- **下拉框**：`{field}_select` (如 `country_select`)
- **复选框**：`{field}_checkbox` (如 `remember_me_checkbox`)

### 2. 定位器优先级
1. **ID** - 最稳定，优先使用
2. **Name** - 次优选择
3. **CSS Selector** - 灵活且性能好
4. **XPath** - 功能强大但维护成本高
5. **Class/Tag** - 不够唯一，谨慎使用

### 3. 元素库维护
- 定期检查元素定位是否失效
- 页面改版时及时更新元素库
- 为元素添加清晰的描述信息
- 使用有意义的元素名称

### 4. 测试用例组织
- 按模块组织测试用例
- 一个测试用例对应一个业务场景
- 操作步骤保持原子性和可复用性

---

## 数据库迁移

在部署新功能前，需要运行数据库迁移：

```bash
# 1. 将模型添加到 assistant/models.py
# 2. 生成迁移文件
python manage.py makemigrations assistant

# 3. 执行迁移
python manage.py migrate

# 4. （可选）创建超级用户以访问 Django Admin
python manage.py createsuperuser
```

---

## 文件清单

### 后端文件
- `assistant/ui_element_models.py` - POM 数据模型定义
- `assistant/ui_element_serializers.py` - DRF 序列化器
- `assistant/ui_element_views.py` - ViewSet CRUD API
- `assistant/ai_urls.py` - URL 路由配置（已更新）
- `assistant/ui_automation_views.py` - AI 脚本生成视图

### 前端文件
- `frontend/src/views/AgentHub.vue` - 智能体中心（已更新）
- `frontend/src/views/ElementLibrary.vue` - 元素库管理页面
- `frontend/src/api/elementLibrary.js` - 元素库 API 封装
- `frontend/src/router/index.js` - 路由配置（已更新）
- `frontend/src/layouts/MainLayout.vue` - 主布局（已更新面包屑）

---

## 故障排查

### 问题 1：元素查找失败
**原因：** 元素库中的定位器已过期
**解决：** 在元素库管理页面更新定位表达式

### 问题 2：AI 生成的代码不使用元素库
**原因：** AI Prompt 未正确配置
**解决：** 检查 `assistant/ui_automation_views.py` 中的 Prompt 是否包含元素库查询逻辑

### 问题 3：树形结构加载失败
**原因：** 项目 ID 未正确传递
**解决：** 确保 `localStorage` 中存在 `current_project_id`

### 问题 4：导入错误
**原因：** 模型未在 `assistant/models.py` 中导入
**解决：** 在 `assistant/models.py` 中添加：
```python
from assistant.ui_element_models import (
    UIModule, UIPage, UIPageElement, UITestCase, UIActionStep
)
```

---

## 未来扩展

1. **元素自动发现**：通过爬虫自动识别页面元素并添加到元素库
2. **元素健康检查**：定期验证元素定位是否有效
3. **元素版本管理**：记录元素定位的历史变更
4. **智能推荐**：AI 根据页面结构推荐最佳定位方式
5. **可视化录制**：通过浏览器插件录制操作并自动生成元素库
6. **元素截图**：为每个元素保存截图，便于识别
7. **批量导入**：支持从 Excel/CSV 批量导入元素

---

## 总结

通过引入元素库管理，AITesta 的 UI 自动化模块实现了：

✅ **关注点分离**：元素定位与测试逻辑分离  
✅ **提高可维护性**：元素变更只需修改一处  
✅ **增强可复用性**：多个测试用例共享元素库  
✅ **降低学习成本**：统一的元素管理方式  
✅ **支持团队协作**：集中管理的元素库便于团队共享  
✅ **符合 POM 架构**：严格遵循页面对象模型最佳实践  

这是迈向企业级 UI 自动化测试平台的重要一步！
