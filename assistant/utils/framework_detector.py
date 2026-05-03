"""
测试框架自动检测工具

支持检测Python和Java的主流测试框架
"""
import os
import re
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class FrameworkDetector:
    """测试框架检测器"""

    @staticmethod
    def detect_python_framework(workspace_path: str) -> str:
        """
        检测Python测试框架

        Args:
            workspace_path: 工作空间路径

        Returns:
            框架名称: PYTEST/UNITTEST/NOSE/ROBOT/BEHAVE/LINEAR
        """
        # 检测优先级
        detectors = [
            ('ROBOT', FrameworkDetector._detect_robot_framework),
            ('BEHAVE', FrameworkDetector._detect_behave),
            ('PYTEST', FrameworkDetector._detect_pytest),
            ('NOSE', FrameworkDetector._detect_nose),
            ('UNITTEST', FrameworkDetector._detect_unittest),
        ]

        for framework_name, detector_func in detectors:
            if detector_func(workspace_path):
                logger.info(f"检测到Python测试框架: {framework_name}")
                return framework_name

        # 检查是否是纯线性脚本（包含selenium/playwright但没有测试框架）
        if FrameworkDetector._detect_linear_script(workspace_path):
            logger.info("检测到线性自动化脚本，将直接运行")
            return 'LINEAR'

        # 默认返回pytest
        logger.warning("未检测到明确的Python测试框架，默认使用PYTEST")
        return 'PYTEST'

    @staticmethod
    def detect_java_framework(workspace_path: str) -> str:
        """
        检测Java测试框架

        Args:
            workspace_path: 工作空间路径

        Returns:
            框架名称: JUNIT4/JUNIT5/TESTNG/CUCUMBER/SPOCK
        """
        # 检测优先级
        detectors = [
            ('CUCUMBER', FrameworkDetector._detect_cucumber),
            ('SPOCK', FrameworkDetector._detect_spock),
            ('TESTNG', FrameworkDetector._detect_testng),
            ('JUNIT5', FrameworkDetector._detect_junit5),
            ('JUNIT4', FrameworkDetector._detect_junit4),
        ]

        for framework_name, detector_func in detectors:
            if detector_func(workspace_path):
                logger.info(f"检测到Java测试框架: {framework_name}")
                return framework_name

        # 默认返回JUnit5
        logger.warning("未检测到明确的Java测试框架，默认使用JUNIT5")
        return 'JUNIT5'

    @staticmethod
    def _detect_pytest(workspace_path: str) -> bool:
        """检测pytest框架"""
        # 检查pytest.ini或pyproject.toml
        if os.path.exists(os.path.join(workspace_path, 'pytest.ini')):
            return True

        pyproject = os.path.join(workspace_path, 'pyproject.toml')
        if os.path.exists(pyproject):
            try:
                with open(pyproject, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '[tool.pytest' in content:
                        return True
            except Exception:
                pass

        # 检查requirements.txt
        requirements = os.path.join(workspace_path, 'requirements.txt')
        if os.path.exists(requirements):
            try:
                with open(requirements, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if re.search(r'pytest[>=<\s]', content, re.IGNORECASE):
                        return True
            except Exception:
                pass

        # 检查Python文件中的pytest导入
        return FrameworkDetector._scan_python_imports(workspace_path, ['pytest'])

    @staticmethod
    def _detect_unittest(workspace_path: str) -> bool:
        """检测unittest框架"""
        # unittest是Python标准库，检查是否有unittest导入
        return FrameworkDetector._scan_python_imports(
            workspace_path,
            ['unittest', 'from unittest import']
        )

    @staticmethod
    def _detect_nose(workspace_path: str) -> bool:
        """检测nose框架"""
        # 检查requirements.txt
        requirements = os.path.join(workspace_path, 'requirements.txt')
        if os.path.exists(requirements):
            try:
                with open(requirements, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if re.search(r'nose[>=<\s]', content, re.IGNORECASE):
                        return True
            except Exception:
                pass

        # 检查nose导入
        return FrameworkDetector._scan_python_imports(workspace_path, ['nose'])

    @staticmethod
    def _detect_robot_framework(workspace_path: str) -> bool:
        """检测Robot Framework"""
        # 检查.robot文件
        for root, dirs, files in os.walk(workspace_path):
            for file in files:
                if file.endswith('.robot'):
                    return True

        # 检查requirements.txt
        requirements = os.path.join(workspace_path, 'requirements.txt')
        if os.path.exists(requirements):
            try:
                with open(requirements, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if re.search(r'robotframework[>=<\s]', content, re.IGNORECASE):
                        return True
            except Exception:
                pass

        return False

    @staticmethod
    def _detect_behave(workspace_path: str) -> bool:
        """检测Behave框架"""
        # 检查features目录和.feature文件
        features_dir = os.path.join(workspace_path, 'features')
        if os.path.exists(features_dir):
            for root, dirs, files in os.walk(features_dir):
                for file in files:
                    if file.endswith('.feature'):
                        return True

        # 检查requirements.txt
        requirements = os.path.join(workspace_path, 'requirements.txt')
        if os.path.exists(requirements):
            try:
                with open(requirements, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if re.search(r'behave[>=<\s]', content, re.IGNORECASE):
                        return True
            except Exception:
                pass

        return False

    @staticmethod
    def _detect_linear_script(workspace_path: str) -> bool:
        """
        检测是否是线性自动化脚本（不包含测试框架的普通脚本）

        特征：
        1. 包含 selenium/playwright 导入
        2. 不包含测试框架的类或装饰器
        """
        try:
            has_automation_lib = False
            has_test_framework = False

            for root, dirs, files in os.walk(workspace_path):
                # 跳过虚拟环境和缓存目录
                dirs[:] = [d for d in dirs if d not in ['venv', '.venv', '__pycache__', '.git']]

                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()

                                # 检查是否导入了自动化库
                                if any(lib in content for lib in [
                                    'from selenium', 'import selenium',
                                    'from playwright', 'import playwright',
                                    'from appium', 'import appium'
                                ]):
                                    has_automation_lib = True

                                # 检查是否包含测试框架特征
                                if any(pattern in content for pattern in [
                                    'class Test', 'def test_', '@pytest',
                                    'unittest.TestCase', 'from unittest import',
                                    '@Test', 'TestCase'
                                ]):
                                    has_test_framework = True

                        except Exception:
                            continue

            # 如果有自动化库但没有测试框架，则认为是线性脚本
            return has_automation_lib and not has_test_framework

        except Exception as e:
            logger.error(f"检测线性脚本失败: {str(e)}")
            return False

    @staticmethod
    def _detect_junit4(workspace_path: str) -> bool:
        """检测JUnit 4框架"""
        # 检查pom.xml
        pom_path = os.path.join(workspace_path, 'pom.xml')
        if os.path.exists(pom_path):
            try:
                with open(pom_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '<artifactId>junit</artifactId>' in content:
                        # 检查版本号是否为4.x
                        version_match = re.search(r'<version>4\.\d+', content)
                        if version_match:
                            return True
            except Exception:
                pass

        # 检查Java文件中的JUnit 4导入
        return FrameworkDetector._scan_java_imports(
            workspace_path,
            ['org.junit.Test', 'org.junit.Assert']
        )

    @staticmethod
    def _detect_junit5(workspace_path: str) -> bool:
        """检测JUnit 5框架"""
        # 检查pom.xml
        pom_path = os.path.join(workspace_path, 'pom.xml')
        if os.path.exists(pom_path):
            try:
                with open(pom_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'junit-jupiter' in content or '<version>5.' in content:
                        return True
            except Exception:
                pass

        # 检查build.gradle
        gradle_path = os.path.join(workspace_path, 'build.gradle')
        if os.path.exists(gradle_path):
            try:
                with open(gradle_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'junit-jupiter' in content:
                        return True
            except Exception:
                pass

        # 检查Java文件中的JUnit 5导入
        return FrameworkDetector._scan_java_imports(
            workspace_path,
            ['org.junit.jupiter', '@Test']
        )

    @staticmethod
    def _detect_testng(workspace_path: str) -> bool:
        """检测TestNG框架"""
        # 检查testng.xml
        if os.path.exists(os.path.join(workspace_path, 'testng.xml')):
            return True

        # 检查pom.xml
        pom_path = os.path.join(workspace_path, 'pom.xml')
        if os.path.exists(pom_path):
            try:
                with open(pom_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '<artifactId>testng</artifactId>' in content:
                        return True
            except Exception:
                pass

        # 检查Java文件中的TestNG导入
        return FrameworkDetector._scan_java_imports(
            workspace_path,
            ['org.testng', '@Test']
        )

    @staticmethod
    def _detect_cucumber(workspace_path: str) -> bool:
        """检测Cucumber框架"""
        # 检查.feature文件
        for root, dirs, files in os.walk(workspace_path):
            for file in files:
                if file.endswith('.feature'):
                    return True

        # 检查pom.xml
        pom_path = os.path.join(workspace_path, 'pom.xml')
        if os.path.exists(pom_path):
            try:
                with open(pom_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'cucumber' in content.lower():
                        return True
            except Exception:
                pass

        return False

    @staticmethod
    def _detect_spock(workspace_path: str) -> bool:
        """检测Spock框架"""
        # 检查.groovy文件
        for root, dirs, files in os.walk(workspace_path):
            for file in files:
                if file.endswith('Spec.groovy'):
                    return True

        # 检查pom.xml或build.gradle
        pom_path = os.path.join(workspace_path, 'pom.xml')
        if os.path.exists(pom_path):
            try:
                with open(pom_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'spock-core' in content:
                        return True
            except Exception:
                pass

        return False

    @staticmethod
    def _scan_python_imports(workspace_path: str, import_patterns: List[str]) -> bool:
        """
        扫描Python文件中的导入语句

        Args:
            workspace_path: 工作空间路径
            import_patterns: 导入模式列表

        Returns:
            是否找到匹配的导入
        """
        try:
            for root, dirs, files in os.walk(workspace_path):
                # 跳过虚拟环境和缓存目录
                dirs[:] = [d for d in dirs if d not in ['venv', '.venv', '__pycache__', '.git']]

                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                for pattern in import_patterns:
                                    if pattern in content:
                                        return True
                        except Exception:
                            continue
        except Exception as e:
            logger.error(f"扫描Python导入失败: {str(e)}")

        return False

    @staticmethod
    def _scan_java_imports(workspace_path: str, import_patterns: List[str]) -> bool:
        """
        扫描Java文件中的导入语句

        Args:
            workspace_path: 工作空间路径
            import_patterns: 导入模式列表

        Returns:
            是否找到匹配的导入
        """
        try:
            for root, dirs, files in os.walk(workspace_path):
                # 跳过target和build目录
                dirs[:] = [d for d in dirs if d not in ['target', 'build', '.git']]

                for file in files:
                    if file.endswith('.java'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                for pattern in import_patterns:
                                    if pattern in content:
                                        return True
                        except Exception:
                            continue
        except Exception as e:
            logger.error(f"扫描Java导入失败: {str(e)}")

        return False

    @staticmethod
    def detect_dependencies(workspace_path: str, language: str) -> Dict[str, Any]:
        """
        检测项目依赖

        Args:
            workspace_path: 工作空间路径
            language: 语言类型 (PYTHON/JAVA)

        Returns:
            依赖信息字典
        """
        if language == 'PYTHON':
            return FrameworkDetector._detect_python_dependencies(workspace_path)
        elif language == 'JAVA':
            return FrameworkDetector._detect_java_dependencies(workspace_path)
        else:
            return {}

    @staticmethod
    def _detect_python_dependencies(workspace_path: str) -> Dict[str, Any]:
        """检测Python依赖"""
        dependencies = {
            'type': 'python',
            'files': [],
            'packages': []
        }

        # 检查requirements.txt
        requirements_path = os.path.join(workspace_path, 'requirements.txt')
        if os.path.exists(requirements_path):
            dependencies['files'].append('requirements.txt')
            try:
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    dependencies['packages'] = [
                        line.strip() for line in f.readlines()
                        if line.strip() and not line.startswith('#')
                    ]
            except Exception:
                pass

        # 检查setup.py
        setup_path = os.path.join(workspace_path, 'setup.py')
        if os.path.exists(setup_path):
            dependencies['files'].append('setup.py')

        # 检查Pipfile
        pipfile_path = os.path.join(workspace_path, 'Pipfile')
        if os.path.exists(pipfile_path):
            dependencies['files'].append('Pipfile')

        return dependencies

    @staticmethod
    def _detect_java_dependencies(workspace_path: str) -> Dict[str, Any]:
        """检测Java依赖"""
        dependencies = {
            'type': 'java',
            'build_tool': None,
            'files': []
        }

        # 检查Maven
        pom_path = os.path.join(workspace_path, 'pom.xml')
        if os.path.exists(pom_path):
            dependencies['build_tool'] = 'maven'
            dependencies['files'].append('pom.xml')

        # 检查Gradle
        gradle_path = os.path.join(workspace_path, 'build.gradle')
        if os.path.exists(gradle_path):
            dependencies['build_tool'] = 'gradle'
            dependencies['files'].append('build.gradle')

        gradle_kts_path = os.path.join(workspace_path, 'build.gradle.kts')
        if os.path.exists(gradle_kts_path):
            dependencies['build_tool'] = 'gradle'
            dependencies['files'].append('build.gradle.kts')

        return dependencies
