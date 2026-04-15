import importlib.util

try:
    import pymysql  # type: ignore

    pymysql.install_as_MySQLdb()
except Exception:
    # pymysql 为可选依赖：未安装时不阻塞 Django 启动（仅在使用 MySQLdb 兼容层时需要）
    pymysql = None  # type: ignore

celery_app = None
try:
    # Celery 为可选依赖：未安装时不阻塞 Django 启动。
    if importlib.util.find_spec("celery") is not None:
        from .celery import app as celery_app
except Exception:
    celery_app = None

__all__ = ("celery_app",)
