# UI自动化测试脚本生成功能实现文档

## 概述
本文档描述了UI自动化测试脚本生成功能的实现，包括后端Mock API和前端Vue组件。

## 后端实现

### 1. API视图文件
**文件路径**: `assistant/ui_automation_views.py`

**功能**: 
- 接收前端发送的URL和测试步骤描述
- 返回模拟生成的Python Unittest测试代码
- 严格遵循7层POM架构的Testcase层

**端点**: `POST /api/ai/ui-automation/generate/`

**请求参数**:
```json
{
  "url": "https://example.com",
  "steps": "用户操作步骤描述"
}
```

**响应格式**:
```json
{
  "success": true,
  "code": "生成的Python代码字符串",
  "message": "UI自动化测试脚本生成成功（Mock）"
}
```

**特性**:
- 使用TokenAuthentication认证
- 需要IsAuthenticated权限
- 输入验证（URL和steps必填）
- 生成的代码包含：
  - Selenium WebDriver初始化
  - 页面对象等待机制
  - 基本断言
  - 性能测试用例
  - 符合Unittest框架规范

### 2. URL路由配置
**文件路径**: `assistant/ai_urls.py`

**修改内容**:
- 导入 `UiAutomationGenerateAPIView`
- 添加路由: `path("ui-automation/generate/", UiAutomationGenerateAPIView.as_view())`

**完整URL**: `/api/ai/ui-automation/generate/`

## 前端实现

### 1. API服务函数
**文件路径**: `frontend/src/api/assistant.js`

**新增函数**:
```javascript
export const generateUiAutomationScriptApi = (data) =>
  request.post("/ai/ui-automation/generate/", data);
```

### 2. Vue组件
**文件路径**: `frontend/src/views/UiAutomationGenerator.vue`

**组件特性**:
- 使用Vue 3 Composition API
- 双栏布局（左侧输入，右侧输出）
- 深色主题，赛博朋克风格，蓝色调

**左侧输入区域**:
- 目标URL输入框
- 场景步骤描述文本域（支持多行）
- "生成脚本"按钮（带加载状态）
- 输入验证（URL和步骤必填才能生成）

**右侧输出区域**:
- 空状态提示
- 加载状态动画
- 错误信息展示
- 代码展示区（`<pre>`标签，等宽字体）
- "复制代码"按钮（右上角）

**交互逻辑**:
1. 用户填写URL和步骤描述
2. 点击"生成脚本"按钮
3. 按钮状态变为"生成中..."
4. 发送POST请求到后端API
5. 接收响应后在右侧展示生成的代码
6. 用户可点击"复制代码"按钮复制到剪贴板

**样式特点**:
- 深色背景 (#0f172a, #1e293b)
- 蓝色主题色 (#60a5fa, #3b82f6)
- 渐变效果和发光阴影
- 自定义滚动条样式
- 响应式布局

## 生成的代码示例

生成的Python代码包含以下结构：

```python
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class TestUIAutomation(unittest.TestCase):
    """UI自动化测试用例"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化：启动浏览器"""
        cls.driver = webdriver.Chrome()
        cls.driver.maximize_window()
        cls.wait = WebDriverWait(cls.driver, 10)
    
    @classmethod
    def tearDownClass(cls):
        """测试类清理：关闭浏览器"""
        if cls.driver:
            cls.driver.quit()
    
    def setUp(self):
        """每个测试用例执行前：导航到目标页面"""
        self.driver.get("目标URL")
    
    def test_user_scenario(self):
        """测试场景"""
        # 包含等待、断言、元素查找等逻辑
        pass
    
    def test_page_load_performance(self):
        """测试页面加载性能"""
        # 性能测试逻辑
        pass

if __name__ == "__main__":
    unittest.main(verbosity=2)
```

## 技术栈

**后端**:
- Django REST Framework
- TokenAuthentication
- Python 3.x

**前端**:
- Vue 3 (Composition API)
- Element Plus UI组件库
- Axios (通过request封装)
- SCSS样式

## 使用流程

1. **路由配置**: 在前端路由中添加该组件的路由
2. **导航**: 用户点击"创建AI场景"进入该页面
3. **输入**: 填写目标URL和测试步骤
4. **生成**: 点击生成按钮，等待AI生成
5. **查看**: 在右侧查看生成的代码
6. **复制**: 点击复制按钮将代码复制到剪贴板

## 注意事项

1. **Mock实现**: 当前为Mock版本，未集成真实LLM API
2. **认证要求**: 需要用户登录并提供有效Token
3. **代码规范**: 生成的代码严格遵循Unittest框架和POM架构
4. **无Markdown**: 返回的代码是纯Python字符串，不包含```python```标记
5. **错误处理**: 包含完整的错误处理和用户提示

## 后续扩展

1. 集成真实的LLM API（如OpenAI、智谱AI等）
2. 支持更多测试框架（Pytest、Robot Framework等）
3. 支持更多浏览器配置
4. 添加代码高亮显示
5. 支持代码编辑和调试
6. 添加测试用例模板选择
7. 支持导出为文件

## 文件清单

- `assistant/ui_automation_views.py` - 后端API视图
- `assistant/ai_urls.py` - URL路由配置（已修改）
- `frontend/src/api/assistant.js` - API服务函数（已修改）
- `frontend/src/views/UiAutomationGenerator.vue` - 前端Vue组件
- `UI_AUTOMATION_IMPLEMENTATION.md` - 本文档
