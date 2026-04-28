"""
Regression test for ResearchAgent._score_relevance.

The agent bus self-review surfaced that all 3 published research findings
shared confidence 0.76 because the previous scoring formula was a discrete
function of (text_hits / N) and (title_hits / N) only — pages with the
same hit pattern collapsed to identical scores.

This test pins the fix: continuous tie-breakers (term-frequency density,
length signal, first-match position) must produce distinct scores for
three pages that share a hit pattern but differ on length / density /
first-match position.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.research_agent import ResearchAgent  # noqa: E402


@dataclass
class _StubPage:
    url: str
    title: str
    text: str
    word_count: int
    headings: List[dict] = field(default_factory=list)
    links: List[dict] = field(default_factory=list)
    tables: List[dict] = field(default_factory=list)
    jsonld: List[dict] = field(default_factory=list)
    error: str = ""


def _make_agent() -> ResearchAgent:
    return ResearchAgent(scraper=None)


def test_three_pages_same_hit_pattern_get_distinct_scores():
    """Same query-term hit pattern, different bodies → distinct scores."""
    query_terms = {"scbe", "hyperbolic", "geometry", "ai", "governance"}
    # Use sorted phrase so we explicitly trigger or avoid the phrase bonus.
    phrase = " ".join(sorted(query_terms))
    title = "Some Unrelated Page Title"  # zero title hits

    body_terms = "scbe hyperbolic geometry ai governance "  # all 5, but not sorted

    short = _StubPage(
        url="https://a.example/short",
        title=title,
        text=body_terms + ("filler word " * 50),
        word_count=120,
    )
    medium = _StubPage(
        url="https://b.example/medium",
        title=title,
        text=body_terms * 3 + ("filler word " * 400),
        word_count=900,
    )
    long_dense = _StubPage(
        url="https://c.example/long",
        title=title,
        text=body_terms * 8 + ("filler word " * 1200),
        word_count=2600,
    )

    # Sanity: no phrase bonus on any of these (sorted phrase not present).
    for p in (short, medium, long_dense):
        assert phrase not in p.text.lower()

    agent = _make_agent()
    scores = [agent._score_relevance(p, query_terms) for p in (short, medium, long_dense)]

    assert all(0.0 <= s <= 1.0 for s in scores), scores
    assert len(set(scores)) == 3, f"expected 3 distinct scores, got {scores}"


def test_empty_text_returns_zero():
    agent = _make_agent()
    page = _StubPage(url="https://x", title="t", text="", word_count=0)
    assert agent._score_relevance(page, {"foo"}) == 0.0


def test_empty_query_returns_neutral():
    agent = _make_agent()
    page = _StubPage(url="https://x", title="t", text="anything", word_count=10)
    assert agent._score_relevance(page, set()) == 0.5


def test_phrase_bonus_present_when_phrase_in_text():
    agent = _make_agent()
    terms = {"alpha", "beta"}
    phrase = " ".join(sorted(terms))
    page_with = _StubPage(
        url="https://w/with",
        title="t",
        text=f"intro {phrase} body more body words " * 30,
        word_count=300,
    )
    page_without = _StubPage(
        url="https://w/without",
        title="t",
        text=("alpha gap " * 50) + ("beta gap " * 50),
        word_count=300,
    )
    s_with = agent._score_relevance(page_with, terms)
    s_without = agent._score_relevance(page_without, terms)
    assert s_with > s_without
