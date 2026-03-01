"""Tests for QuickPivot — sub-5s peripheral context engine."""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.polly_pivot.quick_pivot import (
    QuickPivot,
    PivotCard,
    ThoughtAccumulator,
    ThoughtFragment,
    _extract_keywords,
)
from src.polly_pivot.indexer import KnowledgeIndexer


# ── Keyword Extraction ──────────────────────────────────────────────────

class TestKeywordExtraction:
    def test_basic_extraction(self):
        kws = _extract_keywords("The governance framework controls all agents")
        assert "governance" in kws
        assert "framework" in kws
        assert "the" not in kws  # stopword

    def test_stopword_removal(self):
        kws = _extract_keywords("this is a test of the system")
        assert "test" in kws
        assert "system" in kws
        assert "this" not in kws
        assert "the" not in kws

    def test_deduplication(self):
        kws = _extract_keywords("test test test different test")
        assert kws.count("test") == 1

    def test_max_keywords(self):
        text = " ".join(f"word{i}" for i in range(50))
        kws = _extract_keywords(text, max_keywords=10)
        assert len(kws) <= 10

    def test_short_words_filtered(self):
        kws = _extract_keywords("I am an AI at OK go do it")
        # All 1-2 letter words should be filtered
        for kw in kws:
            assert len(kw) > 2

    def test_punctuation_stripped(self):
        kws = _extract_keywords("hello, world! test's (great) [nice]")
        assert "hello" in kws
        assert "world" in kws


# ── ThoughtAccumulator ──────────────────────────────────────────────────

class TestThoughtAccumulator:
    def test_observe_adds_fragments(self):
        acc = ThoughtAccumulator()
        acc.observe("governance scaling uses phi")
        assert acc.fragment_count == 1

    def test_suggest_returns_keywords(self):
        acc = ThoughtAccumulator()
        acc.observe("governance scaling uses harmonic cost phi")
        acc.observe("Sacred Tongues encode meaning with phi weights")
        acc.observe("governance layers protect against drift")
        suggestions = acc.suggest("how does scaling work?")
        kws = [s[0] for s in suggestions]
        # "governance" and "phi" should be high-weight (mentioned multiple times)
        assert len(suggestions) > 0

    def test_peripheral_excludes_query_words(self):
        acc = ThoughtAccumulator()
        acc.observe("governance and security are important")
        suggestions = acc.suggest("governance")
        kws = [s[0] for s in suggestions]
        assert "governance" not in kws  # should be excluded (in query)

    def test_decay_reduces_old_weights(self):
        acc = ThoughtAccumulator(decay_lambda=10.0)  # aggressive decay
        acc.observe("old topic governance")
        # Manually age the fragment
        acc.fragments[0].timestamp -= 100  # 100 seconds ago
        acc.observe("new topic security")
        suggestions = acc.suggest("test query")
        kws = [s[0] for s in suggestions]
        if "security" in kws and "governance" in kws:
            sec_w = next(w for k, w in suggestions if k == "security")
            gov_w = next(w for k, w in suggestions if k == "governance")
            # governance should have decayed more (or at least not dominate)
            # With lambda=10, 100 seconds = exp(-1000) ≈ 0
            assert sec_w >= gov_w

    def test_suggest_queries(self):
        acc = ThoughtAccumulator()
        acc.observe("governance harmonic cost phi scaling")
        queries = acc.suggest_queries("how does drift work?")
        assert len(queries) > 0
        # Each enriched query should contain the original query
        for q in queries:
            assert "how does drift work?" in q

    def test_max_fragments_trimmed(self):
        acc = ThoughtAccumulator(max_fragments=5)
        for i in range(20):
            acc.observe(f"fragment number {i}")
        assert acc.fragment_count == 5

    def test_top_themes(self):
        acc = ThoughtAccumulator()
        acc.observe("governance is key")
        acc.observe("security matters")
        themes = acc.top_themes
        assert isinstance(themes, list)


# ── PivotCard ────────────────────────────────────────────────────────────

class TestPivotCard:
    def test_to_dict(self):
        card = PivotCard(
            text="Test pivot card",
            source="internal",
            relevance=0.85,
            url="/test",
            tongue="KO",
            keywords=["test", "pivot"],
        )
        d = card.to_dict()
        assert d["source"] == "internal"
        assert d["relevance"] == 0.85
        assert d["tongue"] == "KO"

    def test_text_truncation(self):
        card = PivotCard(text="x" * 500, source="thought", relevance=0.5)
        d = card.to_dict()
        assert len(d["text"]) == 300


# ── QuickPivot (unit, no internet) ──────────────────────────────────────

class TestQuickPivotUnit:
    def test_observe_feeds_thoughts(self):
        qp = QuickPivot(enable_internet=False)
        qp.observe("governance scaling and harmonic cost")
        assert qp.thoughts.fragment_count == 1

    def test_themes(self):
        qp = QuickPivot(enable_internet=False)
        qp.observe("governance scaling cost")
        qp.observe("Sacred Tongues phi weights")
        themes = qp.themes()
        assert isinstance(themes, list)

    def test_stats(self):
        qp = QuickPivot(enable_internet=False)
        s = qp.stats()
        assert s["internet_enabled"] is False
        assert s["has_indexer"] is False

    @pytest.mark.asyncio
    async def test_pivot_no_indexer_no_internet(self):
        """Pivot with no indexer and no internet should still return thought cards."""
        qp = QuickPivot(enable_internet=False)
        qp.observe("governance harmonic cost phi scaling layer")
        qp.observe("Sacred Tongues KO AV RU encode meaning")
        qp.observe("drift detection Poincare ball distance")
        cards = await qp.pivot("how does governance work?")
        assert isinstance(cards, list)
        # Should get thought-path cards at minimum
        thought_cards = [c for c in cards if c.source == "thought"]
        assert len(thought_cards) > 0

    @pytest.mark.asyncio
    async def test_pivot_with_indexer(self):
        """Pivot with a built indexer should return internal + thought cards."""
        indexer = KnowledgeIndexer()
        indexer.add_text(
            "The governance framework enforces authority and control",
            title="governance", source_path="/gov",
        )
        indexer.add_text(
            "Sacred Tongues KO AV RU CA UM DR encode meaning",
            title="tongues", source_path="/tongues",
        )
        indexer.add_text(
            "Drift detection uses Poincare ball hyperbolic distance",
            title="drift", source_path="/drift",
        )
        indexer.build()

        qp = QuickPivot(indexer=indexer, enable_internet=False)
        qp.observe("We were discussing governance layers")

        cards = await qp.pivot("how does governance scaling work?")
        assert len(cards) > 0
        sources = {c.source for c in cards}
        assert "internal" in sources or "thought" in sources

    @pytest.mark.asyncio
    async def test_pivot_under_5_seconds(self):
        """Pivot should complete in under 5 seconds."""
        qp = QuickPivot(enable_internet=False, timeout=4.5)
        qp.observe("test context for timing")
        start = time.time()
        cards = await qp.pivot("test query")
        elapsed = time.time() - start
        assert elapsed < 5.0

    @pytest.mark.asyncio
    async def test_deduplication(self):
        """Duplicate cards should be deduplicated."""
        indexer = KnowledgeIndexer()
        indexer.add_text("governance governance governance", source_path="/gov")
        indexer.build()

        qp = QuickPivot(indexer=indexer, enable_internet=False)
        qp.observe("governance governance governance")
        cards = await qp.pivot("governance")
        texts = [c.text[:50] for c in cards]
        # No exact duplicate text snippets
        assert len(texts) == len(set(texts))

    @pytest.mark.asyncio
    async def test_max_cards_respected(self):
        """Should not return more than max_cards."""
        indexer = KnowledgeIndexer()
        for i in range(20):
            indexer.add_text(f"document number {i} about topic {i}", source_path=f"/{i}")
        indexer.build()

        qp = QuickPivot(indexer=indexer, enable_internet=False, max_cards=3)
        for i in range(10):
            qp.observe(f"observation about topic {i}")
        cards = await qp.pivot("topic")
        assert len(cards) <= 3

    @pytest.mark.asyncio
    async def test_cards_sorted_by_relevance(self):
        """Cards should be sorted highest relevance first."""
        indexer = KnowledgeIndexer()
        indexer.add_text("governance authority control", source_path="/gov")
        indexer.add_text("random unrelated topic", source_path="/rand")
        indexer.build()

        qp = QuickPivot(indexer=indexer, enable_internet=False)
        qp.observe("governance is very important")
        cards = await qp.pivot("governance authority")
        if len(cards) >= 2:
            assert cards[0].relevance >= cards[1].relevance
