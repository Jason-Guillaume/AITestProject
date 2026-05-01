# AI 自动化测试平台 - 架构设计文档

## 一、系统架构概览

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 (Vue 3)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 用例管理 │  │ 执行引擎 │  │ AI 助手  │  │ 数据分析 │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                    API 网关层 (Django)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  认证中间件 │ 权限中间件 │ 限流中间件 │ 日志中间件  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      应用服务层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  User    │  │ Project  │  │ TestCase │  │Execution │   │
│  │ Service  │  │ Service  │  │ Service  │  │ Service  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ Assistant│  │  Defect  │  │ServerLogs│                 │
│  │ Service  │  │ Service  │  │ Service  │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    数据访问层 (Repository)                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ORM 封装 │ 查询优化 │ 缓存策略 │ 事务管理           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      数据存储层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  MySQL   │  │  Redis   │  │  Chroma  │  │Elasticsearch│
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      异步任务层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │  Celery  │  │Channels  │  │APScheduler│                │
│  │  Worker  │  │WebSocket │  │  定时任务 │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈

**后端**:
- Django 4.2 (Web 框架)
- Django REST Framework (API 框架)
- Celery (异步任务队列)
- Django Channels (WebSocket)
- APScheduler (定时任务)

**前端**:
- Vue 3 (前端框架)
- Vite (构建工具)
- Element Plus (UI 组件库)
- Pinia (状态管理)
- Axios (HTTP 客户端)

**数据存储**:
- MySQL 8.0 (主数据库)
- Redis 7.0 (缓存/消息队列)
- Chroma (向量数据库)
- Elasticsearch 8.x (日志检索)

**AI 集成**:
- OpenAI API
- 智谱 AI
- Ollama (本地部署)

## 二、后端分层架构

### 2.1 Controller 层 (Views)

**职责**: 
- 接收 HTTP 请求
- 参数验证
- 调用 Service 层
- 返回响应

**示例**:
```python
# testcase/views.py
class TestCaseViewSet(BaseModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TestCaseSerializer
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = TestCaseService()
    
    @action(detail=False, methods=['post'])
    def batch_create(self, request):
        """批量创建测试用例"""
        serializer = BatchTestCaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = self.service.batch_create_testcases(
            serializer.validated_data,
            request.user
        )
        
        return ApiResponse.success(result)
```

### 2.2 Service 层

**职责**:
- 业务逻辑处理
- 事务管理
- 调用多个 Repository
- 触发事件/消息

**目录结构**:
```
testcase/
├── services/
│   ├── __init__.py
│   ├── testcase_service.py      # 用例业务逻辑
│   ├── module_service.py        # 模块业务逻辑
│   ├── environment_service.py   # 环境业务逻辑
│   └── execution_service.py     # 执行业务逻辑
```

**示例**:
```python
# testcase/services/testcase_service.py
from typing import List, Dict
from django.db import transaction
from testcase.repositories import TestCaseRepository, ModuleRepository
from common.services.audit import AuditService

class TestCaseService:
    def __init__(self):
        self.testcase_repo = TestCaseRepository()
        self.module_repo = ModuleRepository()
        self.audit_service = AuditService()
    
    @transaction.atomic
    def batch_create_testcases(
        self, 
        data: List[Dict], 
        user
    ) -> Dict:
        """批量创建测试用例"""
        created_cases = []
        
        for item in data:
            # 验证模块是否存在
            module = self.module_repo.get_by_id(item['module_id'])
            if not module:
                raise ValidationError(f"模块 {item['module_id']} 不存在")
            
            # 创建用例
            testcase = self.testcase_repo.create(item, creator=user)
            created_cases.append(testcase)
            
            # 记录审计日志
            self.audit_service.record_create(testcase, user)
        
        return {
            'count': len(created_cases),
            'testcases': created_cases
        }
```

### 2.3 Repository 层

**职责**:
- 数据访问封装
- 查询优化
- 缓存管理

**目录结构**:
```
testcase/
├── repositories/
│   ├── __init__.py
│   ├── testcase_repository.py
│   ├── module_repository.py
│   └── environment_repository.py
```

**示例**:
```python
# testcase/repositories/testcase_repository.py
from typing import Optional, List
from django.db.models import QuerySet, Prefetch
from django.core.cache import cache
from testcase.models import TestCase, TestCaseStep

class TestCaseRepository:
    CACHE_PREFIX = 'testcase'
    CACHE_TTL = 300  # 5分钟
    
    def get_by_id(self, testcase_id: int) -> Optional[TestCase]:
        """根据 ID 获取用例（带缓存）"""
        cache_key = f"{self.CACHE_PREFIX}:{testcase_id}"
        testcase = cache.get(cache_key)
        
        if testcase is None:
            testcase = TestCase.objects.select_related(
                'creator', 'module', 'project'
            ).prefetch_related(
                Prefetch('steps', queryset=TestCaseStep.objects.order_by('step_order'))
            ).filter(id=testcase_id, is_deleted=False).first()
            
            if testcase:
                cache.set(cache_key, testcase, self.CACHE_TTL)
        
        return testcase
    
    def get_by_project(
        self, 
        project_id: int, 
        filters: Optional[Dict] = None
    ) -> QuerySet:
        """按项目查询用例"""
        qs = TestCase.objects.filter(
            project_id=project_id,
            is_deleted=False
        ).select_related('creator', 'module')
        
        if filters:
            if 'test_type' in filters:
                qs = qs.filter(test_type=filters['test_type'])
            if 'module_id' in filters:
                qs = qs.filter(module_id=filters['module_id'])
            if 'search' in filters:
                qs = qs.filter(
                    Q(case_name__icontains=filters['search']) |
                    Q(case_desc__icontains=filters['search'])
                )
        
        return qs.order_by('-create_time')
    
    def create(self, data: Dict, creator) -> TestCase:
        """创建测试用例"""
        testcase = TestCase.objects.create(
            **data,
            creator=creator
        )
        
        # 清除相关缓存
        self._invalidate_cache(testcase.project_id)
        
        return testcase
    
    def _invalidate_cache(self, project_id: int):
        """清除项目相关缓存"""
        cache.delete_pattern(f"{self.CACHE_PREFIX}:project:{project_id}:*")
```

### 2.4 Model 层

**职责**:
- 数据模型定义
- 字段验证
- 模型方法

**优化建议**:
```python
# testcase/models.py
from django.db import models
from common.models import BaseModel

class TestCase(BaseModel):
    """测试用例模型"""
    
    case_name = models.CharField(max_length=255, verbose_name="用例名称")
    case_desc = models.TextField(blank=True, default="", verbose_name="用例描述")
    test_type = models.CharField(
        max_length=32,
        choices=[
            ('functional', '功能测试'),
            ('api', 'API测试'),
            ('performance', '性能测试'),
            ('security', '安全测试'),
        ],
        default='functional',
        verbose_name="测试类型"
    )
    
    project = models.ForeignKey(
        'project.TestProject',
        on_delete=models.CASCADE,
        related_name='testcases',
        verbose_name="所属项目"
    )
    
    module = models.ForeignKey(
        'TestModule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testcases',
        verbose_name="所属模块"
    )
    
    class Meta:
        db_table = "test_case"
        verbose_name = "测试用例"
        verbose_name_plural = verbose_name
        ordering = ['-create_time']
        indexes = [
            models.Index(fields=['project', 'is_deleted']),
            models.Index(fields=['module', 'test_type']),
            models.Index(fields=['test_type', 'create_time']),
        ]
    
    def __str__(self):
        return self.case_name
    
    def to_dict(self) -> dict:
        """转换为字典（用于缓存）"""
        return {
            'id': self.id,
            'case_name': self.case_name,
            'test_type': self.test_type,
            'project_id': self.project_id,
            'module_id': self.module_id,
        }
```

## 三、前端架构设计

### 3.1 目录结构

```
frontend/
├── src/
│   ├── api/                    # API 接口层
│   │   ├── base.js            # 基础请求配置
│   │   ├── testcase.js        # 用例相关接口
│   │   ├── project.js         # 项目相关接口
│   │   └── ...
│   ├── assets/                # 静态资源
│   ├── components/            # 公共组件
│   │   ├── common/           # 通用组件
│   │   │   ├── DataTable.vue
│   │   │   ├── SearchForm.vue
│   │   │   └── ...
│   │   └── business/         # 业务组件
│   │       ├── TestCaseForm.vue
│   │       ├── ExecutionPanel.vue
│   │       └── ...
│   ├── composables/          # 组合式函数
│   │   ├── useTable.js
│   │   ├── useForm.js
│   │   └── ...
│   ├── router/               # 路由配置
│   ├── stores/               # 状态管理
│   │   ├── user.js
│   │   ├── testcase.js
│   │   └── ...
│   ├── utils/                # 工具函数
│   │   ├── request.js
│   │   ├── validate.js
│   │   └── ...
│   ├── views/                # 页面视图
│   │   ├── testcase/
│   │   ├── project/
│   │   └── ...
│   ├── App.vue
│   └── main.js
├── public/
├── index.html
├── vite.config.js
└── package.json
```

### 3.2 组件设计原则

**1. 单一职责原则**
- 每个组件只负责一个功能
- 大组件拆分为小组件

**2. 组件复用**
- 提取通用组件
- 使用插槽和作用域插槽

**3. 组件通信**
- Props down, Events up
- 使用 Pinia 管理全局状态

**示例 - 通用表格组件**:
```vue
<!-- components/common/DataTable.vue -->
<template>
  <div class="data-table">
    <el-table
      v-loading="loading"
      :data="data"
      :border="border"
      @selection-change="handleSelectionChange"
    >
      <el-table-column
        v-if="showSelection"
        type="selection"
        width="55"
      />
      
      <el-table-column
        v-for="column in columns"
        :key="column.prop"
        :prop="column.prop"
        :label="column.label"
        :width="column.width"
        :formatter="column.formatter"
      >
        <template v-if="column.slot" #default="scope">
          <slot :name="column.slot" :row="scope.row" />
        </template>
      </el-table-column>
      
      <el-table-column
        v-if="showActions"
        label="操作"
        :width="actionsWidth"
        fixed="right"
      >
        <template #default="scope">
          <slot name="actions" :row="scope.row" />
        </template>
      </el-table-column>
    </el-table>
    
    <el-pagination
      v-if="showPagination"
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="pageSizes"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="handleSizeChange"
      @current-change="handlePageChange"
    />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  columns: {
    type: Array,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  },
  border: {
    type: Boolean,
    default: true
  },
  showSelection: {
    type: Boolean,
    default: false
  },
  showActions: {
    type: Boolean,
    default: true
  },
  actionsWidth: {
    type: String,
    default: '180'
  },
  showPagination: {
    type: Boolean,
    default: true
  },
  total: {
    type: Number,
    default: 0
  },
  page: {
    type: Number,
    default: 1
  },
  size: {
    type: Number,
    default: 10
  },
  pageSizes: {
    type: Array,
    default: () => [10, 20, 50, 100]
  }
})

const emit = defineEmits([
  'selection-change',
  'page-change',
  'size-change'
])

const currentPage = ref(props.page)
const pageSize = ref(props.size)

watch(() => props.page, (val) => {
  currentPage.value = val
})

watch(() => props.size, (val) => {
  pageSize.value = val
})

const handleSelectionChange = (selection) => {
  emit('selection-change', selection)
}

const handlePageChange = (page) => {
  emit('page-change', page)
}

const handleSizeChange = (size) => {
  emit('size-change', size)
}
</script>
```

### 3.3 状态管理

**Pinia Store 设计**:
```javascript
// stores/testcase.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as testcaseApi from '@/api/testcase'

export const useTestcaseStore = defineStore('testcase', () => {
  // State
  const testcases = ref([])
  const currentTestcase = ref(null)
  const loading = ref(false)
  const pagination = ref({
    page: 1,
    size: 10,
    total: 0
  })
  
  // Getters
  const testcaseCount = computed(() => testcases.value.length)
  const hasTestcases = computed(() => testcases.value.length > 0)
  
  // Actions
  async function fetchTestcases(params = {}) {
    loading.value = true
    try {
      const response = await testcaseApi.getTestcases({
        page: pagination.value.page,
        size: pagination.value.size,
        ...params
      })
      testcases.value = response.results
      pagination.value.total = response.count
    } catch (error) {
      console.error('获取测试用例失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  async function createTestcase(data) {
    try {
      const newTestcase = await testcaseApi.createTestcase(data)
      testcases.value.unshift(newTestcase)
      pagination.value.total += 1
      return newTestcase
    } catch (error) {
      console.error('创建测试用例失败:', error)
      throw error
    }
  }
  
  async function updateTestcase(id, data) {
    try {
      const updated = await testcaseApi.updateTestcase(id, data)
      const index = testcases.value.findIndex(tc => tc.id === id)
      if (index !== -1) {
        testcases.value[index] = updated
      }
      return updated
    } catch (error) {
      console.error('更新测试用例失败:', error)
      throw error
    }
  }
  
  async function deleteTestcase(id) {
    try {
      await testcaseApi.deleteTestcase(id)
      testcases.value = testcases.value.filter(tc => tc.id !== id)
      pagination.value.total -= 1
    } catch (error) {
      console.error('删除测试用例失败:', error)
      throw error
    }
  }
  
  function setCurrentTestcase(testcase) {
    currentTestcase.value = testcase
  }
  
  function clearCurrentTestcase() {
    currentTestcase.value = null
  }
  
  function resetPagination() {
    pagination.value = {
      page: 1,
      size: 10,
      total: 0
    }
  }
  
  return {
    // State
    testcases,
    currentTestcase,
    loading,
    pagination,
    // Getters
    testcaseCount,
    hasTestcases,
    // Actions
    fetchTestcases,
    createTestcase,
    updateTestcase,
    deleteTestcase,
    setCurrentTestcase,
    clearCurrentTestcase,
    resetPagination
  }
})
```

## 四、数据库设计优化

### 4.1 索引优化

**原则**:
1. 为高频查询字段添加索引
2. 复合索引遵循最左前缀原则
3. 避免过多索引影响写入性能

**示例**:
```python
class TestCase(BaseModel):
    class Meta:
        indexes = [
            # 单字段索引
            models.Index(fields=['project_id']),
            models.Index(fields=['create_time']),
            
            # 复合索引（常用查询组合）
            models.Index(fields=['project_id', 'is_deleted']),
            models.Index(fields=['module_id', 'test_type']),
            models.Index(fields=['test_type', 'create_time']),
        ]
```

### 4.2 查询优化

**N+1 问题解决**:
```python
# 优化前 - N+1 查询
testcases = TestCase.objects.filter(project_id=1)
for tc in testcases:
    print(tc.creator.username)  # 每次循环都查询数据库

# 优化后 - 使用 select_related
testcases = TestCase.objects.filter(
    project_id=1
).select_related('creator', 'module')

# 优化后 - 使用 prefetch_related（多对多/反向外键）
testcases = TestCase.objects.filter(
    project_id=1
).prefetch_related('steps', 'tags')
```

**分页优化**:
```python
# 使用游标分页（大数据量）
from django.core.paginator import Paginator

def get_testcases_paginated(project_id, page=1, size=20):
    queryset = TestCase.objects.filter(
        project_id=project_id,
        is_deleted=False
    ).select_related('creator').order_by('-id')
    
    paginator = Paginator(queryset, size)
    page_obj = paginator.get_page(page)
    
    return {
        'results': list(page_obj),
        'count': paginator.count,
        'page': page,
        'pages': paginator.num_pages
    }
```

## 五、安全设计

### 5.1 认证与授权

**JWT Token 认证**:
```python
# user/authentication.py
from rest_framework.authentication import TokenAuthentication

class CustomTokenAuthentication(TokenAuthentication):
    """自定义 Token 认证"""
    
    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise AuthenticationFailed('无效的认证令牌')
        
        if not token.user.is_active:
            raise AuthenticationFailed('用户已被禁用')
        
        return (token.user, token)
```

**权限控制**:
```python
# common/permissions.py
from rest_framework.permissions import BasePermission

class IsProjectMember(BasePermission):
    """项目成员权限"""
    
    def has_object_permission(self, request, view, obj):
        # 检查用户是否是项目成员
        return obj.project.members.filter(id=request.user.id).exists()

class IsTestCaseOwner(BasePermission):
    """用例所有者权限"""
    
    def has_object_permission(self, request, view, obj):
        # 只有创建者可以删除
        if request.method == 'DELETE':
            return obj.creator == request.user
        return True
```

### 5.2 数据脱敏

**敏感字段脱敏**:
```python
# common/utils/mask.py
def mask_phone(phone: str) -> str:
    """手机号脱敏"""
    if not phone or len(phone) < 11:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"

def mask_email(email: str) -> str:
    """邮箱脱敏"""
    if not email or '@' not in email:
        return email
    username, domain = email.split('@')
    if len(username) <= 2:
        return f"*@{domain}"
    return f"{username[0]}***{username[-1]}@{domain}"
```

### 5.3 SQL 注入防护

**使用参数化查询**:
```python
# 错误示例 - SQL 注入风险
def get_user_by_name(name):
    query = f"SELECT * FROM user WHERE username = '{name}'"
    # 危险！

# 正确示例 - 使用 ORM
def get_user_by_name(name):
    return User.objects.filter(username=name).first()

# 正确示例 - 原始 SQL 使用参数化
def get_user_by_name(name):
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM user WHERE username = %s",
            [name]
        )
        return cursor.fetchone()
```

---

**文档版本**: v1.0  
**创建时间**: 2026-04-27
