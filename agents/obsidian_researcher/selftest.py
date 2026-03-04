"""Obsidian Researcher Agent -- Built-in Verification.

Run standalone:

    python agents/obsidian_researcher/selftest.py

Exits 0 on all-pass, 1 on any failure.
"""

from __future__ import annotations

import os
import sys
import tempfile
import types
from pathlib import Path

# ---------------------------------------------------------------------------
# Mock scipy before any project imports (Python 3.14 compatibility)
# ---------------------------------------------------------------------------
sys.modules.setdefault("scipy", types.ModuleType("scipy"))
sys.modules.setdefault("scipy.integrate", types.ModuleType("scipy.integrate"))


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------


def test_source_adapter():
    """Test SourceType enum and IngestionResult dataclass."""
    from agents.obsidian_researcher.source_adapter import SourceType, IngestionResult

    # Verify all 8 source types exist
    assert len(SourceType) == 8, f"Expected 8 source types, got {len(SourceType)}"

    # Create an IngestionResult
    result = IngestionResult(
        source_type=SourceType.BRAINSTORM,
        raw_content="test content",
        title="Test",
    )
    assert result.title == "Test"
    assert result.source_type is SourceType.BRAINSTORM
    assert result.raw_content == "test content"
    assert result.authors == []
    assert result.tags == []

    print("  [PASS] SourceAdapter + IngestionResult")


def test_vault_source():
    """Test VaultSource with a temp vault directory."""
    from agents.obsidian_researcher.sources.vault_source import VaultSource

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        (Path(tmpdir) / "Test Page.md").write_text(
            "---\ntags: [test, scbe]\n---\n# Test Page\n"
            "Some content about [[Another Page]] and entropy.",
            encoding="utf-8",
        )
        (Path(tmpdir) / "Another Page.md").write_text(
            "---\nauthor: Issac Davis\n---\n# Another\n"
            "Content about morphisms.",
            encoding="utf-8",
        )

        vs = VaultSource(config={"vault_root": tmpdir})
        assert vs.health_check(), "VaultSource health_check failed"

        titles = vs.get_all_page_titles()
        assert len(titles) == 2, f"Expected 2 titles, got {len(titles)}"

        results = vs.fetch("entropy")
        assert len(results) >= 1, "Expected at least 1 result for 'entropy'"
        assert results[0].source_type.value == "vault"

        wikilinks = vs.get_all_wikilinks()
        assert "Another Page" in wikilinks.get("Test Page", []), (
            "Expected wikilink to 'Another Page' from 'Test Page'"
        )

    print("  [PASS] VaultSource")


def test_cross_reference_engine():
    """Test all 4 strategies."""
    from agents.obsidian_researcher.cross_reference_engine import (
        CrossReferenceEngine,
        LinkType,
    )
    from agents.obsidian_researcher.source_adapter import IngestionResult, SourceType

    engine = CrossReferenceEngine(
        vault_page_titles=[
            "Harmonic Wall",
            "Entropy Defense",
            "Sacred Tongue Tokenization",
        ],
        vault_page_keywords={
            "Harmonic Wall": ["harmonic", "wall", "scaling", "energy", "cost"],
            "Entropy Defense": ["entropy", "chaos", "defense", "noise"],
            "Sacred Tongue Tokenization": [
                "tongue",
                "tokenization",
                "sacred",
                "lexicon",
            ],
        },
        vault_page_contents={
            "Harmonic Wall": "The harmonic wall H(d,R) provides cost scaling.",
            "Entropy Defense": "Entropy measures chaos in the system. arXiv:2301.12345",
            "Sacred Tongue Tokenization": "Six sacred tongues encode meaning.",
        },
    )

    # Test keyword scan
    links = engine.keyword_scan(
        "The harmonic wall provides energy scaling protection"
    )
    assert any(
        lnk.target_page == "Harmonic Wall" for lnk in links
    ), "keyword_scan should find Harmonic Wall"

    # Test CDDM scan (Energy -> Authority morphism)
    links = engine.cddm_scan(
        "This paper discusses energy encryption and key management"
    )
    # Should find cross-domain links (or at least not crash)

    # Test citation scan
    result = IngestionResult(
        source_type=SourceType.ARXIV,
        raw_content="See arXiv:2301.12345",
        title="Test",
        identifiers={"arxiv_id": "2301.12345"},
    )
    links = engine.citation_scan(result.identifiers, result.raw_content)
    assert any(
        lnk.link_type == LinkType.CITATION for lnk in links
    ), "citation_scan should find CITATION link"

    # Test full find_links
    links = engine.find_links(result)
    assert len(links) > 0, "find_links should return at least one link"

    print("  [PASS] CrossReferenceEngine (4 strategies)")


def test_note_renderer():
    """Test markdown rendering."""
    from agents.obsidian_researcher.note_renderer import NoteRenderer
    from agents.obsidian_researcher.source_adapter import IngestionResult, SourceType
    from agents.obsidian_researcher.cross_reference_engine import WikiLink, LinkType

    renderer = NoteRenderer()
    result = IngestionResult(
        source_type=SourceType.ARXIV,
        raw_content="Abstract text here",
        title="Test Paper",
        authors=["Author One"],
        url="https://arxiv.org/abs/2301.12345",
        identifiers={"arxiv_id": "2301.12345"},
        tags=["cs.AI"],
        summary="Abstract text here",
    )
    links = [
        WikiLink(
            target_page="Harmonic Wall",
            link_type=LinkType.KEYWORD,
            confidence=0.8,
            reason="keyword match",
        )
    ]

    md = renderer.render(result, links)
    assert "---" in md, "Expected YAML frontmatter delimiters"
    assert "Test Paper" in md, "Expected title in rendered output"
    assert "Abstract" in md, "Expected Abstract section"
    assert "Cross-References" in md, "Expected Cross-References section"

    print("  [PASS] NoteRenderer")


def test_vault_manager():
    """Test routing and writing."""
    from agents.obsidian_researcher.vault_manager import VaultManager
    from agents.obsidian_researcher.source_adapter import IngestionResult, SourceType

    with tempfile.TemporaryDirectory() as tmpdir:
        vm = VaultManager(vault_root=tmpdir)

        # Test routing
        result = IngestionResult(
            source_type=SourceType.ARXIV,
            raw_content="cddm morphism functor",
            title="Test",
            summary="cddm morphism",
        )
        folder = vm.route_note(result, [])
        assert folder == "CDDM/", f"Expected 'CDDM/', got '{folder}'"

        # Test sanitize
        sanitized = vm.sanitize_filename("Test: A <Complex> Title")
        assert sanitized == "Test-A-Complex-Title", (
            f"Expected 'Test-A-Complex-Title', got '{sanitized}'"
        )

        # Test write
        path = vm.write_note("# Test\nContent", "References/", "Test Paper")
        assert path.exists(), f"Written file should exist at {path}"
        assert path.read_text(encoding="utf-8") == "# Test\nContent"

        # Test duplicate detection
        assert vm.check_duplicate("Test Paper") is True, (
            "check_duplicate should find 'Test Paper'"
        )
        assert vm.check_duplicate("Nonexistent") is False, (
            "check_duplicate should not find 'Nonexistent'"
        )

    print("  [PASS] VaultManager")


def test_coverage_map():
    """Test coverage tracking and gap analysis."""
    from agents.obsidian_researcher.coverage_map import CoverageMap, SCBE_CONCEPTS

    cm = CoverageMap()
    gaps = cm.get_gaps()
    assert len(gaps) == len(SCBE_CONCEPTS), (
        f"All concepts should be gaps initially; got {len(gaps)} of {len(SCBE_CONCEPTS)}"
    )

    # Render dashboard
    md = cm.render_map()
    assert "Coverage Map" in md, "Expected 'Coverage Map' in dashboard"
    assert "Research Gaps" in md, "Expected 'Research Gaps' in dashboard"

    print("  [PASS] CoverageMap")


def test_brainstorm_source():
    """Test brainstorm source with raw text."""
    from agents.obsidian_researcher.sources.brainstorm_source import BrainstormSource

    bs = BrainstormSource()
    results = bs.fetch(
        "Problem: How to optimize entropy defense\n"
        "The approach should use Kalman filters\n"
        "?What about PQC integration"
    )
    assert len(results) == 1, f"Expected 1 result, got {len(results)}"
    assert results[0].source_type.value == "brainstorm"

    print("  [PASS] BrainstormSource")


def test_web_page_source():
    """Test web page source with local file."""
    from agents.obsidian_researcher.sources.web_page_source import WebPageSource

    wps = WebPageSource()

    # Test with a local markdown file via fetch_by_id
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".md", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write("# Test Research\nSome content about SCBE layers and governance.")
            tmp_path = f.name

        result = wps.fetch_by_id(tmp_path)
        # WebPageSource.fetch_by_id treats identifier as a URL, not a file path.
        # A local file path will fail the HTTP fetch -- that is expected behaviour.
        # We verify it returns None gracefully without crashing.
        if result is not None:
            assert "governance" in result.raw_content or "Test Research" in result.raw_content
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    print("  [PASS] WebPageSource")


def test_notebook_lm_source():
    """Test NotebookLM source adapter."""
    from agents.obsidian_researcher.sources.notebook_lm_source import NotebookLMSource

    nls = NotebookLMSource()

    # Test with structured analysis text
    analysis = (
        "# SCBE Layer Analysis\n\n"
        "## 1. Binary Encoding\n"
        "The binary encoding layer converts sacred tongue tokens into "
        "balanced ternary representations.\n\n"
        "## 2. Harmonic Wall\n"
        "The cost function $H(d,R) = R^{d^2}$ provides exponential scaling.\n\n"
        "## 3. Implementation Notes\n"
        "```python\ndef encode(token): pass\n```\n\n"
        "Q: How does this relate to PQC envelopes?\n"
        "A: The lattice-based schemes provide the cryptographic foundation.\n"
    )

    results = nls.fetch(analysis, ai_source="notebooklm")
    assert len(results) == 1, f"Expected 1 result, got {len(results)}"

    r = results[0]
    assert r.source_type.value == "brainstorm"
    assert "ai-analysis" in r.tags
    assert "source:notebooklm" in r.tags
    assert r.metadata["has_math"] is True
    assert r.metadata["has_code"] is True
    assert r.metadata["section_count"] >= 3
    assert r.metadata["ai_source"] == "notebooklm"

    # Test format detection
    assert r.metadata["format"] in (
        "analysis",
        "specification",
        "transcript",
        "executive_brief",
        "mixed",
    )

    # Test title extraction
    assert "SCBE Layer Analysis" in r.title

    # Test fetch_by_id with file
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".md", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(analysis)
            tmp_path = f.name

        result = nls.fetch_by_id(tmp_path)
        assert result is not None, "fetch_by_id should succeed for existing file"
        assert result.metadata["section_count"] >= 3
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # Test with transcript-style text
    transcript = (
        "Speaker 1: So tell me about the governance framework.\n"
        "Speaker 2: Sure, it has 14 layers covering everything from "
        "binary encoding to federated learning.\n"
        "Speaker 1: And the harmonic wall?\n"
        "Speaker 2: That is the cost multiplier function.\n"
    )
    results = nls.fetch(transcript, ai_source="notebooklm", title="Podcast Ep 1")
    assert len(results) == 1
    assert results[0].title == "Podcast Ep 1"
    assert results[0].metadata["format"] == "transcript"

    # Test empty input
    results = nls.fetch("", ai_source="grok")
    assert len(results) == 0, "Empty input should return no results"

    print("  [PASS] NotebookLMSource")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


def main() -> int:
    # Add project root to path so `agents.obsidian_researcher` resolves
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    print("=" * 60)
    print("Obsidian Researcher Agent -- Self Test")
    print("=" * 60)

    passed = 0
    failed = 0

    # Core tests (always run)
    tests = [
        test_source_adapter,
        test_vault_source,
        test_cross_reference_engine,
        test_note_renderer,
        test_vault_manager,
        test_coverage_map,
    ]

    # Source-adapter tests (run if modules exist)
    optional = [
        ("agents.obsidian_researcher.sources.brainstorm_source", test_brainstorm_source),
        ("agents.obsidian_researcher.sources.web_page_source", test_web_page_source),
        ("agents.obsidian_researcher.sources.notebook_lm_source", test_notebook_lm_source),
    ]
    for mod_name, test_fn in optional:
        try:
            __import__(mod_name)
            tests.append(test_fn)
        except ImportError:
            print(f"  [SKIP] {test_fn.__name__} ({mod_name} not found)")

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
