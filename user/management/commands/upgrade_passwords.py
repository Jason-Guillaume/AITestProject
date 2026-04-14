from __future__ import annotations

import re

from django.core.management.base import BaseCommand

from user.models import User


class Command(BaseCommand):
    help = "批量升级/禁用历史非 Django 哈希密码（强制用户重置密码）。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="仅统计不落库",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        total = 0
        changed = 0

        md5_re = re.compile(r"^[a-f0-9]{32}$", re.IGNORECASE)
        sha256_re = re.compile(r"^[a-f0-9]{64}$", re.IGNORECASE)

        qs = User.objects.all().only("id", "username", "password")
        for u in qs.iterator():
            total += 1
            pwd = u.password or ""
            # Django 哈希通常含 "$"（如 pbkdf2_sha256$...）
            if "$" in pwd:
                continue
            # 识别常见遗留：纯 md5/sha256 hex 或明文（无前缀）
            if md5_re.match(pwd) or sha256_re.match(pwd) or pwd:
                changed += 1
                if not dry_run:
                    u.set_unusable_password()
                    u.save(update_fields=["password"])

        self.stdout.write(self.style.SUCCESS(f"scanned={total}, changed={changed}, dry_run={dry_run}"))

