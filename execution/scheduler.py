import logging
from typing import Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.utils import timezone
from django.db import transaction
from django_apscheduler.jobstores import DjangoJobStore

from execution.models import ScheduledTask, ScheduledTaskLog
from testcase.models import TestCase
from testcase.services.case_subtypes import get_api_profile_for_execute
from testcase.services.api_execution import run_api_case

logger = logging.getLogger(__name__)


class TestScheduler:
    """统一封装 APScheduler 的生命周期与任务同步。"""

    _instance = None

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=str(timezone.get_current_timezone()))
        self.scheduler.add_jobstore(DjangoJobStore(), "default")
        self._started = False

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
            if task.status == ScheduledTask.STATUS_DISABLED or task.is_deleted:
                self.remove_task(task.id)
                return

            trigger = CronTrigger.from_crontab(task.cron_expression)
            self.scheduler.add_job(
                func=execute_scheduled_task,
                trigger=trigger,
                args=[task.id],
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
        try:
            self.scheduler.remove_job(task.job_id)
        except Exception:
            # 任务不存在时忽略，不中断业务流程。
            pass
        ScheduledTask.objects.filter(pk=task.pk).update(next_run_time=None)
        logger.info("调度任务已移除: task_id=%s", task.id)

    def pause_task(self, task: ScheduledTask):
        try:
            self.scheduler.pause_job(task.job_id)
        except Exception:
            logger.exception("暂停调度任务失败: task_id=%s", task.id)
            raise
        ScheduledTask.objects.filter(pk=task.pk).update(status=ScheduledTask.STATUS_PAUSED)

    def resume_task(self, task: ScheduledTask):
        try:
            self.scheduler.resume_job(task.job_id)
        except Exception:
            logger.exception("恢复调度任务失败: task_id=%s", task.id)
            raise
        ScheduledTask.objects.filter(pk=task.pk).update(status=ScheduledTask.STATUS_ACTIVE)


def execute_scheduled_task(task_id: int):
    """
    调度执行入口：
    这里聚焦执行轨迹与日志沉淀，可在后续扩展真实用例执行流程。
    """
    task = ScheduledTask.objects.filter(pk=task_id, is_deleted=False).first()
    if not task:
        logger.warning("调度任务不存在或已删除: task_id=%s", task_id)
        return

    now = timezone.now()
    log = ScheduledTaskLog.objects.create(
        scheduled_task=task,
        trigger_time=now,
        start_time=now,
        status=ScheduledTaskLog.STATUS_RUNNING,
        message="任务已触发，开始执行",
        detail={},
    )

    try:
        detail: Dict[str, Any] = {
            "task_id": task.id,
            "executed_case_ids": [],
            "api_errors": [],
            "skipped_non_api_case_ids": [],
        }
        total = 0
        api_count = 0
        api_failed = 0
        skipped_non_api = 0
        env_id = task.environment_id
        for case in task.test_cases.filter(is_deleted=False).iterator():
            total += 1
            detail["executed_case_ids"].append(case.id)
            if case.test_type != TestCase.TEST_TYPE_API:
                skipped_non_api += 1
                detail["skipped_non_api_case_ids"].append(case.id)
                logger.warning(
                    "调度任务跳过非 API 用例: task_id=%s case_id=%s test_type=%s",
                    task.id,
                    case.id,
                    case.test_type,
                )
                continue
            api_count += 1
            api_prof = get_api_profile_for_execute(case)
            if api_prof is None:
                detail["api_errors"].append({"case_id": case.id, "error": "API 用例扩展数据缺失"})
                api_failed += 1
                continue
            try:
                result = run_api_case(
                    case,
                    api_prof,
                    overrides={"environment_id": env_id},
                    user=None,
                    write_legacy_apilog=False,
                )
                if not result.execution_log.is_passed:
                    api_failed += 1
                    detail["api_errors"].append(
                        {
                            "case_id": case.id,
                            "error": result.message or "断言未通过",
                        }
                    )
            except Exception as exc:
                api_failed += 1
                err_text = str(exc)[:500]
                detail["api_errors"].append({"case_id": case.id, "error": err_text})
                logger.exception("调度执行 API 用例失败: task_id=%s case_id=%s", task.id, case.id)

        end_time = timezone.now()
        if api_count > 0 and api_failed >= api_count:
            log.status = ScheduledTaskLog.STATUS_FAILED
            message = f"共 {total} 条用例，API {api_count} 条均未通过或异常"
            if skipped_non_api:
                message += f"，跳过非 API {skipped_non_api} 条"
            last_st = ScheduledTask.LAST_FAILED
        elif api_count > 0 and api_failed > 0:
            log.status = ScheduledTaskLog.STATUS_PARTIAL
            message = f"共 {total} 条用例，API {api_count} 条（失败 {api_failed}）"
            if skipped_non_api:
                message += f"，跳过非 API {skipped_non_api} 条"
            last_st = ScheduledTask.LAST_PARTIAL
        elif api_count == 0 and skipped_non_api > 0:
            log.status = ScheduledTaskLog.STATUS_PARTIAL
            message = f"共 {total} 条用例，均为非 API 类型，已跳过 {skipped_non_api} 条"
            last_st = ScheduledTask.LAST_PARTIAL
        else:
            log.status = ScheduledTaskLog.STATUS_SUCCESS
            message = f"共触发 {total} 条用例（API: {api_count}）"
            last_st = ScheduledTask.LAST_SUCCESS
        log.message = message
        log.detail = detail
        log.end_time = end_time
        log.save(update_fields=["status", "message", "detail", "end_time", "update_time"])

        with transaction.atomic():
            task.last_run_time = end_time
            task.last_status = last_st
            task.last_message = message
            task.save(update_fields=["last_run_time", "last_status", "last_message", "update_time"])
        logger.info("调度任务执行结束: task_id=%s status=%s", task.id, log.status)
    except Exception as exc:
        end_time = timezone.now()
        err = str(exc)[:255]
        log.status = ScheduledTaskLog.STATUS_FAILED
        log.message = f"执行失败: {err}"
        log.detail = {"error": err}
        log.end_time = end_time
        log.save(update_fields=["status", "message", "detail", "end_time", "update_time"])

        ScheduledTask.objects.filter(pk=task.pk).update(
            last_run_time=end_time,
            last_status=ScheduledTask.LAST_FAILED,
            last_message=f"执行失败: {err}",
        )
        logger.exception("调度任务执行失败: task_id=%s", task.id)
