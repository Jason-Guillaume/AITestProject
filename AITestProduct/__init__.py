import pymysql
import importlib.util

pymysql.install_as_MySQLdb()

celery_app = None
try:
    # Celery 为可选依赖：未安装时不阻塞 Django 启动。
    if importlib.util.find_spec("celery") is not None:
        from .celery import app as celery_app
except Exception:
    celery_app = None

__all__ = ("celery_app",)
