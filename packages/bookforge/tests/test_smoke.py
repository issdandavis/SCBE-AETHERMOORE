"""Smoke tests for scbe-bookforge."""

from __future__ import annotations

import json
import base64
from pathlib import Path

from scbe_bookforge import load_profile, build_cover, build_docx, build_epub, build_interior, interior_engine_for
from scbe_bookforge.profile import KDP_TRIM_SIZES, SPINE_PER_PAGE
from scbe_bookforge.cover import spine_text_allowed
from scbe_bookforge.manuscript import clean_source_text, parse_markdown, word_count


def test_kdp_trim_sizes_match_kdp():
    assert KDP_TRIM_SIZES["5x8"] == (5.0, 8.0)
    assert KDP_TRIM_SIZES["5.5x8.5"] == (5.5, 8.5)
    assert KDP_TRIM_SIZES["6x9"] == (6.0, 9.0)


def test_current_kdp_paperback_spine_factors():
    assert SPINE_PER_PAGE["bw_white"] == 0.002252
    assert SPINE_PER_PAGE["bw_cream"] == 0.0025
    assert SPINE_PER_PAGE["color_standard"] == 0.002252
    assert SPINE_PER_PAGE["color_premium"] == 0.002347


def test_spine_text_gate_matches_kdp_threshold():
    assert spine_text_allowed(79) is False
    assert spine_text_allowed(80) is True


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


def test_parse_markdown_preserves_code_lists_and_quotes():
    src = """# Test

## Chapter 1. Terminal

```powershell
python -m pip --version
python -m pip wheel -r requirements.txt -w wheelhouse
```

- first item
2. second item

> A short warning.
"""
    blocks = parse_markdown(src)
    code = next(b for b in blocks if b.kind == "code")
    assert code.language == "powershell"
    assert "python -m pip wheel" in code.text
    items = [b for b in blocks if b.kind == "list_item"]
    assert [b.marker for b in items] == ["•", "2."]
    assert any(b.kind == "blockquote" and b.text == "A short warning." for b in blocks)


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
        "cover": {"art": "cover.png", "simulated_gold": True},
        "ornament": {"style": "rose", "color": "#9A4559", "opacity": 0.3},
    }), encoding="utf-8")
    (tmp_path / "cover.png").write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    ))
    profile = load_profile(profile_path)
    assert profile.title == "Test Book"
    assert profile.trim_w_in == 5.5
    assert abs(profile.spine_width_in() - 0.25) < 1e-9   # 100 * 0.0025
    assert profile.cover_art == (tmp_path / "cover.png").resolve()
    assert profile.simulated_gold is True
    assert profile.ornament_style == "rose"
    engine = interior_engine_for(profile)
    assert engine in {"xelatex", "reportlab"}


def test_reportlab_interior_and_cover_accept_ornament_and_art(tmp_path: Path):
    md = tmp_path / "manuscript.md"
    md.write_text("# Test\n\n## Chapter 1. Hello\n\nWorld.\n", encoding="utf-8")
    (tmp_path / "cover.png").write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    ))
    profile_path = tmp_path / "bookforge.json"
    profile_path.write_text(json.dumps({
        "title": "Test Book",
        "author": "Tester",
        "source": "manuscript.md",
        "output_dir": "build",
        "trim": "5x8",
        "page_count": 100,
        "interior_engine": "reportlab",
        "cover": {"art": "cover.png", "simulated_gold": True},
        "ornament": {"style": "water_channel"},
        "hook": "A test hook",
        "blurb_paragraphs": ["A short back-cover paragraph."],
    }), encoding="utf-8")
    profile = load_profile(profile_path)
    interior = build_interior(profile)
    cover = build_cover(profile, hook="A test hook", blurb_paragraphs=["A short back-cover paragraph."])
    assert interior.exists() and interior.stat().st_size > 1024
    assert cover.exists() and cover.stat().st_size > 1024


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
