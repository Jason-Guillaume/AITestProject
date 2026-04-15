# 多表继承：子表 DDL 使用 IF NOT EXISTS，便于中断后重跑；API 部分用 SeparateDatabaseAndState 分离状态与数据库步骤。

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def forwards_create_subtype_tables_mysql(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS testcase_perftestcase (
                testcase_ptr_id bigint NOT NULL PRIMARY KEY,
                concurrency int unsigned NOT NULL,
                duration_seconds int unsigned NOT NULL,
                target_rps int unsigned NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS testcase_securitytestcase (
                testcase_ptr_id bigint NOT NULL PRIMARY KEY,
                attack_surface varchar(512) NOT NULL,
                tool_preset varchar(128) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS testcase_uitestcase (
                testcase_ptr_id bigint NOT NULL PRIMARY KEY,
                app_under_test varchar(255) NOT NULL,
                primary_locator varchar(512) NOT NULL,
                automation_framework varchar(64) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)


def forwards_create_subtype_tables_sqlite(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS testcase_perftestcase (
                testcase_ptr_id integer NOT NULL PRIMARY KEY REFERENCES test_case(id),
                concurrency integer NOT NULL,
                duration_seconds integer NOT NULL,
                target_rps integer NULL
            )
            """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS testcase_securitytestcase (
                testcase_ptr_id integer NOT NULL PRIMARY KEY REFERENCES test_case(id),
                attack_surface varchar(512) NOT NULL,
                tool_preset varchar(128) NOT NULL
            )
            """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS testcase_uitestcase (
                testcase_ptr_id integer NOT NULL PRIMARY KEY REFERENCES test_case(id),
                app_under_test varchar(255) NOT NULL,
                primary_locator varchar(512) NOT NULL,
                automation_framework varchar(64) NOT NULL
            )
            """)


def forwards_fill_perf_security_ui(apps, schema_editor):
    connection = schema_editor.connection
    vendor = connection.vendor
    with connection.cursor() as cursor:
        if vendor == "mysql":
            cursor.execute(
                """
                INSERT IGNORE INTO testcase_perftestcase (
                    testcase_ptr_id, concurrency, duration_seconds, target_rps
                )
                SELECT id, 1, 60, NULL FROM test_case WHERE test_type = %s
                """,
                ["performance"],
            )
            cursor.execute(
                """
                INSERT IGNORE INTO testcase_securitytestcase (
                    testcase_ptr_id, attack_surface, tool_preset
                )
                SELECT id, '', '' FROM test_case WHERE test_type = %s
                """,
                ["security"],
            )
            cursor.execute(
                """
                INSERT IGNORE INTO testcase_uitestcase (
                    testcase_ptr_id, app_under_test, primary_locator, automation_framework
                )
                SELECT id, '', '', '' FROM test_case WHERE test_type = %s
                """,
                ["ui-automation"],
            )
        else:
            cursor.execute("""
                INSERT OR IGNORE INTO testcase_perftestcase (
                    testcase_ptr_id, concurrency, duration_seconds, target_rps
                )
                SELECT id, 1, 60, NULL FROM test_case WHERE test_type = 'performance'
                """)
            cursor.execute("""
                INSERT OR IGNORE INTO testcase_securitytestcase (
                    testcase_ptr_id, attack_surface, tool_preset
                )
                SELECT id, '', '' FROM test_case WHERE test_type = 'security'
                """)
            cursor.execute("""
                INSERT OR IGNORE INTO testcase_uitestcase (
                    testcase_ptr_id, app_under_test, primary_locator, automation_framework
                )
                SELECT id, '', '', '' FROM test_case WHERE test_type = 'ui-automation'
                """)


def backwards_noop(apps, schema_editor):
    pass


def forwards_api_table_copy_and_drop_parent_cols(apps, schema_editor):
    connection = schema_editor.connection
    vendor = connection.vendor
    with connection.cursor() as cursor:
        if vendor == "mysql":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS testcase_apitestcase (
                    testcase_ptr_id bigint NOT NULL PRIMARY KEY,
                    api_url varchar(2048) NOT NULL,
                    api_method varchar(16) NOT NULL,
                    api_headers json NOT NULL,
                    api_body longtext NOT NULL,
                    api_expected_status smallint unsigned NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
            cursor.execute("""
                INSERT IGNORE INTO testcase_apitestcase (
                    testcase_ptr_id, api_url, api_method, api_headers, api_body, api_expected_status
                )
                SELECT id, api_url, api_method, api_headers, api_body, api_expected_status
                FROM test_case WHERE test_type = 'api'
                """)
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'test_case' AND COLUMN_NAME = 'api_url'
                """)
            if cursor.fetchone()[0]:
                cursor.execute("""
                    ALTER TABLE test_case
                        DROP COLUMN api_url,
                        DROP COLUMN api_method,
                        DROP COLUMN api_headers,
                        DROP COLUMN api_body,
                        DROP COLUMN api_expected_status
                    """)
        elif vendor == "sqlite":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS testcase_apitestcase (
                    testcase_ptr_id integer NOT NULL PRIMARY KEY REFERENCES test_case(id),
                    api_url varchar(2048) NOT NULL,
                    api_method varchar(16) NOT NULL,
                    api_headers text NOT NULL,
                    api_body text NOT NULL,
                    api_expected_status integer NULL
                )
                """)
            cursor.execute("""
                INSERT OR IGNORE INTO testcase_apitestcase (
                    testcase_ptr_id, api_url, api_method, api_headers, api_body, api_expected_status
                )
                SELECT id, api_url, api_method, api_headers, api_body, api_expected_status
                FROM test_case WHERE test_type = 'api'
                """)
            cursor.execute("PRAGMA table_info(test_case)")
            colnames = {row[1] for row in cursor.fetchall()}
            if "api_url" in colnames:
                for col in (
                    "api_expected_status",
                    "api_body",
                    "api_headers",
                    "api_method",
                    "api_url",
                ):
                    cursor.execute(f"ALTER TABLE test_case DROP COLUMN {col}")
        else:
            raise NotImplementedError(
                f"请在 {vendor} 上补充 testcase_apitestcase 迁移，或改用 MySQL/SQLite。"
            )


def backwards_api_noop(apps, schema_editor):
    pass


def forwards_create_subtype_tables(apps, schema_editor):
    forwards_create_subtype_tables_mysql(apps, schema_editor)
    forwards_create_subtype_tables_sqlite(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("testcase", "0011_update_case_number_unique_constraint"),
    ]

    operations = [
        migrations.RunPython(forwards_create_subtype_tables, backwards_noop),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="PerfTestCase",
                    fields=[
                        (
                            "testcase_ptr",
                            models.OneToOneField(
                                auto_created=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                parent_link=True,
                                primary_key=True,
                                serialize=False,
                                to="testcase.testcase",
                            ),
                        ),
                        (
                            "concurrency",
                            models.PositiveIntegerField(
                                default=1, verbose_name="并发数"
                            ),
                        ),
                        (
                            "duration_seconds",
                            models.PositiveIntegerField(
                                default=60, verbose_name="持续时间(秒)"
                            ),
                        ),
                        (
                            "target_rps",
                            models.PositiveIntegerField(
                                blank=True, null=True, verbose_name="目标 RPS"
                            ),
                        ),
                    ],
                    options={
                        "db_table": "testcase_perftestcase",
                    },
                    bases=("testcase.testcase",),
                ),
                migrations.CreateModel(
                    name="SecurityTestCase",
                    fields=[
                        (
                            "testcase_ptr",
                            models.OneToOneField(
                                auto_created=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                parent_link=True,
                                primary_key=True,
                                serialize=False,
                                to="testcase.testcase",
                            ),
                        ),
                        (
                            "attack_surface",
                            models.CharField(
                                blank=True,
                                default="",
                                max_length=512,
                                verbose_name="攻击面/范围说明",
                            ),
                        ),
                        (
                            "tool_preset",
                            models.CharField(
                                blank=True,
                                default="",
                                max_length=128,
                                verbose_name="工具/扫描模板",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "testcase_securitytestcase",
                    },
                    bases=("testcase.testcase",),
                ),
                migrations.CreateModel(
                    name="UITestCase",
                    fields=[
                        (
                            "testcase_ptr",
                            models.OneToOneField(
                                auto_created=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                parent_link=True,
                                primary_key=True,
                                serialize=False,
                                to="testcase.testcase",
                            ),
                        ),
                        (
                            "app_under_test",
                            models.CharField(
                                blank=True,
                                default="",
                                max_length=255,
                                verbose_name="被测应用/包名",
                            ),
                        ),
                        (
                            "primary_locator",
                            models.CharField(
                                blank=True,
                                default="",
                                max_length=512,
                                verbose_name="主定位符",
                            ),
                        ),
                        (
                            "automation_framework",
                            models.CharField(
                                blank=True,
                                default="",
                                max_length=64,
                                verbose_name="自动化框架",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "testcase_uitestcase",
                    },
                    bases=("testcase.testcase",),
                ),
            ],
        ),
        migrations.RunPython(forwards_fill_perf_security_ui, backwards_noop),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    forwards_api_table_copy_and_drop_parent_cols,
                    backwards_api_noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(model_name="testcase", name="api_body"),
                migrations.RemoveField(
                    model_name="testcase", name="api_expected_status"
                ),
                migrations.RemoveField(model_name="testcase", name="api_headers"),
                migrations.RemoveField(model_name="testcase", name="api_method"),
                migrations.RemoveField(model_name="testcase", name="api_url"),
                migrations.CreateModel(
                    name="ApiTestCase",
                    fields=[
                        (
                            "testcase_ptr",
                            models.OneToOneField(
                                auto_created=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                parent_link=True,
                                primary_key=True,
                                serialize=False,
                                to="testcase.testcase",
                            ),
                        ),
                        (
                            "api_url",
                            models.CharField(
                                blank=True,
                                default="",
                                max_length=2048,
                                verbose_name="API 地址",
                            ),
                        ),
                        (
                            "api_method",
                            models.CharField(
                                default="GET",
                                max_length=16,
                                verbose_name="HTTP 方法",
                            ),
                        ),
                        (
                            "api_headers",
                            models.JSONField(
                                blank=True,
                                default=dict,
                                verbose_name="请求头(JSON)",
                            ),
                        ),
                        (
                            "api_body",
                            models.TextField(
                                blank=True, default="", verbose_name="请求体"
                            ),
                        ),
                        (
                            "api_expected_status",
                            models.PositiveSmallIntegerField(
                                blank=True,
                                help_text="为空则仅校验 2xx；与步骤里「预期结果」子串断言可同时生效",
                                null=True,
                                verbose_name="期望状态码",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "testcase_apitestcase",
                    },
                    bases=("testcase.testcase",),
                ),
            ],
        ),
        migrations.AlterModelOptions(
            name="apitestlog",
            options={"ordering": ["-create_time"]},
        ),
        migrations.AlterField(
            model_name="apitestlog",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_created",
                to=settings.AUTH_USER_MODEL,
                verbose_name="创建人",
            ),
        ),
        migrations.AlterField(
            model_name="apitestlog",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_updated",
                to=settings.AUTH_USER_MODEL,
                verbose_name="更新人",
            ),
        ),
    ]
