import logging
from typing import Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import threading
from django.utils import timezone
from django.db import transaction
from django_apscheduler.jobstores import DjangoJobStore

from execution.models import ScheduledTask, ScheduledTaskLog
from execution.tasks import run_scheduled_task

logger = logging.getLogger(__name__)


class TestScheduler:
    """统一封装 APScheduler 的生命周期与任务同步。"""

    _instance = None

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=str(timezone.get_current_timezone()))
        self.scheduler.add_jobstore(DjangoJobStore(), "default")
        self._started = False
        self._op_lock = threading.RLock()

    @classmethod
    def instance(cls) -> "TestScheduler":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start(self):
        if self._started:
            return
        self.scheduler.start()
        self._started = True
        logger.info("测试调度器已启动")
        self.sync_all_active_tasks()

    def shutdown(self):
        if not self._started:
            return
        self.scheduler.shutdown(wait=False)
        self._started = False
        logger.info("测试调度器已关闭")

    def sync_all_active_tasks(self):
        """重载所有启用中的调度任务。"""
        tasks = ScheduledTask.objects.filter(is_deleted=False)
        for task in tasks:
            self.sync_task(task)

    def sync_task(self, task: ScheduledTask):
        """
        按 DB 状态同步调度器任务：
        - disabled: 删除
        - paused: 注册并暂停
        - active: 注册并恢复
        """
        try:
            with transaction.atomic():
                task = ScheduledTask.objects.select_for_update().get(pk=task.pk)
                if task.status == ScheduledTask.STATUS_DISABLED or task.is_deleted:
                    self.remove_task(task.id)
                    return

                trigger = CronTrigger.from_crontab(task.cron_expression)
                with self._op_lock:
                    try:
                        self.scheduler.remove_job(task.job_id)
                    except Exception:
                        pass
                    self.scheduler.add_job(
                        func=execute_scheduled_task,
                        trigger=trigger,
                        args=[str(task.id)],
                        id=task.job_id,
                        replace_existing=True,
                        max_instances=1,
                        coalesce=True,
                        misfire_grace_time=60,
                    )
                    job = self.scheduler.get_job(task.job_id)
                    next_run_time = job.next_run_time if job else None
                    ScheduledTask.objects.filter(pk=task.pk).update(next_run_time=next_run_time)

                    if task.status == ScheduledTask.STATUS_PAUSED:
                        self.scheduler.pause_job(task.job_id)
                    else:
                        self.scheduler.resume_job(task.job_id)
            logger.info("调度任务已同步: task_id=%s, status=%s", task.id, task.status)
        except Exception:
            logger.exception("同步调度任务失败: task_id=%s", task.id)
            raise

    def remove_task(self, task_id: int):
        task = ScheduledTask.objects.filter(pk=task_id).first()
        if not task:
            return
        with self._op_lock:
            try:
                self.scheduler.remove_job(task.job_id)
            except Exception:
                # 任务不存在时忽略，不中断业务流程。
                pass
        ScheduledTask.objects.filter(pk=task.pk).update(next_run_time=None)
        logger.info("调度任务已移除: task_id=%s", task.id)

    def pause_task(self, task: ScheduledTask):
        with self._op_lock:
            try:
                self.scheduler.pause_job(task.job_id)
            except Exception:
                logger.exception("暂停调度任务失败: task_id=%s", task.id)
                raise
        ScheduledTask.objects.filter(pk=task.pk).update(status=ScheduledTask.STATUS_PAUSED)

    def resume_task(self, task: ScheduledTask):
        with self._op_lock:
            try:
                self.scheduler.resume_job(task.job_id)
            except Exception:
                logger.exception("恢复调度任务失败: task_id=%s", task.id)
                raise
        ScheduledTask.objects.filter(pk=task.pk).update(status=ScheduledTask.STATUS_ACTIVE)


def execute_scheduled_task(task_id: str):
    """
    调度执行入口：
    这里聚焦执行轨迹与日志沉淀，可在后续扩展真实用例执行流程。
    """
    try:
        tid = int(task_id)
    except (TypeError, ValueError):
        logger.warning("调度任务参数非法: task_id=%s", task_id)
        return
    task = ScheduledTask.objects.filter(pk=tid, is_deleted=False).first()
    if not task:
        logger.warning("调度任务不存在或已删除: task_id=%s", tid)
        return

    now = timezone.now()
    log = ScheduledTaskLog.objects.create(
        scheduled_task=task,
        trigger_time=now,
        start_time=now,
        status=ScheduledTaskLog.STATUS_RUNNING,
        message="任务已触发，已投递异步执行",
        detail={},
    )
    try:
        run_scheduled_task.delay(tid, scheduled_task_log_id=log.id)
    except Exception as exc:
        end_time = timezone.now()
        err = str(exc)[:255]
        log.status = ScheduledTaskLog.STATUS_FAILED
        log.message = f"投递失败: {err}"
        log.detail = {"error": err}
        log.end_time = end_time
        log.save(update_fields=["status", "message", "detail", "end_time", "update_time"])
        ScheduledTask.objects.filter(pk=task.pk).update(
            last_run_time=end_time,
            last_status=ScheduledTask.LAST_FAILED,
            last_message=f"投递失败: {err}",
        )
        logger.exception("调度任务投递失败: task_id=%s", task.id)
