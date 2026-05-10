"""Shared runner for runnable-ebook chapter tests.

Each chapter test calls `run_chapter(book_slug, chapter_number)` to:
1. Locate the chapter markdown file
2. Extract its examples via scripts.book.extract_chapter_examples
3. Exec each example in an isolated namespace, capturing stdout
4. If the example was followed by an `output` / `text` block, assert the
   captured stdout matches it line-by-line (whitespace-trimmed)
5. Return a dict summary: examples_run, examples_failed, failures

The runner intentionally does NOT swallow exceptions — failures bubble as
AssertionError so pytest reports them with the chapter context.
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.book.extract_chapter_examples import extract_chapter  # noqa: E402


class ChapterExampleFailure(AssertionError):
    """Raised when an example block fails to run or its output mismatches."""


def _normalize_lines(text: str) -> List[str]:
    return [ln.rstrip() for ln in text.strip().splitlines()]


def _find_chapter_path(book_slug: str, chapter_number: int) -> Path:
    book_dir = REPO_ROOT / "book" / book_slug
    if not book_dir.is_dir():
        raise FileNotFoundError(f"book directory not found: {book_dir}")
    prefix = f"chapter-{chapter_number:02d}-"
    for md in sorted(book_dir.glob("chapter-*.md")):
        if md.name.startswith(prefix):
            return md
    raise FileNotFoundError(f"chapter {chapter_number:02d} not found in {book_dir}")


def run_chapter(book_slug: str, chapter_number: int) -> Dict[str, Any]:
    md_path = _find_chapter_path(book_slug, chapter_number)
    view = extract_chapter(md_path)

    failures: List[Dict[str, Any]] = []
    for idx, example in enumerate(view.examples, 1):
        # Only Python examples are auto-executed in v1 of the format.
        if example.language != "python":
            continue
        ns: Dict[str, Any] = {"__name__": f"_chapter_example_{idx}"}
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                exec(compile(example.code, f"<{md_path.name}#example-{idx}>", "exec"), ns)  # noqa: S102
        except Exception as exc:  # noqa: BLE001
            failures.append({"example": idx, "kind": "exception", "detail": f"{type(exc).__name__}: {exc}"})
            continue

        if example.expected_output:
            captured = _normalize_lines(buf.getvalue())
            expected = _normalize_lines(example.expected_output)
            if captured != expected:
                failures.append(
                    {
                        "example": idx,
                        "kind": "output_mismatch",
                        "captured": captured[:6],
                        "expected": expected[:6],
                    }
                )

    if failures:
        raise ChapterExampleFailure(
            f"book={book_slug} chapter={chapter_number:02d}: {len(failures)} example(s) failed: {failures}"
        )

    return {
        "book": book_slug,
        "chapter": chapter_number,
        "chapter_path": md_path.relative_to(REPO_ROOT).as_posix(),
        "examples_run": sum(1 for e in view.examples if e.language == "python"),
        "examples_failed": 0,
        "frontmatter": view.frontmatter,
    }
