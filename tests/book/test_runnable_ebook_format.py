"""Validator for the runnable-ebook v1 schema.

Walks every chapter under `book/<book-slug>/chapter-*.md` and asserts:

1. YAML frontmatter is parseable
2. schema field equals `scbe_runnable_ebook_v1`
3. All five W fields are present and non-empty (single line, ≤ 200 chars)
4. test_suite path resolves to an existing file
5. Chapter has at least one runnable code block
6. Chapter and test file are paired one-to-one (no orphan tests, no
   chapter without a paired test)

If a future chapter ships without these, this validator fails CI. That is
the contract the runnable-ebook format makes with downstream consumers
(Polly chat, HF training extraction, paid bundle delivery).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.book.extract_chapter_examples import extract_chapter

REPO_ROOT = Path(__file__).resolve().parents[2]
BOOK_ROOT = REPO_ROOT / "book"
TEST_BOOK_ROOT = REPO_ROOT / "tests" / "book"
REQUIRED_5W = ("who", "what", "when", "where", "why")
MAX_5W_LEN = 200


def _all_chapters() -> list[Path]:
    if not BOOK_ROOT.is_dir():
        return []
    return sorted(BOOK_ROOT.glob("*/chapter-*.md"))


@pytest.mark.parametrize("chapter_path", _all_chapters(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_chapter_has_valid_frontmatter(chapter_path: Path) -> None:
    view = extract_chapter(chapter_path)
    fm = view.frontmatter
    assert fm.get("schema") == "scbe_runnable_ebook_v1", f"{chapter_path}: bad schema={fm.get('schema')}"
    assert isinstance(fm.get("chapter"), int), f"{chapter_path}: chapter must be an int"
    assert isinstance(fm.get("slug"), str) and fm["slug"], f"{chapter_path}: slug missing"
    assert isinstance(fm.get("title"), str) and fm["title"], f"{chapter_path}: title missing"


@pytest.mark.parametrize("chapter_path", _all_chapters(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_chapter_has_all_five_ws(chapter_path: Path) -> None:
    view = extract_chapter(chapter_path)
    fm = view.frontmatter
    for field in REQUIRED_5W:
        value = fm.get(field)
        assert isinstance(value, str) and value.strip(), f"{chapter_path}: 5W field '{field}' missing or empty"
        assert "\n" not in value, f"{chapter_path}: 5W field '{field}' must be single line"
        assert len(value) <= MAX_5W_LEN, f"{chapter_path}: 5W field '{field}' over {MAX_5W_LEN} chars"


@pytest.mark.parametrize("chapter_path", _all_chapters(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_chapter_test_suite_exists(chapter_path: Path) -> None:
    view = extract_chapter(chapter_path)
    test_suite = view.frontmatter.get("test_suite")
    assert isinstance(test_suite, str) and test_suite, f"{chapter_path}: test_suite path missing"
    resolved = REPO_ROOT / test_suite
    assert resolved.is_file(), f"{chapter_path}: declared test_suite does not exist: {resolved}"


@pytest.mark.parametrize("chapter_path", _all_chapters(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_chapter_has_at_least_one_runnable_example(chapter_path: Path) -> None:
    view = extract_chapter(chapter_path)
    runnable = [e for e in view.examples if e.language in {"python", "typescript"}]
    assert runnable, f"{chapter_path}: chapter must contain at least one runnable example"


def test_no_orphan_test_files() -> None:
    """Every test file under tests/book/<book-slug>/ must have a paired chapter."""
    if not TEST_BOOK_ROOT.is_dir():
        return
    declared = {(REPO_ROOT / extract_chapter(c).frontmatter.get("test_suite", "")).resolve() for c in _all_chapters()}
    declared.discard(REPO_ROOT.resolve())
    orphans = []
    for test_file in TEST_BOOK_ROOT.rglob("test_chapter_*.py"):
        if test_file.resolve() not in declared:
            orphans.append(test_file.relative_to(REPO_ROOT).as_posix())
    assert not orphans, f"orphan chapter test files (no chapter declares them): {orphans}"
