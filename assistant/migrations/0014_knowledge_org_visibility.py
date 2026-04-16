from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("user", "0009_aimodelconfig_project_organization_projects_and_more"),
        ("assistant", "0013_alter_aiusageevent_action"),
    ]

    operations = [
        migrations.AddField(
            model_name="knowledgearticle",
            name="org",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="knowledge_articles",
                to="user.organization",
                verbose_name="所属组织",
            ),
        ),
        migrations.AddField(
            model_name="knowledgearticle",
            name="visibility_scope",
            field=models.CharField(
                choices=[
                    ("private", "仅自己可见"),
                    ("project", "项目内共享"),
                    ("org", "组织内共享"),
                ],
                db_index=True,
                default="private",
                max_length=16,
                verbose_name="可见范围",
            ),
        ),
        migrations.AddField(
            model_name="knowledgedocument",
            name="org",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="knowledge_documents",
                to="user.organization",
                verbose_name="所属组织",
            ),
        ),
        migrations.AddField(
            model_name="knowledgedocument",
            name="visibility_scope",
            field=models.CharField(
                choices=[
                    ("private", "仅自己可见"),
                    ("project", "项目内共享"),
                    ("org", "组织内共享"),
                ],
                db_index=True,
                default="private",
                max_length=16,
                verbose_name="可见范围",
            ),
        ),
    ]

