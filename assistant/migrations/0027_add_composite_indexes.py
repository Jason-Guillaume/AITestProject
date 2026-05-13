from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0026_kw_models"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="knowledgearticle",
            index=models.Index(
                fields=["category", "is_deleted"],
                name="ka_cat_del_idx",
            ),
        ),
    ]
