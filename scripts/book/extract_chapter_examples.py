"""Extract runnable code examples from a runnable-ebook chapter.

Reads `book/<book>/chapter-<NN>-<slug>.md`, parses the YAML frontmatter, and
returns a structured view: prose, examples, and any expected-output blocks
that follow examples. Used by the chapter test runner and by Polly chat to
preview what a chapter contains before the reader buys.

Usage:
  python scripts/book/extract_chapter_examples.py book/<book>/<file.md>
  python scripts/book/extract_chapter_examples.py book/<book>/<file.md> --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
FENCED_BLOCK_RE = re.compile(r"^```(\w*)\n(.*?)\n```", re.MULTILINE | re.DOTALL)
RUNNABLE_LANGUAGES = {"python", "py", "typescript", "ts"}
OUTPUT_TAGS = {"output", "text"}


@dataclass
class CodeExample:
    language: str
    code: str
    expected_output: Optional[str] = None


@dataclass
class ChapterView:
    frontmatter: Dict[str, Any]
    body: str
    examples: List[CodeExample] = field(default_factory=list)
    output_only_blocks: int = 0


def _parse_frontmatter(text: str) -> tuple[Dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw, body = match.group(1), match.group(2)
    if yaml is None:
        # Minimal fallback: accept simple `key: value` lines.
        meta: Dict[str, Any] = {}
        for line in raw.splitlines():
            if ":" in line and not line.strip().startswith("#"):
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
        return meta, body
    return yaml.safe_load(raw) or {}, body


def _walk_blocks(body: str) -> List[tuple[str, str]]:
    return [(m.group(1) or "", m.group(2)) for m in FENCED_BLOCK_RE.finditer(body)]


def extract_chapter(md_path: Path) -> ChapterView:
    text = md_path.read_text(encoding="utf-8", errors="replace")
    meta, body = _parse_frontmatter(text)

    blocks = _walk_blocks(body)
    examples: List[CodeExample] = []
    output_only = 0
    i = 0
    while i < len(blocks):
        lang, code = blocks[i]
        normalized = lang.lower()
        if normalized in RUNNABLE_LANGUAGES:
            expected: Optional[str] = None
            # Peek ahead for an output block immediately after.
            if i + 1 < len(blocks):
                next_lang = blocks[i + 1][0].lower()
                if next_lang in OUTPUT_TAGS:
                    expected = blocks[i + 1][1]
                    i += 1
            examples.append(
                CodeExample(
                    language="python" if normalized in {"python", "py"} else "typescript",
                    code=code,
                    expected_output=expected,
                )
            )
        elif normalized in OUTPUT_TAGS:
            output_only += 1
        i += 1

    return ChapterView(
        frontmatter=meta,
        body=body,
        examples=examples,
        output_only_blocks=output_only,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract code examples from a runnable-ebook chapter")
    parser.add_argument("path", help="Path to chapter markdown")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human summary")
    args = parser.parse_args()

    md_path = Path(args.path)
    if not md_path.is_file():
        print(f"chapter not found: {md_path}", file=sys.stderr)
        return 2

    view = extract_chapter(md_path)
    payload = {
        "schema": view.frontmatter.get("schema"),
        "book": view.frontmatter.get("book"),
        "chapter": view.frontmatter.get("chapter"),
        "title": view.frontmatter.get("title"),
        "examples": [asdict(e) for e in view.examples],
        "output_only_blocks": view.output_only_blocks,
        "five_ws": {k: view.frontmatter.get(k) for k in ("who", "what", "when", "where", "why")},
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"book: {payload['book']}  chapter {payload['chapter']}: {payload['title']}")
        print(f"examples: {len(payload['examples'])}  output-only blocks: {view.output_only_blocks}")
        for i, ex in enumerate(view.examples, 1):
            head = ex.code.splitlines()[0] if ex.code.strip() else "(empty)"
            print(f"  [{i}] {ex.language}  {head[:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
