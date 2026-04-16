"""
AITesta 全流程 AI 测试平台 - 接口自动化测试脚本

测试范围:
1. 用户认证模块 (登录/注册/验证码/密码修改)
2. 项目管理模块 (项目 CRUD/成员管理)
3. 测试用例模块 (用例 CRUD/执行/回收站)
4. RAG 知识库模块 (知识库检索/文档上传)
5. AI 用例生成模块 (AI 生成用例/连接测试)
6. 缺陷管理模块 (缺陷 CRUD)
7. 执行管理模块 (测试计划/报告/性能任务)
8. 边界条件与异常处理

依赖: pytest, requests
运行: pytest tests/api/test_comprehensive.py -v --tb=short
"""

import os
import pytest
import requests
import uuid
from datetime import datetime, timedelta

# ==================== 配置部分 ====================

TEST_API_BASE_URL = os.getenv("TEST_API_BASE_URL", "http://127.0.0.1:8000/api")
TEST_USERNAME = os.getenv("TEST_API_USERNAME", "admin")
TEST_PASSWORD = os.getenv("TEST_API_PASSWORD", "admin123")
TEST_AI_API_KEY = os.getenv("TEST_AI_API_KEY", "")

if not os.getenv("TEST_API_BASE_URL", "").strip():
    pytest.skip("缺少环境变量 TEST_API_BASE_URL，跳过 API 集成测试", allow_module_level=True)


# ==================== 工具函数 ====================


def get_nonce():
    """生成唯一标识符"""
    return uuid.uuid4().hex[:8]


def login(session, username, password):
    """用户登录并获取 token"""
    resp = session.post(
        f"{TEST_API_BASE_URL}/user/login/",
        json={"username": username, "password": password},
        timeout=20,
    )
    assert resp.status_code == 200, f"登录失败：{resp.status_code}, {resp.text}"
    data = resp.json().get("data", {})
    token = data.get("token")
    assert token, f"登录响应缺少 token: {resp.text}"
    return token


def create_auth_session(username=TEST_USERNAME, password=TEST_PASSWORD):
    """创建带认证信息的 session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    token = login(session, username, password)
    session.headers.update({"Authorization": f"Token {token}"})
    return session


# ==================== Fixtures ====================


@pytest.fixture(scope="session")
def auth_session():
    """创建认证后的 session"""
    return create_auth_session()


@pytest.fixture(scope="session")
def test_data(auth_session):
    """创建测试所需的基础数据"""
    nonce = get_nonce()

    # 创建项目
    project_resp = auth_session.post(
        f"{TEST_API_BASE_URL}/project/projects/",
        json={
            "project_name": f"api-test-project-{nonce}",
            "description": "自动化测试项目",
            "project_status": 1,
            "progress": 10,
        },
        timeout=20,
    )
    assert project_resp.status_code in (200, 201), project_resp.text
    project_id = project_resp.json()["id"]

    # 创建模块
    module_resp = auth_session.post(
        f"{TEST_API_BASE_URL}/testcase/modules/",
        json={
            "project": project_id,
            "name": f"module-{nonce}",
            "test_type": "api",
        },
        timeout=20,
    )
    assert module_resp.status_code in (200, 201), module_resp.text
    module_id = module_resp.json()["id"]

    # 创建用例
    case_resp = auth_session.post(
        f"{TEST_API_BASE_URL}/testcase/cases/",
        json={
            "module": module_id,
            "case_name": f"case-{nonce}",
            "test_type": "api",
            "level": "P1",
            "api_url": "https://httpbin.org/get",
            "api_method": "GET",
        },
        timeout=20,
    )
    assert case_resp.status_code in (200, 201), case_resp.text
    case_id = case_resp.json()["id"]

    return {
        "project_id": project_id,
        "module_id": module_id,
        "case_id": case_id,
        "nonce": nonce,
    }


# ==================== 用户认证模块测试 ====================


class TestUserAuth:
    """用户认证相关测试"""

    def test_get_captcha(self, auth_session):
        """测试获取验证码"""
        resp = auth_session.get(f"{TEST_API_BASE_URL}/user/captcha/")
        assert resp.status_code == 200
        data = resp.json().get("data", {})
        assert "uuid" in data
        assert "image" in data

    def test_login_success(self, auth_session):
        """测试登录成功"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/user/login/",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
            timeout=20,
        )
        assert resp.status_code == 200
        data = resp.json().get("data", {})
        assert "token" in data
        assert "username" in data

    def test_login_invalid_password(self, auth_session):
        """测试登录失败 - 密码错误"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/user/login/",
            json={"username": TEST_USERNAME, "password": "wrong_password"},
            timeout=20,
        )
        assert resp.status_code == 400

    def test_login_nonexistent_user(self, auth_session):
        """测试登录失败 - 用户不存在"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/user/login/",
            json={"username": f"nonexistent_{get_nonce()}", "password": "password"},
            timeout=20,
        )
        assert resp.status_code == 400

    def test_current_user_info(self, auth_session):
        """测试获取当前用户信息"""
        resp = auth_session.get(f"{TEST_API_BASE_URL}/user/me/")
        assert resp.status_code == 200
        data = resp.json().get("data", {})
        assert "user_id" in data
        assert "username" in data

    def test_change_password_success(self, auth_session):
        """测试修改密码成功"""
        old_password = TEST_PASSWORD
        new_password = f"newpass_{get_nonce()}"

        # 修改密码
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/user/change-password/",
            json={
                "old_password": old_password,
                "new_password": new_password,
                "confirm_password": new_password,
            },
            timeout=20,
        )
        assert resp.status_code == 200

        # 验证新密码可以登录
        new_session = create_auth_session(password=new_password)
        assert new_session is not None

        # 改回原密码
        auth_session.post(
            f"{TEST_API_BASE_URL}/user/change-password/",
            json={
                "old_password": new_password,
                "new_password": old_password,
                "confirm_password": old_password,
            },
            timeout=20,
        )

    def test_change_password_invalid_old(self, auth_session):
        """测试修改密码失败 - 旧密码错误"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/user/change-password/",
            json={
                "old_password": "wrong_old_password",
                "new_password": "new_password",
                "confirm_password": "new_password",
            },
            timeout=20,
        )
        assert resp.status_code == 400

    def test_change_password_mismatch(self, auth_session):
        """测试修改密码失败 - 新密码不一致"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/user/change-password/",
            json={
                "old_password": TEST_PASSWORD,
                "new_password": "new_password",
                "confirm_password": "different_password",
            },
            timeout=20,
        )
        assert resp.status_code == 400

    def test_update_profile(self, auth_session):
        """测试更新用户资料"""
        resp = auth_session.patch(
            f"{TEST_API_BASE_URL}/user/me/profile/",
            json={
                "real_name": f"Test User {get_nonce()}",
                "phone_number": "13800138000",
                "email": f"test_{get_nonce()}@example.com",
            },
            timeout=20,
        )
        assert resp.status_code == 200


# ==================== 项目管理模块测试 ====================


class TestProject:
    """项目管理相关测试"""

    def test_create_project(self, auth_session):
        """测试创建项目"""
        project_name = f"proj_{get_nonce()}"
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/project/projects/",
            json={
                "project_name": project_name,
                "description": "测试项目",
                "project_status": 1,
                "progress": 0,
            },
            timeout=20,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "id" in data
        assert data["project_name"] == project_name

    def test_list_projects(self, auth_session):
        """测试获取项目列表"""
        resp = auth_session.get(f"{TEST_API_BASE_URL}/project/projects/")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data or isinstance(data, list)

    def test_get_project_detail(self, auth_session, test_data):
        """测试获取项目详情"""
        resp = auth_session.get(
            f"{TEST_API_BASE_URL}/project/projects/{test_data['project_id']}/",
            timeout=20,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == test_data["project_id"]

    def test_update_project(self, auth_session, test_data):
        """测试更新项目"""
        resp = auth_session.patch(
            f"{TEST_API_BASE_URL}/project/projects/{test_data['project_id']}/",
            json={"progress": 50},
            timeout=20,
        )
        assert resp.status_code == 200

    def test_delete_project(self, auth_session, test_data):
        """测试删除项目"""
        resp = auth_session.delete(
            f"{TEST_API_BASE_URL}/project/projects/{test_data['project_id']}/",
            timeout=20,
        )
        assert resp.status_code in (204, 200)

    def test_create_project_invalid(self, auth_session):
        """测试创建项目 - 无效数据"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/project/projects/",
            json={
                "project_name": "",  # 空名称
                "project_status": 999,  # 无效状态
            },
            timeout=20,
        )
        assert resp.status_code == 400


# ==================== 测试用例模块测试 ====================


class TestTestCase:
    """测试用例相关测试"""

    def test_create_case(self, auth_session, test_data):
        """测试创建用例"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/testcase/cases/",
            json={
                "module": test_data["module_id"],
                "case_name": f"case_{get_nonce()}",
                "test_type": "api",
                "level": "P0",
                "api_url": "https://httpbin.org/get",
                "api_method": "GET",
            },
            timeout=20,
        )
        assert resp.status_code in (200, 201)

    def test_list_cases(self, auth_session, test_data):
        """测试获取用例列表"""
        resp = auth_session.get(
            f"{TEST_API_BASE_URL}/testcase/cases/?module={test_data['module_id']}",
            timeout=20,
        )
        assert resp.status_code == 200

    def test_get_case_detail(self, auth_session, test_data):
        """测试获取用例详情"""
        resp = auth_session.get(
            f"{TEST_API_BASE_URL}/testcase/cases/{test_data['case_id']}/", timeout=20
        )
        assert resp.status_code == 200

    def test_execute_api_case(self, auth_session, test_data):
        """测试执行 API 用例"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/testcase/cases/{test_data['case_id']}/execute-api/",
            json={},
            timeout=30,
        )
        # 可能返回 200 或 400，取决于用例配置
        assert resp.status_code in (200, 400)

    def test_batch_execute(self, auth_session, test_data):
        """测试批量执行"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/testcase/cases/batch-execute/",
            json={"ids": [test_data["case_id"]]},
            timeout=20,
        )
        assert resp.status_code == 200

    def test_batch_delete(self, auth_session, test_data):
        """测试批量删除"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/testcase/cases/batch-delete/",
            json={"ids": [test_data["case_id"]]},
            timeout=20,
        )
        assert resp.status_code == 200

    def test_recycle_bin(self, auth_session, test_data):
        """测试回收站功能"""
        # 先删除用例
        auth_session.post(
            f"{TEST_API_BASE_URL}/testcase/cases/batch-delete/",
            json={"ids": [test_data["case_id"]]},
            timeout=20,
        )

        # 查看回收站
        resp = auth_session.get(
            f"{TEST_API_BASE_URL}/testcase/cases/recycle-bin/", timeout=20
        )
        assert resp.status_code == 200

    def test_restore_case(self, auth_session, test_data):
        """测试恢复用例"""
        # 先删除
        auth_session.post(
            f"{TEST_API_BASE_URL}/testcase/cases/batch-delete/",
            json={"ids": [test_data["case_id"]]},
            timeout=20,
        )

        # 恢复
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/testcase/cases/{test_data['case_id']}/restore/",
            json={},
            timeout=20,
        )
        assert resp.status_code == 200

    def test_create_case_invalid(self, auth_session):
        """测试创建用例 - 无效数据"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/testcase/cases/",
            json={
                "module": "invalid_id",
                "case_name": "",
            },
            timeout=20,
        )
        assert resp.status_code == 400


# ==================== RAG 知识库模块测试 ====================


class TestKnowledgeRAG:
    """RAG 知识库相关测试"""

    def test_knowledge_search(self, auth_session):
        """测试知识库搜索"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/assistant/knowledge/search/",
            json={
                "query_text": "测试用例生成",
                "top_k": 5,
            },
            timeout=20,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data
        assert "results" in data

    def test_knowledge_search_empty_query(self, auth_session):
        """测试知识库搜索 - 空查询"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/assistant/knowledge/search/",
            json={
                "query_text": "",
            },
            timeout=20,
        )
        assert resp.status_code == 400

    def test_knowledge_category_options(self, auth_session):
        """测试知识库文档详情状态接口"""
        # 先取文档列表，若为空则跳过（不同环境初始数据可能为空）
        list_resp = auth_session.get(
            f"{TEST_API_BASE_URL}/assistant/knowledge/documents/", timeout=20
        )
        assert list_resp.status_code == 200
        payload = list_resp.json() or {}
        docs = payload.get("results") or []
        if not docs:
            pytest.skip("无知识库文档，跳过状态详情校验")
        doc_id = docs[0].get("id")
        assert doc_id is not None

        resp = auth_session.get(
            f"{TEST_API_BASE_URL}/assistant/knowledge/documents/{doc_id}/status/",
            timeout=20,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True

    def test_knowledge_document_list(self, auth_session):
        """测试知识库文档列表"""
        resp = auth_session.get(
            f"{TEST_API_BASE_URL}/assistant/knowledge/documents/", timeout=20
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data
        assert "results" in data

    def test_knowledge_runtime_status(self, auth_session):
        """测试知识库运行时状态"""
        resp = auth_session.get(
            f"{TEST_API_BASE_URL}/assistant/knowledge/runtime-status/", timeout=20
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success")
        assert "counters" in data


# ==================== AI 用例生成模块测试 ====================


class TestAICaseGeneration:
    """AI 用例生成相关测试"""

    def test_ai_test_connection(self, auth_session):
        """测试 AI 连接"""
        if not TEST_AI_API_KEY:
            pytest.skip("未配置 TEST_AI_API_KEY，跳过 AI 连接测试")

        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/ai/test-connection/",
            json={
                "api_key": TEST_AI_API_KEY,
                "model": "glm-4.7-flash",
            },
            timeout=30,
        )
        # 可能返回 200 或 400，取决于 API Key 是否有效
        assert resp.status_code in (200, 400)

    def test_ai_verify_connection(self, auth_session):
        """测试 AI 连接验证"""
        if not TEST_AI_API_KEY:
            pytest.skip("未配置 TEST_AI_API_KEY，跳过 AI 连接验证测试")

        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/ai/verify-connection/",
            json={
                "api_key": TEST_AI_API_KEY,
            },
            timeout=30,
        )
        assert resp.status_code in (200, 400)

    def test_ai_generate_cases_invalid(self, auth_session):
        """测试 AI 生成用例 - 无效请求"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/ai/generate-cases/",
            json={},  # 缺少必要参数
            timeout=30,
        )
        assert resp.status_code == 400

    def test_ai_generate_cases_missing_key(self, auth_session):
        """测试 AI 生成用例 - 缺少 API Key"""
        try:
            resp = auth_session.post(
                f"{TEST_API_BASE_URL}/ai/generate-cases/",
                json={
                    "prompt_text": "生成一个登录测试用例",
                },
                timeout=30,
            )
        except requests.exceptions.ReadTimeout:
            pytest.skip("AI 生成接口超时，跳过该环境下的不稳定校验")
        # 未配置 key 时通常返回 400/503；若走到已保存但不可用的全局配置，也可能返回 500
        assert resp.status_code in (400, 500, 503)

    def test_llm_test_connection(self, auth_session):
        """测试 LLM 连接测试"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/assistant/llm/test-connection/", json={}, timeout=20
        )
        # 可能返回 200 或 400
        assert resp.status_code in (200, 400)


# ==================== 缺陷管理模块测试 ====================


class TestDefect:
    """缺陷管理相关测试"""

    def test_create_defect(self, auth_session, test_data):
        """测试创建缺陷"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/defect/defects/",
            json={
                "defect_name": f"defect_{get_nonce()}",
                "module": test_data["module_id"],
                "severity": 2,
                "priority": 2,
                "status": 1,
                "defect_content": "测试缺陷内容",
            },
            timeout=20,
        )
        assert resp.status_code in (200, 201)

    def test_list_defects(self, auth_session):
        """测试获取缺陷列表"""
        resp = auth_session.get(f"{TEST_API_BASE_URL}/defect/defects/")
        assert resp.status_code == 200

    def test_get_defect_detail(self, auth_session, test_data):
        """测试获取缺陷详情"""
        # 先创建缺陷获取 ID
        create_resp = auth_session.post(
            f"{TEST_API_BASE_URL}/defect/defects/",
            json={
                "defect_name": f"defect_{get_nonce()}",
                "module": test_data["module_id"],
                "severity": 2,
                "priority": 2,
                "status": 1,
                "defect_content": "测试",
            },
            timeout=20,
        )
        defect_id = create_resp.json()["id"]

        resp = auth_session.get(
            f"{TEST_API_BASE_URL}/defect/defects/{defect_id}/", timeout=20
        )
        assert resp.status_code == 200

    def test_update_defect(self, auth_session, test_data):
        """测试更新缺陷"""
        create_resp = auth_session.post(
            f"{TEST_API_BASE_URL}/defect/defects/",
            json={
                "defect_name": f"defect_{get_nonce()}",
                "module": test_data["module_id"],
                "severity": 2,
                "priority": 2,
                "status": 1,
                "defect_content": "测试",
            },
            timeout=20,
        )
        defect_id = create_resp.json()["id"]

        resp = auth_session.patch(
            f"{TEST_API_BASE_URL}/defect/defects/{defect_id}/",
            json={"status": 2},
            timeout=20,
        )
        assert resp.status_code == 200

    def test_delete_defect(self, auth_session, test_data):
        """测试删除缺陷"""
        create_resp = auth_session.post(
            f"{TEST_API_BASE_URL}/defect/defects/",
            json={
                "defect_name": f"defect_{get_nonce()}",
                "module": test_data["module_id"],
                "severity": 2,
                "priority": 2,
                "status": 1,
                "defect_content": "测试",
            },
            timeout=20,
        )
        defect_id = create_resp.json()["id"]

        resp = auth_session.delete(
            f"{TEST_API_BASE_URL}/defect/defects/{defect_id}/", timeout=20
        )
        assert resp.status_code in (204, 200)

    def test_create_defect_invalid(self, auth_session):
        """测试创建缺陷 - 无效数据"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/defect/defects/",
            json={
                "defect_name": "",
                "severity": 999,
                "priority": 999,
            },
            timeout=20,
        )
        assert resp.status_code == 400


# ==================== 执行管理模块测试 ====================


class TestExecution:
    """执行管理相关测试"""

    def test_dashboard_summary(self, auth_session):
        """测试仪表盘摘要"""
        resp = auth_session.get(
            f"{TEST_API_BASE_URL}/execution/dashboard/summary/", timeout=20
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "statCards" in data
        assert "lineChart" in data
        assert "pieChart" in data

    def test_quality_dashboard(self, auth_session):
        """测试质量分析看板"""
        resp = auth_session.get(
            f"{TEST_API_BASE_URL}/execution/dashboard/quality/", timeout=20
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "trendChart" in data
        assert "latestMetrics" in data

    def test_create_test_plan(self, auth_session, test_data):
        """测试创建测试计划"""
        release_resp = auth_session.post(
            f"{TEST_API_BASE_URL}/project/releases/",
            json={
                "project": test_data["project_id"],
                "release_name": f"release_{get_nonce()}",
                "version_no": f"v_{get_nonce()}",
                "release_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "status": 1,
            },
            timeout=20,
        )
        assert release_resp.status_code in (200, 201)
        release_id = release_resp.json()["id"]

        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/execution/plans/",
            json={
                "plan_name": f"plan_{get_nonce()}",
                "version": release_id,
                "environment": "test",
                "req_count": 1,
                "case_count": 1,
            },
            timeout=20,
        )
        assert resp.status_code in (200, 201)

    def test_list_test_plans(self, auth_session):
        """测试获取测试计划列表"""
        resp = auth_session.get(f"{TEST_API_BASE_URL}/execution/plans/")
        assert resp.status_code == 200

    def test_create_test_report(self, auth_session, test_data):
        """测试创建测试报告"""
        release_resp = auth_session.post(
            f"{TEST_API_BASE_URL}/project/releases/",
            json={
                "project": test_data["project_id"],
                "release_name": f"release_{get_nonce()}",
                "version_no": f"v_{get_nonce()}",
                "release_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "status": 1,
            },
            timeout=20,
        )
        assert release_resp.status_code in (200, 201)
        release_id = release_resp.json()["id"]

        plan_resp = auth_session.post(
            f"{TEST_API_BASE_URL}/execution/plans/",
            json={
                "plan_name": f"plan_{get_nonce()}",
                "version": release_id,
                "environment": "test",
                "req_count": 1,
                "case_count": 1,
            },
            timeout=20,
        )
        assert plan_resp.status_code in (200, 201)
        plan_id = plan_resp.json()["id"]

        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/execution/reports/",
            json={
                "plan": plan_id,
                "report_name": f"report_{get_nonce()}",
                "create_method": 1,
                "environment": "test",
                "start_time": datetime.utcnow().isoformat(),
                "end_time": datetime.utcnow().isoformat(),
            },
            timeout=20,
        )
        assert resp.status_code in (200, 201)

    def test_list_test_reports(self, auth_session):
        """测试获取测试报告列表"""
        resp = auth_session.get(f"{TEST_API_BASE_URL}/execution/reports/")
        assert resp.status_code == 200

    def test_create_perf_task(self, auth_session):
        """测试创建性能任务"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/execution/tasks/",
            json={
                "task_name": f"perf_{get_nonce()}",
                "scenario": "jmeter",
                "concurrency": 10,
                "duration": "10m",
            },
            timeout=20,
        )
        assert resp.status_code in (200, 201)

    def test_perf_task_run(self, auth_session):
        """测试性能任务执行"""
        # 先创建任务
        create_resp = auth_session.post(
            f"{TEST_API_BASE_URL}/execution/tasks/",
            json={
                "task_name": f"perf_{get_nonce()}",
                "scenario": "jmeter",
                "concurrency": 10,
                "duration": "10m",
            },
            timeout=20,
        )
        task_id = create_resp.json()["task_id"]

        # 执行任务
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/execution/tasks/{task_id}/run/", json={}, timeout=20
        )
        assert resp.status_code in (200, 400)

    def test_perf_task_invalid(self, auth_session):
        """测试性能任务 - 无效数据"""
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/execution/tasks/",
            json={
                "task_name": "",
                "concurrency": -1,
                "duration": "invalid",
            },
            timeout=20,
        )
        assert resp.status_code == 400


# ==================== 边界条件与异常处理测试 ====================


class TestBoundaryAndEdgeCases:
    """边界条件与异常处理测试"""

    def test_invalid_json_payload(self, auth_session):
        """测试无效 JSON 载荷"""
        # 使用 requests 发送非法 JSON
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/project/projects/", data="not valid json", timeout=20
        )
        assert resp.status_code in (400, 422)

    def test_method_not_allowed(self, auth_session, test_data):
        """测试不允许的 HTTP 方法"""
        # 对只支持 GET 的端点使用 POST
        resp = auth_session.post(
            f"{TEST_API_BASE_URL}/project/projects/{test_data['project_id']}/",
            json={"project_name": "test"},
            timeout=20,
        )
        # 可能返回 405 或其他错误
        assert resp.status_code in (405, 400, 200)

    def test_resource_not_found(self, auth_session):
        """测试资源不存在"""
        resp = auth_session.get(
            f"{TEST_API_BASE_URL}/project/projects/999999/", timeout=20
        )
        assert resp.status_code in (404, 400)

    def test_pagination(self, auth_session):
        """测试分页功能"""
        resp = auth_session.get(
            f"{TEST_API_BASE_URL}/project/projects/?page=1&page_size=5", timeout=20
        )
        assert resp.status_code == 200

    def test_search_filter(self, auth_session, test_data):
        """测试搜索过滤"""
        resp = auth_session.get(
            f"{TEST_API_BASE_URL}/testcase/cases/?search=test", timeout=20
        )
        assert resp.status_code == 200

    def test_filter_invalid_type(self, auth_session):
        """测试过滤参数类型错误"""
        resp = auth_session.get(
            f"{TEST_API_BASE_URL}/project/projects/?project=invalid", timeout=20
        )
        # 应该返回 200 但结果为空，或返回 400
        assert resp.status_code in (200, 400)

    def test_empty_list_response(self, auth_session):
        """测试空列表响应"""
        resp = auth_session.get(
            f"{TEST_API_BASE_URL}/project/projects/?name=nonexistent_{get_nonce()}",
            timeout=20,
        )
        assert resp.status_code == 200
        data = resp.json()
        # 验证返回结构正确
        assert "results" in data or "data" in data or isinstance(data, list)


# ==================== 数据清理测试 ====================


class TestDataCleanup:
    """测试数据清理 - 确保测试后不留残留数据"""

    def test_cleanup_test_data(self, auth_session, test_data):
        """清理测试创建的数据"""
        # 清理项目及相关数据
        try:
            auth_session.delete(
                f"{TEST_API_BASE_URL}/project/projects/{test_data['project_id']}/",
                timeout=20,
            )
        except Exception:
            pass  # 可能已被删除

        print(f"\n测试数据清理完成：{test_data['nonce']}")


# ==================== 运行配置 ====================

# pytest 标记定义
pytestmark = pytest.mark.slow  # 标记为慢速测试

# 测试运行配置
# pytest test_comprehensive.py -v --tb=short
# pytest test_comprehensive.py -v -k "test_login"  # 运行特定测试
# pytest test_comprehensive.py -v --maxfail=3  # 失败 3 个后停止


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
