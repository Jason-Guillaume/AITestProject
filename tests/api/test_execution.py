from __future__ import annotations

import pytest

from ._helpers import assert_status, url

pytestmark = [pytest.mark.full]


@pytest.mark.regression
def test_execution_endpoints_happy_and_invalid(authed_client, seed_objects):
    plan_id = seed_objects["plan_id"]
    report_id = seed_objects["report_id"]
    perf_task_id = seed_objects["perf_task_id"]

    for path in [
        "/execution/plans/",
        "/execution/reports/",
        "/execution/tasks/",
        "/perf/tasks/",
    ]:
        resp = authed_client.get(url(authed_client, path), timeout=20)
        assert_status(resp, (200,))

    plan_detail = authed_client.get(url(authed_client, f"/execution/plans/{plan_id}/"), timeout=20)
    assert_status(plan_detail, (200,))
    report_detail = authed_client.get(url(authed_client, f"/execution/reports/{report_id}/"), timeout=20)
    assert_status(report_detail, (200,))
    perf_detail = authed_client.get(url(authed_client, f"/execution/tasks/{perf_task_id}/"), timeout=20)
    assert_status(perf_detail, (200,))

    run_ok = authed_client.post(url(authed_client, f"/execution/tasks/{perf_task_id}/run/"), json={}, timeout=20)
    assert_status(run_ok, (200, 400))

    invalid_perf = authed_client.post(
        url(authed_client, "/execution/tasks/"),
        json={"task_name": "", "scenario": "invalid", "concurrency": -1, "duration": "oops"},
        timeout=20,
    )
    assert_status(invalid_perf, (400,))

    dashboard = authed_client.get(url(authed_client, "/execution/dashboard/summary/"), timeout=20)
    assert_status(dashboard, (200,))

    quality = authed_client.get(url(authed_client, "/execution/dashboard/quality/"), timeout=20)
    assert_status(quality, (200,))
    quality_body = quality.json()
    assert "trendChart" in quality_body
    trend = quality_body["trendChart"]
    assert isinstance(trend.get("xAxis"), list)
    assert isinstance(trend.get("series"), list)
    assert len(trend.get("series") or []) >= 3
    assert len(trend.get("xAxis") or []) >= 30
    assert "latestMetrics" in quality_body
    assert "raw" in quality_body

