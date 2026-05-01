"""
UI自动化测试脚本生成视图
"""
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class UiAutomationGenerateAPIView(APIView):
    """
    UI自动化测试脚本生成接口（Mock版本）
    POST /api/ui-automation/generate/
    接收 url 和 steps，返回模拟生成的 Python Unittest 测试代码
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request: Request) -> Response:
        url = request.data.get("url", "").strip()
        steps = request.data.get("steps", "").strip()

        if not url:
            return Response(
                {"success": False, "error": "URL is required", "code": ""},
                status=400
            )

        if not steps:
            return Response(
                {"success": False, "error": "Steps description is required", "code": ""},
                status=400
            )

        # 模拟生成的 Python Unittest 代码（严格遵循 7 层 POM 架构的 Testcase 层）
        mock_code = f'''import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class TestUIAutomation(unittest.TestCase):
    """
    UI自动化测试用例
    目标URL: {url}
    测试场景: {steps[:100]}...
    """

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
        self.driver.get("{url}")

    def test_user_scenario(self):
        """
        测试场景: {steps[:200]}
        """
        # 步骤1: 等待页面加载完成
        self.wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # 步骤2: 验证页面标题
        self.assertIsNotNone(self.driver.title, "页面标题不应为空")

        # 步骤3: 查找并验证关键元素存在
        try:
            element = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input, button, a"))
            )
            self.assertTrue(element.is_displayed(), "关键元素应该可见")
        except Exception as e:
            self.fail(f"未找到预期的页面元素: {{str(e)}}")

        # 步骤4: 验证页面URL正确
        current_url = self.driver.current_url
        self.assertIn("{url.split('://')[1].split('/')[0]}", current_url,
                     f"当前URL应包含目标域名")

    def test_page_load_performance(self):
        """测试页面加载性能"""
        import time
        start_time = time.time()
        self.driver.get("{url}")
        load_time = time.time() - start_time

        # 断言页面加载时间应小于5秒
        self.assertLess(load_time, 5.0,
                       f"页面加载时间 {{load_time:.2f}}s 超过预期的5秒")


if __name__ == "__main__":
    unittest.main(verbosity=2)
'''

        return Response(
            {
                "success": True,
                "code": mock_code,
                "message": "UI自动化测试脚本生成成功（Mock）"
            },
            status=200
        )
