#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


H1_RE = re.compile(r"^#\s+(.+)$")
CHAPTER_RE = re.compile(r"^#\s+Chapter\s+(\d+)\s*:\s*(.+)$", re.IGNORECASE)
INTERLUDE_RE = re.compile(r"^#\s+Interlude\s*:\s*(.+)$", re.IGNORECASE)

SUSPICIOUS_PATTERNS = [
    ("placement-note", re.compile(r"^\*\[Placed between\b", re.IGNORECASE)),
    ("todo-marker", re.compile(r"\b(?:TODO|FIXME|TBD)\b", re.IGNORECASE)),
    (
        "meta-ending",
        re.compile(
            r"\bThis was the end of Book\b|\bThat was a Book\s+\d+\s+problem\b",
            re.IGNORECASE,
        ),
    ),
    ("short-ch-ref", re.compile(r"\bch\d{1,3}\b", re.IGNORECASE)),
]


@dataclass
class Section:
    line: int
    title: str
    words: int


@dataclass
class WarningItem:
    kind: str
    line: int
    message: str
    excerpt: str


def build_sections(lines: list[str]) -> list[Section]:
    headings: list[tuple[int, str]] = []
    for idx, line in enumerate(lines, start=1):
        match = H1_RE.match(line)
        if match:
            headings.append((idx, match.group(1).strip()))

    sections: list[Section] = []
    for index, (line_no, title) in enumerate(headings):
        start = line_no
        end = headings[index + 1][0] - 1 if index + 1 < len(headings) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        words = len(re.findall(r"\S+", body))
        sections.append(Section(line=line_no, title=title, words=words))
    return sections


def find_warnings(lines: list[str]) -> list[WarningItem]:
    warnings: list[WarningItem] = []
    chapter_numbers: dict[int, int] = {}
    last_chapter: int | None = None

    for idx, line in enumerate(lines, start=1):
        chapter = CHAPTER_RE.match(line)
        if chapter:
            chapter_number = int(chapter.group(1))
            if chapter_number in chapter_numbers:
                warnings.append(
                    WarningItem(
                        kind="duplicate-chapter-number",
                        line=idx,
                        message=(
                            f"Duplicate chapter number {chapter_number}; "
                            f"first seen at line {chapter_numbers[chapter_number]}."
                        ),
                        excerpt=line.strip(),
                    )
                )
            if last_chapter is not None and chapter_number <= last_chapter:
                warnings.append(
                    WarningItem(
                        kind="non-monotonic-chapter-number",
                        line=idx,
                        message=(
                            f"Chapter numbering moved from {last_chapter} to {chapter_number}."
                        ),
                        excerpt=line.strip(),
                    )
                )
            chapter_numbers.setdefault(chapter_number, idx)
            last_chapter = chapter_number

        for kind, pattern in SUSPICIOUS_PATTERNS:
            if pattern.search(line):
                warnings.append(
                    WarningItem(
                        kind=kind,
                        line=idx,
                        message=f"Matched {kind}.",
                        excerpt=line.strip(),
                    )
                )
    return warnings


def render_text_report(path: Path, sections: list[Section], warnings: list[WarningItem]) -> str:
    chapters = sum(1 for section in sections if CHAPTER_RE.match(f"# {section.title}"))
    interludes = sum(1 for section in sections if INTERLUDE_RE.match(f"# {section.title}"))
    lines = [
        f"Audit: {path}",
        f"H1 sections: {len(sections)}",
        f"Chapter headings: {chapters}",
        f"Interludes: {interludes}",
        f"Warnings: {len(warnings)}",
        "",
    ]

    if warnings:
        lines.append("Warnings:")
        for warning in warnings:
            lines.append(
                f"- line {warning.line}: [{warning.kind}] {warning.message} :: {warning.excerpt}"
            )
        lines.append("")

    lines.append("Sections:")
    for section in sections:
        lines.append(f"- line {section.line}: {section.title} ({section.words} words)")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a compiled manuscript for publication issues.")
    parser.add_argument("--input", required=True, help="Path to the manuscript file.")
    parser.add_argument(
        "--json-out",
        help="Optional path for JSON report output.",
    )
    args = parser.parse_args()

    path = Path(args.input)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    sections = build_sections(lines)
    warnings = find_warnings(lines)

    report = {
        "input": str(path),
        "sections": [asdict(section) for section in sections],
        "warnings": [asdict(warning) for warning in warnings],
        "summary": {
            "h1_sections": len(sections),
            "chapter_headings": sum(
                1 for section in sections if CHAPTER_RE.match(f"# {section.title}")
            ),
            "interludes": sum(
                1 for section in sections if INTERLUDE_RE.match(f"# {section.title}")
            ),
            "warnings": len(warnings),
        },
    }

    print(render_text_report(path, sections, warnings))

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
