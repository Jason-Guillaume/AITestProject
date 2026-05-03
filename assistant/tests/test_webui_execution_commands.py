"""WebUI 执行链路：命令构建（无真实浏览器、无 Redis）。"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from assistant.models import UIScriptUpload
from assistant.utils.multi_framework_runner import MultiFrameworkRunner


@pytest.fixture
def workspace_tmp(tmp_path: Path) -> Path:
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_a(): pass\n", encoding="utf-8")
    return tmp_path


def _script(**kwargs: object) -> MagicMock:
    s = MagicMock(spec=UIScriptUpload)
    for k, v in kwargs.items():
        setattr(s, k, v)
    s.build_config = {}
    return s


def test_linear_headless_prepends_launcher(workspace_tmp: Path) -> None:
    script = _script(
        script_type=UIScriptUpload.ScriptType.LINEAR,
        language="PYTHON",
        framework="PYTEST",
        entry_point="main.py",
    )
    runner = MultiFrameworkRunner(
        script, str(workspace_tmp), execution_config={"headless": True}
    )
    cmd = runner.build_command()
    assert sys.executable in cmd[0] or cmd[0].endswith("python.exe") or "python" in cmd[0].lower()
    joined = " ".join(cmd)
    assert "launch_ui_entry.py" in joined
    assert str(workspace_tmp / "main.py") in cmd[-1] or cmd[-1].endswith("main.py")


def test_linear_headed_no_launcher(workspace_tmp: Path) -> None:
    script = _script(
        script_type=UIScriptUpload.ScriptType.LINEAR,
        language="PYTHON",
        framework="PYTEST",
        entry_point="main.py",
    )
    runner = MultiFrameworkRunner(
        script, str(workspace_tmp), execution_config={"headless": False}
    )
    cmd = runner.build_command()
    joined = " ".join(cmd)
    assert "launch_ui_entry.py" not in joined
    assert cmd[-1].endswith("main.py") or "main.py" in cmd[-1]


def test_pom_pytest_uses_pytest(workspace_tmp: Path) -> None:
    script = _script(
        script_type=UIScriptUpload.ScriptType.POM,
        language="PYTHON",
        framework="PYTEST",
        entry_point="tests",
    )
    runner = MultiFrameworkRunner(script, str(workspace_tmp), execution_config={"headless": True})
    cmd = runner.build_command()
    assert cmd[0] == "pytest"
    assert any("tests" in str(c) for c in cmd)


def test_pom_unittest_headless_uses_launch_ui_entry_for_direct_py(workspace_tmp: Path) -> None:
    """工作空间路径含非法包名段（如 5.2）时走 python -u run.py，无头应经 launch_ui_entry。"""
    bad = workspace_tmp / "5.2"
    bad.mkdir()
    run_py = bad / "run.py"
    run_py.write_text("# unittest pom\n", encoding="utf-8")
    script = _script(
        script_type=UIScriptUpload.ScriptType.POM,
        language="PYTHON",
        framework="UNITTEST",
        entry_point="5.2/run.py",
    )
    runner = MultiFrameworkRunner(script, str(workspace_tmp), execution_config={"headless": True})
    cmd = runner.build_command()
    joined = " ".join(str(c) for c in cmd)
    assert "launch_ui_entry.py" in joined
    assert str(run_py.resolve()) in joined or joined.endswith("run.py")


def test_pom_unittest_headless_uses_launch_ui_unittest_for_m(tmp_path: Path) -> None:
    pkg = tmp_path / "uimod"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "test_x.py").write_text(
        "import unittest\nclass T(unittest.TestCase):\n def test_a(self): pass\n",
        encoding="utf-8",
    )
    script = _script(
        script_type=UIScriptUpload.ScriptType.POM,
        language="PYTHON",
        framework="UNITTEST",
        entry_point="uimod/test_x.py",
    )
    runner = MultiFrameworkRunner(script, str(tmp_path), execution_config={"headless": True})
    cmd = runner.build_command()
    joined = " ".join(str(c) for c in cmd)
    assert "launch_ui_unittest.py" in joined
    assert cmd[1] == "-u" and "launch_ui_unittest.py" in str(cmd[2])
    assert not (len(cmd) >= 3 and cmd[1] == "-m" and cmd[2] == "unittest")
