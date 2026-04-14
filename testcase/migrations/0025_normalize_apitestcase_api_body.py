# Generated manually: normalize legacy api_body shapes to dict/list wrapper form.

from django.db import migrations


def normalize_api_body_rows(apps, schema_editor):
    ApiTestCase = apps.get_model("testcase", "ApiTestCase")
    from testcase.services.api_execution import normalize_api_body

    for row in ApiTestCase.objects.iterator():
        raw = row.api_body
        norm = normalize_api_body(raw)
        new_body = {} if norm is None else norm
        if new_body != raw:
            row.api_body = new_body
            row.save(update_fields=["api_body"])


class Migration(migrations.Migration):
    dependencies = [
        ("testcase", "0024_apitestcase_api_source_curl"),
    ]

    operations = [
        migrations.RunPython(normalize_api_body_rows, migrations.RunPython.noop),
    ]
