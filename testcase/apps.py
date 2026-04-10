from django.apps import AppConfig


class TestcaseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "testcase"

    def ready(self):
        import testcase.signals  # noqa: F401
