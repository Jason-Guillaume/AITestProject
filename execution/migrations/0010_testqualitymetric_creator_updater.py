from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("execution", "0009_testqualitymetric"),
    ]

    operations = [
        migrations.AddField(
            model_name="testqualitymetric",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="testqualitymetric_created",
                to=settings.AUTH_USER_MODEL,
                verbose_name="创建人",
            ),
        ),
        migrations.AddField(
            model_name="testqualitymetric",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="testqualitymetric_updated",
                to=settings.AUTH_USER_MODEL,
                verbose_name="更新人",
            ),
        ),
    ]
