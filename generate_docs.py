"""Documentation Generation Script

This script scans the project's backend (Python) and frontend (JavaScript/TypeScript/HTML) files
to produce Markdown documentation summarising:

1. **Technology usage** – which technologies/libraries are imported/required in each file.
2. **File overview** – a brief description of what each file does, derived from the module
   docstring (for Python) or the first comment block (for frontend files).

The generated documentation is written into the ``开发文档`` directory as:

* ``backend_technology_doc.md`` – backend technologies per file.
* ``backend_overview.md`` – backend file purpose overview.
* ``frontend_technology_doc.md`` – frontend technologies per file.
* ``frontend_overview.md`` – frontend file purpose overview.

The script uses static analysis (``ast`` for Python) and regular expressions for frontend files.
"""

import ast
import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DOCS_DIR = PROJECT_ROOT / "开发文档"


def ensure_docs_dir():
    """Create the documentation directory if it does not exist."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)


def write_md(path: Path, content: str):
    """Write the given content to a Markdown file using UTF‑8 encoding."""
    with path.open("w", encoding="utf-8") as f:
        f.write(content)


def get_python_file_info(py_path: Path):
    """Extract imports and module docstring from a Python file.

    Returns a tuple ``(imports, description)`` where ``imports`` is a set of top‑level imported
    module names and ``description`` is the first line of the module docstring or the first
    top‑level comment.
    """
    try:
        source = py_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = set()
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        docstring = ast.get_docstring(tree) or ""
        description = docstring.strip().split("\n")[0]
        if not description:
            # Fallback to first comment line starting with '#'
            for line in source.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    description = stripped.lstrip("# ")
                    break
        return imports, description
    except Exception as e:
        return set(), f"[Error: {e}]"


def scan_backend():
    """Gather backend (Python) information.

    Two kinds of documentation are produced:
    1. *File‑centric* – ``backend_technology_doc.md`` lists, for each file, the
       imported third‑party modules, and ``backend_overview.md`` provides a one‑line
       purpose description.
    2. *Technology‑centric* – ``backend_technology_by_tech.md`` groups files by
       the technology they import, so readers can see *which files use a given
       library*.
    """
    backend_dir = PROJECT_ROOT / "AITestProduct"
    file_tech_entries = []
    overview_entries = []
    tech_to_files: dict[str, list[str]] = {}
    for py_file in backend_dir.rglob("*.py"):
        rel = py_file.relative_to(PROJECT_ROOT)
        imports, desc = get_python_file_info(py_file)
        # File‑centric entries
        file_tech_entries.append(f"- **{rel}**: {', '.join(sorted(imports)) or 'No imports'}")
        overview_entries.append(f"- **{rel}**: {desc or 'No description'}")
        # Build tech‑centric mapping
        for tech in imports:
            tech_to_files.setdefault(tech, []).append(str(rel))
    write_md(DOCS_DIR / "backend_technology_doc.md", "# Backend Technology Usage\n\n" + "\n".join(file_tech_entries))
    write_md(DOCS_DIR / "backend_overview.md", "# Backend File Overview\n\n" + "\n".join(overview_entries))
    # Write technology‑centric doc
    tech_lines = ["# Backend Technology Usage (by technology)\n"]
    for tech in sorted(tech_to_files):
        tech_lines.append(f"## {tech}\n")
        for file_path in sorted(tech_to_files[tech]):
            tech_lines.append(f"- {file_path}")
        tech_lines.append("")
    write_md(DOCS_DIR / "backend_technology_by_tech.md", "\n".join(tech_lines))


def get_frontend_file_info(file_path: Path):
    """Extract import statements and a brief description from JS/TS/Vue/HTML/CSS files.

    Returns ``(imports, description)`` similar to the Python counterpart.
    """
    try:
        text = file_path.read_text(encoding="utf-8")
        # Match ES6 imports and CommonJS require statements
        import_pattern = re.compile(r"^\s*(?:import\s+.*?from\s+|require\(['\"])([^'\"]+)['\"]", re.MULTILINE)
        imports = {m.group(1).split("/")[0] for m in import_pattern.finditer(text)}
        # Find first comment block (/* ... */) or line comment //
        comment_match = re.search(r"/\*\s*(.*?)\s*\*/|//\s*(.*)", text, re.DOTALL)
        description = ""
        if comment_match:
            description = (comment_match.group(1) or comment_match.group(2) or "").strip().split("\n")[0]
        return imports, description
    except Exception as e:
        return set(), f"[Error: {e}]"


def scan_frontend():
    """Gather frontend (JS/TS/Vue) information.

    Similar to ``scan_backend`` we emit three Markdown files:
    * ``frontend_technology_doc.md`` – file‑centric list of imports.
    * ``frontend_overview.md`` – file‑centric brief description.
    * ``frontend_technology_by_tech.md`` – technology‑centric mapping of files.
    """
    frontend_dir = PROJECT_ROOT / "frontend"
    file_tech_entries = []
    overview_entries = []
    tech_to_files: dict[str, list[str]] = {}
    patterns = ("*.js", "*.ts", "*.vue", "*.html")
    for pattern in patterns:
        for file_path in frontend_dir.rglob(pattern):
            if "node_modules" in file_path.parts:
                continue
            rel = file_path.relative_to(PROJECT_ROOT)
            imports, desc = get_frontend_file_info(file_path)
            file_tech_entries.append(f"- **{rel}**: {', '.join(sorted(imports)) or 'No imports'}")
            overview_entries.append(f"- **{rel}**: {desc or 'No description'}")
            for tech in imports:
                tech_to_files.setdefault(tech, []).append(str(rel))
    write_md(DOCS_DIR / "frontend_technology_doc.md", "# Frontend Technology Usage\n\n" + "\n".join(file_tech_entries))
    write_md(DOCS_DIR / "frontend_overview.md", "# Frontend File Overview\n\n" + "\n".join(overview_entries))
    # Technology‑centric doc for frontend
    tech_lines = ["# Frontend Technology Usage (by technology)\n"]
    for tech in sorted(tech_to_files):
        tech_lines.append(f"## {tech}\n")
        for file_path in sorted(tech_to_files[tech]):
            tech_lines.append(f"- {file_path}")
        tech_lines.append("")
    write_md(DOCS_DIR / "frontend_technology_by_tech.md", "\n".join(tech_lines))


def main():
    ensure_docs_dir()
    scan_backend()
    scan_frontend()
    print("Documentation generation completed. Files are located in the '开发文档' directory.")


if __name__ == "__main__":
    main()