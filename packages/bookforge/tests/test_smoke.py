"""Smoke tests for scbe-bookforge."""

from __future__ import annotations

import json
from pathlib import Path

from scbe_bookforge import load_profile, build_epub, build_docx, interior_engine_for
from scbe_bookforge.interior_xelatex import _compose_document
from scbe_bookforge.profile import KDP_TRIM_SIZES
from scbe_bookforge.manuscript import clean_source_text, parse_markdown, word_count


def test_kdp_trim_sizes_match_kdp():
    assert KDP_TRIM_SIZES["5x8"] == (5.0, 8.0)
    assert KDP_TRIM_SIZES["5.5x8.5"] == (5.5, 8.5)
    assert KDP_TRIM_SIZES["6x9"] == (6.0, 9.0)


def test_clean_source_drops_scaffold_lines():
    src = "Manuscript v1 spine, consolidated 2026-05-12\n\nReal first line.\n"
    cleaned, removed = clean_source_text(src)
    assert "Real first line." in cleaned
    assert any(r.startswith("Manuscript v1 spine") for r in removed)


def test_parse_markdown_identifies_scene_breaks_and_headings():
    src = "# Title\n\n## Chapter 1. Foo\n\nPara one.\n\n---\n\nPara two.\n"
    blocks = parse_markdown(src)
    kinds = [b.kind for b in blocks]
    assert "scene_break" in kinds
    assert any(b.kind == "heading" and b.level == 1 for b in blocks)
    assert any(b.kind == "heading" and b.level == 2 for b in blocks)


def test_word_count_counts_heading_and_body():
    assert word_count("# Heading\n\nfour words here now") == 5


def test_load_profile_round_trip(tmp_path: Path):
    md = tmp_path / "manuscript.md"
    md.write_text("# Test\n\n## Chapter 1. Hello\n\nWorld.\n", encoding="utf-8")
    profile_path = tmp_path / "bookforge.json"
    profile_path.write_text(json.dumps({
        "title": "Test Book",
        "author": "Tester",
        "source": "manuscript.md",
        "output_dir": "build",
        "trim": "5.5x8.5",
        "page_count": 100,
    }), encoding="utf-8")
    profile = load_profile(profile_path)
    assert profile.title == "Test Book"
    assert profile.trim_w_in == 5.5
    assert abs(profile.spine_width_in() - 0.25) < 1e-9   # 100 * 0.0025
    engine = interior_engine_for(profile)
    assert engine in {"xelatex", "reportlab"}


def test_build_docx_round_trip(tmp_path: Path):
    md = tmp_path / "manuscript.md"
    md.write_text("# Test\n\n## Chapter 1. Hello\n\nWorld.\n", encoding="utf-8")
    profile_path = tmp_path / "bookforge.json"
    profile_path.write_text(json.dumps({
        "title": "Test Book",
        "author": "Tester",
        "source": "manuscript.md",
        "output_dir": "build",
        "trim": "5x8",
    }), encoding="utf-8")
    profile = load_profile(profile_path)
    out = build_docx(profile)
    assert out.exists()
    assert out.stat().st_size > 1024


def test_xelatex_document_loads_hyperref_for_pandoc_heading_anchors(tmp_path: Path):
    md = tmp_path / "manuscript.md"
    md.write_text("# Test\n\n## Chapter 1. Hello\n\nWorld.\n", encoding="utf-8")
    profile_path = tmp_path / "bookforge.json"
    profile_path.write_text(json.dumps({
        "title": "Test Book",
        "author": "Tester",
        "source": "manuscript.md",
        "output_dir": "build",
        "trim": "5.5x8.5",
    }), encoding="utf-8")
    profile = load_profile(profile_path)
    document = _compose_document(profile, "body.tex")
    assert r"\usepackage[hidelinks]{hyperref}" in document
