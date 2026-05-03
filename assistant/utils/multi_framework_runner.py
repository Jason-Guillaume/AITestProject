"""
多框架测试执行引擎

支持Python和Java的所有主流测试框架
"""
import importlib.util
import os
import sys
import subprocess
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from assistant.models import UIScriptUpload

logger = logging.getLogger(__name__)


class MultiFrameworkRunner:
    """多框架测试执行器"""

    def __init__(
        self,
        script_instance: UIScriptUpload,
        workspace_path: str,
        execution_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化执行器

        Args:
            script_instance: 脚本实例
            workspace_path: 工作空间路径
            execution_config: 来自前端的执行配置（browser/headless/parallel），用于线性/unittest 无头时是否经启动器注入补丁
        """
        self.script_instance = script_instance
        self.workspace_path = workspace_path
        self.language = script_instance.language
        self.framework = script_instance.framework
        self.execution_config = execution_config or {}

    def build_command(self) -> List[str]:
        """
        根据语言和框架构建执行命令

        Returns:
            命令列表
        """
        if self.language == 'PYTHON':
            return self._build_python_command()
        elif self.language == 'JAVA':
            return self._build_java_command()
        else:
            raise ValueError(f"不支持的语言: {self.language}")

    def _is_linear_script_file(self, file_path: str) -> bool:
        """
        检查文件是否是线性脚本（不包含测试框架）

        Args:
            file_path: 文件路径

        Returns:
            是否是线性脚本
        """
        if not os.path.exists(file_path):
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

                # 检查是否包含自动化库
                has_automation = any(lib in content for lib in [
                    'from selenium', 'import selenium',
                    'from playwright', 'import playwright',
                    'from appium', 'import appium'
                ])

                # 检查是否包含测试框架特征
                has_test_framework = any(pattern in content for pattern in [
                    'class Test', 'def test_', '@pytest',
                    'unittest.TestCase', 'from unittest import',
                    '@Test', 'TestCase'
                ])

                # 如果有自动化库但没有测试框架，则是线性脚本
                return has_automation and not has_test_framework

        except Exception as e:
            logger.error(f"检查文件失败: {str(e)}")
            return False

    def _build_python_command(self) -> List[str]:
        """构建Python测试命令"""
        entry_point = self.script_instance.entry_point or ''

        # 业务上标记为「线性脚本」时一律用解释器直接跑入口文件，不走 pytest。
        # 否则 framework 常为 PYTEST（自动检测默认），若启发式未命中会误走 pytest，
        # 仅 import + 收集用例就可能耗十余到数十秒，用户体感为「很久才弹浏览器」。
        if self.script_instance.script_type == UIScriptUpload.ScriptType.LINEAR and entry_point:
            logger.info("script_type=LINEAR，使用 python -u 直接执行: %s", entry_point)
            return self._build_linear_command(entry_point)

        framework = self.framework

        # 未标记为 LINEAR 时：仍可通过内容识别线性脚本，避免 pytest 开销
        if entry_point:
            entry_path = os.path.join(self.workspace_path, entry_point)
            if self._is_linear_script_file(entry_path):
                logger.info(f"入口点文件 {entry_point} 是线性脚本，将直接运行")
                return self._build_linear_command(entry_point)

        # 根据框架类型构建命令
        if framework == 'PYTEST':
            return self._build_pytest_command(entry_point)
        elif framework == 'UNITTEST':
            return self._build_unittest_command(entry_point)
        elif framework == 'NOSE':
            return self._build_nose_command(entry_point)
        elif framework == 'ROBOT':
            return self._build_robot_command(entry_point)
        elif framework == 'BEHAVE':
            return self._build_behave_command(entry_point)
        elif framework == 'LINEAR' or framework == 'AUTO':
            # 线性脚本或未检测到框架，直接用Python运行
            return self._build_linear_command(entry_point)
        else:
            # 默认尝试直接运行
            logger.warning(f"未知的Python框架: {framework}，尝试直接运行")
            return self._build_linear_command(entry_point)

    def _build_java_command(self) -> List[str]:
        """构建Java测试命令"""
        framework = self.framework
        build_config = self.script_instance.build_config or {}
        build_tool = build_config.get('build_tool', 'maven')

        if framework in ['JUNIT4', 'JUNIT5']:
            return self._build_junit_command(build_tool)
        elif framework == 'TESTNG':
            return self._build_testng_command(build_tool)
        elif framework == 'CUCUMBER':
            return self._build_cucumber_command(build_tool)
        elif framework == 'SPOCK':
            return self._build_spock_command(build_tool)
        else:
            # 默认使用JUnit
            logger.warning(f"未知的Java框架: {framework}，使用JUnit")
            return self._build_junit_command(build_tool)

    def _build_pytest_command(self, entry_point: str) -> List[str]:
        """构建pytest命令"""
        cmd = ['pytest']

        # 详细输出
        cmd.extend(['-v', '-s'])

        # 颜色输出
        cmd.append('--color=yes')

        # 实时输出
        cmd.append('--capture=no')

        # 添加目标路径
        if entry_point:
            target_path = os.path.join(self.workspace_path, entry_point)
            if os.path.exists(target_path):
                cmd.append(target_path)
        else:
            # 默认执行当前目录
            cmd.append('.')

        # 简短的traceback
        cmd.append('--tb=short')

        # JUnit XML报告（pytest 内置）
        report_path = os.path.join(self.workspace_path, 'test-results', 'junit.xml')
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        cmd.extend(['--junitxml', report_path])

        # HTML 报告依赖 pytest-html，未安装时跳过以免整条命令失败
        if importlib.util.find_spec('pytest_html') is not None:
            html_report_path = os.path.join(
                self.workspace_path, 'test-results', 'report.html'
            )
            cmd.extend(['--html', html_report_path, '--self-contained-html'])

        return cmd

    def _build_unittest_command(self, entry_point: str) -> List[str]:
        """
        构建 unittest 命令。

        若入口路径转成「点分模块名」后任一段不是合法 Python 标识符（例如目录名 ``5.2周考题练习``
        会变成 ``5``、``2周考题练习`` 两段，先 import ``5`` 即失败），则改为直接 ``python -u 脚本.py``，
        或目录时用 ``unittest discover -s 目录``。
        """
        if not entry_point:
            return self._wrap_unittest_cmd_for_headless(
                [sys.executable, "-m", "unittest", "discover", "-v"]
            )

        target_path = os.path.normpath(
            os.path.join(self.workspace_path, entry_point.replace("\\", os.sep))
        )

        def _dot_parts(rel: str) -> List[str]:
            mp = rel.replace("/", ".").replace("\\", ".")
            if mp.lower().endswith(".py"):
                mp = mp[:-3]
            return [p for p in mp.split(".") if p]

        parts = _dot_parts(entry_point)
        path_ok = all(p.isidentifier() for p in parts) if parts else False

        if os.path.isfile(target_path) and entry_point.lower().endswith(".py"):
            if not path_ok:
                return self._wrap_unittest_cmd_for_headless(
                    [sys.executable, "-u", target_path]
                )
        elif os.path.isdir(target_path) and not path_ok:
            return self._wrap_unittest_cmd_for_headless(
                [sys.executable, "-m", "unittest", "discover", "-s", target_path, "-v"]
            )

        cmd = [sys.executable, "-m", "unittest"]
        module_path = entry_point.replace("/", ".").replace("\\", ".")
        if module_path.lower().endswith(".py"):
            module_path = module_path[:-3]
        if module_path:
            cmd.append(module_path)
        else:
            cmd.append("discover")
        cmd.append("-v")
        return self._wrap_unittest_cmd_for_headless(cmd)

    def _wrap_unittest_cmd_for_headless(self, cmd: List[str]) -> List[str]:
        """
        无头时在同一进程内先安装 browser_env_patch，再跑 unittest。
        HEADLESS_MODE 仅由 script_runner 注入时，若不经过此处，Selenium 仍为有头。
        """
        if not self.execution_config.get("headless"):
            return cmd

        runtime_dir = Path(__file__).resolve().parents[1] / "runtime"
        launcher_entry = runtime_dir / "launch_ui_entry.py"
        launcher_unittest = runtime_dir / "launch_ui_unittest.py"

        # python -u <script.py>  → 与线性脚本相同，经 launch_ui_entry 再 runpy
        if (
            len(cmd) >= 3
            and cmd[1] == "-u"
            and str(cmd[2]).lower().endswith(".py")
            and "launch_ui_entry" not in str(cmd[2])
            and launcher_entry.is_file()
        ):
            return [cmd[0], "-u", str(launcher_entry), cmd[2]] + cmd[3:]

        # python -m unittest ...
        if (
            len(cmd) >= 3
            and cmd[1] == "-m"
            and cmd[2] == "unittest"
            and launcher_unittest.is_file()
        ):
            return [cmd[0], "-u", str(launcher_unittest)] + cmd[3:]

        if self.execution_config.get("headless"):
            logger.warning(
                "无头 unittest 需要 launch_ui_entry.py / launch_ui_unittest.py，未找到则无法自动注入无头参数"
            )
        return cmd

    def _build_nose_command(self, entry_point: str) -> List[str]:
        """构建nose命令"""
        cmd = ['nosetests']

        # 详细输出
        cmd.append('-v')

        # 添加目标路径
        if entry_point:
            target_path = os.path.join(self.workspace_path, entry_point)
            if os.path.exists(target_path):
                cmd.append(target_path)

        # XML报告
        report_path = os.path.join(self.workspace_path, 'test-results', 'nosetests.xml')
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        cmd.extend(['--with-xunit', f'--xunit-file={report_path}'])

        return cmd

    def _build_robot_command(self, entry_point: str) -> List[str]:
        """构建Robot Framework命令"""
        cmd = ['robot']

        # 输出目录
        output_dir = os.path.join(self.workspace_path, 'test-results')
        os.makedirs(output_dir, exist_ok=True)
        cmd.extend(['--outputdir', output_dir])

        # 添加目标路径
        if entry_point:
            target_path = os.path.join(self.workspace_path, entry_point)
            if os.path.exists(target_path):
                cmd.append(target_path)
        else:
            # 默认执行所有.robot文件
            cmd.append('.')

        return cmd

    def _build_behave_command(self, entry_point: str) -> List[str]:
        """构建Behave命令"""
        cmd = ['behave']

        # 详细输出
        cmd.append('--verbose')

        # JUnit XML报告
        report_path = os.path.join(self.workspace_path, 'test-results', 'behave.xml')
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        cmd.extend(['--junit', '--junit-directory', os.path.dirname(report_path)])

        # 添加目标路径
        if entry_point:
            target_path = os.path.join(self.workspace_path, entry_point)
            if os.path.exists(target_path):
                cmd.append(target_path)

        return cmd

    def _build_linear_command(self, entry_point: str) -> List[str]:
        """构建线性脚本命令（直接用Python运行；无头时可经启动器注入 Selenium 补丁）"""
        if not entry_point:
            raise ValueError("线性脚本必须指定入口点文件")
        target_path = os.path.join(self.workspace_path, entry_point)
        if not os.path.exists(target_path):
            raise ValueError(f"入口点文件不存在: {target_path}")

        cmd = [sys.executable, "-u"]
        if self.execution_config.get("headless"):
            launcher = Path(__file__).resolve().parents[1] / "runtime" / "launch_ui_entry.py"
            if launcher.is_file():
                cmd.append(str(launcher))
            else:
                logger.warning("launch_ui_entry.py 不存在，无头自动注入不可用，退回直接执行脚本")
        cmd.append(target_path)
        return cmd

    def _build_junit_command(self, build_tool: str) -> List[str]:
        """构建JUnit命令"""
        if build_tool == 'maven':
            return ['mvn', 'test', '-Dmaven.test.failure.ignore=true']
        elif build_tool == 'gradle':
            return ['gradle', 'test', '--continue']
        else:
            # 默认使用Maven
            return ['mvn', 'test']

    def _build_testng_command(self, build_tool: str) -> List[str]:
        """构建TestNG命令"""
        if build_tool == 'maven':
            cmd = ['mvn', 'test']

            # 如果有testng.xml，指定配置文件
            testng_xml = os.path.join(self.workspace_path, 'testng.xml')
            if os.path.exists(testng_xml):
                cmd.append(f'-DsuiteXmlFile=testng.xml')

            return cmd
        elif build_tool == 'gradle':
            return ['gradle', 'test', '--continue']
        else:
            return ['mvn', 'test']

    def _build_cucumber_command(self, build_tool: str) -> List[str]:
        """构建Cucumber命令"""
        if build_tool == 'maven':
            return ['mvn', 'test', '-Dcucumber.options=--plugin json:target/cucumber.json']
        elif build_tool == 'gradle':
            return ['gradle', 'test', '--continue']
        else:
            return ['mvn', 'test']

    def _build_spock_command(self, build_tool: str) -> List[str]:
        """构建Spock命令"""
        if build_tool == 'maven':
            return ['mvn', 'test']
        elif build_tool == 'gradle':
            return ['gradle', 'test', '--continue']
        else:
            return ['mvn', 'test']

    def get_environment(self) -> Dict[str, str]:
        """
        获取执行环境变量

        Returns:
            环境变量字典
        """
        env = os.environ.copy()

        if self.language == 'PYTHON':
            # 设置PYTHONPATH
            pythonpath = env.get('PYTHONPATH', '')
            if pythonpath:
                env['PYTHONPATH'] = f"{self.workspace_path}{os.pathsep}{pythonpath}"
            else:
                env['PYTHONPATH'] = self.workspace_path

            # 禁用Python字节码生成
            env['PYTHONDONTWRITEBYTECODE'] = '1'

        elif self.language == 'JAVA':
            # 设置JAVA_HOME（如果未设置）
            if 'JAVA_HOME' not in env:
                # 尝试自动检测
                java_home = self._detect_java_home()
                if java_home:
                    env['JAVA_HOME'] = java_home

            # 设置Maven选项
            env['MAVEN_OPTS'] = env.get('MAVEN_OPTS', '-Xmx1024m')

        # 通用环境变量
        env['UI_SCRIPT_WORKSPACE'] = self.workspace_path

        return env

    def _detect_java_home(self) -> Optional[str]:
        """检测JAVA_HOME"""
        try:
            result = subprocess.run(
                ['java', '-XshowSettings:properties', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )

            for line in result.stderr.split('\n'):
                if 'java.home' in line:
                    java_home = line.split('=')[1].strip()
                    return java_home
        except Exception:
            pass

        return None

    def install_dependencies(self) -> bool:
        """
        安装项目依赖

        Returns:
            是否成功
        """
        try:
            if self.language == 'PYTHON':
                return self._install_python_dependencies()
            elif self.language == 'JAVA':
                return self._install_java_dependencies()
            else:
                return True
        except Exception as e:
            logger.error(f"安装依赖失败: {str(e)}", exc_info=True)
            return False

    def _install_python_dependencies(self) -> bool:
        """安装Python依赖"""
        requirements_path = os.path.join(self.workspace_path, 'requirements.txt')

        if not os.path.exists(requirements_path):
            logger.info("未找到requirements.txt，跳过依赖安装")
            return True

        try:
            logger.info("开始安装Python依赖...")
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', requirements_path],
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                logger.info("Python依赖安装成功")
                return True
            else:
                logger.error(f"Python依赖安装失败: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Python依赖安装超时")
            return False
        except Exception as e:
            logger.error(f"Python依赖安装异常: {str(e)}", exc_info=True)
            return False

    def _install_java_dependencies(self) -> bool:
        """安装Java依赖"""
        build_config = self.script_instance.build_config or {}
        build_tool = build_config.get('build_tool', 'maven')

        try:
            if build_tool == 'maven':
                logger.info("开始Maven依赖下载...")
                result = subprocess.run(
                    ['mvn', 'dependency:resolve'],
                    cwd=self.workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
            elif build_tool == 'gradle':
                logger.info("开始Gradle依赖下载...")
                result = subprocess.run(
                    ['gradle', 'dependencies'],
                    cwd=self.workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
            else:
                logger.warning(f"未知的构建工具: {build_tool}")
                return True

            if result.returncode == 0:
                logger.info("Java依赖安装成功")
                return True
            else:
                logger.error(f"Java依赖安装失败: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Java依赖安装超时")
            return False
        except Exception as e:
            logger.error(f"Java依赖安装异常: {str(e)}", exc_info=True)
            return False
