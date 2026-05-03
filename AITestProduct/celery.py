"""Celery 应用入口：与 ``django.conf:settings`` 中 ``CELERY_*`` 对齐。

Worker 在 2C2G 机器上请与配置一致，例如::

    celery -A AITestProduct worker -l info --concurrency=1

``CELERY_WORKER_CONCURRENCY`` 与 ``CELERY_WORKER_MAX_TASKS_PER_CHILD`` 由 settings 注入。
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AITestProduct.settings")

app = Celery("AITestProduct")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
