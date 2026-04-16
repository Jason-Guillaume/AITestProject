# AI 自动化测试平台 - 重构实施指南

## 目录

1. [准备工作](#准备工作)
2. [后端重构步骤](#后端重构步骤)
3. [前端重构步骤](#前端重构步骤)
4. [数据库优化](#数据库优化)
5. [测试策略](#测试策略)
6. [部署与回滚](#部署与回滚)

---

## 准备工作

### 1. 环境准备

**开发环境要求**:
- Python 3.11+
- Node.js 18+
- MySQL 8.0+
- Redis 7.0+

**安装开发工具**:
```bash
# Python 代码质量工具
pip install black isort flake8 mypy pytest pytest-cov

# 前端代码质量工具
npm install -g eslint prettier
```

### 2. 代码备份

```bash
# 创建备份分支
git checkout -b backup/before-refactoring
git push origin backup/before-refactoring

# 创建重构分支
git checkout -b refactor/architecture-improvement
```

### 3. 数据库备份

```bash
# 备份 MySQL 数据库
mysqldump -u root -p ai_test_product > backup_$(date +%Y%m%d).sql

# 备份 Redis 数据
redis-cli --rdb backup_redis_$(date +%Y%m%d).rdb
```

---

## 后端重构步骤

### 阶段一：创建基础架构（Week 1）

#### 1.1 创建 Repository 基类

```python
# common/repositories/base_repository.py
from typing import Generic, TypeVar, Optional, List, Dict, Any
from django.db.models import Model, QuerySet
from django.core.cache import cache

T = TypeVar('T', bound=Model)

class BaseRepository(Generic[T]):
    """Repository 基类"""
    
    def __init__(self, model: type[T]):
        self.model = model
        self.cache_prefix = model._meta.db_table
        self.cache_ttl = 300  # 5分钟
    
    def get_by_id(self, obj_id: int) -> Optional[T]:
        """根据 ID 获取对象"""
        cache_key = f"{self.cache_prefix}:{obj_id}"
        obj = cache.get(cache_key)
        
        if obj is None:
            obj = self.model.objects.filter(
                id=obj_id,
                is_deleted=False
            ).first()
            
            if obj:
                cache.set(cache_key, obj, self.cache_ttl)
        
        return obj
    
    def get_all(self, filters: Optional[Dict] = None) -> QuerySet:
        """获取所有对象"""
        qs = self.model.objects.filter(is_deleted=False)
        
        if filters:
            qs = qs.filter(**filters)
        
        return qs
    
    def create(self, data: Dict, **kwargs) -> T:
        """创建对象"""
        obj = self.model.objects.create(**data, **kwargs)
        self._invalidate_cache()
        return obj
    
    def update(self, obj_id: int, data: Dict) -> Optional[T]:
        """更新对象"""
        obj = self.get_by_id(obj_id)
        if not obj:
            return None
        
        for key, value in data.items():
            setattr(obj, key, value)
        obj.save()
        
        self._invalidate_cache(obj_id)
        return obj
    
    def delete(self, obj_id: int, soft: bool = True) -> bool:
        """删除对象（软删除或硬删除）"""
        obj = self.get_by_id(obj_id)
        if not obj:
            return False
        
        if soft:
            obj.is_deleted = True
            obj.save()
        else:
            obj.delete()
        
        self._invalidate_cache(obj_id)
        return True
    
    def _invalidate_cache(self, obj_id: Optional[int] = None):
        """清除缓存"""
        if obj_id:
            cache_key = f"{self.cache_prefix}:{obj_id}"
            cache.delete(cache_key)
        else:
            cache.delete_pattern(f"{self.cache_prefix}:*")
```

#### 1.2 创建 Service 基类

```python
# common/services/base_service.py
from typing import Generic, TypeVar, Optional, Dict, List
from django.db import transaction
from common.repositories.base_repository import BaseRepository

T = TypeVar('T')

class BaseService(Generic[T]):
    """Service 基类"""
    
    def __init__(self, repository: BaseRepository[T]):
        self.repository = repository
    
    def get_by_id(self, obj_id: int) -> Optional[T]:
        """根据 ID 获取对象"""
        return self.repository.get_by_id(obj_id)
    
    def get_all(self, filters: Optional[Dict] = None) -> List[T]:
        """获取所有对象"""
        return list(self.repository.get_all(filters))
    
    @transaction.atomic
    def create(self, data: Dict, user=None) -> T:
        """创建对象"""
        if user:
            data['creator'] = user
        
        obj = self.repository.create(data)
        self._after_create(obj, user)
        return obj
    
    @transaction.atomic
    def update(self, obj_id: int, data: Dict, user=None) -> Optional[T]:
        """更新对象"""
        if user:
            data['updater'] = user
        
        obj = self.repository.update(obj_id, data)
        if obj:
            self._after_update(obj, user)
        return obj
    
    @transaction.atomic
    def delete(self, obj_id: int, user=None) -> bool:
        """删除对象"""
        result = self.repository.delete(obj_id)
        if result:
            self._after_delete(obj_id, user)
        return result
    
    def _after_create(self, obj: T, user=None):
        """创建后的钩子方法"""
        pass
    
    def _after_update(self, obj: T, user=None):
        """更新后的钩子方法"""
        pass
    
    def _after_delete(self, obj_id: int, user=None):
        """删除后的钩子方法"""
        pass
```

#### 1.3 创建统一响应类

```python
# common/response.py
from typing import Any, Optional
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

class ApiResponse:
    """统一 API 响应格式"""
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "操作成功",
        code: int = 200,
        status_code: int = status.HTTP_200_OK
    ) -> Response:
        """成功响应"""
        return Response({
            "code": code,
            "message": message,
            "data": data,
            "timestamp": timezone.now().isoformat()
        }, status=status_code)
    
    @staticmethod
    def error(
        message: str,
        code: int = 400,
        data: Any = None,
        status_code: Optional[int] = None
    ) -> Response:
        """错误响应"""
        if status_code is None:
            status_code = code
        
        return Response({
            "code": code,
            "message": message,
            "data": data,
            "timestamp": timezone.now().isoformat()
        }, status=status_code)
    
    @staticmethod
    def paginated(
        results: list,
        total: int,
        page: int,
        page_size: int,
        message: str = "查询成功"
    ) -> Response:
        """分页响应"""
        return Response({
            "code": 200,
            "message": message,
            "data": {
                "results": results,
                "pagination": {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }
            },
            "timestamp": timezone.now().isoformat()
        })
```

#### 1.4 创建全局异常处理

```python
# common/exceptions.py
from rest_framework.exceptions import APIException
from rest_framework import status

class BusinessException(APIException):
    """业务异常基类"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "业务处理失败"
    default_code = "business_error"

class ResourceNotFoundException(BusinessException):
    """资源不存在异常"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "资源不存在"
    default_code = "resource_not_found"

class PermissionDeniedException(BusinessException):
    """权限不足异常"""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "权限不足"
    default_code = "permission_denied"

class ValidationException(BusinessException):
    """数据验证异常"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "数据验证失败"
    default_code = "validation_error"
```

```python
# common/middleware/exception_middleware.py
import logging
from django.http import JsonResponse
from rest_framework.exceptions import APIException
from rest_framework import status
from common.exceptions import BusinessException

logger = logging.getLogger(__name__)

class GlobalExceptionMiddleware:
    """全局异常处理中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            return self.handle_exception(e, request)
    
    def handle_exception(self, exc, request):
        """处理异常"""
        if isinstance(exc, BusinessException):
            return self._handle_business_exception(exc)
        elif isinstance(exc, APIException):
            return self._handle_api_exception(exc)
        else:
            return self._handle_unknown_exception(exc, request)
    
    def _handle_business_exception(self, exc):
        """处理业务异常"""
        return JsonResponse({
            "code": exc.status_code,
            "message": str(exc.detail),
            "data": None
        }, status=exc.status_code)
    
    def _handle_api_exception(self, exc):
        """处理 DRF 异常"""
        return JsonResponse({
            "code": exc.status_code,
            "message": str(exc.detail),
            "data": None
        }, status=exc.status_code)
    
    def _handle_unknown_exception(self, exc, request):
        """处理未知异常"""
        logger.exception(f"未处理的异常: {exc}")
        return JsonResponse({
            "code": 500,
            "message": "服务器内部错误",
            "data": None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

### 阶段二：重构具体模块（Week 2-5）

#### 2.1 重构 TestCase 模块示例

**Step 1: 创建 Repository**

```python
# testcase/repositories/testcase_repository.py
from typing import Optional, Dict
from django.db.models import QuerySet, Q
from common.repositories.base_repository import BaseRepository
from testcase.models import TestCase

class TestCaseRepository(BaseRepository[TestCase]):
    """测试用例 Repository"""
    
    def __init__(self):
        super().__init__(TestCase)
    
    def get_by_project(
        self,
        project_id: int,
        filters: Optional[Dict] = None
    ) -> QuerySet:
        """按项目查询用例"""
        qs = self.model.objects.filter(
            project_id=project_id,
            is_deleted=False
        ).select_related('creator', 'module', 'project')
        
        if filters:
            if 'test_type' in filters:
                qs = qs.filter(test_type=filters['test_type'])
            
            if 'module_id' in filters:
                qs = qs.filter(module_id=filters['module_id'])
            
            if 'search' in filters:
                search = filters['search']
                qs = qs.filter(
                    Q(case_name__icontains=search) |
                    Q(case_desc__icontains=search)
                )
        
        return qs.order_by('-create_time')
    
    def get_by_module(self, module_id: int) -> QuerySet:
        """按模块查询用例"""
        return self.model.objects.filter(
            module_id=module_id,
            is_deleted=False
        ).select_related('creator')
    
    def count_by_project(self, project_id: int) -> int:
        """统计项目用例数"""
        return self.model.objects.filter(
            project_id=project_id,
            is_deleted=False
        ).count()
```

**Step 2: 创建 Service**

```python
# testcase/services/testcase_service.py
from typing import List, Dict, Optional
from django.db import transaction
from common.services.base_service import BaseService
from common.exceptions import ResourceNotFoundException, ValidationException
from testcase.repositories.testcase_repository import TestCaseRepository
from testcase.repositories.module_repository import ModuleRepository
from testcase.models import TestCase

class TestCaseService(BaseService[TestCase]):
    """测试用例 Service"""
    
    def __init__(self):
        super().__init__(TestCaseRepository())
        self.module_repo = ModuleRepository()
    
    def get_by_project(
        self,
        project_id: int,
        filters: Optional[Dict] = None
    ) -> List[TestCase]:
        """获取项目下的用例"""
        return list(self.repository.get_by_project(project_id, filters))
    
    @transaction.atomic
    def create_testcase(self, data: Dict, user) -> TestCase:
        """创建测试用例"""
        # 验证模块是否存在
        if 'module_id' in data:
            module = self.module_repo.get_by_id(data['module_id'])
            if not module:
                raise ResourceNotFoundException("模块不存在")
        
        # 验证必填字段
        if not data.get('case_name'):
            raise ValidationException("用例名称不能为空")
        
        # 创建用例
        testcase = self.repository.create(data, creator=user)
        
        return testcase
    
    @transaction.atomic
    def batch_create_testcases(
        self,
        testcases_data: List[Dict],
        user
    ) -> Dict:
        """批量创建测试用例"""
        created_cases = []
        errors = []
        
        for idx, data in enumerate(testcases_data):
            try:
                testcase = self.create_testcase(data, user)
                created_cases.append(testcase)
            except Exception as e:
                errors.append({
                    "index": idx,
                    "data": data,
                    "error": str(e)
                })
        
        return {
            "success_count": len(created_cases),
            "error_count": len(errors),
            "created_cases": created_cases,
            "errors": errors
        }
    
    def _after_create(self, obj: TestCase, user=None):
        """创建后的钩子 - 记录审计日志"""
        from common.services.audit import AuditService
        audit_service = AuditService()
        audit_service.record_create(obj, user)
```

**Step 3: 重构 Views**

```python
# testcase/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from common.response import ApiResponse
from common.exceptions import ResourceNotFoundException
from testcase.services.testcase_service import TestCaseService
from testcase.serialize import TestCaseSerializer, BatchTestCaseSerializer

class TestCaseViewSet(viewsets.ViewSet):
    """测试用例视图集"""
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = TestCaseService()
    
    def list(self, request):
        """获取用例列表"""
        project_id = request.query_params.get('project_id')
        if not project_id:
            return ApiResponse.error("project_id 参数必填")
        
        filters = {
            'test_type': request.query_params.get('test_type'),
            'module_id': request.query_params.get('module_id'),
            'search': request.query_params.get('search'),
        }
        filters = {k: v for k, v in filters.items() if v}
        
        testcases = self.service.get_by_project(int(project_id), filters)
        serializer = TestCaseSerializer(testcases, many=True)
        
        return ApiResponse.success(serializer.data)
    
    def retrieve(self, request, pk=None):
        """获取用例详情"""
        testcase = self.service.get_by_id(int(pk))
        if not testcase:
            raise ResourceNotFoundException("测试用例不存在")
        
        serializer = TestCaseSerializer(testcase)
        return ApiResponse.success(serializer.data)
    
    def create(self, request):
        """创建用例"""
        serializer = TestCaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        testcase = self.service.create_testcase(
            serializer.validated_data,
            request.user
        )
        
        return ApiResponse.success(
            TestCaseSerializer(testcase).data,
            message="创建成功",
            status_code=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'])
    def batch_create(self, request):
        """批量创建用例"""
        serializer = BatchTestCaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = self.service.batch_create_testcases(
            serializer.validated_data['testcases'],
            request.user
        )
        
        return ApiResponse.success(result, message="批量创建完成")
    
    def update(self, request, pk=None):
        """更新用例"""
        serializer = TestCaseSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        testcase = self.service.update(
            int(pk),
            serializer.validated_data,
            request.user
        )
        
        if not testcase:
            raise ResourceNotFoundException("测试用例不存在")
        
        return ApiResponse.success(
            TestCaseSerializer(testcase).data,
            message="更新成功"
        )
    
    def destroy(self, request, pk=None):
        """删除用例"""
        result = self.service.delete(int(pk), request.user)
        if not result:
            raise ResourceNotFoundException("测试用例不存在")
        
        return ApiResponse.success(message="删除成功")
```

---

## 前端重构步骤

### 1. 创建通用组合式函数

```javascript
// src/composables/useTable.js
import { ref, reactive } from 'vue'

export function useTable(fetchFn) {
  const loading = ref(false)
  const data = ref([])
  const pagination = reactive({
    page: 1,
    size: 10,
    total: 0
  })
  
  const fetchData = async (params = {}) => {
    loading.value = true
    try {
      const response = await fetchFn({
        page: pagination.page,
        size: pagination.size,
        ...params
      })
      data.value = response.results || response
      pagination.total = response.count || response.length
    } catch (error) {
      console.error('获取数据失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  const handlePageChange = (page) => {
    pagination.page = page
    fetchData()
  }
  
  const handleSizeChange = (size) => {
    pagination.size = size
    pagination.page = 1
    fetchData()
  }
  
  const refresh = () => {
    fetchData()
  }
  
  return {
    loading,
    data,
    pagination,
    fetchData,
    handlePageChange,
    handleSizeChange,
    refresh
  }
}
```

```javascript
// src/composables/useForm.js
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

export function useForm(submitFn) {
  const formRef = ref(null)
  const loading = ref(false)
  const formData = ref({})
  
  const validate = async () => {
    if (!formRef.value) return false
    try {
      await formRef.value.validate()
      return true
    } catch {
      return false
    }
  }
  
  const submit = async () => {
    const valid = await validate()
    if (!valid) {
      ElMessage.warning('请检查表单填写')
      return false
    }
    
    loading.value = true
    try {
      const result = await submitFn(formData.value)
      ElMessage.success('操作成功')
      return result
    } catch (error) {
      ElMessage.error(error.message || '操作失败')
      throw error
    } finally {
      loading.value = false
    }
  }
  
  const reset = () => {
    if (formRef.value) {
      formRef.value.resetFields()
    }
  }
  
  return {
    formRef,
    loading,
    formData,
    validate,
    submit,
    reset
  }
}
```

### 2. 重构 API 层

```javascript
// src/api/testcase.js
import request from './base'

export const testcaseApi = {
  // 获取用例列表
  getList(params) {
    return request.get('/api/testcase/', { params })
  },
  
  // 获取用例详情
  getDetail(id) {
    return request.get(`/api/testcase/${id}/`)
  },
  
  // 创建用例
  create(data) {
    return request.post('/api/testcase/', data)
  },
  
  // 批量创建用例
  batchCreate(data) {
    return request.post('/api/testcase/batch_create/', data)
  },
  
  // 更新用例
  update(id, data) {
    return request.put(`/api/testcase/${id}/`, data)
  },
  
  // 删除用例
  delete(id) {
    return request.delete(`/api/testcase/${id}/`)
  }
}
```

---

## 数据库优化

### 1. 添加索引

```python
# 在 models.py 中添加索引
class TestCase(BaseModel):
    class Meta:
        indexes = [
            models.Index(fields=['project', 'is_deleted']),
            models.Index(fields=['module', 'test_type']),
            models.Index(fields=['create_time']),
        ]
```

```bash
# 生成迁移文件
python manage.py makemigrations

# 执行迁移
python manage.py migrate
```

### 2. 查询优化检查

```python
# 使用 Django Debug Toolbar 检查查询
# settings.py
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

---

## 测试策略

### 1. 单元测试

```python
# testcase/tests/test_services.py
import pytest
from django.contrib.auth import get_user_model
from testcase.services.testcase_service import TestCaseService
from testcase.models import TestCase

User = get_user_model()

@pytest.mark.django_db
class TestTestCaseService:
    def test_create_testcase(self):
        """测试创建用例"""
        service = TestCaseService()
        user = User.objects.create_user(username='test', password='test123')
        
        data = {
            'case_name': '测试用例1',
            'test_type': 'functional',
            'project_id': 1
        }
        
        testcase = service.create_testcase(data, user)
        
        assert testcase.id is not None
        assert testcase.case_name == '测试用例1'
        assert testcase.creator == user
```

### 2. 集成测试

```python
# testcase/tests/test_views.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestTestCaseAPI:
    def test_create_testcase_api(self):
        """测试创建用例 API"""
        client = APIClient()
        user = User.objects.create_user(username='test', password='test123')
        client.force_authenticate(user=user)
        
        data = {
            'case_name': '测试用例1',
            'test_type': 'functional',
            'project_id': 1
        }
        
        response = client.post('/api/testcase/', data, format='json')
        
        assert response.status_code == 201
        assert response.data['code'] == 200
```

---

## 部署与回滚

### 1. 灰度发布

```bash
# 部署到测试环境
git push origin refactor/architecture-improvement

# 运行测试
python manage.py test

# 部署到生产环境（灰度 10%）
# 使用负载均衡器配置流量分配
```

### 2. 回滚方案

```bash
# 如果出现问题，快速回滚
git checkout backup/before-refactoring
git push origin main --force

# 恢复数据库
mysql -u root -p ai_test_product < backup_20260427.sql
```

---

**文档版本**: v1.0  
**创建时间**: 2026-04-27
