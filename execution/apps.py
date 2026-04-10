from django.apps import AppConfig
import os
import sys
import logging

logger = logging.getLogger(__name__)


class ExecutionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "execution"

    def ready(self):
        """
        在开发环境下自动启动调度器。
        通过 RUN_MAIN 避免 runserver 双启动；可用 DISABLE_TEST_SCHEDULER=1 关闭。
        """
        if os.environ.get("DISABLE_TEST_SCHEDULER") == "1":
            return
        if "runserver" not in sys.argv:
            return
        if os.environ.get("RUN_MAIN") != "true":
            return
        try:
            from execution.scheduler import TestScheduler

            TestScheduler.instance().start()
        except Exception:
            logger.exception("启动测试调度器失败")
