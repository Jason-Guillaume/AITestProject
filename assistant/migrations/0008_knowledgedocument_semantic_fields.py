from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0007_knowledgedocument_document_type_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="knowledgedocument",
            name="semantic_chunks",
            field=models.JSONField(blank=True, default=list, verbose_name="语义切片"),
        ),
        migrations.AddField(
            model_name="knowledgedocument",
            name="semantic_summary",
            field=models.TextField(blank=True, default="", verbose_name="语义摘要"),
        ),
    ]

