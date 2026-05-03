"""
unittest 启动器：先安装 Selenium 无头补丁，再在同一进程内执行 unittest CLI。

用于 POM / unittest 工程在平台勾选「无头」时与线性脚本、pytest 行为一致。
"""
from __future__ import annotations

import sys
from pathlib import Path


def _ensure_project_root_on_path() -> None:
    root = Path(__file__).resolve().parents[2]
    rs = str(root)
    if rs not in sys.path:
        sys.path.insert(0, rs)


def main() -> None:
    _ensure_project_root_on_path()
    from assistant.runtime.browser_env_patch import install

    install()

    from unittest.main import main as unittest_main

    argv = [sys.argv[0]] + sys.argv[1:]
    unittest_main(module=None, argv=argv)


if __name__ == "__main__":
    main()
