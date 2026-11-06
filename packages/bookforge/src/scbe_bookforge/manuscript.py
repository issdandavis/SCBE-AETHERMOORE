"""Manuscript-source helpers (parsing + sanitation)."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Block:
    kind: str   # heading | para | scene_break | code | list_item | blockquote
    text: str
    level: int = 0
    marker: str = ""
    language: str = ""


SCAFFOLD_PREFIXES = (
    "Manuscript v1 spine, consolidated",
    "<!-- bookforge:ignore -->",
)


def clean_source_text(source: str) -> tuple[str, list[str]]:
    """Strip manuscript scaffolding lines that should never reach print."""
    removed: list[str] = []
    kept: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(p) for p in SCAFFOLD_PREFIXES):
            removed.append(stripped)
            continue
        kept.append(line)
    return "\n".join(kept), removed


def word_count(text: str) -> int:
    body = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
    body = re.sub(r"[*_`>#\[\]()-]+", " ", body)
    return len(re.findall(r"\b[\w']+\b", body))


def parse_markdown(source: str) -> list[Block]:
    """Light markdown parser sufficient for the ReportLab fallback."""
    blocks: list[Block] = []
    para: list[str] = []
    code: list[str] = []
    code_language = ""
    in_code = False

    def flush_para() -> None:
        if para:
            joined = " ".join(part.strip() for part in para if part.strip()).strip()
            if joined:
                blocks.append(Block("para", joined))
            para.clear()

    for raw_line in source.splitlines():
        line = raw_line.rstrip()
        fence = re.match(r"^\s*```\s*([^`]*)$", line)
        if fence:
            flush_para()
            if in_code:
                blocks.append(Block("code", "\n".join(code), language=code_language))
                code.clear()
                code_language = ""
                in_code = False
            else:
                in_code = True
                code_language = fence.group(1).strip()
            continue
        if in_code:
            code.append(line)
            continue
        if not line.strip():
            flush_para()
            continue
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", line.strip()):
            flush_para()
            blocks.append(Block("scene_break", "* * *"))
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            flush_para()
            blocks.append(Block("heading", m.group(2).strip(), level=len(m.group(1))))
            continue
        m = re.match(r"^(\s*)([-+*]|\d+[.)])\s+(.+)$", line)
        if m:
            flush_para()
            indent_level = max(1, (len(m.group(1).expandtabs(4)) // 2) + 1)
            marker = m.group(2)
            if marker in {"-", "+", "*"}:
                marker = "•"
            blocks.append(Block("list_item", m.group(3).strip(), level=indent_level, marker=marker))
            continue
        m = re.match(r"^>\s?(.*)$", line)
        if m:
            flush_para()
            blocks.append(Block("blockquote", m.group(1).strip()))
            continue
        para.append(line)
    if in_code:
        blocks.append(Block("code", "\n".join(code), language=code_language))
    flush_para()
    return blocks
