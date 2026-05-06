"""
无 pom.xml 的 Java 线性工程：在工作区内 javac 全部 .java，再用 JUnit Console Launcher 跑指定测试类。

依赖由 ``python manage.py build_java_linear_runtime`` 下载到项目根 ``java_linear_runtime/jars``。

参数: <workspace> <entry_point相对路径> <jars目录绝对路径>
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _skip_dir(name: str) -> bool:
    return name in {
        ".aitesta_classes",
        "target",
        "build",
        ".git",
        ".idea",
        "node_modules",
        "__pycache__",
    }


def _collect_java(workspace: Path) -> list[Path]:
    out: list[Path] = []
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if not _skip_dir(d)]
        for fn in files:
            if fn.endswith(".java"):
                out.append(Path(root) / fn)
    return sorted(set(out), key=lambda p: str(p).lower())


def _parse_fqn(entry_file: Path) -> str:
    pkg = ""
    with open(entry_file, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if s.startswith("package "):
                rest = s[len("package ") :].rstrip(";").strip()
                pkg = rest + "." if rest else ""
                break
    return f"{pkg}{entry_file.stem}"


def main() -> int:
    if len(sys.argv) < 4:
        print(
            "usage: python -u launch_java_linear.py <workspace> <entry.java> <jars_dir>",
            file=sys.stderr,
        )
        return 2
    workspace = Path(sys.argv[1]).resolve()
    entry_rel = sys.argv[2].replace("\\", "/")
    jars_dir = Path(sys.argv[3]).resolve()
    entry_file = (workspace / entry_rel).resolve()
    if not workspace.is_dir():
        print(f"工作区不存在: {workspace}", file=sys.stderr)
        return 2
    if not entry_file.is_file():
        print(f"入口文件不存在: {entry_file}", file=sys.stderr)
        return 2
    if not jars_dir.is_dir():
        print(f"jars 目录不存在: {jars_dir}", file=sys.stderr)
        return 2

    consoles = sorted(jars_dir.glob("junit-platform-console-standalone*.jar"))
    if not consoles:
        print(
            "未找到 junit-platform-console-standalone*.jar，请先执行: python manage.py build_java_linear_runtime",
            file=sys.stderr,
        )
        return 2
    console_jar = consoles[0]

    out_dir = workspace / ".aitesta_classes"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    java_files = _collect_java(workspace)
    if not java_files:
        print("工作区内未发现任何 .java 文件", file=sys.stderr)
        return 2

    sep = os.pathsep
    jars_sorted = sorted(jars_dir.glob("*.jar"))
    jar_cp = sep.join(str(j) for j in jars_sorted)
    if not jar_cp.strip():
        print(
            "jars 目录下没有任何 .jar，请先执行: python manage.py build_java_linear_runtime",
            file=sys.stderr,
        )
        return 2
    compile_cp = jar_cp
    javac = shutil.which("javac")
    java = shutil.which("java")
    if not javac or not java:
        print("PATH 中未找到 javac/java，请安装 JDK 并配置环境变量", file=sys.stderr)
        return 2

    # Windows 命令行长度限制：使用 @argfile；路径用正斜杠减少 javac 解析问题
    argfile = out_dir / "javac_sources.txt"
    ws_res = workspace.resolve()
    source_lines: list[str] = []
    for p in java_files:
        pr = p.resolve()
        try:
            rel = pr.relative_to(ws_res)
            source_lines.append(str(rel).replace("\\", "/"))
        except ValueError:
            source_lines.append(str(pr).replace("\\", "/"))

    lines = ["-encoding", "UTF-8", "-cp", compile_cp.replace("\\", "/"), "-d", str(out_dir).replace("\\", "/")]
    lines.extend(source_lines)
    argfile.write_text("\n".join(lines) + "\n", encoding="utf-8")

    r = subprocess.run(
        [javac, f"@{argfile.resolve()}"],
        cwd=str(workspace),
        capture_output=False,
    )
    if r.returncode != 0:
        print(
            "javac 失败：请确认已执行 python manage.py build_java_linear_runtime；"
            "若仍报「程序包 pages/common 不存在」，请将含 common/、pages/ 等目录的完整工程解压到工作区。",
            file=sys.stderr,
        )
        return r.returncode

    fqn = _parse_fqn(entry_file)
    run_cp = jar_cp + sep + str(out_dir)
    cmd = [
        java,
        "-jar",
        str(console_jar),
        "execute",
        "--class-path",
        run_cp,
        "--select-class",
        fqn,
    ]
    r2 = subprocess.run(cmd, cwd=str(workspace))
    return r2.returncode


if __name__ == "__main__":
    raise SystemExit(main())
