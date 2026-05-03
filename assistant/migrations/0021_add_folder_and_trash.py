# Generated migration for folder and trash support

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0020_uiscriptupload_build_config_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='uiscriptupload',
            name='folder',
            field=models.CharField(
                max_length=500,
                blank=True,
                null=True,
                default='/',
                verbose_name='所属文件夹',
                help_text='文件夹路径，如: /项目A/子文件夹'
            ),
        ),
        migrations.AddField(
            model_name='uiscriptupload',
            name='is_deleted',
            field=models.BooleanField(
                default=False,
                verbose_name='是否已删除',
                help_text='软删除标记，删除的文件进入回收站'
            ),
        ),
        migrations.AddField(
            model_name='uiscriptupload',
            name='deleted_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='删除时间'
            ),
        ),
        migrations.AddIndex(
            model_name='uiscriptupload',
            index=models.Index(fields=['folder', 'is_deleted'], name='ui_script_folder_idx'),
        ),
    ]
