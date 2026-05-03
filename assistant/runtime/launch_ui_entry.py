"""
线性脚本启动器：先安装浏览器无头补丁，再以 __main__ 方式执行用户入口文件。

由 MultiFrameworkRunner._build_linear_command 引用，勿单独依赖工作目录导入 assistant。
"""
from __future__ import annotations

import sys
from pathlib import Path


def _ensure_project_root_on_path() -> None:
    # .../assistant/runtime/launch_ui_entry.py -> repo root = parents[2]
    root = Path(__file__).resolve().parents[2]
    rs = str(root)
    if rs not in sys.path:
        sys.path.insert(0, rs)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -u launch_ui_entry.py <script.py> [argv...]")
    _ensure_project_root_on_path()
    from assistant.runtime.browser_env_patch import install

    install()

    script = sys.argv[1]
    sys.argv = [script] + sys.argv[2:]
    import runpy

    runpy.run_path(script, run_name="__main__")


if __name__ == "__main__":
    main()
