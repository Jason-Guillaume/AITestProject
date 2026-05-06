"""
将 JUnit 5 + Selenium 等依赖下载到 ``<项目根>/java_linear_runtime/jars``，
供无 ``pom.xml`` 的 Java 线性脚本通过 ``launch_java_linear.py`` 编译与执行。

用法::

    python manage.py build_java_linear_runtime

需要本机已安装 ``mvn``（Maven）与网络。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "下载 Java 线性运行时依赖（JUnit5 + Selenium）到 java_linear_runtime/jars"

    def handle(self, *args, **options):
        base = Path(settings.BASE_DIR)
        skel = base / "assistant" / "runtime" / "java_linear_skeleton" / "pom.xml"
        if not skel.is_file():
            self.stderr.write(self.style.ERROR(f"未找到 {skel}"))
            return
        jars = base / "java_linear_runtime" / "jars"
        jars.mkdir(parents=True, exist_ok=True)

        cmd = [
            "mvn",
            "-f",
            str(skel),
            "-q",
            "dependency:copy-dependencies",
            f"-DoutputDirectory={jars}",
        ]
        self.stdout.write("执行: " + " ".join(cmd))
        try:
            subprocess.check_call(cmd, cwd=str(skel.parent))
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR("未找到 mvn 命令，请安装 Maven 并加入 PATH"))
            raise SystemExit(1)
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f"Maven 执行失败: {e}"))
            raise SystemExit(e.returncode)

        n = len(list(jars.glob("*.jar")))
        self.stdout.write(self.style.SUCCESS(f"完成，共 {n} 个 jar 已写入 {jars}"))
