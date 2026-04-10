from collections import defaultdict
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from testcase.models import TestCase


class Command(BaseCommand):
    help = "按测试类型重排启用态用例业务编号(case_number)，从 1 开始连续递增"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="仅预览变更，不落库",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="若存在待修复记录则返回非 0 退出码（用于 CI 守护）",
        )
        parser.add_argument(
            "--report-file",
            type=str,
            default="",
            help="将检查报告输出到指定文件路径",
        )
        parser.add_argument(
            "--report-json-file",
            type=str,
            default="",
            help="将检查报告输出为 JSON 到指定文件路径",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        strict = bool(options.get("strict"))
        report_file = str(options.get("report_file") or "").strip()
        report_json_file = str(options.get("report_json_file") or "").strip()
        qs = (
            TestCase.all_objects.filter(is_deleted=False)
            .order_by("test_type", "case_number", "id")
            .only("id", "test_type", "case_number")
        )

        next_no = defaultdict(int)
        to_update = []
        preview_limit = 20

        for case in qs.iterator(chunk_size=500):
            next_no[case.test_type] += 1
            expected = next_no[case.test_type]
            if case.case_number != expected:
                to_update.append((case, expected))

        self.stdout.write(self.style.NOTICE(f"发现待修复记录: {len(to_update)}"))
        if to_update:
            rows = to_update[:preview_limit]
            self.stdout.write(self.style.NOTICE(f"预览前 {preview_limit} 条（表格）："))
            header = f"{'id':>6} | {'type':<14} | {'old':>8} | {'new':>8}"
            self.stdout.write(header)
            self.stdout.write("-" * len(header))
            for case, expected in rows:
                old_val = "None" if case.case_number is None else str(case.case_number)
                self.stdout.write(
                    f"{case.id:>6} | {str(case.test_type):<14} | {old_val:>8} | {str(expected):>8}"
                )

        if report_file:
            lines = [f"pending={len(to_update)}"]
            if to_update:
                lines.append(f"preview_top_{preview_limit}:")
                lines.append(f"{'id':>6} | {'type':<14} | {'old':>8} | {'new':>8}")
                lines.append("-" * 46)
                for case, expected in to_update[:preview_limit]:
                    old_val = "None" if case.case_number is None else str(case.case_number)
                    lines.append(
                        f"{case.id:>6} | {str(case.test_type):<14} | {old_val:>8} | {str(expected):>8}"
                    )
            p = Path(report_file)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.stdout.write(self.style.NOTICE(f"报告已写入: {p}"))

        if report_json_file:
            pending = len(to_update)
            payload = {
                "schema_version": "1.1",
                "generated_at": timezone.now().isoformat(),
                "strict_mode": strict,
                "status": "fail" if pending > 0 else "pass",
                "pending": pending,
                "preview_limit": preview_limit,
                "preview": [
                    {
                        "id": case.id,
                        "test_type": str(case.test_type),
                        "old": case.case_number,
                        "new": expected,
                    }
                    for case, expected in to_update[:preview_limit]
                ],
            }
            p_json = Path(report_json_file)
            p_json.parent.mkdir(parents=True, exist_ok=True)
            p_json.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            self.stdout.write(self.style.NOTICE(f"JSON 报告已写入: {p_json}"))

        if dry_run:
            if strict and to_update:
                raise SystemExit(1)
            self.stdout.write(self.style.SUCCESS("dry-run 完成"))
            return

        if not to_update:
            self.stdout.write(self.style.SUCCESS("无需修复"))
            return

        with transaction.atomic():
            for case, expected in to_update:
                case.case_number = expected
                case.save(update_fields=["case_number", "update_time"])

        self.stdout.write(self.style.SUCCESS(f"修复完成: {len(to_update)}"))
