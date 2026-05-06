"""
Java「无 pom.xml 线性」运行依赖：预下载到仓库根 ``java_linear_runtime/jars`` 后，
由 ``launch_java_linear.py`` 做 javac + JUnit Console Launcher。

运维/开发在本机执行::

    python manage.py build_java_linear_runtime

需要已安装 Maven 与 JDK。
"""
from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import List, Optional


def _repo_root() -> Path:
    # assistant/utils/java_linear_runtime.py -> parents[2] = 项目根
    return Path(__file__).resolve().parents[2]


def default_jars_dir() -> Path:
    return _repo_root() / "java_linear_runtime" / "jars"


def is_java_linear_runtime_ready(jars_dir: Optional[Path] = None) -> bool:
    d = jars_dir or default_jars_dir()
    if not d.is_dir():
        return False
    if not list(d.glob("junit-platform-console-standalone*.jar")):
        return False
    # copy-dependencies 后至少应有 console + 若干传递 jar；阈值不宜过高以免未拉全时误判为「未就绪」
    return len(list(d.glob("*.jar"))) >= 2


def java_source_needs_linear_runtime(entry_java_path: str) -> bool:
    """
    判断无 pom 的线性入口是否必须走 javac + 预置 jars（而非 ``java X.java`` 单文件模式）。

    命中则应在未执行 ``build_java_linear_runtime`` 时直接报错，避免误导性的「程序包不存在」。
    """
    try:
        with open(entry_java_path, encoding="utf-8", errors="ignore") as f:
            head = f.read(16000)
    except OSError:
        return False
    needles = (
        "org.junit.jupiter",
        "org.junit.platform",
        "org.junit.Test",
        "junit.framework",
        "org.testng",
        "org.openqa.selenium",
        "import common.",
        "import pages.",
    )
    return any(n in head for n in needles)


def parse_java_fqn(workspace: Path, entry_rel: str) -> str:
    """从入口 .java 文件解析 JUnit --select-class 用的全限定类名。"""
    rel = entry_rel.replace("\\", "/").lstrip("/")
    path = (workspace / rel).resolve()
    if not path.is_file():
        raise ValueError(f"入口文件不存在: {entry_rel}")
    pkg = ""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if s.startswith("package "):
                rest = s[len("package ") :].rstrip(";").strip()
                pkg = rest + "." if rest else ""
                break
    stem = Path(rel).stem
    return f"{pkg}{stem}"


def collect_java_sources(workspace: Path) -> List[Path]:
    """收集工作区内待编译的 .java（排除输出与构建目录）。"""
    skip_parts = {
        ".aitesta_classes",
        "target",
        "build",
        ".git",
        ".idea",
        "node_modules",
        "__pycache__",
    }
    out: List[Path] = []
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in skip_parts]
        for name in files:
            if not name.endswith(".java"):
                continue
            p = Path(root) / name
            out.append(p)
    return sorted(set(out), key=lambda p: str(p).lower())


def build_classpath(jars_dir: Path, classes_dir: Path) -> str:
    jars = sorted(jars_dir.glob("*.jar"))
    sep = os.pathsep
    cp = sep.join(str(j) for j in jars)
    if cp:
        cp = cp + sep + str(classes_dir)
    else:
        cp = str(classes_dir)
    return cp
