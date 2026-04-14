"""
远程日志路径校验：降低命令注入与异常 shell 元字符风险（路径仍经 shlex.quote / PowerShell LiteralPath）。
"""

from __future__ import annotations


def validate_remote_log_path(path: str, server_type: str) -> str | None:
    """
    合法返回 None；否则返回简短中文错误说明。
    """
    p = (path or "").strip()
    if not p:
        return "日志路径不能为空"
    if len(p) > 2048:
        return "路径过长"

    forbidden = "\x00\r\n;$`"
    if any(ch in p for ch in forbidden):
        return "路径包含不允许的字符（换行、分号、反引号等）"
    if "$(" in p or "${" in p:
        return "路径包含疑似命令替换片段"

    st = str(server_type or "linux").lower()
    if st == "linux" and not p.startswith("/"):
        return "Linux 主机须使用绝对路径（以 / 开头）"
    return None
