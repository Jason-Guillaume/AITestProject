import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AITestProduct.settings")

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

# Ensure project root in sys.path when running from scripts/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.utils import timezone  # noqa: E402
from django.db import transaction  # noqa: E402

from testcase.models import TestDesign  # noqa: E402
from execution.models import TestPlan, TestReport  # noqa: E402
from project.models import ReleasePlan, TestProject  # noqa: E402


def ensure_user():
    User = get_user_model()
    u = User.objects.filter(is_deleted=False).order_by("id").first()
    if u:
        return u
    return User.objects.create_user(
        username="admin",
        password="admin123",
        real_name="Admin",
    )


def ensure_project_and_release(user):
    proj = TestProject.objects.filter(is_deleted=False).order_by("id").first()
    if not proj:
        proj = TestProject.objects.create(
            project_name="Demo",
            project_status=1,
            progress=0,
            creator=user,
            updater=user,
        )
        try:
            proj.members.add(user)
        except Exception:
            pass
    rp = ReleasePlan.objects.filter(is_deleted=False).order_by("id").first()
    if not rp:
        rp = ReleasePlan.objects.create(
            project=proj,
            release_name="R1",
            version_no="v1",
            release_date=timezone.now(),
            status=1,
            creator=user,
            updater=user,
        )
    return proj, rp


def ensure_plan(user, release_plan):
    plan = TestPlan.objects.filter(is_deleted=False).order_by("id").first()
    if plan:
        return plan
    plan = TestPlan.objects.create(
        plan_name="P1",
        iteration="it",
        version=release_plan,
        environment="TEST",
        req_count=11,
        case_count=22,
        coverage_rate=55,
        plan_status=1,
        pass_rate=88,
        defect_count=3,
        creator=user,
        updater=user,
    )
    try:
        plan.testers.add(user)
    except Exception:
        pass
    return plan


def main():
    u = ensure_user()
    proj, rp = ensure_project_and_release(u)
    plan = ensure_plan(u, rp)

    with transaction.atomic():
        d1 = TestDesign.objects.create(
            design_name="D1",
            req_count=1,
            point_count=2,
            case_count=3,
            review_status=1,
            archive_status=1,
            creator=u,
            updater=u,
        )
        d2 = TestDesign.objects.create(
            design_name="D2",
            req_count=1,
            point_count=2,
            case_count=3,
            review_status=1,
            archive_status=1,
            creator=u,
            updater=u,
        )

    with transaction.atomic():
        r1 = TestReport.objects.create(
            plan=plan,
            report_name="R1",
            create_method=1,
            environment="OLD",
            req_count=0,
            case_count=0,
            coverage_rate=0,
            pass_rate=0,
            defect_count=0,
            start_time=timezone.now(),
            end_time=timezone.now(),
            creator=u,
            updater=u,
            project=proj,
        )
        r2 = TestReport.objects.create(
            plan=plan,
            report_name="R2",
            create_method=1,
            environment="OLD",
            req_count=0,
            case_count=0,
            coverage_rate=0,
            pass_rate=0,
            defect_count=0,
            start_time=timezone.now(),
            end_time=timezone.now(),
            creator=u,
            updater=u,
            project=proj,
        )

    print("Created designs:", d1.id, d2.id)
    print("Created reports:", r1.id, r2.id)
    print("Plan stats:", plan.environment, plan.req_count, plan.case_count, plan.pass_rate, plan.defect_count)
    print("Before refresh:", list(TestReport.objects.filter(id__in=[r1.id, r2.id]).values_list("id", "environment", "req_count", "case_count", "pass_rate", "defect_count")))

    # Simulate "refresh from plan" in pure ORM (mirrors API behavior)
    with transaction.atomic():
        for obj in TestReport.objects.filter(id__in=[r1.id, r2.id]).select_related("plan"):
            p = obj.plan
            obj.environment = p.environment
            obj.req_count = p.req_count
            obj.case_count = p.case_count
            obj.coverage_rate = p.coverage_rate
            obj.pass_rate = p.pass_rate
            obj.defect_count = p.defect_count
            obj.updater = u
            obj.save()

    print("After refresh:", list(TestReport.objects.filter(id__in=[r1.id, r2.id]).values_list("id", "environment", "req_count", "case_count", "pass_rate", "defect_count")))

    # Simulate "batch archive designs"
    with transaction.atomic():
        TestDesign.objects.filter(id__in=[d1.id, d2.id]).update(archive_status=2, updater=u)

    print("After archive designs:", list(TestDesign.objects.filter(id__in=[d1.id, d2.id]).values_list("id", "archive_status", "review_status")))


if __name__ == "__main__":
    main()

