# AI 自动化测试平台 - 编码规范

## 目录

1. [Python 编码规范](#python-编码规范)
2. [JavaScript/Vue 编码规范](#javascriptvue-编码规范)
3. [数据库设计规范](#数据库设计规范)
4. [API 设计规范](#api-设计规范)
5. [Git 提交规范](#git-提交规范)

---

## Python 编码规范

### 1. 代码风格

**遵循 PEP 8 规范**，使用 `black` 和 `isort` 自动格式化。

#### 1.1 命名规范

```python
# 类名：大驼峰命名法
class TestCaseService:
    pass

# 函数名/变量名：小写下划线命名法
def get_testcase_by_id(testcase_id: int):
    user_name = "test"
    return None

# 常量：全大写下划线命名法
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30

# 私有方法/变量：前缀单下划线
class MyClass:
    def _private_method(self):
        pass
    
    def __init__(self):
        self._private_var = None
```

#### 1.2 类型注解

**强制使用类型注解**，提高代码可读性和 IDE 支持。

```python
from typing import List, Dict, Optional, Union

def get_testcases(
    project_id: int,
    filters: Optional[Dict[str, str]] = None
) -> List[Dict[str, any]]:
    """
    获取测试用例列表
    
    Args:
        project_id: 项目 ID
        filters: 过滤条件
    
    Returns:
        测试用例列表
    """
    pass

# 类型别名
UserId = int
TestCaseData = Dict[str, any]

def create_testcase(user_id: UserId, data: TestCaseData) -> bool:
    pass
```

#### 1.3 文档字符串

**使用 Google 风格的 docstring**。

```python
def batch_create_testcases(
    testcases_data: List[Dict],
    user: User
) -> Dict[str, any]:
    """批量创建测试用例
    
    Args:
        testcases_data: 测试用例数据列表
        user: 当前用户对象
    
    Returns:
        包含创建结果的字典，格式如下:
        {
            'success_count': 10,
            'error_count': 2,
            'created_cases': [...],
            'errors': [...]
        }
    
    Raises:
        ValidationException: 数据验证失败
        PermissionDeniedException: 权限不足
    
    Example:
        >>> service = TestCaseService()
        >>> result = service.batch_create_testcases(data, user)
        >>> print(result['success_count'])
        10
    """
    pass
```

#### 1.4 异常处理

```python
# 明确捕获具体异常，避免使用裸 except
try:
    result = some_operation()
except ValueError as e:
    logger.error(f"值错误: {e}")
    raise ValidationException(f"数据验证失败: {e}")
except KeyError as e:
    logger.error(f"键不存在: {e}")
    raise ResourceNotFoundException(f"资源不存在: {e}")

# 使用自定义异常
from common.exceptions import BusinessException

class TestCaseNotFoundException(BusinessException):
    """测试用例不存在异常"""
    default_detail = "测试用例不存在"
    default_code = "testcase_not_found"
```

#### 1.5 日志记录

```python
import logging

logger = logging.getLogger(__name__)

# 使用合适的日志级别
logger.debug("调试信息：变量值 = %s", variable)
logger.info("用户 %s 创建了测试用例 %s", user.username, testcase.id)
logger.warning("测试用例 %s 执行超时", testcase.id)
logger.error("创建测试用例失败: %s", str(e))
logger.exception("未处理的异常")  # 自动记录堆栈信息

# 避免字符串拼接，使用占位符
# 错误示例
logger.info("用户 " + user.username + " 登录")

# 正确示例
logger.info("用户 %s 登录", user.username)
```

### 2. Django 最佳实践

#### 2.1 Model 设计

```python
from django.db import models
from common.models import BaseModel

class TestCase(BaseModel):
    """测试用例模型
    
    Attributes:
        case_name: 用例名称
        test_type: 测试类型
        project: 所属项目
    """
    
    case_name = models.CharField(
        max_length=255,
        verbose_name="用例名称",
        help_text="测试用例的名称"
    )
    
    test_type = models.CharField(
        max_length=32,
        choices=[
            ('functional', '功能测试'),
            ('api', 'API测试'),
        ],
        default='functional',
        db_index=True,  # 高频查询字段添加索引
        verbose_name="测试类型"
    )
    
    project = models.ForeignKey(
        'project.TestProject',
        on_delete=models.CASCADE,
        related_name='testcases',
        verbose_name="所属项目"
    )
    
    class Meta:
        db_table = "test_case"
        verbose_name = "测试用例"
        verbose_name_plural = verbose_name
        ordering = ['-create_time']
        indexes = [
            models.Index(fields=['project', 'is_deleted']),
            models.Index(fields=['test_type', 'create_time']),
        ]
    
    def __str__(self):
        return self.case_name
    
    def clean(self):
        """模型验证"""
        if not self.case_name:
            raise ValidationError("用例名称不能为空")
```

#### 2.2 QuerySet 优化

```python
# 使用 select_related 优化一对一/外键查询
testcases = TestCase.objects.select_related(
    'creator',
    'module',
    'project'
).filter(project_id=1)

# 使用 prefetch_related 优化多对多/反向外键查询
testcases = TestCase.objects.prefetch_related(
    'steps',
    'tags'
).filter(project_id=1)

# 使用 only/defer 只查询需要的字段
testcases = TestCase.objects.only(
    'id',
    'case_name',
    'test_type'
).filter(project_id=1)

# 使用 values/values_list 返回字典/元组
testcase_names = TestCase.objects.filter(
    project_id=1
).values_list('case_name', flat=True)

# 使用 exists() 检查是否存在
has_testcases = TestCase.objects.filter(project_id=1).exists()

# 使用 count() 统计数量
testcase_count = TestCase.objects.filter(project_id=1).count()
```

#### 2.3 事务管理

```python
from django.db import transaction

# 使用装饰器
@transaction.atomic
def create_testcase_with_steps(testcase_data, steps_data):
    testcase = TestCase.objects.create(**testcase_data)
    for step_data in steps_data:
        TestCaseStep.objects.create(testcase=testcase, **step_data)
    return testcase

# 使用上下文管理器
def update_testcase(testcase_id, data):
    with transaction.atomic():
        testcase = TestCase.objects.select_for_update().get(id=testcase_id)
        for key, value in data.items():
            setattr(testcase, key, value)
        testcase.save()
        return testcase

# 使用 savepoint
def complex_operation():
    with transaction.atomic():
        # 操作 1
        create_something()
        
        # 创建保存点
        sid = transaction.savepoint()
        
        try:
            # 操作 2（可能失败）
            risky_operation()
            transaction.savepoint_commit(sid)
        except Exception:
            # 回滚到保存点
            transaction.savepoint_rollback(sid)
```

---

## JavaScript/Vue 编码规范

### 1. 代码风格

**遵循 ESLint + Prettier 规范**。

#### 1.1 命名规范

```javascript
// 变量/函数：小驼峰命名法
const userName = 'test'
function getUserInfo() {}

// 常量：全大写下划线命名法
const MAX_RETRY_COUNT = 3
const API_BASE_URL = 'http://api.example.com'

// 类/组件：大驼峰命名法
class UserService {}
// Vue 组件文件名也使用大驼峰
// TestCaseList.vue

// 私有变量/方法：前缀下划线
class MyClass {
  _privateMethod() {}
  
  constructor() {
    this._privateVar = null
  }
}
```

#### 1.2 Vue 组件规范

```vue
<!-- 组件名使用多个单词，避免与 HTML 元素冲突 -->
<!-- TestCaseList.vue -->
<template>
  <div class="test-case-list">
    <!-- 使用 v-for 时必须添加 key -->
    <div
      v-for="item in list"
      :key="item.id"
      class="test-case-item"
    >
      {{ item.name }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTestcaseStore } from '@/stores/testcase'

// Props 定义
const props = defineProps({
  projectId: {
    type: Number,
    required: true
  },
  showActions: {
    type: Boolean,
    default: true
  }
})

// Emits 定义
const emit = defineEmits(['update', 'delete'])

// 响应式数据
const list = ref([])
const loading = ref(false)

// 计算属性
const filteredList = computed(() => {
  return list.value.filter(item => !item.isDeleted)
})

// 方法
const fetchList = async () => {
  loading.value = true
  try {
    const store = useTestcaseStore()
    await store.fetchTestcases({ project_id: props.projectId })
    list.value = store.testcases
  } finally {
    loading.value = false
  }
}

// 生命周期
onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.test-case-list {
  padding: 20px;
}

.test-case-item {
  margin-bottom: 10px;
}
</style>
```

#### 1.3 组合式函数

```javascript
// composables/useTestcase.js
import { ref } from 'vue'
import { testcaseApi } from '@/api/testcase'
import { ElMessage } from 'element-plus'

/**
 * 测试用例相关的组合式函数
 * @param {number} projectId - 项目 ID
 * @returns {Object} 返回测试用例相关的状态和方法
 */
export function useTestcase(projectId) {
  const testcases = ref([])
  const loading = ref(false)
  
  /**
   * 获取测试用例列表
   */
  const fetchTestcases = async () => {
    loading.value = true
    try {
      const data = await testcaseApi.getList({ project_id: projectId })
      testcases.value = data
    } catch (error) {
      ElMessage.error('获取测试用例失败')
      throw error
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 创建测试用例
   * @param {Object} data - 测试用例数据
   */
  const createTestcase = async (data) => {
    try {
      const newTestcase = await testcaseApi.create(data)
      testcases.value.unshift(newTestcase)
      ElMessage.success('创建成功')
      return newTestcase
    } catch (error) {
      ElMessage.error('创建失败')
      throw error
    }
  }
  
  return {
    testcases,
    loading,
    fetchTestcases,
    createTestcase
  }
}
```

#### 1.4 API 调用

```javascript
// api/testcase.js
import request from './base'

/**
 * 测试用例相关 API
 */
export const testcaseApi = {
  /**
   * 获取测试用例列表
   * @param {Object} params - 查询参数
   * @param {number} params.project_id - 项目 ID
   * @param {string} [params.test_type] - 测试类型
   * @returns {Promise<Array>} 测试用例列表
   */
  getList(params) {
    return request.get('/api/testcase/', { params })
  },
  
  /**
   * 获取测试用例详情
   * @param {number} id - 测试用例 ID
   * @returns {Promise<Object>} 测试用例详情
   */
  getDetail(id) {
    return request.get(`/api/testcase/${id}/`)
  },
  
  /**
   * 创建测试用例
   * @param {Object} data - 测试用例数据
   * @returns {Promise<Object>} 创建的测试用例
   */
  create(data) {
    return request.post('/api/testcase/', data)
  }
}
```

---

## 数据库设计规范

### 1. 表命名规范

```sql
-- 表名：小写下划线命名法，使用单数形式
CREATE TABLE test_case (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    case_name VARCHAR(255) NOT NULL,
    create_time DATETIME NOT NULL
);

-- 中间表：使用两个表名组合
CREATE TABLE project_member (
    project_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    PRIMARY KEY (project_id, user_id)
);
```

### 2. 字段规范

```sql
-- 主键：统一使用 id，BIGINT 类型
id BIGINT PRIMARY KEY AUTO_INCREMENT

-- 外键：表名_id
project_id BIGINT NOT NULL
user_id BIGINT NOT NULL

-- 布尔字段：is_ 前缀
is_deleted TINYINT(1) DEFAULT 0
is_active TINYINT(1) DEFAULT 1

-- 时间字段：_time 后缀
create_time DATETIME NOT NULL
update_time DATETIME NOT NULL

-- 状态字段：_status 后缀
project_status TINYINT NOT NULL DEFAULT 1

-- 数量字段：_count 后缀
case_count INT NOT NULL DEFAULT 0
```

### 3. 索引规范

```sql
-- 单列索引
CREATE INDEX idx_project_id ON test_case(project_id);

-- 复合索引（遵循最左前缀原则）
CREATE INDEX idx_project_type ON test_case(project_id, test_type);

-- 唯一索引
CREATE UNIQUE INDEX uk_case_no ON test_case(case_no);

-- 全文索引
CREATE FULLTEXT INDEX ft_case_desc ON test_case(case_desc);
```

---

## API 设计规范

### 1. RESTful API 规范

```
# 资源命名：使用复数形式
GET    /api/testcases/          # 获取列表
GET    /api/testcases/{id}/     # 获取详情
POST   /api/testcases/          # 创建
PUT    /api/testcases/{id}/     # 完整更新
PATCH  /api/testcases/{id}/     # 部分更新
DELETE /api/testcases/{id}/     # 删除

# 自定义操作：使用动词
POST   /api/testcases/batch_create/      # 批量创建
POST   /api/testcases/{id}/execute/      # 执行用例
GET    /api/testcases/{id}/history/      # 获取历史
```

### 2. 请求参数规范

```javascript
// 查询参数：使用下划线命名
GET /api/testcases/?project_id=1&test_type=api&page=1&page_size=20

// 请求体：使用下划线命名
POST /api/testcases/
{
  "case_name": "测试用例1",
  "test_type": "api",
  "project_id": 1,
  "module_id": 10
}
```

### 3. 响应格式规范

```javascript
// 成功响应
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "id": 1,
    "case_name": "测试用例1"
  },
  "timestamp": "2026-04-27T10:00:00Z"
}

// 列表响应
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "results": [...],
    "pagination": {
      "total": 100,
      "page": 1,
      "page_size": 20,
      "total_pages": 5
    }
  },
  "timestamp": "2026-04-27T10:00:00Z"
}

// 错误响应
{
  "code": 400,
  "message": "数据验证失败",
  "data": {
    "errors": {
      "case_name": ["用例名称不能为空"]
    }
  },
  "timestamp": "2026-04-27T10:00:00Z"
}
```

### 4. HTTP 状态码规范

```
200 OK              - 请求成功
201 Created         - 创建成功
204 No Content      - 删除成功
400 Bad Request     - 请求参数错误
401 Unauthorized    - 未认证
403 Forbidden       - 权限不足
404 Not Found       - 资源不存在
500 Internal Error  - 服务器错误
```

---

## Git 提交规范

### 1. 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 2. Type 类型

```
feat:     新功能
fix:      修复 bug
docs:     文档更新
style:    代码格式调整（不影响功能）
refactor: 重构（不是新功能也不是修复 bug）
perf:     性能优化
test:     测试相关
chore:    构建过程或辅助工具的变动
```

### 3. 示例

```bash
# 新功能
git commit -m "feat(testcase): 添加批量创建测试用例功能"

# 修复 bug
git commit -m "fix(execution): 修复测试执行超时问题"

# 重构
git commit -m "refactor(testcase): 重构测试用例 Service 层"

# 文档
git commit -m "docs: 更新 API 文档"

# 详细提交信息
git commit -m "feat(testcase): 添加批量创建测试用例功能

- 实现批量创建 API
- 添加数据验证
- 添加单元测试

Closes #123"
```

---

## 代码审查清单

### Python 代码审查

- [ ] 是否遵循 PEP 8 规范
- [ ] 是否添加了类型注解
- [ ] 是否添加了文档字符串
- [ ] 是否有适当的异常处理
- [ ] 是否有日志记录
- [ ] 是否有单元测试
- [ ] 是否优化了数据库查询
- [ ] 是否有安全漏洞

### Vue 代码审查

- [ ] 组件名是否使用多个单词
- [ ] Props 是否定义了类型
- [ ] v-for 是否添加了 key
- [ ] 是否有内存泄漏（事件监听器未清理）
- [ ] 是否有性能问题（大列表渲染）
- [ ] 样式是否使用了 scoped
- [ ] 是否有 ESLint 错误

---

**文档版本**: v1.0  
**创建时间**: 2026-04-27
