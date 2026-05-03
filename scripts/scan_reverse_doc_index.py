# -*- coding: utf-8 -*-
"""Regenerate 开发文档/逆向技术文档/规划与磁盘对照扫描.md from 子功能文档全量索引.md."""
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_ROOT = ROOT / "开发文档" / "逆向技术文档"
INDEX = DOC_ROOT / "子功能文档全量索引.md"
OUT = DOC_ROOT / "规划与磁盘对照扫描.md"


def main() -> None:
    text = INDEX.read_text(encoding="utf-8")
    planned = re.findall(r"\|\s*`([^`]+\.md)`\s*\|", text)
    existing_rel = {p.relative_to(DOC_ROOT).as_posix() for p in DOC_ROOT.rglob("*.md")}
    skip_extra = {"子功能文档全量索引.md", "撰写进度.md", "命名与结构规范.md", "规划与磁盘对照扫描.md"}

    missing = [p for p in planned if p not in existing_rel]
    extra = sorted(existing_rel - set(planned) - skip_extra)

    folder_order: list[str] = []
    for p in planned:
        top = p.split("/")[0]
        if top not in folder_order:
            folder_order.append(top)

    sections: dict[str, dict] = defaultdict(lambda: {"ok": 0, "miss": 0})
    for p in planned:
        top = p.split("/")[0]
        if p in existing_rel:
            sections[top]["ok"] += 1
        else:
            sections[top]["miss"] += 1

    lines = [
        "# 规划路径 vs 磁盘对照（自动生成）",
        "",
        "> 重新生成：`python scripts/scan_reverse_doc_index.py`",
        "",
        f"- **索引规划文件数**：{len(planned)}",
        f"- **已存在（相对 `开发文档/逆向技术文档/`）**：{len(planned) - len(missing)}",
        f"- **缺失**：{len(missing)}",
        f"- **磁盘上存在但未列入索引的 .md**（已排除索引/进度/规范/本对照表）：{len(extra)}",
        "",
        "## 按一级目录汇总",
        "",
        "| 目录 | 已有/规划 | 缺失 |",
        "|------|-----------|------|",
    ]
    for top in folder_order:
        s = sections[top]
        tot = s["ok"] + s["miss"]
        lines.append(f"| `{top}/` | {s['ok']}/{tot} | {s['miss']} |")

    lines.extend(["", "## 缺失文件清单（逐条）", ""])
    for p in missing:
        lines.append(f"- [ ] `{p}`")

    if extra:
        lines.extend(["", "## 未编入索引的现有文件", ""])
        for p in extra:
            lines.append(f"- `{p}`")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}  planned={len(planned)} missing={len(missing)} extra={len(extra)}")


if __name__ == "__main__":
    main()
