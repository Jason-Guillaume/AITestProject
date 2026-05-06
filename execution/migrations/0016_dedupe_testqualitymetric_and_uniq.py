# 合并重复的质量指标行；新增 dimension_key（MySQL 无法对 JSON 列建唯一索引）

import json

from django.db import migrations, models


def dedupe_test_quality_metrics(apps, schema_editor):
    TestQualityMetric = apps.get_model("execution", "TestQualityMetric")
    from collections import defaultdict

    groups = defaultdict(list)
    for row in TestQualityMetric.objects.all().order_by("id"):
        dim = row.dimension or {}
        if not isinstance(dim, dict):
            dim = {}
        key = (
            row.metric_date,
            row.metric_type,
            json.dumps(dim, sort_keys=True, default=str),
        )
        groups[key].append(row.pk)

    for pks in groups.values():
        if len(pks) <= 1:
            continue
        TestQualityMetric.objects.filter(pk__in=pks[1:]).delete()


def backfill_dimension_keys(apps, schema_editor):
    TestQualityMetric = apps.get_model("execution", "TestQualityMetric")
    for row in TestQualityMetric.objects.all().iterator():
        dim = row.dimension or {}
        if not isinstance(dim, dict):
            dim = {}
        dk = json.dumps(dim, sort_keys=True, default=str)
        TestQualityMetric.objects.filter(pk=row.pk).update(dimension_key=dk)


class Migration(migrations.Migration):

    dependencies = [
        ("execution", "0015_apiscenario_apiscenariorun_apiscenariostep_and_more"),
    ]

    operations = [
        migrations.RunPython(dedupe_test_quality_metrics, migrations.RunPython.noop),
        migrations.AddField(
            model_name="testqualitymetric",
            name="dimension_key",
            field=models.CharField(
                blank=True,
                default="",
                max_length=320,
                verbose_name="维度归一化键",
                help_text="与 dimension 同步，供 MySQL 等对 JSON 无法建唯一索引时使用",
            ),
        ),
        migrations.RunPython(backfill_dimension_keys, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="testqualitymetric",
            constraint=models.UniqueConstraint(
                fields=("metric_date", "metric_type", "dimension_key"),
                name="execution_tqm_uniq_date_type_dimkey",
            ),
        ),
    ]
