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
            from django.db.utils import OperationalError

            from execution.scheduler import TestScheduler

            TestScheduler.instance().start()
        except OperationalError as e:
            logger.error(
                "启动测试调度器失败（数据库无法连接）。请检查 .env 中 DB_HOST / DB_USER / DB_PASSWORD "
                "是否与本地 MySQL 一致（1045 多为密码未配置或错误）。原始错误: %s",
                e,
            )
        except Exception:
            logger.exception("启动测试调度器失败")
