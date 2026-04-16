from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("assistant", "0014_knowledge_org_visibility"),
    ]

    operations = [
        migrations.CreateModel(
            name="GeneratedTestArtifact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("create_time", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("update_time", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("is_deleted", models.BooleanField(default=False, verbose_name="是否已删除")),
                ("artifact_type", models.CharField(choices=[("test_plan", "测试计划"), ("test_points", "测试点"), ("case_draft", "用例草稿"), ("api_scenario", "API 场景")], db_index=True, max_length=32, verbose_name="资产类型")),
                ("title", models.CharField(blank=True, default="", max_length=255, verbose_name="标题")),
                ("content", models.JSONField(blank=True, default=dict, verbose_name="结构化内容")),
                ("citations", models.JSONField(blank=True, default=list, verbose_name="引用来源（citations/chunks）")),
                ("model_used", models.CharField(blank=True, default="", max_length=128, verbose_name="模型（可选）")),
                ("source_question", models.TextField(blank=True, default="", verbose_name="来源问题（可选）")),
                ("creator", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generatedtestartifact_created", to="user.user", verbose_name="创建人")),
                ("updater", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generatedtestartifact_updated", to="user.user", verbose_name="更新人")),
                ("org", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generated_test_artifacts", to="user.organization", verbose_name="所属组织")),
                ("project", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generated_test_artifacts", to="project.testproject", verbose_name="所属项目")),
                ("module", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generated_test_artifacts", to="testcase.testmodule", verbose_name="关联模块")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generated_artifacts", to="assistant.knowledgedocument", verbose_name="来源知识文档")),
            ],
            options={
                "db_table": "generated_test_artifact",
                "ordering": ("-create_time",),
            },
        ),
        migrations.AddIndex(
            model_name="generatedtestartifact",
            index=models.Index(fields=["artifact_type", "-create_time"], name="generated_t_artifact_0f4d2f_idx"),
        ),
        migrations.AddIndex(
            model_name="generatedtestartifact",
            index=models.Index(fields=["project", "-create_time"], name="generated_t_project_1f3b0c_idx"),
        ),
        migrations.AddIndex(
            model_name="generatedtestartifact",
            index=models.Index(fields=["module", "-create_time"], name="generated_t_module_cdd3d9_idx"),
        ),
        migrations.AddIndex(
            model_name="generatedtestartifact",
            index=models.Index(fields=["source_document", "-create_time"], name="generated_t_source_d_64b2fe_idx"),
        ),
    ]

