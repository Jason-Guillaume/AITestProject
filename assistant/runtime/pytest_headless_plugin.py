"""
pytest 最早阶段安装 Selenium 无头补丁，使 POM / pytest 工程无需手写读 HEADLESS_MODE。

由环境变量 PYTEST_PLUGINS=assistant.runtime.pytest_headless_plugin 加载。
"""

from __future__ import annotations


def pytest_load_initial_conftests(early_config, parser, args) -> None:  # noqa: ARG001
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    rs = str(root)
    if rs not in sys.path:
        sys.path.insert(0, rs)
    from assistant.runtime.browser_env_patch import install

    install()
