#!/usr/bin/env python3
"""Build docs/file-index/: a one-line explanation for every tracked file in the repo.

Each tracked file (``git ls-files``) gets one table row. The explanation is taken from the
file itself, in this order of preference:

* ``doc``     -- text the author wrote: module docstring, leading comment block, Markdown
  title / front-matter description, HTML ``<title>``, workflow ``name:``, package description.
* ``derived`` -- no author-written header exists, so the row is inferred from structure:
  defined classes/functions, exported symbols, test names, JSON/YAML top-level keys, etc.
* ``meta``    -- binary or opaque content; only type and size are reported.

Nothing is invented: a ``derived`` row lists what the parser found and nothing more.

Usage::

    python scripts/docs/build_file_index.py           # regenerate docs/file-index/
    python scripts/docs/build_file_index.py --check   # exit 1 if the index is stale
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "docs" / "file-index"
MAX_READ = 2_000_000  # bytes; larger files are described by metadata only
MAX_DESC = 170

CODE_EXT = {".ts", ".tsx", ".js", ".cjs", ".mjs", ".jsx", ".rs", ".go", ".c", ".h", ".cpp", ".java", ".css", ".proto"}
HASH_EXT = {".sh", ".bash", ".ps1", ".psm1", ".toml", ".cfg", ".ini", ".conf", ".env", ".rb", ".tf", ".r", ".mk"}
BINARY_EXT = {
    ".png": "PNG image",
    ".jpg": "JPEG image",
    ".jpeg": "JPEG image",
    ".gif": "GIF image",
    ".webp": "WebP image",
    ".ico": "Icon",
    ".svg": "SVG image",
    ".pdf": "PDF document",
    ".zip": "ZIP archive",
    ".gz": "gzip archive",
    ".wav": "WAV audio",
    ".mp3": "MP3 audio",
    ".mp4": "MP4 video",
    ".woff": "Web font",
    ".woff2": "Web font",
    ".ttf": "TrueType font",
    ".docx": "Word document",
    ".xlsx": "Excel workbook",
    ".pptx": "PowerPoint deck",
    ".npy": "NumPy array",
    ".npz": "NumPy archive",
    ".pkl": "Python pickle",
    ".pt": "PyTorch tensor/checkpoint",
    ".bin": "Binary blob",
    ".db": "Database file",
    ".sqlite": "SQLite database",
    ".parquet": "Parquet table",
    ".epub": "EPUB book",
    ".lock": "Lockfile",
}
STANDARD_FILES = {
    ".gitignore": "Git ignore rules",
    ".gitattributes": "Git path attributes (line endings, diff/merge drivers)",
    ".gitmodules": "Git submodule registry (path -> URL)",
    ".gitkeep": "Placeholder that keeps an otherwise empty directory tracked",
    ".prettierrc": "Prettier formatting options",
    ".prettierignore": "Paths Prettier must not format",
    ".flake8": "flake8 lint configuration",
    ".firebaserc": "Firebase CLI project aliases",
    ".npmignore": "Paths excluded from the published npm tarball",
    ".dockerignore": "Paths excluded from the Docker build context",
    ".vercelignore": "Paths excluded from Vercel deployments",
    ".nvmrc": "Pinned Node.js version",
    ".python-version": "Pinned Python version",
    "package-lock.json": "npm lockfile (exact dependency versions)",
    "pnpm-lock.yaml": "pnpm lockfile (exact dependency versions)",
    "yarn.lock": "Yarn lockfile (exact dependency versions)",
    "cargo.lock": "Cargo lockfile (exact crate versions)",
    "poetry.lock": "Poetry lockfile (exact dependency versions)",
    "py.typed": "PEP 561 marker: the package ships type hints",
}
COMMENT_PREFIX = re.compile(r"^(#+|;+|//+|--+|%+|REM\b|::)\s*", re.I)
NOISE_COMMENT = re.compile(
    r"^(!|-\*-|coding[:=]|type:|noqa|pylint|flake8|eslint|prettier|ts-|@ts-|jshint|global |istanbul|"
    r"copyright|spdx|license|requires |usr/bin|vim:|shellcheck|region|nolint|mypy:|ruff:|fmt:|isort:)",
    re.I,
)
TAG_LINE = re.compile(r"^@(\w+)\s*(.*)$")


def sh(*args: str) -> str:
    """Run a git command in the repo and return stdout."""
    return subprocess.check_output(args, cwd=REPO, text=True)


def clean(text: str) -> str:
    """Collapse to one table-safe line of at most MAX_DESC characters."""
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip("=-*#~_ ").strip()
    if len(text) > MAX_DESC:
        text = text[: MAX_DESC - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return text.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def first_sentence(text: str) -> str:
    """First paragraph of a docstring/comment, cut at the first sentence end if it is long."""
    para = text.strip().split("\n\n", 1)[0]
    kept = [ln for ln in para.splitlines() if not re.fullmatch(r"\s*[=\-~*_#]{3,}\s*", ln)]
    para = (
        " — ".join(kept[:2]) + (" " + " ".join(kept[2:]) if len(kept) > 2 else "")
        if kept != para.splitlines()
        else para
    )
    para = re.sub(r"\s+", " ", para).strip()
    m = re.match(r"^(.{25,}?[.!?])\s", para + " ")
    return m.group(1) if m and len(para) > MAX_DESC else para


def names(items: List[str], limit: int = 6) -> str:
    """Comma-join up to ``limit`` names, noting how many were omitted."""
    extra = len(items) - limit
    return ", ".join(items[:limit]) + (f" (+{extra} more)" if extra > 0 else "")


def meaningful(line: str) -> bool:
    """True if a comment line carries prose rather than a directive or decoration."""
    return bool(re.search(r"[A-Za-z]{3}", line)) and not NOISE_COMMENT.match(line)


def leading_hash_comment(text: str) -> Optional[str]:
    """Prose from the leading ``#`` comment block (PowerShell ``<# #>`` handled too)."""
    m = re.match(r"\s*(?:#!.*\n)?\s*<#(.*?)#>", text, re.S)
    if m:
        body = re.sub(r"^\s*\.(SYNOPSIS|DESCRIPTION)\s*$", "", m.group(1), flags=re.M | re.I)
        body = re.split(r"^\s*\.[A-Z]+", body.strip(), maxsplit=1, flags=re.M)[0]
        if meaningful(body.strip()):
            return first_sentence(body)
    out: List[str] = []
    for raw in text.splitlines()[:40]:
        line = raw.strip()
        if not line:
            if out:
                break
            continue
        if not line.startswith("#"):
            break
        body = line.lstrip("#").strip()
        if not meaningful(body):
            if out:
                break
            continue
        out.append(body)
    return first_sentence(" ".join(out)) if out else None


def leading_c_comment(text: str) -> Optional[str]:
    """Prose from a leading ``/* */`` or ``//`` block; falls back to @file/@module tags."""
    body = text.lstrip("\ufeff \t\r\n")
    if body.startswith("#!"):
        body = body.split("\n", 1)[1].lstrip() if "\n" in body else ""
    body = re.sub(r"^(['\"]use (strict|client|server)['\"];?\s*)+", "", body)
    lines: List[str] = []
    if body.startswith("/*"):
        block = body[2:].split("*/", 1)[0]
        lines = [ln.strip().lstrip("*").strip() for ln in block.splitlines()]
    elif body.startswith("//"):
        for raw in body.splitlines():
            if not raw.strip().startswith("//"):
                break
            lines.append(raw.strip().lstrip("/").strip())
    prose: List[str] = []
    tags: Dict[str, str] = {}
    for ln in lines:
        tag = TAG_LINE.match(ln)
        if tag:
            if tag.group(1) in ("description", "fileoverview", "overview", "summary") and tag.group(2):
                prose.append(tag.group(2))
            else:
                tags.setdefault(tag.group(1), tag.group(2))
            if prose and tag.group(1) not in ("description", "fileoverview", "overview", "summary"):
                break
            continue
        if not ln:
            if prose:
                break
            continue
        if meaningful(ln):
            prose.append(ln)
    if prose:
        return first_sentence(" ".join(prose))
    parts = [f"{k}: {tags[k]}" for k in ("component", "module", "layer", "file") if tags.get(k)]
    return "; ".join(parts) if parts else None


def describe_python(text: str, name: str) -> Tuple[str, str]:
    """Docstring, else leading comment, else defined symbols."""
    if not text.strip():
        return ("Empty package marker" if name == "__init__.py" else "Empty file"), "meta"
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return f"Does not parse as Python (SyntaxError line {exc.lineno})", "derived"
    doc = ast.get_docstring(tree)
    if doc and meaningful(doc):
        return first_sentence(doc), "doc"
    if not tree.body and re.search(r"^#\s*(import|from|def|class)\s", text, re.M):
        return f"All code is commented out ({text.count(chr(10)) + 1} lines)", "derived"
    comment = leading_hash_comment(text)
    if comment:
        return comment, "doc"
    classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    tests = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    tests = [t for t in tests if t.startswith("test_")]
    if name.startswith("test_") or name.endswith("_test.py"):
        if tests:
            return f"{len(tests)} tests: {names(tests, 4)}", "derived"
    parts = []
    if classes:
        parts.append("classes " + names(classes))
    if funcs:
        parts.append("functions " + names(funcs))
    if parts:
        return "Defines " + "; ".join(parts), "derived"
    imports = sorted(
        {
            (n.module or "").split(".")[0] if isinstance(n, ast.ImportFrom) else n.names[0].name.split(".")[0]
            for n in tree.body
            if isinstance(n, (ast.Import, ast.ImportFrom))
        }
        - {""}
    )
    if name == "__init__.py":
        return "Package init" + (f"; re-exports from {names(imports)}" if imports else ""), "derived"
    return "Top-level script" + (f" using {names(imports)}" if imports else ""), "derived"


def describe_code(text: str, name: str) -> Tuple[str, str]:
    """Leading comment, else test suite names, else exported/declared symbols."""
    if not text.strip():
        return "Empty file", "meta"
    comment = leading_c_comment(text)
    if comment:
        return comment, "doc"
    if re.search(r"\.(test|spec)\.[cm]?[jt]sx?$", name):
        suites = re.findall(r"\bdescribe\(\s*['\"`]([^'\"`]+)", text)
        cases = len(re.findall(r"\b(?:it|test)\(\s*['\"`]", text))
        if suites or cases:
            return f"{cases} test cases" + (f" in suites: {names(suites, 3)}" if suites else ""), "derived"
    exports = re.findall(
        r"^export\s+(?:default\s+)?(?:async\s+)?(?:abstract\s+)?"
        r"(?:function\*?|class|const|let|interface|type|enum)\s+([A-Za-z_$][\w$]*)",
        text,
        re.M,
    )
    exports += re.findall(r"^(?:module\.)?exports\.([A-Za-z_$][\w$]*)\s*=", text, re.M)
    exports += re.findall(r"^pub\s+(?:async\s+)?(?:fn|struct|enum|trait|mod)\s+([A-Za-z_]\w*)", text, re.M)
    for group in re.findall(r"^(?:export\s*|module\.exports\s*=\s*)\{([^}]*)\}", text, re.M):
        exports += [g.split(":")[0].split(" as ")[-1].strip() for g in group.split(",") if g.strip()]
    exports = [e for e in dict.fromkeys(exports) if re.match(r"^[A-Za-z_$][\w$]*$", e)]
    extras = []
    if re.search(r"^export\s+default\b|^module\.exports\s*=\s*(?:async\s+)?(?:function|\()", text, re.M):
        extras.append("default handler/export")
    routes = list(dict.fromkeys(re.findall(r"\bpath:\s*['\"`](/[^'\"`]+)", text)))
    if routes:
        extras.append("route " + names(routes, 3))
    tail = ("; " + "; ".join(extras)) if extras else ""
    if exports:
        return "Exports " + names(exports) + tail, "derived"
    decls = re.findall(r"^(?:async\s+)?(?:function|class|fn)\s+([A-Za-z_$][\w$]*)", text, re.M)
    decls = list(dict.fromkeys(decls))
    if decls:
        return "Declares " + names(decls) + tail, "derived"
    deps = re.findall(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)", text)
    deps += re.findall(r"^import\s[^'\"]*['\"]([^'\"]+)['\"]", text, re.M)
    deps = list(dict.fromkeys(deps))
    if deps:
        return f"{text.count(chr(10)) + 1}-line entry script; loads {names(deps, 5)}" + tail, "derived"
    if extras:
        return "; ".join(extras).capitalize(), "derived"
    if name.endswith(".css"):
        return f"Stylesheet, {len(re.findall(r'{', text))} rule blocks", "derived"
    return f"Script, {text.count(chr(10)) + 1} lines, no exported symbols", "derived"


def describe_markdown(text: str) -> Tuple[str, str]:
    """Front-matter description/title, else first heading, else first prose line."""
    fm = re.match(r"\ufeff?---\s*\n(.*?)\n---\s*\n", text, re.S)
    if fm:
        for key in ("description", "title", "name"):
            m = re.search(rf"^{key}:\s*[\"']?(.+?)[\"']?\s*$", fm.group(1), re.M)
            if m and meaningful(m.group(1)) and m.group(1) not in (">", "|", ">-", "|-"):
                return m.group(1), "doc"
        text = text[fm.end() :]
    m = re.search(r"^#{1,6}\s+(.+?)\s*#*$", text, re.M)
    if m:
        title = re.sub(r"[*`]|\[([^\]]+)\]\([^)]*\)", r"\1", m.group(1)).strip()
        if len(title) < 14:
            for line in text[m.end() :].splitlines():
                body = line.strip()
                if meaningful(body) and not body.startswith(("#", "|", "```", "<", "![", "---")):
                    return f"{title} — {first_sentence(re.sub(r'[*`]', '', body))}", "doc"
        return title, "doc"
    for line in text.splitlines():
        if meaningful(line.strip()):
            return line.strip(), "doc"
    return "Empty document", "meta"


def describe_json(text: str, name: str) -> Tuple[str, str]:
    """Package description, else title/description fields, else top-level shape."""
    if name.endswith(".jsonl"):
        rows = [ln for ln in text.splitlines() if ln.strip()]
        try:
            first = json.loads(rows[0]) if rows else None
        except ValueError:
            first = None
        keys = f"; keys: {names(list(first), 6)}" if isinstance(first, dict) else ""
        return f"JSONL, {len(rows)} records{keys}", "derived"
    try:
        data = json.loads(text)
    except ValueError:
        return "JSON-like file that does not parse as strict JSON (comments or trailing commas)", "derived"
    if isinstance(data, dict):
        for key in ("description", "title", "$comment", "summary"):
            if isinstance(data.get(key), str) and meaningful(data[key]):
                label = f"{data['name']}: " if isinstance(data.get("name"), str) else ""
                return label + data[key], "doc"
        if name == "package.json" and isinstance(data.get("name"), str):
            scripts = list(data.get("scripts") or {})
            return f"npm package {data['name']}" + (f"; scripts: {names(scripts, 6)}" if scripts else ""), "derived"
        if name.startswith("tsconfig") and "compilerOptions" in data:
            opts = data["compilerOptions"]
            bits = [f"{k}={opts[k]}" for k in ("target", "module", "outDir", "rootDir") if k in opts]
            return "TypeScript compiler config" + (f" ({', '.join(bits)})" if bits else ""), "derived"
        return f"JSON object, {len(data)} keys: {names([str(k) for k in data], 7)}", "derived"
    if isinstance(data, list):
        inner = f" of objects with keys {names(list(data[0]), 5)}" if data and isinstance(data[0], dict) else ""
        return f"JSON array, {len(data)} items{inner}", "derived"
    return "JSON scalar", "derived"


def describe_yaml(text: str, path: str) -> Tuple[str, str]:
    """Workflow/compose ``name:``, else leading comment, else top-level keys."""
    m = re.search(r"^name:\s*[\"']?(.+?)[\"']?\s*$", text, re.M)
    if m and meaningful(m.group(1)):
        trig = ""
        if ".github/workflows/" in path:
            on = re.search(r"^(?:on|['\"]on['\"]):\s*(.*(?:\n[ \t]+.*)*)", text, re.M)
            if on:
                events = re.findall(
                    r"\b(push|pull_request|pull_request_target|schedule|workflow_dispatch|workflow_call|release|"
                    r"issues|issue_comment|workflow_run)\b",
                    on.group(1),
                )
                trig = f" (triggers: {', '.join(dict.fromkeys(events))})" if events else ""
        return m.group(1) + trig, "doc"
    comment = leading_hash_comment(text)
    if comment:
        return comment, "doc"
    keys = list(dict.fromkeys(re.findall(r"^([A-Za-z_][\w.-]*):", text, re.M)))
    kinds = list(dict.fromkeys(re.findall(r"^kind:\s*(\S+)", text, re.M)))
    if kinds:
        return f"Kubernetes manifest: {names(kinds)}", "derived"
    return (f"YAML, top-level keys: {names(keys, 7)}" if keys else "YAML document"), "derived"


def describe_notebook(text: str) -> Tuple[str, str]:
    """First Markdown heading of a Jupyter notebook plus cell counts."""
    try:
        cells = json.loads(text).get("cells", [])
    except ValueError:
        return "Jupyter notebook (unparseable JSON)", "derived"
    code = sum(1 for c in cells if c.get("cell_type") == "code")
    for cell in cells:
        if cell.get("cell_type") == "markdown":
            src = "".join(cell.get("source", []))
            m = re.search(r"^#{1,6}\s+(.+)$", src, re.M)
            if m:
                return f"{m.group(1).strip()} ({code} code cells)", "doc"
    return f"Jupyter notebook, {len(cells)} cells ({code} code), no title cell", "derived"


def describe_hash_script(text: str, name: str, ext: str) -> Tuple[str, str]:
    """Shell / PowerShell / config: leading comment, else functions or sections."""
    if not text.strip():
        return "Empty file", "meta"
    comment = leading_hash_comment(text)
    if comment:
        return comment, "doc"
    if ext in (".ps1", ".psm1"):
        funcs = list(dict.fromkeys(re.findall(r"^\s*function\s+([\w-]+)", text, re.M | re.I)))
        params = re.findall(r"\[(?:string|int|switch|bool)[^\]]*\]\s*\$(\w+)", text, re.I)
        bits = []
        if params:
            bits.append("params " + names(list(dict.fromkeys(params)), 5))
        if funcs:
            bits.append("functions " + names(funcs, 5))
        return (
            "PowerShell script" + ("; " + "; ".join(bits) if bits else f", {text.count(chr(10)) + 1} lines"),
            "derived",
        )
    if ext in (".sh", ".bash"):
        funcs = list(dict.fromkeys(re.findall(r"^\s*(?:function\s+)?([\w-]+)\s*\(\)\s*\{", text, re.M)))
        cmds = [ln.split()[0] for ln in text.splitlines() if ln.strip() and not ln.strip().startswith(("#", "set "))]
        if funcs:
            return "Shell script; functions " + names(funcs, 5), "derived"
        return "Shell script; runs " + names(list(dict.fromkeys(cmds)), 6), "derived"
    sections = list(dict.fromkeys(re.findall(r"^\[+([^\]]+)\]+", text, re.M)))
    if sections:
        return f"Config sections: {names(sections, 7)}", "derived"
    keys = list(dict.fromkeys(re.findall(r"^([A-Za-z_][\w.-]*)\s*=", text, re.M)))
    return (f"Settings: {names(keys, 7)}" if keys else f"{name}, {text.count(chr(10)) + 1} lines"), "derived"


def describe(path: str, mode: str, submodules: Dict[str, str]) -> Tuple[str, str]:
    """Return (description, basis) for one tracked path."""
    full = REPO / path
    name = os.path.basename(path)
    ext = os.path.splitext(name)[1].lower()
    if mode == "160000":
        return f"Git submodule → {submodules.get(path, 'no URL in .gitmodules')}", "meta"
    if mode == "120000":
        return f"Symlink → {os.readlink(full)}", "meta"
    if not full.is_file():
        return "Tracked but missing from the working tree", "meta"
    size = full.stat().st_size
    if ext in BINARY_EXT and ext != ".svg":
        return f"{BINARY_EXT[ext]}, {size:,} bytes", "meta"
    if size == 0:
        return ("Empty package marker" if name == "__init__.py" else "Empty file"), "meta"
    if size > MAX_READ:
        return f"Large {ext or 'text'} file, {size:,} bytes (not parsed)", "meta"
    if name.lower() in STANDARD_FILES:
        return STANDARD_FILES[name.lower()], "meta"
    raw = full.read_bytes()
    if b"\x00" in raw[:4096]:
        return f"Binary file, {size:,} bytes", "meta"
    text = raw.decode("utf-8", errors="replace")
    low = name.lower()
    if not ext and text.startswith("#!"):
        shebang = text.split("\n", 1)[0]
        ext = ".py" if "python" in shebang else (".js" if "node" in shebang else ".sh")
    if ext == ".py" or ext == ".pyi":
        return describe_python(text, name)
    if ext in CODE_EXT:
        return describe_code(text, name)
    if ext in (".md", ".mdx", ".markdown", ".rst"):
        return describe_markdown(text)
    if ext in (".json", ".jsonl"):
        return describe_json(text, name)
    if ext in (".yaml", ".yml"):
        return describe_yaml(text, path)
    if ext == ".ipynb":
        return describe_notebook(text)
    if ext in (".html", ".htm"):
        m = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
        if m and meaningful(m.group(1).strip()):
            return m.group(1), "doc"
        m = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S | re.I)
        if m:
            return re.sub(r"<[^>]+>", "", m.group(1)), "doc"
        return f"HTML fragment, {text.count(chr(10)) + 1} lines, no title", "derived"
    if ext == ".svg":
        m = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
        return (m.group(1), "doc") if m else (f"SVG image, {size:,} bytes", "meta")
    if low.startswith("dockerfile") or ext == ".dockerfile":
        comment = leading_hash_comment(text)
        bases = list(dict.fromkeys(re.findall(r"^FROM\s+(\S+)", text, re.M | re.I)))
        if comment:
            return comment, "doc"
        return f"Docker build; base images: {names(bases, 4)}", "derived"
    if ext in HASH_EXT or low in ("makefile", ".gitignore", ".dockerignore", ".gitattributes", ".npmignore"):
        return describe_hash_script(text, name, ext)
    if low.startswith(".env"):
        return describe_hash_script(text, name, ".env")
    if ext == ".lean":
        m = re.search(r"/-[-!]?(.*?)-/", text, re.S)
        if m and meaningful(m.group(1).strip()):
            return first_sentence(m.group(1)), "doc"
        thms = re.findall(r"^(?:theorem|lemma|def)\s+(\S+)", text, re.M)
        if thms:
            return f"Lean source; declares {names(thms)}", "derived"
        mods = re.findall(r"^import\s+(\S+)", text, re.M)
        return f"Lean root module; imports {names(mods)}", "derived"
    if ext == ".tex":
        m = re.search(r"\\title\{(.+?)\}\s*$", text, re.S | re.M)
        if m:
            title = re.sub(r"\\[a-zA-Z]+\{?|[{}%]|\\\\", " ", m.group(1))
            return title, "doc"
        return f"LaTeX source, {text.count(chr(10)) + 1} lines", "derived"
    if ext == ".sql":
        tables = re.findall(r"create\s+table\s+(?:if\s+not\s+exists\s+)?([\w.\"]+)", text, re.I)
        comment = re.match(r"\s*--\s*(.+)", text)
        if comment and meaningful(comment.group(1)):
            return comment.group(1), "doc"
        return f"SQL; creates tables {names(tables)}" if tables else "SQL script", "derived"
    if ext == ".csv" or ext == ".tsv":
        lines = text.splitlines()
        return f"Table, {max(len(lines) - 1, 0)} rows; columns: {clean(lines[0])[:110]}", "derived"
    for line in text.splitlines():
        body = line.strip()
        if COMMENT_PREFIX.match(body) and meaningful(COMMENT_PREFIX.sub("", body)):
            return COMMENT_PREFIX.sub("", body), "doc"
        if meaningful(body):
            if ext in (".txt", ""):
                return body, "doc"
            break
    return f"{ext.lstrip('.') or 'Text'} file, {text.count(chr(10)) + 1} lines", "derived"


def load_submodules() -> Dict[str, str]:
    """Map submodule path -> URL from .gitmodules."""
    gm = REPO / ".gitmodules"
    if not gm.exists():
        return {}
    out: Dict[str, str] = {}
    path = None
    for line in gm.read_text().splitlines():
        m = re.match(r"\s*path\s*=\s*(.+)", line)
        if m:
            path = m.group(1).strip()
        m = re.match(r"\s*url\s*=\s*(.+)", line)
        if m and path:
            out[path] = m.group(1).strip()
    return out


SUBDIR_SOURCES = ("README.md", "readme.md", "package.json", "pyproject.toml", "SKILL.md", "__init__.py")
SUBDIR_SOURCES += ("index.ts", "index.js", "mod.rs", "lib.rs", "Cargo.toml", "WHY_HERE.md")


def describe_subdir(directory: str, tracked: Dict[str, str], submodules: Dict[str, str]) -> str:
    """One line for a directory, taken from its README / manifest / package init if any."""
    for candidate in SUBDIR_SOURCES:
        path = f"{directory}/{candidate}"
        if path not in tracked:
            continue
        if candidate == "pyproject.toml":
            m = re.search(r"^description\s*=\s*[\"'](.+?)[\"']\s*$", (REPO / path).read_text(errors="replace"), re.M)
            if m:
                return clean(m.group(1))
            continue
        desc, basis = describe(path, tracked[path], submodules)
        if basis == "doc":
            return clean(desc)
    return ""


def page_name(top: str) -> str:
    """File name of the index page for a top-level directory."""
    return (
        "_root" if top == "." else top.lstrip(".").replace("/", "_") + ("_dot" if top.startswith(".") else "")
    ) + ".md"


def build() -> Dict[str, str]:
    """Return {output filename: content} for the whole index."""
    submodules = load_submodules()
    entries = []
    for line in sh("git", "ls-files", "-s").splitlines():
        meta, path = line.split("\t", 1)
        if path.startswith('"'):
            path = ast.literal_eval(path).encode("latin-1").decode("utf-8")
        if path.startswith("docs/file-index/"):
            continue
        entries.append((path, meta.split()[0]))
    by_top: Dict[str, Dict[str, List[Tuple[str, str, str]]]] = defaultdict(lambda: defaultdict(list))
    totals: Dict[str, Counter] = defaultdict(Counter)
    for path, mode in sorted(entries):
        desc, basis = describe(path, mode, submodules)
        parts = path.split("/")
        top = parts[0] if len(parts) > 1 else "."
        directory = "/".join(parts[:-1]) or "."
        by_top[top][directory].append((parts[-1], clean(desc) or "(no content)", basis))
        totals[top][basis] += 1
    tracked = dict(entries)
    described = 0
    undescribed: List[str] = []
    pages: Dict[str, str] = {}
    rows = []
    grand: Counter = Counter()
    for top in sorted(by_top, key=lambda t: (t != ".", t.lower())):
        count = sum(totals[top].values())
        grand.update(totals[top])
        title = "repository root" if top == "." else f"{top}/"
        lines = [
            f"# File index: {title}",
            "",
            f"{count} tracked files. Generated by `scripts/docs/build_file_index.py`; do not edit by hand.",
            "",
            "Basis: **doc** = text written in the file (docstring, header comment, title); "
            "**derived** = inferred from symbols or structure because the file has no header; "
            "**meta** = binary/opaque, type and size only.",
            "",
        ]
        children: Counter = Counter()
        for path in tracked:
            parts = path.split("/")
            if top != "." and parts[0] == top and len(parts) > 2:
                children[parts[1]] += 1
        if len(children) > 1:
            lines += ["## Subdirectories", "", "| Directory | Files | Purpose (from its README / manifest / init) |"]
            lines += ["|-----------|------:|-----------------------------------------------|"]
            for child in sorted(children, key=str.lower):
                purpose = describe_subdir(f"{top}/{child}", tracked, submodules)
                if purpose:
                    described += 1
                else:
                    undescribed.append(f"{top}/{child}")
                lines.append(f"| `{child}/` | {children[child]} | {purpose or '_none stated_'} |")
            lines.append("")
        for directory in sorted(by_top[top]):
            files = by_top[top][directory]
            if top != ".":
                lines += [f"## {directory}/", ""]
            lines += ["| File | What it is | Basis |", "|------|------------|-------|"]
            lines += [f"| `{name}` | {desc} | {basis} |" for name, desc, basis in files]
            lines.append("")
        pages[page_name(top)] = "\n".join(lines)
        t = totals[top]
        rows.append(f"| [{title}]({page_name(top)}) | {count} | {t['doc']} | {t['derived']} | {t['meta']} |")
    total = sum(grand.values())
    pct = 100.0 * grand["doc"] / total
    pages["README.md"] = "\n".join(
        [
            "# File index",
            "",
            "One line of explanation for every tracked file in the repository, grouped by top-level directory.",
            "Generated by `scripts/docs/build_file_index.py` from the files themselves "
            "(`--check` reports whether it is stale).",
            "",
            f"**{total} files**: {grand['doc']} ({pct:.1f}%) carry an author-written header or title (**doc**), "
            f"{grand['derived']} have none and are described from their symbols or structure (**derived**), "
            f"{grand['meta']} are binary, empty, or submodule pointers (**meta**).",
            "",
            f"Second-level directories: {described} state their purpose in a README, manifest, or package init; "
            f"{len(undescribed)} do not (shown as _none stated_ in the Subdirectories table of each page).",
            "",
            "For the purpose of each directory see its own `README.md`; for architecture start at "
            "[`docs/README.md`](../README.md).",
            "",
            "| Directory | Files | doc | derived | meta |",
            "|-----------|------:|----:|--------:|-----:|",
            *rows,
            "",
        ]
    )
    return pages


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if docs/file-index/ is out of date")
    args = parser.parse_args()
    pages = build()
    if args.check:
        existing = {p.name for p in OUT_DIR.glob("*.md")} if OUT_DIR.exists() else set()
        stale = sorted(n for n, c in pages.items() if not (OUT_DIR / n).exists() or (OUT_DIR / n).read_text() != c)
        stale += sorted(existing - set(pages))
        if stale:
            print("file index is stale: " + ", ".join(stale))
            return 1
        print(f"file index is current ({len(pages)} pages)")
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.md"):
        if old.name not in pages:
            old.unlink()
    for name, content in pages.items():
        (OUT_DIR / name).write_text(content, encoding="utf-8")
    print(f"wrote {len(pages)} pages to {OUT_DIR.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
