from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from testcase.models import TestCase


class Command(BaseCommand):
    help = "清理回收站中超过 N 天的用例（物理删除并触发编号重排）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="删除超过多少天的回收站用例，默认 90",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="仅统计，不实际删除",
        )

    def handle(self, *args, **options):
        days = max(1, int(options["days"]))
        dry_run = bool(options["dry_run"])
        cutoff = timezone.now() - timedelta(days=days)

        qs = TestCase.deleted_objects.filter(
            deleted_at__isnull=False,
            deleted_at__lt=cutoff,
        ).order_by("deleted_at", "id")

        total = qs.count()
        self.stdout.write(self.style.NOTICE(f"待清理数量: {total} (cutoff={cutoff.isoformat()})"))
        if dry_run or total == 0:
            self.stdout.write(self.style.SUCCESS("dry-run 完成" if dry_run else "无需清理"))
            return

        deleted = 0
        for case in qs.iterator(chunk_size=200):
            case.hard_delete()
            deleted += 1

        self.stdout.write(self.style.SUCCESS(f"清理完成: {deleted}"))
