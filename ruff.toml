# Ruff：对 Django 中大量 import * 放宽 F403/F405；asgi 需在 setup 后导入子应用路由。
target-version = "py312"
line-length = 120

[lint]
extend-ignore = ["F403", "F405"]

[lint.per-file-ignores]
"AITestProduct/asgi.py" = ["E402"]
