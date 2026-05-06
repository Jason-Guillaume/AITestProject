"""java_linear_runtime 纯函数单测（不依赖 Maven）。"""
from __future__ import annotations

from pathlib import Path

from assistant.utils.java_linear_runtime import (
    collect_java_sources,
    java_source_needs_linear_runtime,
    parse_java_fqn,
)


def test_parse_java_fqn_with_package(tmp_path: Path) -> None:
    p = tmp_path / "x" / "T.java"
    p.parent.mkdir(parents=True)
    p.write_text("package x.demo;\npublic class T {}\n", encoding="utf-8")
    assert parse_java_fqn(tmp_path, "x/T.java") == "x.demo.T"


def test_parse_java_fqn_default_package(tmp_path: Path) -> None:
    p = tmp_path / "Run.java"
    p.write_text("public class Run {}\n", encoding="utf-8")
    assert parse_java_fqn(tmp_path, "Run.java") == "Run"


def test_java_source_needs_linear_runtime(tmp_path: Path) -> None:
    plain = tmp_path / "Main.java"
    plain.write_text("public class Main { public static void main(String[] a) {} }", encoding="utf-8")
    assert not java_source_needs_linear_runtime(str(plain))

    junit = tmp_path / "T.java"
    junit.write_text("import org.junit.jupiter.api.Test;\nclass T {}\n", encoding="utf-8")
    assert java_source_needs_linear_runtime(str(junit))

    pages = tmp_path / "P.java"
    pages.write_text("import pages.LoginPage;\nclass P {}\n", encoding="utf-8")
    assert java_source_needs_linear_runtime(str(pages))


def test_collect_java_sources_skips_build_dirs(tmp_path: Path) -> None:
    (tmp_path / "A.java").write_text("class A {}", encoding="utf-8")
    tgt = tmp_path / "target"
    tgt.mkdir(parents=True)
    (tgt / "B.java").write_text("class B {}", encoding="utf-8")
    found = collect_java_sources(tmp_path)
    assert any(f.name == "A.java" for f in found)
    assert not any("target" in str(f) for f in found)
