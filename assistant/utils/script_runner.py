"""
UI自动化脚本执行引擎

提供脚本执行、日志收集、状态管理等功能
"""
import os
import sys
import subprocess
import threading
import time
import json
import logging
import platform
import signal
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

import redis
from django.conf import settings
from django.utils import timezone

from assistant.models import UIScriptUpload

logger = logging.getLogger(__name__)


def _inject_local_webdriver_for_fast_start(
    env: Dict[str, Any],
    browser: str,
    base_dir: Path,
) -> str:
    """
    优先使用项目内 drivers/ 下的本地驱动，注入 Selenium Manager 识别的 SE_*，并设 SE_OFFLINE=true，
    避免冷启动时联网解析/下载驱动，便于尽快进入浏览器与脚本输出。

    若进程环境或 env 中已存在对应 SE_*，则不覆盖。
    """
    b = (browser or "chrome").strip().lower()
    mapping = {
        "chrome": ("SE_CHROMEDRIVER", ("chromedriver.exe", "chromedriver")),
        "edge": ("SE_EDGEDRIVER", ("msedgedriver.exe", "msedgedriver")),
        "firefox": ("SE_GECKODRIVER", ("geckodriver.exe", "geckodriver")),
    }
    if b not in mapping:
        b = "chrome"
    se_key, names = mapping[b]
    existing = (env.get(se_key) or os.environ.get(se_key) or "").strip()
    if existing:
        return f"驱动策略: 沿用已有 {se_key}={existing}（不覆盖）。"

    drivers_dir = base_dir / "drivers"
    for name in names:
        candidate = drivers_dir / name
        if candidate.is_file():
            env[se_key] = str(candidate.resolve())
            env["SE_OFFLINE"] = "true"
            return (
                f"驱动策略: 已自动使用本地 {candidate}，并设置 SE_OFFLINE=true（不联网拉取驱动）；"
                f"请保证该驱动与已安装浏览器主版本匹配。"
            )

    return (
        "驱动策略: 未在 {drivers_dir} 下发现 {names}，且未设置 {se_key}；"
        "将交由 Selenium Manager（可能联网、首次较慢）。可将驱动放入 drivers/ 目录以加速。"
    ).format(drivers_dir=drivers_dir, names="/".join(names), se_key=se_key)


class ScriptExecutionError(Exception):
    """脚本执行异常"""
    pass


def _try_parse_pytest_junit_stats(workspace_path: str) -> Optional[Dict[str, int]]:
    """若存在 pytest 生成的 junit.xml，解析用例统计供前端展示。"""
    from xml.etree import ElementTree as ET

    path = os.path.join(workspace_path, "test-results", "junit.xml")
    if not os.path.isfile(path):
        return None
    try:
        root = ET.parse(path).getroot()
        suites = root.findall("testsuite")
        if not suites and root.tag == "testsuite":
            suites = [root]
        if not suites:
            return None
        tests = failures = errors = skipped = 0
        for ts in suites:
            tests += int(ts.attrib.get("tests", 0) or 0)
            failures += int(ts.attrib.get("failures", 0) or 0)
            errors += int(ts.attrib.get("errors", 0) or 0)
            skipped += int(ts.attrib.get("skipped", 0) or 0)
        passed = tests - failures - errors - skipped
        return {
            "total": tests,
            "passed": max(0, passed),
            "failed": failures + errors,
            "skipped": skipped,
        }
    except Exception:
        return None


def _linear_fallback_stats(success: bool) -> Dict[str, int]:
    """线性脚本等无 junit 时：按单次进程退化为 1 条用例统计。"""
    return {
        "total": 1,
        "passed": 1 if success else 0,
        "failed": 0 if success else 1,
        "skipped": 0,
    }


def _cancelled_stats() -> Dict[str, int]:
    """用户停止：记为 1 条跳过，便于前端与 junit 语义区分。"""
    return {"total": 1, "passed": 0, "failed": 0, "skipped": 1}


def _kill_process_tree(pid: int) -> None:
    """终止子进程及其子进程（如 chromedriver / 浏览器）。"""
    if pid <= 0:
        return
    try:
        if platform.system() == "Windows":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                text=True,
                timeout=45,
            )
        else:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                return
            time.sleep(0.4)
            try:
                os.kill(pid, 0)
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    except Exception:
        logger.warning("终止 UI 脚本子进程失败 pid=%s", pid, exc_info=True)


class ScriptRunner:
    """UI脚本执行器"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        初始化执行器

        Args:
            redis_client: Redis客户端实例，如果为None则创建新实例
        """
        if redis_client is None:
            _conn = int(getattr(settings, "REDIS_SOCKET_CONNECT_TIMEOUT", 3))
            _sock = int(getattr(settings, "REDIS_SOCKET_TIMEOUT", 20))
            self.redis_client = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True,
                socket_connect_timeout=_conn,
                socket_timeout=_sock,
            )
        else:
            self.redis_client = redis_client

    def _ensure_redis(self) -> None:
        """执行前必须能连上 Redis，否则日志全丢且界面长期空白。"""
        try:
            self.redis_client.ping()
        except Exception as e:
            host = getattr(settings, "REDIS_HOST", "localhost")
            port = getattr(settings, "REDIS_PORT", 6379)
            db = getattr(settings, "REDIS_DB", 0)
            raise ScriptExecutionError(
                f"无法连接 Redis（{host}:{port} db={db}）：{e}。"
                f"引擎日志依赖 Redis；请启动与 Django 配置一致的 Redis（见 REDIS_HOST/REDIS_PORT），"
                f"否则界面不会出现任何引擎输出。"
            ) from e

    def _get_log_key(self, execution_id: str) -> str:
        """
        获取Redis日志键名

        Args:
            execution_id: 执行ID

        Returns:
            Redis键名
        """
        return f"ui_script_execution:{execution_id}:logs"

    def _get_status_key(self, execution_id: str) -> str:
        """
        获取Redis状态键名

        Args:
            execution_id: 执行ID

        Returns:
            Redis键名
        """
        return f"ui_script_execution:{execution_id}:status"

    def _get_pid_key(self, execution_id: str) -> str:
        return f"ui_script_execution:{execution_id}:pid"

    def _get_cancel_key(self, execution_id: str) -> str:
        return f"ui_script_execution:{execution_id}:cancel"

    def _register_subprocess_pid(self, execution_id: str, pid: int) -> None:
        try:
            self.redis_client.set(self._get_pid_key(execution_id), str(pid), ex=86400)
        except Exception as e:
            logger.warning("写入子进程 PID 到 Redis 失败: %s", e)

    def _unregister_subprocess_pid(self, execution_id: str) -> None:
        try:
            self.redis_client.delete(self._get_pid_key(execution_id))
        except Exception as e:
            logger.debug("清理 PID 键失败: %s", e)

    def _is_user_cancel_requested(self, execution_id: str) -> bool:
        try:
            v = self.redis_client.get(self._get_cancel_key(execution_id))
            return bool(v and str(v).strip() in ("1", "true", "yes", "on"))
        except Exception:
            return False

    def request_stop(self, execution_id: str) -> Dict[str, Any]:
        """
        用户停止：写入 Redis 标记并尽量终止子进程树（与 execute 是否同进程无关）。
        """
        self._ensure_redis()
        try:
            self.redis_client.set(self._get_cancel_key(execution_id), "1", ex=86400)
        except Exception as e:
            logger.error("写入停止标记失败: %s", e, exc_info=True)
            return {"cancel_requested": False, "killed": False, "error": str(e)}
        killed = False
        try:
            raw = self.redis_client.get(self._get_pid_key(execution_id))
            if raw:
                pid = int(str(raw).strip())
                _kill_process_tree(pid)
                killed = True
        except (TypeError, ValueError) as e:
            logger.debug("解析 PID 失败: %s", e)
        except Exception:
            logger.warning("按 PID 终止子进程时异常", exc_info=True)
        return {"cancel_requested": True, "killed": killed}

    def _write_log(self, execution_id: str, log_type: str, message: str):
        """
        写入日志到Redis

        Args:
            execution_id: 执行ID
            log_type: 日志类型（stdout/stderr/system）
            message: 日志消息
        """
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': log_type,
                'message': message.rstrip('\n')
            }

            log_key = self._get_log_key(execution_id)
            # 每条日志单独 EXPIRE 会产生大量 Redis 往返；同一 execution 只对 key 设置一次 TTL
            if not hasattr(self, "_log_keys_expired"):
                self._log_keys_expired = set()
            pipe = self.redis_client.pipeline()
            pipe.rpush(log_key, json.dumps(log_entry))
            if log_key not in self._log_keys_expired:
                pipe.expire(log_key, 86400)
                self._log_keys_expired.add(log_key)
            pipe.execute()

        except Exception as e:
            logger.error(f"写入日志到Redis失败: {str(e)}", exc_info=True)

    def _update_status(self, execution_id: str, status: str, **kwargs):
        """
        更新执行状态到Redis

        Args:
            execution_id: 执行ID
            status: 状态（running/success/failed/timeout）
            **kwargs: 其他状态信息
        """
        try:
            status_data = {
                'status': status,
                'updated_at': datetime.now().isoformat(),
                **kwargs
            }

            status_key = self._get_status_key(execution_id)
            self.redis_client.set(status_key, json.dumps(status_data), ex=86400)

        except Exception as e:
            logger.error(f"更新状态到Redis失败: {str(e)}", exc_info=True)

    def _build_environment(self, workspace_path: str) -> Dict[str, str]:
        """
        构建执行环境变量

        Args:
            workspace_path: 工作空间路径

        Returns:
            环境变量字典
        """
        env = os.environ.copy()

        # 将workspace路径添加到PYTHONPATH
        pythonpath = env.get('PYTHONPATH', '')
        if pythonpath:
            env['PYTHONPATH'] = f"{workspace_path}{os.pathsep}{pythonpath}"
        else:
            env['PYTHONPATH'] = workspace_path

        # 设置其他必要的环境变量
        env['UI_SCRIPT_WORKSPACE'] = workspace_path

        return env

    def _build_pytest_command(
        self,
        script_instance: UIScriptUpload,
        workspace_path: str
    ) -> List[str]:
        """
        构建pytest执行命令

        Args:
            script_instance: 脚本实例
            workspace_path: 工作空间路径

        Returns:
            命令列表
        """
        # 基础命令
        cmd = ['pytest']

        # 添加详细输出
        cmd.extend(['-v', '-s'])

        # 添加颜色输出（如果支持）
        cmd.append('--color=yes')

        # 添加实时输出
        cmd.append('--capture=no')

        # 构建执行目标路径
        entry_point = script_instance.entry_point
        target_path = os.path.join(workspace_path, entry_point)

        if not os.path.exists(target_path):
            raise ScriptExecutionError(f"入口点文件不存在: {target_path}")

        # 根据脚本类型决定执行方式
        if script_instance.script_type == UIScriptUpload.ScriptType.LINEAR:
            # LINEAR模式：执行单个文件
            cmd.append(target_path)
        else:
            # POM模式：执行目录或文件
            if os.path.isdir(target_path):
                cmd.append(target_path)
            else:
                cmd.append(target_path)

        # 添加pytest输出格式
        cmd.extend(['--tb=short'])

        # 添加超时设置（可选）
        timeout = getattr(settings, 'UI_SCRIPT_TIMEOUT', 3600)  # 默认1小时
        cmd.extend(['--timeout', str(timeout)])

        return cmd

    def _stream_output(
        self,
        process: subprocess.Popen,
        execution_id: str,
        timeout: Optional[int] = None
    ) -> tuple:
        """
        流式读取进程输出

        Args:
            process: 子进程对象
            execution_id: 执行ID
            timeout: 超时时间（秒）

        Returns:
            (return_code, stdout_lines, stderr_lines)
        """
        stdout_lines = []
        stderr_lines = []

        def read_stdout():
            """读取标准输出"""
            try:
                for line in iter(process.stdout.readline, ''):
                    if not line:
                        break
                    stdout_lines.append(line)
                    self._write_log(execution_id, 'stdout', line)
            except Exception as e:
                logger.error(f"读取stdout失败: {str(e)}", exc_info=True)

        def read_stderr():
            """读取标准错误"""
            try:
                for line in iter(process.stderr.readline, ''):
                    if not line:
                        break
                    stderr_lines.append(line)
                    self._write_log(execution_id, 'stderr', line)
            except Exception as e:
                logger.error(f"读取stderr失败: {str(e)}", exc_info=True)

        # 创建读取线程
        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)

        stdout_thread.start()
        stderr_thread.start()

        def _heartbeat() -> None:
            """长时间无 stdout/stderr 时写一条系统日志，避免前端误以为卡死。"""
            try:
                first = True
                while process.poll() is None:
                    delay = 35.0 if first else 45.0
                    first = False
                    time.sleep(delay)
                    if process.poll() is not None:
                        break
                    self._write_log(
                        execution_id,
                        'system',
                        '子进程仍在运行，尚未产生新的控制台输出：常见于 Chrome/Chromedriver 首次初始化、'
                        'unittest 收集/导入用例、或脚本在 setUp/首次打开页面阶段未 print（无头模式同样可能长时间无输出）。'
                        ' 可在运行 Django 的机器上查看 chromedriver.exe、chrome 及网络活动。',
                    )
            except Exception:
                logger.debug('UI 执行 heartbeat 结束', exc_info=True)

        threading.Thread(target=_heartbeat, daemon=True).start()

        # 等待进程完成
        try:
            return_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.warning(f"脚本执行超时 (execution_id={execution_id})")
            process.kill()
            return_code = -1
            self._write_log(execution_id, 'system', '执行超时，进程已被终止')

        # 等待读取线程完成
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)

        return return_code, stdout_lines, stderr_lines

    def execute_ui_script(
        self,
        script_upload_instance_id: int,
        execution_id: Optional[str] = None,
        timeout: Optional[int] = None,
        execution_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行UI自动化脚本

        Args:
            script_upload_instance_id: UIScriptUpload实例ID
            execution_id: 执行ID（可选，用于日志追踪）
            timeout: 超时时间（秒），默认使用配置值
            execution_config: 执行配置（浏览器、无头模式等）

        Returns:
            执行结果字典，包含：
            - success: 是否成功
            - execution_id: 执行ID
            - return_code: 返回码
            - duration: 执行时长（秒）
            - error: 错误信息（如果有）

        Raises:
            ScriptExecutionError: 脚本执行失败
        """
        # 生成执行ID
        if execution_id is None:
            execution_id = f"{script_upload_instance_id}_{int(time.time())}"

        # 默认执行配置
        if execution_config is None:
            execution_config = {}

        start_time = time.time()

        # 初始化结果
        result = {
            'success': False,
            'execution_id': execution_id,
            'return_code': None,
            'duration': 0,
            'error': None
        }

        try:
            self._ensure_redis()
            # 1. 查询数据库获取脚本实例
            self._write_log(execution_id, 'system', f'开始执行脚本 (ID: {script_upload_instance_id})')

            try:
                script_instance = UIScriptUpload.objects.get(
                    id=script_upload_instance_id,
                    is_active=True
                )
            except UIScriptUpload.DoesNotExist:
                raise ScriptExecutionError(
                    f"脚本不存在或已禁用 (ID: {script_upload_instance_id})"
                )

            self._write_log(
                execution_id,
                'system',
                f'脚本信息: {script_instance.name} ({script_instance.get_script_type_display()})'
            )

            # 2. 获取工作空间路径
            workspace_path = script_instance.workspace_path
            if not workspace_path or not os.path.exists(workspace_path):
                raise ScriptExecutionError(
                    f"工作空间路径不存在: {workspace_path}"
                )

            workspace_path = os.path.abspath(workspace_path)
            self._write_log(execution_id, 'system', f'工作空间: {workspace_path}')

            # 3. 构建环境变量
            from assistant.utils.multi_framework_runner import MultiFrameworkRunner
            from django.conf import settings as dj_settings

            cfg = execution_config or {}
            multi_runner = MultiFrameworkRunner(script_instance, workspace_path, execution_config=cfg)
            cmd = multi_runner.build_command()
            env = multi_runner.get_environment()

            # 4. 注入浏览器配置到环境变量（须在 build_command 之后写入，供子进程与补丁读取）
            # execution_config 已规范为 dict，勿用 if execution_config（空 {} 会跳过）
            browser = execution_config.get('browser', 'chrome')
            headless = execution_config.get('headless', False)
            parallel = execution_config.get('parallel', 1)
            env['BROWSER_TYPE'] = browser
            env['HEADLESS_MODE'] = str(headless)
            env['PARALLEL_COUNT'] = str(parallel)

            _wpid = (execution_config or {}).get("workspace_project_id")
            _tenv = (execution_config or {}).get("test_environment_id")
            if _wpid is not None and str(_wpid).strip():
                env["AITESTA_WORKSPACE_PROJECT_ID"] = str(_wpid).strip()
            if _tenv is not None and str(_tenv).strip():
                env["AITESTA_TEST_ENVIRONMENT_ID"] = str(_tenv).strip()
            if (_wpid and str(_wpid).strip()) or (_tenv and str(_tenv).strip()):
                self._write_log(
                    execution_id,
                    "system",
                    "工作台上下文: AITESTA_WORKSPACE_PROJECT_ID="
                    f"{str(_wpid).strip() if _wpid is not None and str(_wpid).strip() else '—'} "
                    "AITESTA_TEST_ENVIRONMENT_ID="
                    f"{str(_tenv).strip() if _tenv is not None and str(_tenv).strip() else '—'}",
                )

            self._write_log(execution_id, 'system', f'浏览器配置: {browser} (无头模式: {headless})')

            driver_hint = _inject_local_webdriver_for_fast_start(
                env, browser, Path(dj_settings.BASE_DIR)
            )
            self._write_log(execution_id, 'system', driver_hint)

            # 保证子进程可 import assistant（线性启动器、pytest 插件）；
            # 同时把「入口脚本所在目录」加入 PYTHONPATH，避免入口在 workspace 子目录时
            # （如 …/12/5.2周考题练习/run.py）与同级包 TestCase/pages 无法被 from TestCase import … 解析。
            _root = str(dj_settings.BASE_DIR)
            _pp = (env.get('PYTHONPATH') or '').strip()
            path_parts: List[str] = [_root]
            ep = (getattr(script_instance, 'entry_point', None) or '').strip()
            if ep:
                entry_abs = os.path.normpath(
                    os.path.join(workspace_path, ep.replace('\\', os.sep))
                )
                script_parent = os.path.dirname(entry_abs)
                if script_parent and os.path.isdir(script_parent):
                    path_parts.append(script_parent)
            if _pp:
                for seg in _pp.split(os.pathsep):
                    seg = seg.strip()
                    if seg and seg not in path_parts:
                        path_parts.append(seg)
            env['PYTHONPATH'] = os.pathsep.join(path_parts)

            # pytest：无头时尽早加载补丁（POM 等）
            if execution_config.get('headless'):
                plug = 'assistant.runtime.pytest_headless_plugin'
                existing = (env.get('PYTEST_PLUGINS') or '').strip()
                if plug not in existing:
                    env['PYTEST_PLUGINS'] = f'{plug},{existing}' if existing else plug

            # 子进程尽早刷 stdout/stderr，避免脚本 print 长时间留在缓冲里导致前端「无日志」
            env.setdefault('PYTHONUNBUFFERED', '1')
            # Selenium Manager 会读取 SE_CHROMEDRIVER / SE_EDGEDRIVER / SE_GECKODRIVER / SE_OFFLINE（见 .env.example）。
            # env 来自 os.environ.copy()，勿在此清空上述变量；驱动应放本机磁盘，勿存 Redis。

            self._write_log(execution_id, 'system', f'执行命令: {" ".join(cmd)}')
            self._write_log(execution_id, 'system', f'测试框架: {script_instance.framework}')
            self._write_log(execution_id, 'system', f'脚本语言: {script_instance.language}')
            self._write_log(execution_id, 'system', f'PYTHONPATH: {env.get("PYTHONPATH", "N/A")}')

            # 5. 更新状态为运行中
            self._update_status(
                execution_id,
                'running',
                script_id=script_upload_instance_id,
                script_name=script_instance.name,
                started_at=datetime.now().isoformat()
            )

            # 用户在引擎构建完命令后、拉起浏览器前点击停止
            if self._is_user_cancel_requested(execution_id):
                duration = time.time() - start_time
                self._write_log(execution_id, 'system', '执行在启动子进程前已由用户停止。')
                stats = _cancelled_stats()
                self._update_status(
                    execution_id,
                    'cancelled',
                    script_id=script_upload_instance_id,
                    script_name=script_instance.name,
                    return_code=None,
                    duration=duration,
                    completed_at=datetime.now().isoformat(),
                    result_stats=stats,
                )
                try:
                    self.redis_client.delete(self._get_cancel_key(execution_id))
                except Exception:
                    pass
                result.update(
                    {
                        'cancelled': True,
                        'success': False,
                        'duration': duration,
                        'return_code': None,
                    }
                )
                return result

            # 6. 执行脚本
            self._write_log(execution_id, 'system', '=' * 60)
            self._write_log(execution_id, 'system', '开始执行测试')
            self._write_log(execution_id, 'system', '=' * 60)

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=workspace_path,
                env=env,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            self._register_subprocess_pid(execution_id, process.pid)
            self._write_log(
                execution_id,
                "system",
                f"子进程已启动 (PID={process.pid})。Selenium 首次拉起 Chrome/Chromedriver、unittest 收集用例、"
                "或脚本在 setUp/打开首屏前未 print 时，常出现数十秒至数分钟几乎无标准输出，无头与有头均可能发生，属正常现象。"
                " 若超过数分钟仍无下文，请在 Django 所在机器查看 CPU、chromedriver、chrome 与网络。",
            )

            if timeout is None:
                timeout = getattr(settings, 'UI_SCRIPT_TIMEOUT', 3600)

            try:
                return_code, stdout_lines, stderr_lines = self._stream_output(
                    process,
                    execution_id,
                    timeout
                )
            finally:
                self._unregister_subprocess_pid(execution_id)

            duration = time.time() - start_time

            if self._is_user_cancel_requested(execution_id):
                self._write_log(execution_id, 'system', '=' * 60)
                self._write_log(
                    execution_id,
                    'system',
                    f'执行已由用户停止（返回码: {return_code}）',
                )
                self._write_log(execution_id, 'system', f'执行时长: {duration:.2f}秒')
                self._write_log(execution_id, 'system', '=' * 60)
                stats = _cancelled_stats()
                self._update_status(
                    execution_id,
                    'cancelled',
                    script_id=script_upload_instance_id,
                    script_name=script_instance.name,
                    return_code=return_code,
                    duration=duration,
                    completed_at=datetime.now().isoformat(),
                    result_stats=stats,
                )
                try:
                    self.redis_client.delete(self._get_cancel_key(execution_id))
                except Exception:
                    pass
                result.update(
                    {
                        'cancelled': True,
                        'success': False,
                        'return_code': return_code,
                        'duration': duration,
                    }
                )
                return result

            # 7. 记录执行结果（正常结束）
            self._write_log(execution_id, 'system', '=' * 60)
            self._write_log(execution_id, 'system', f'执行完成 (返回码: {return_code})')
            self._write_log(execution_id, 'system', f'执行时长: {duration:.2f}秒')
            self._write_log(execution_id, 'system', '=' * 60)

            success = return_code == 0
            stats = _try_parse_pytest_junit_stats(workspace_path)
            if stats is None:
                stats = _linear_fallback_stats(success)

            self._update_status(
                execution_id,
                'success' if success else 'failed',
                script_id=script_upload_instance_id,
                script_name=script_instance.name,
                return_code=return_code,
                duration=duration,
                completed_at=datetime.now().isoformat(),
                result_stats=stats,
            )

            result.update({
                'success': success,
                'return_code': return_code,
                'duration': duration
            })

            if not success:
                result['error'] = f'脚本执行失败 (返回码: {return_code})'

            return result

        except ScriptExecutionError as e:
            # 脚本执行异常
            error_msg = str(e)
            logger.error(f"脚本执行失败: {error_msg}", exc_info=True)

            try:
                self._write_log(execution_id, 'system', f'错误: {error_msg}')
                self._update_status(
                    execution_id,
                    'failed',
                    error=error_msg,
                    duration=time.time() - start_time,
                )
            except Exception:
                logger.error("Redis 不可用，无法在 Redis 中记录失败原因", exc_info=True)

            result['error'] = error_msg
            result['duration'] = time.time() - start_time

            return result

        except Exception as e:
            # 未预期的异常
            error_msg = f"执行过程中发生异常: {str(e)}"
            logger.error(error_msg, exc_info=True)

            try:
                self._write_log(execution_id, 'system', f'系统错误: {error_msg}')
                self._update_status(
                    execution_id,
                    'failed',
                    error=error_msg,
                    duration=time.time() - start_time,
                )
            except Exception:
                logger.error("Redis 不可用，无法在 Redis 中记录系统错误", exc_info=True)

            result['error'] = error_msg
            result['duration'] = time.time() - start_time

            return result

    def get_execution_logs(
        self,
        execution_id: str,
        start: int = 0,
        end: int = -1
    ) -> List[Dict[str, Any]]:
        """
        获取执行日志

        Args:
            execution_id: 执行ID
            start: 起始索引
            end: 结束索引（-1表示到末尾）

        Returns:
            日志列表
        """
        try:
            log_key = self._get_log_key(execution_id)
            logs = self.redis_client.lrange(log_key, start, end)

            return [json.loads(log) for log in logs]

        except Exception as e:
            logger.error(f"获取执行日志失败: {str(e)}", exc_info=True)
            return []

    def get_execution_logs_tail(
        self,
        execution_id: str,
        tail: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        仅取 Redis 中最近 tail 条日志，避免数万行一次性载入内存。
        """
        try:
            log_key = self._get_log_key(execution_id)
            n = int(self.redis_client.llen(log_key) or 0)
            if n <= 0:
                return []
            tail = max(1, min(int(tail), 5000))
            start = max(0, n - tail)
            logs = self.redis_client.lrange(log_key, start, -1)
            return [json.loads(log) for log in logs]
        except Exception as e:
            logger.error(f"获取执行日志尾部失败: {str(e)}", exc_info=True)
            return []

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取执行状态

        Args:
            execution_id: 执行ID

        Returns:
            状态字典，如果不存在返回None
        """
        try:
            status_key = self._get_status_key(execution_id)
            status_data = self.redis_client.get(status_key)

            if status_data:
                return json.loads(status_data)

            return None

        except Exception as e:
            logger.error(f"获取执行状态失败: {str(e)}", exc_info=True)
            return None

    def clear_execution_data(self, execution_id: str):
        """
        清理执行数据

        Args:
            execution_id: 执行ID
        """
        try:
            log_key = self._get_log_key(execution_id)
            status_key = self._get_status_key(execution_id)

            self.redis_client.delete(
                log_key,
                status_key,
                self._get_pid_key(execution_id),
                self._get_cancel_key(execution_id),
            )

            logger.info(f"已清理执行数据: {execution_id}")

        except Exception as e:
            logger.error(f"清理执行数据失败: {str(e)}", exc_info=True)


# 便捷函数
def execute_ui_script(
    script_upload_instance_id: int,
    execution_id: Optional[str] = None,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    执行UI自动化脚本（便捷函数）

    Args:
        script_upload_instance_id: UIScriptUpload实例ID
        execution_id: 执行ID（可选）
        timeout: 超时时间（秒）

    Returns:
        执行结果字典
    """
    runner = ScriptRunner()
    return runner.execute_ui_script(
        script_upload_instance_id,
        execution_id,
        timeout
    )
