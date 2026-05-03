# WebUI工作台上传功能修复

## 问题诊断
你使用的是 `frontend/src/views/script/WebUIWorkbench.vue` 文件。
原来的"上传"按钮只是装饰性按钮，没有实际文件上传功能。

## 修复内容

### 1. 替换为真正的文件上传组件
使用 el-upload 组件包裹输入框，支持文件选择。

### 2. 添加文件处理逻辑
- handleFileChange: 处理文件选择
- handleFileRemove: 处理文件移除
- uploadedFile: 存储选中的文件

### 3. 更新导入逻辑
添加后端API调用，包含必需字段：
- name, script_type, language, framework, entry_point, file_path

## 使用方法

1. **刷新浏览器** (F5)
2. 点击"导入工程"
3. 填写工程信息
4. **点击"上传"按钮**选择文件
5. 文件名会自动填充到路径框
6. 点击"确认导入"

## 支持的文件
- .py - Python脚本
- .zip - POM工程压缩包

## 验证
- 点击上传按钮打开文件选择
- 选择文件后路径自动填充
- 成功导入工程
