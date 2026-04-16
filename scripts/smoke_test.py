import os
import subprocess
import sys
import time
from pathlib import Path


def _tail_lines(s: str, limit: int = 60) -> str:
    lines = (s or "").splitlines()
    if len(lines) <= limit:
        return "\n".join(lines)
    return "\n".join(lines[-limit:])


def _run_cmd(*, cwd: Path, cmd: list[str], timeout_s: int = 900) -> int:
    t0 = time.time()
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            shell=False,
        )
        dur_ms = int((time.time() - t0) * 1000)
        if p.returncode != 0:
            print(f"[smoke] FAIL rc={p.returncode} dur_ms={dur_ms} cmd={' '.join(cmd)}")
            if p.stdout:
                print("[smoke] stdout_tail:\n" + _tail_lines(p.stdout))
            if p.stderr:
                print("[smoke] stderr_tail:\n" + _tail_lines(p.stderr))
        return p.returncode
    except subprocess.TimeoutExpired as e:
        dur_ms = int((time.time() - t0) * 1000)
        print(f"[smoke] TIMEOUT dur_ms={dur_ms} cmd={' '.join(cmd)}")
        out = getattr(e, "stdout", "") or ""
        err = getattr(e, "stderr", "") or ""
        if out:
            print("[smoke] stdout_tail:\n" + _tail_lines(out))
        if err:
            print("[smoke] stderr_tail:\n" + _tail_lines(err))
        return 124
    except Exception as e:
        print(f"[smoke] ERROR cmd={' '.join(cmd)} error={e!r}")
        return 125


def main():
    root = Path(__file__).resolve().parents[1]
    print(f"[smoke] start root={root} python={sys.executable} py={sys.version.split()[0]}")
    rc = 0

    # A: 依赖/语法层面问题（编译/导入）
    # Avoid compiling virtualenv / built assets / large deps.
    exclude_re = r"(\\\.venv\\|\\node_modules\\|\\frontend\\dist\\|\\frontend\\\.vite\\|\\__pycache__\\)"
    rc |= _run_cmd(cwd=root, cmd=[sys.executable, "-m", "compileall", "-q", "-x", exclude_re, str(root)])

    # B: Django 基础配置/启动检查（可能因 .env / settings / app 配置导致失败）
    rc |= _run_cmd(cwd=root, cmd=[sys.executable, "manage.py", "check"])

    # C: 数据库迁移/连接问题（migrate --check 在部分版本不可用，这里用 showmigrations --plan 作为轻量证据）
    rc |= _run_cmd(cwd=root, cmd=[sys.executable, "manage.py", "showmigrations", "--plan"])

    # D: pytest 冒烟（API 套件依赖已启动的后端与测试账号环境变量）
    if (root / "tests" / "api").exists():
        rc |= _run_cmd(cwd=root, cmd=[sys.executable, "-m", "pytest", "-m", "smoke", "tests/api"], timeout_s=1200)

    # E: 前端构建（若未安装依赖则记录为跳过，不强行 npm install）
    frontend = root / "frontend"
    if (frontend / "package.json").exists():
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        node_modules = frontend / "node_modules"
        if node_modules.exists():
            rc |= _run_cmd(cwd=frontend, cmd=[npm_cmd, "run", "build"], timeout_s=1800)
        else:
            print("[smoke] frontend build skipped (node_modules missing)")

    print(f"[smoke] end rc={int(rc)}")
    return int(rc)


if __name__ == "__main__":
    raise SystemExit(main())

