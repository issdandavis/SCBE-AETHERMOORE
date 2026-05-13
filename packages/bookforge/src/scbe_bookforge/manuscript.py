"""Manuscript-source helpers (parsing + sanitation)."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Block:
    kind: str   # "heading" | "para" | "scene_break"
    text: str
    level: int = 0


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

    def flush_para() -> None:
        if para:
            joined = " ".join(part.strip() for part in para if part.strip()).strip()
            if joined:
                blocks.append(Block("para", joined))
            para.clear()

    for raw_line in source.splitlines():
        line = raw_line.rstrip()
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
        para.append(line)
    flush_para()
    return blocks
