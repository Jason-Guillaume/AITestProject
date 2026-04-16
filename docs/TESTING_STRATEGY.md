# AI 自动化测试平台 - 测试策略

## 目录

1. [测试金字塔](#测试金字塔)
2. [单元测试](#单元测试)
3. [集成测试](#集成测试)
4. [E2E 测试](#e2e-测试)
5. [性能测试](#性能测试)
6. [测试覆盖率](#测试覆盖率)

---

## 测试金字塔

```
        /\
       /  \      E2E 测试 (10%)
      /____\     - 关键业务流程
     /      \    
    /        \   集成测试 (30%)
   /__________\  - API 测试
  /            \ - 模块集成
 /              \
/________________\ 单元测试 (60%)
                   - Service 层
                   - Repository 层
                   - 工具函数
```

**测试目标**:
- 单元测试覆盖率: > 80%
- 集成测试覆盖率: > 60%
- E2E 测试覆盖核心流程: 100%

---

## 单元测试

### 1. 测试框架

**后端**: pytest + pytest-django + pytest-cov

```bash
# 安装依赖
pip install pytest pytest-django pytest-cov pytest-mock factory-boy
```

**配置文件**:
```ini
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = AITestProduct.settings
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
python_functions = test_*
addopts = 
    --cov=.
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
    --reuse-db
```

### 2. Service 层测试

```python
# testcase/tests/test_services.py
import pytest
from django.contrib.auth import get_user_model
from testcase.services.testcase_service import TestCaseService
from testcase.models import TestCase, TestModule
from project.models import TestProject
from common.exceptions import ResourceNotFoundException, ValidationException

User = get_user_model()

@pytest.fixture
def user(db):
    """创建测试用户"""
    return User.objects.create_user(
        username='testuser',
        password='testpass123',
        real_name='测试用户'
    )

@pytest.fixture
def project(db, user):
    """创建测试项目"""
    return TestProject.objects.create(
        project_name='测试项目',
        creator=user
    )

@pytest.fixture
def module(db, project, user):
    """创建测试模块"""
    return TestModule.objects.create(
        module_name='测试模块',
        project=project,
        creator=user
    )

@pytest.fixture
def testcase_service():
    """创建 TestCaseService 实例"""
    return TestCaseService()

@pytest.mark.django_db
class TestTestCaseService:
    """测试用例 Service 测试"""
    
    def test_create_testcase_success(self, testcase_service, project, module, user):
        """测试创建用例 - 成功"""
        data = {
            'case_name': '测试用例1',
            'case_desc': '这是一个测试用例',
            'test_type': 'functional',
            'project_id': project.id,
            'module_id': module.id
        }
        
        testcase = testcase_service.create_testcase(data, user)
        
        assert testcase.id is not None
        assert testcase.case_name == '测试用例1'
        assert testcase.creator == user
        assert testcase.project == project
        assert testcase.module == module
    
    def test_create_testcase_without_name(self, testcase_service, project, user):
        """测试创建用例 - 缺少名称"""
        data = {
            'test_type': 'functional',
            'project_id': project.id
        }
        
        with pytest.raises(ValidationException) as exc_info:
            testcase_service.create_testcase(data, user)
        
        assert "用例名称不能为空" in str(exc_info.value)
    
    def test_create_testcase_with_invalid_module(self, testcase_service, project, user):
        """测试创建用例 - 无效的模块 ID"""
        data = {
            'case_name': '测试用例1',
            'test_type': 'functional',
            'project_id': project.id,
            'module_id': 99999  # 不存在的模块
        }
        
        with pytest.raises(ResourceNotFoundException) as exc_info:
            testcase_service.create_testcase(data, user)
        
        assert "模块不存在" in str(exc_info.value)
    
    def test_get_by_project(self, testcase_service, project, user):
        """测试按项目查询用例"""
        # 创建测试数据
        TestCase.objects.create(
            case_name='用例1',
            test_type='functional',
            project=project,
            creator=user
        )
        TestCase.objects.create(
            case_name='用例2',
            test_type='api',
            project=project,
            creator=user
        )
        
        # 查询所有用例
        testcases = testcase_service.get_by_project(project.id)
        assert len(testcases) == 2
        
        # 按类型过滤
        testcases = testcase_service.get_by_project(
            project.id,
            filters={'test_type': 'api'}
        )
        assert len(testcases) == 1
        assert testcases[0].test_type == 'api'
    
    def test_batch_create_testcases(self, testcase_service, project, user):
        """测试批量创建用例"""
        testcases_data = [
            {
                'case_name': f'用例{i}',
                'test_type': 'functional',
                'project_id': project.id
            }
            for i in range(5)
        ]
        
        result = testcase_service.batch_create_testcases(testcases_data, user)
        
        assert result['success_count'] == 5
        assert result['error_count'] == 0
        assert len(result['created_cases']) == 5
```

### 3. Repository 层测试

```python
# testcase/tests/test_repositories.py
import pytest
from django.contrib.auth import get_user_model
from testcase.repositories.testcase_repository import TestCaseRepository
from testcase.models import TestCase
from project.models import TestProject

User = get_user_model()

@pytest.fixture
def repository():
    """创建 Repository 实例"""
    return TestCaseRepository()

@pytest.mark.django_db
class TestTestCaseRepository:
    """测试用例 Repository 测试"""
    
    def test_get_by_id(self, repository, project, user):
        """测试根据 ID 获取用例"""
        testcase = TestCase.objects.create(
            case_name='测试用例',
            project=project,
            creator=user
        )
        
        result = repository.get_by_id(testcase.id)
        
        assert result is not None
        assert result.id == testcase.id
        assert result.case_name == '测试用例'
    
    def test_get_by_id_not_found(self, repository):
        """测试获取不存在的用例"""
        result = repository.get_by_id(99999)
        assert result is None
    
    def test_get_by_id_with_cache(self, repository, project, user):
        """测试缓存功能"""
        testcase = TestCase.objects.create(
            case_name='测试用例',
            project=project,
            creator=user
        )
        
        # 第一次查询（从数据库）
        result1 = repository.get_by_id(testcase.id)
        
        # 第二次查询（从缓存）
        result2 = repository.get_by_id(testcase.id)
        
        assert result1.id == result2.id
```

### 4. 使用 Factory Boy 创建测试数据

```python
# testcase/tests/factories.py
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from testcase.models import TestCase, TestModule
from project.models import TestProject

User = get_user_model()

class UserFactory(DjangoModelFactory):
    """用户工厂"""
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'user{n}')
    real_name = factory.Faker('name', locale='zh_CN')
    email = factory.Faker('email')

class ProjectFactory(DjangoModelFactory):
    """项目工厂"""
    class Meta:
        model = TestProject
    
    project_name = factory.Sequence(lambda n: f'项目{n}')
    description = factory.Faker('text', locale='zh_CN')
    creator = factory.SubFactory(UserFactory)

class ModuleFactory(DjangoModelFactory):
    """模块工厂"""
    class Meta:
        model = TestModule
    
    module_name = factory.Sequence(lambda n: f'模块{n}')
    project = factory.SubFactory(ProjectFactory)
    creator = factory.SubFactory(UserFactory)

class TestCaseFactory(DjangoModelFactory):
    """测试用例工厂"""
    class Meta:
        model = TestCase
    
    case_name = factory.Sequence(lambda n: f'测试用例{n}')
    case_desc = factory.Faker('text', locale='zh_CN')
    test_type = 'functional'
    project = factory.SubFactory(ProjectFactory)
    module = factory.SubFactory(ModuleFactory)
    creator = factory.SubFactory(UserFactory)

# 使用示例
@pytest.mark.django_db
def test_with_factory():
    # 创建单个对象
    testcase = TestCaseFactory()
    
    # 批量创建
    testcases = TestCaseFactory.create_batch(10)
    
    # 自定义属性
    testcase = TestCaseFactory(case_name='自定义名称')
```

---

## 集成测试

### 1. API 测试

```python
# testcase/tests/test_api.py
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from testcase.tests.factories import UserFactory, ProjectFactory, TestCaseFactory

User = get_user_model()

@pytest.fixture
def api_client():
    """创建 API 客户端"""
    return APIClient()

@pytest.fixture
def authenticated_client(api_client):
    """创建已认证的客户端"""
    user = UserFactory()
    api_client.force_authenticate(user=user)
    return api_client, user

@pytest.mark.django_db
class TestTestCaseAPI:
    """测试用例 API 测试"""
    
    def test_list_testcases(self, authenticated_client):
        """测试获取用例列表"""
        client, user = authenticated_client
        project = ProjectFactory(creator=user)
        TestCaseFactory.create_batch(5, project=project, creator=user)
        
        response = client.get(
            '/api/testcase/',
            {'project_id': project.id}
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 200
        assert len(response.data['data']) == 5
    
    def test_create_testcase(self, authenticated_client):
        """测试创建用例"""
        client, user = authenticated_client
        project = ProjectFactory(creator=user)
        
        data = {
            'case_name': '新测试用例',
            'test_type': 'functional',
            'project_id': project.id
        }
        
        response = client.post('/api/testcase/', data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['code'] == 200
        assert response.data['data']['case_name'] == '新测试用例'
    
    def test_create_testcase_without_auth(self, api_client):
        """测试未认证创建用例"""
        data = {
            'case_name': '新测试用例',
            'test_type': 'functional',
            'project_id': 1
        }
        
        response = api_client.post('/api/testcase/', data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_update_testcase(self, authenticated_client):
        """测试更新用例"""
        client, user = authenticated_client
        testcase = TestCaseFactory(creator=user)
        
        data = {
            'case_name': '更新后的名称'
        }
        
        response = client.patch(
            f'/api/testcase/{testcase.id}/',
            data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['case_name'] == '更新后的名称'
    
    def test_delete_testcase(self, authenticated_client):
        """测试删除用例"""
        client, user = authenticated_client
        testcase = TestCaseFactory(creator=user)
        
        response = client.delete(f'/api/testcase/{testcase.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        
        # 验证软删除
        testcase.refresh_from_db()
        assert testcase.is_deleted is True
```

### 2. 数据库集成测试

```python
# testcase/tests/test_database.py
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from testcase.tests.factories import ProjectFactory, TestCaseFactory

@pytest.mark.django_db
class TestDatabaseQueries:
    """数据库查询测试"""
    
    def test_query_optimization(self):
        """测试查询优化 - N+1 问题"""
        project = ProjectFactory()
        TestCaseFactory.create_batch(10, project=project)
        
        # 使用 select_related 优化
        with CaptureQueriesContext(connection) as context:
            from testcase.models import TestCase
            testcases = TestCase.objects.filter(
                project=project
            ).select_related('creator', 'module')
            
            # 访问关联对象
            for tc in testcases:
                _ = tc.creator.username
                if tc.module:
                    _ = tc.module.module_name
        
        # 验证查询次数（应该只有 1 次查询）
        assert len(context.captured_queries) <= 2
```

---

## E2E 测试

### 1. Playwright 测试

```bash
# 安装 Playwright
cd frontend
npm install -D @playwright/test
npx playwright install
```

**配置文件**:
```javascript
// playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:5173',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' }
    }
  ]
})
```

**测试用例**:
```javascript
// tests/e2e/testcase.spec.js
import { test, expect } from '@playwright/test'

test.describe('测试用例管理', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/login')
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[name="password"]', 'testpass123')
    await page.click('button[type="submit"]')
    await page.waitForURL('/dashboard')
  })
  
  test('创建测试用例', async ({ page }) => {
    // 进入测试用例页面
    await page.goto('/testcase')
    
    // 点击创建按钮
    await page.click('button:has-text("创建用例")')
    
    // 填写表单
    await page.fill('input[name="case_name"]', '新测试用例')
    await page.selectOption('select[name="test_type"]', 'functional')
    await page.fill('textarea[name="case_desc"]', '这是一个测试用例')
    
    // 提交
    await page.click('button:has-text("确定")')
    
    // 验证成功消息
    await expect(page.locator('.el-message--success')).toBeVisible()
    
    // 验证列表中出现新用例
    await expect(page.locator('text=新测试用例')).toBeVisible()
  })
  
  test('编辑测试用例', async ({ page }) => {
    await page.goto('/testcase')
    
    // 点击第一个用例的编辑按钮
    await page.click('tr:first-child button:has-text("编辑")')
    
    // 修改名称
    await page.fill('input[name="case_name"]', '修改后的名称')
    await page.click('button:has-text("确定")')
    
    // 验证
    await expect(page.locator('text=修改后的名称')).toBeVisible()
  })
  
  test('删除测试用例', async ({ page }) => {
    await page.goto('/testcase')
    
    // 点击删除按钮
    await page.click('tr:first-child button:has-text("删除")')
    
    // 确认删除
    await page.click('.el-message-box button:has-text("确定")')
    
    // 验证成功消息
    await expect(page.locator('.el-message--success')).toBeVisible()
  })
})
```

---

## 性能测试

### 1. Locust 性能测试

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class TestCaseUser(HttpUser):
    """测试用例性能测试"""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """登录"""
        response = self.client.post('/api/user/login/', json={
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.token = response.json()['data']['token']
        self.client.headers.update({
            'Authorization': f'Token {self.token}'
        })
    
    @task(3)
    def list_testcases(self):
        """获取用例列表"""
        self.client.get('/api/testcase/?project_id=1')
    
    @task(1)
    def get_testcase_detail(self):
        """获取用例详情"""
        self.client.get('/api/testcase/1/')
    
    @task(1)
    def create_testcase(self):
        """创建用例"""
        self.client.post('/api/testcase/', json={
            'case_name': '性能测试用例',
            'test_type': 'functional',
            'project_id': 1
        })
```

**运行性能测试**:
```bash
# 启动 Locust
locust -f tests/performance/locustfile.py

# 访问 http://localhost:8089 配置并发用户数
```

---

## 测试覆盖率

### 1. 生成覆盖率报告

```bash
# 运行测试并生成覆盖率报告
pytest --cov=. --cov-report=html --cov-report=term-missing

# 查看 HTML 报告
open htmlcov/index.html
```

### 2. 覆盖率目标

```
模块                覆盖率目标
----------------------------------
Service 层          > 90%
Repository 层       > 85%
Views 层            > 80%
Models 层           > 70%
工具函数            > 95%
----------------------------------
整体                > 80%
```

### 3. CI/CD 集成

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest --cov=. --cov-report=xml --cov-fail-under=80
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

---

**文档版本**: v1.0  
**创建时间**: 2026-04-27
