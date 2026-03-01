"""
QuickPivot — Sub-5-Second Peripheral Context Engine
====================================================

Tri-path parallel search that provides "thought suggestions" —
the peripheral context that appears alongside a conversation,
like Grok's sidebar suggestions or ChatGPT's related topics.

Three paths run concurrently with a hard 4.5s deadline:

  Path 1: INTERNAL — PollyPivot FAISS+BM25 (local knowledge base)
  Path 2: INTERNET — HeadlessBrowser DuckDuckGo quick search
  Path 3: THOUGHT  — Pre-weighted suggestion from accumulated
                     conversation context (exponential decay memory)

Results merge into a ranked PivotCard list with source attribution.

Usage:
    pivot = QuickPivot(indexer=my_indexer)
    pivot.observe("We discussed Sacred Tongue encoding for KO domain")
    pivot.observe("The harmonic cost function uses phi^(d^2)")

    cards = await pivot.pivot("How does governance scaling work?")
    # Returns 3-8 PivotCards in < 5 seconds

@layer L3, L5
@component PollyPivot.QuickPivot
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .indexer import KnowledgeIndexer
from .searcher import HybridSearcher, SearchResult


# ---------------------------------------------------------------------------
# Thought accumulator — exponential-decay conversation memory
# ---------------------------------------------------------------------------

@dataclass
class ThoughtFragment:
    """A single observed statement from the conversation."""
    text: str
    timestamp: float
    weight: float = 1.0
    keywords: List[str] = field(default_factory=list)


class ThoughtAccumulator:
    """Weighted memory of conversation fragments with exponential decay.

    Each observation gets a weight that decays over time:
        w(t) = w_0 * exp(-lambda * (now - t_observed))

    When asked for suggestions, it extracts the highest-weight keywords
    and generates thought pivots — things the conversation is circling
    around but hasn't explicitly asked about.

    This is the "Grok sidebar" — pre-weighted hunches from context buildup.
    """

    def __init__(self, decay_lambda: float = 0.01, max_fragments: int = 100):
        self.decay_lambda = decay_lambda
        self.max_fragments = max_fragments
        self.fragments: List[ThoughtFragment] = []
        self._keyword_weights: Dict[str, float] = defaultdict(float)

    def observe(self, text: str, weight: float = 1.0) -> None:
        """Record a conversation fragment."""
        now = time.time()
        keywords = _extract_keywords(text)
        frag = ThoughtFragment(
            text=text,
            timestamp=now,
            weight=weight,
            keywords=keywords,
        )
        self.fragments.append(frag)

        # Update keyword weights
        for kw in keywords:
            self._keyword_weights[kw] += weight

        # Trim old fragments
        if len(self.fragments) > self.max_fragments:
            self.fragments = self.fragments[-self.max_fragments:]

    def suggest(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Generate thought-weighted suggestions based on accumulated context.

        Returns keywords that have been building up in the conversation
        but weren't directly in the query — peripheral context.

        Args:
            query: Current query to find peripheral context for.
            top_k: Number of suggestions.

        Returns:
            List of (keyword, weight) tuples sorted by accumulated weight.
        """
        now = time.time()
        query_words = set(query.lower().split())

        # Compute decayed keyword weights
        decayed: Dict[str, float] = defaultdict(float)
        for frag in self.fragments:
            age = now - frag.timestamp
            decay = math.exp(-self.decay_lambda * age)
            for kw in frag.keywords:
                decayed[kw] += frag.weight * decay

        # Remove keywords that are already in the query (we want peripheral)
        peripheral = {
            kw: w for kw, w in decayed.items()
            if kw.lower() not in query_words and len(kw) > 2
        }

        sorted_kw = sorted(peripheral.items(), key=lambda x: x[1], reverse=True)
        return sorted_kw[:top_k]

    def suggest_queries(self, query: str, top_k: int = 3) -> List[str]:
        """Generate full search queries from thought suggestions.

        Combines the current query with top peripheral keywords
        to create enriched search queries.
        """
        suggestions = self.suggest(query, top_k=top_k * 2)
        queries = []
        for kw, _ in suggestions[:top_k]:
            queries.append(f"{query} {kw}")
        return queries if queries else [query]

    @property
    def fragment_count(self) -> int:
        return len(self.fragments)

    @property
    def top_themes(self) -> List[Tuple[str, float]]:
        """Current top conversation themes."""
        return self.suggest("", top_k=10)


# ---------------------------------------------------------------------------
# Keyword extraction (fast, no deps)
# ---------------------------------------------------------------------------

# Stop words for keyword extraction
_STOP_WORDS = frozenset(
    "the a an is are was were be been being have has had do does did "
    "will would shall should may might can could this that these those "
    "i me my we our you your he she it they them his her its their "
    "and or but not if then else when where what which who whom how "
    "in on at to for from by with of about as into through during "
    "before after above below between under over up down out off "
    "all each every both few many much some any no more most other "
    "than too very just also still even already yet again "
    "so because while although though since until unless".split()
)


def _extract_keywords(text: str, max_keywords: int = 15) -> List[str]:
    """Fast keyword extraction — split + filter stopwords + deduplicate."""
    words = text.lower().split()
    # Remove punctuation from edges
    cleaned = []
    for w in words:
        w = w.strip(".,;:!?\"'()[]{}<>-_/\\@#$%^&*+=~`")
        if w and w not in _STOP_WORDS and len(w) > 2:
            cleaned.append(w)
    # Deduplicate preserving order
    seen = set()
    unique = []
    for w in cleaned:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return unique[:max_keywords]


# ---------------------------------------------------------------------------
# PivotCard — the output unit
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PivotCard:
    """A single peripheral context suggestion."""
    text: str               # summary snippet
    source: str             # "internal", "internet", "thought"
    relevance: float        # 0-1 relevance score
    url: str = ""           # source URL (for internet results)
    tongue: str = ""        # Sacred Tongue affinity
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "text": self.text[:300],
            "source": self.source,
            "relevance": round(self.relevance, 3),
            "url": self.url,
            "tongue": self.tongue,
            "keywords": self.keywords[:5],
        }


# ---------------------------------------------------------------------------
# QuickPivot — the orchestrator
# ---------------------------------------------------------------------------

class QuickPivot:
    """Sub-5-second peripheral context engine with tri-path parallel search.

    Usage:
        pivot = QuickPivot(indexer=my_built_indexer)

        # Feed conversation context over time
        pivot.observe("We're discussing SCBE governance layers")
        pivot.observe("The harmonic cost uses phi^(d^2) scaling")

        # Get peripheral context for current query
        cards = await pivot.pivot("How does drift detection work?")
        for card in cards:
            print(f"[{card.source}] {card.text} (relevance={card.relevance:.2f})")
    """

    def __init__(
        self,
        indexer: Optional[KnowledgeIndexer] = None,
        enable_internet: bool = True,
        timeout: float = 4.5,
        max_cards: int = 8,
    ):
        self.indexer = indexer
        self.searcher: Optional[HybridSearcher] = None
        if indexer and indexer.is_built:
            self.searcher = HybridSearcher(indexer)
        self.enable_internet = enable_internet
        self.timeout = timeout
        self.max_cards = max_cards
        self.thoughts = ThoughtAccumulator()

    def observe(self, text: str, weight: float = 1.0) -> None:
        """Feed a conversation fragment into the thought accumulator."""
        self.thoughts.observe(text, weight)

    async def pivot(self, query: str) -> List[PivotCard]:
        """Run tri-path parallel search and return merged PivotCards.

        All three paths run concurrently with a hard timeout.
        Partial results are returned if some paths timeout.

        Args:
            query: Current conversation query/context.

        Returns:
            List of PivotCards sorted by relevance (max: max_cards).
        """
        # Record the query itself as an observation
        self.thoughts.observe(query, weight=0.5)

        # Launch all three paths concurrently
        tasks = [
            asyncio.create_task(self._path_internal(query)),
            asyncio.create_task(self._path_internet(query)),
            asyncio.create_task(self._path_thought(query)),
        ]

        # Wait with hard timeout
        done, pending = await asyncio.wait(
            tasks, timeout=self.timeout, return_when=asyncio.ALL_COMPLETED
        )

        # Cancel any that didn't finish
        for task in pending:
            task.cancel()

        # Collect results
        cards: List[PivotCard] = []
        for task in done:
            try:
                result = task.result()
                cards.extend(result)
            except Exception:
                pass

        # Deduplicate by text hash
        seen_hashes = set()
        unique = []
        for card in cards:
            h = hashlib.md5(card.text[:100].encode()).hexdigest()[:8]
            if h not in seen_hashes:
                seen_hashes.add(h)
                unique.append(card)

        # Sort by relevance, cap at max_cards
        unique.sort(key=lambda c: c.relevance, reverse=True)
        return unique[:self.max_cards]

    # ── Path 1: Internal Knowledge ────────────────────────────────────

    async def _path_internal(self, query: str) -> List[PivotCard]:
        """Search local FAISS+BM25 index."""
        if self.searcher is None:
            return []

        # Run in thread pool since FAISS is sync
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, lambda: self.searcher.search(query, top_k=5)
        )

        cards = []
        for r in results:
            # Normalize score to 0-1 range
            norm_score = min(r.score * 50, 1.0)  # RRF scores are small
            cards.append(PivotCard(
                text=r.document.text[:250],
                source="internal",
                relevance=norm_score,
                url=r.document.source_path,
                tongue=r.document.tongue,
                keywords=_extract_keywords(r.document.text, 5),
            ))
        return cards

    # ── Path 2: Quick Internet Search ──────────────────────────────────

    async def _path_internet(self, query: str) -> List[PivotCard]:
        """Quick DuckDuckGo search via headless browser (2s budget)."""
        if not self.enable_internet:
            return []

        try:
            from src.browser.headless import HeadlessBrowser
        except ImportError:
            return []

        cards = []
        try:
            async with HeadlessBrowser(enable_playwright=False) as browser:
                results = await asyncio.wait_for(
                    browser.search(query, max_results=5),
                    timeout=3.0,
                )
                for r in results:
                    cards.append(PivotCard(
                        text=f"{r.title}: {r.snippet}"[:250],
                        source="internet",
                        relevance=0.6,  # base relevance for web results
                        url=r.url,
                        keywords=_extract_keywords(r.snippet, 5),
                    ))
        except (asyncio.TimeoutError, Exception):
            pass

        return cards

    # ── Path 3: Thought Suggestions ────────────────────────────────────

    async def _path_thought(self, query: str) -> List[PivotCard]:
        """Generate pre-weighted suggestions from accumulated context."""
        if self.thoughts.fragment_count == 0:
            return []

        suggestions = self.thoughts.suggest(query, top_k=5)
        enriched_queries = self.thoughts.suggest_queries(query, top_k=3)

        cards = []

        # Direct keyword suggestions
        for kw, weight in suggestions:
            norm_weight = min(weight / 5.0, 1.0)
            if norm_weight > 0.1:
                cards.append(PivotCard(
                    text=f"Related theme: {kw}",
                    source="thought",
                    relevance=norm_weight * 0.8,
                    keywords=[kw],
                ))

        # Enriched query suggestions (the "you might also want to ask" cards)
        for eq in enriched_queries:
            cards.append(PivotCard(
                text=f"Consider: {eq}",
                source="thought",
                relevance=0.5,
                keywords=_extract_keywords(eq, 5),
            ))

        # If we have internal search, use thought-enriched queries for deeper hits
        if self.searcher is not None:
            loop = asyncio.get_event_loop()
            for eq in enriched_queries[:2]:
                try:
                    results = await loop.run_in_executor(
                        None, lambda q=eq: self.searcher.search(q, top_k=2)
                    )
                    for r in results:
                        norm_score = min(r.score * 40, 0.9)
                        cards.append(PivotCard(
                            text=r.document.text[:200],
                            source="thought",
                            relevance=norm_score,
                            url=r.document.source_path,
                            tongue=r.document.tongue,
                            keywords=_extract_keywords(r.document.text, 5),
                        ))
                except Exception:
                    pass

        return cards

    # ── Convenience methods ────────────────────────────────────────────

    async def pivot_sync_wrapper(self, query: str) -> List[PivotCard]:
        """Synchronous-friendly wrapper (runs event loop if needed)."""
        try:
            loop = asyncio.get_running_loop()
            return await self.pivot(query)
        except RuntimeError:
            return asyncio.run(self.pivot(query))

    def themes(self) -> List[Tuple[str, float]]:
        """Get current conversation themes from the thought accumulator."""
        return self.thoughts.top_themes

    def stats(self) -> Dict:
        """Diagnostic stats."""
        return {
            "fragments": self.thoughts.fragment_count,
            "themes": len(self.thoughts.top_themes),
            "has_indexer": self.searcher is not None,
            "internet_enabled": self.enable_internet,
            "timeout": self.timeout,
            "max_cards": self.max_cards,
        }
