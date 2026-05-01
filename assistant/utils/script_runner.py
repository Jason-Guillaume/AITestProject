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
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

import redis
from django.conf import settings
from django.utils import timezone

from assistant.models import UIScriptUpload

logger = logging.getLogger(__name__)


class ScriptExecutionError(Exception):
    """脚本执行异常"""
    pass


class ScriptRunner:
    """UI脚本执行器"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        初始化执行器

        Args:
            redis_client: Redis客户端实例，如果为None则创建新实例
        """
        if redis_client is None:
            self.redis_client = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True
            )
        else:
            self.redis_client = redis_client

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
            self.redis_client.rpush(log_key, json.dumps(log_entry))

            # 设置过期时间（24小时）
            self.redis_client.expire(log_key, 86400)

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
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        执行UI自动化脚本

        Args:
            script_upload_instance_id: UIScriptUpload实例ID
            execution_id: 执行ID（可选，用于日志追踪）
            timeout: 超时时间（秒），默认使用配置值

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
            env = self._build_environment(workspace_path)
            self._write_log(execution_id, 'system', f'PYTHONPATH: {env["PYTHONPATH"]}')

            # 4. 构建pytest命令
            cmd = self._build_pytest_command(script_instance, workspace_path)
            self._write_log(execution_id, 'system', f'执行命令: {" ".join(cmd)}')

            # 5. 更新状态为运行中
            self._update_status(
                execution_id,
                'running',
                script_id=script_upload_instance_id,
                script_name=script_instance.name,
                started_at=datetime.now().isoformat()
            )

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

            # 7. 流式读取输出
            if timeout is None:
                timeout = getattr(settings, 'UI_SCRIPT_TIMEOUT', 3600)

            return_code, stdout_lines, stderr_lines = self._stream_output(
                process,
                execution_id,
                timeout
            )

            # 8. 计算执行时长
            duration = time.time() - start_time

            # 9. 记录执行结果
            self._write_log(execution_id, 'system', '=' * 60)
            self._write_log(execution_id, 'system', f'执行完成 (返回码: {return_code})')
            self._write_log(execution_id, 'system', f'执行时长: {duration:.2f}秒')
            self._write_log(execution_id, 'system', '=' * 60)

            # 10. 更新最终状态
            success = return_code == 0

            self._update_status(
                execution_id,
                'success' if success else 'failed',
                script_id=script_upload_instance_id,
                script_name=script_instance.name,
                return_code=return_code,
                duration=duration,
                completed_at=datetime.now().isoformat()
            )

            # 11. 返回结果
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

            self._write_log(execution_id, 'system', f'错误: {error_msg}')
            self._update_status(
                execution_id,
                'failed',
                error=error_msg,
                duration=time.time() - start_time
            )

            result['error'] = error_msg
            result['duration'] = time.time() - start_time

            return result

        except Exception as e:
            # 未预期的异常
            error_msg = f"执行过程中发生异常: {str(e)}"
            logger.error(error_msg, exc_info=True)

            self._write_log(execution_id, 'system', f'系统错误: {error_msg}')
            self._update_status(
                execution_id,
                'failed',
                error=error_msg,
                duration=time.time() - start_time
            )

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

            self.redis_client.delete(log_key, status_key)

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
