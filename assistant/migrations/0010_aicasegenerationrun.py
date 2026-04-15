from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0009_aiusageevent"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AiCaseGenerationRun",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        max_length=64,
                        verbose_name="动作",
                    ),
                ),
                (
                    "test_type",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        max_length=32,
                        verbose_name="测试类型",
                    ),
                ),
                (
                    "module_id",
                    models.IntegerField(
                        blank=True,
                        db_index=True,
                        null=True,
                        verbose_name="模块ID（可选）",
                    ),
                ),
                (
                    "streamed",
                    models.BooleanField(default=False, verbose_name="是否流式"),
                ),
                (
                    "model_used",
                    models.CharField(
                        blank=True, default="", max_length=128, verbose_name="模型名"
                    ),
                ),
                (
                    "prompt_version",
                    models.CharField(
                        blank=True,
                        default="v1",
                        max_length=64,
                        verbose_name="提示词版本",
                    ),
                ),
                (
                    "params",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="参数（脱敏）"
                    ),
                ),
                (
                    "requirement_sha256",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        max_length=64,
                        verbose_name="需求哈希",
                    ),
                ),
                (
                    "requirement_preview",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=256,
                        verbose_name="需求摘要（脱敏）",
                    ),
                ),
                (
                    "ext_config",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="扩展配置（脱敏）"
                    ),
                ),
                (
                    "phase1_analysis",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="Phase1 分析结果"
                    ),
                ),
                (
                    "phase1_override",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="Phase1 覆盖输入（可选）"
                    ),
                ),
                (
                    "success",
                    models.BooleanField(
                        db_index=True, default=False, verbose_name="是否成功"
                    ),
                ),
                (
                    "all_covered",
                    models.BooleanField(default=False, verbose_name="是否判定无需生成"),
                ),
                (
                    "cases_count",
                    models.IntegerField(default=0, verbose_name="生成用例条数"),
                ),
                (
                    "prompt_chars",
                    models.IntegerField(default=0, verbose_name="输入字符数"),
                ),
                (
                    "output_chars",
                    models.IntegerField(default=0, verbose_name="输出字符数"),
                ),
                ("latency_ms", models.IntegerField(default=0, verbose_name="耗时(ms)")),
                (
                    "error_code",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=64,
                        verbose_name="错误码（可选）",
                    ),
                ),
                (
                    "error_message",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=512,
                        verbose_name="错误摘要（脱敏）",
                    ),
                ),
                (
                    "meta",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="元信息（脱敏）"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, verbose_name="创建时间"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ai_case_generation_runs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="发起用户",
                    ),
                ),
            ],
            options={
                "db_table": "ai_case_generation_run",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="aicasegenerationrun",
            index=models.Index(
                fields=["action", "-created_at"], name="ai_case_ge_action_efc1e8_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="aicasegenerationrun",
            index=models.Index(
                fields=["test_type", "-created_at"],
                name="ai_case_ge_test_ty_9f6b2f_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="aicasegenerationrun",
            index=models.Index(
                fields=["user", "-created_at"], name="ai_case_ge_user_id_9d3e67_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="aicasegenerationrun",
            index=models.Index(
                fields=["module_id", "-created_at"],
                name="ai_case_ge_module__c8b8ea_idx",
            ),
        ),
    ]
