"""
Research agent built on WebScraper + PlaywrightRuntime.

Performs multi-site research tasks: searches, reads, extracts, compares,
and produces structured research reports. Designed for agent workflows
and MCP tool integration.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger("scbe.agents.research_agent")


@dataclass
class ResearchFinding:
    """A single finding from research."""

    source_url: str
    title: str
    relevant_text: str
    confidence: float  # 0-1
    tags: List[str] = field(default_factory=list)


@dataclass
class ResearchReport:
    """Structured output from a research task."""

    query: str
    findings: List[ResearchFinding] = field(default_factory=list)
    sources_checked: int = 0
    total_words_read: int = 0
    duration_seconds: float = 0
    summary: str = ""
    errors: List[str] = field(default_factory=list)
    source_outcomes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        lines = [f"# Research: {self.query}", ""]
        if self.summary:
            lines += [self.summary, ""]
        lines += [
            f"**Sources**: {self.sources_checked} checked, "
            f"{len(self.findings)} relevant findings, "
            f"{self.total_words_read:,} words read in {self.duration_seconds:.1f}s",
            "",
        ]
        for i, f in enumerate(self.findings, 1):
            lines += [
                f"## {i}. {f.title}",
                f"**Source**: {f.source_url}",
                f"**Confidence**: {f.confidence:.0%}",
                f"**Tags**: {', '.join(f.tags)}" if f.tags else "",
                "",
                f.relevant_text[:1000],
                "",
            ]
        if self.errors:
            lines += ["## Errors", ""] + [f"- {e}" for e in self.errors]
        return "\n".join(lines)


class ResearchAgent:
    """
    Autonomous research agent. Given a query, searches the web, reads
    top results, extracts relevant information, and produces a report.

    Usage:
        from agents.playwright_runtime import PlaywrightRuntime
        from agents.web_scraper import WebScraper
        from agents.research_agent import ResearchAgent

        rt = PlaywrightRuntime()
        await rt.launch(headless=True)
        scraper = WebScraper(rt)
        researcher = ResearchAgent(scraper)

        report = await researcher.research("SCBE hyperbolic geometry AI safety")
        print(report.to_markdown())
        await rt.close()
    """

    def __init__(
        self,
        scraper,
        *,
        max_sources: int = 8,
        max_depth: int = 1,
        relevance_threshold: float = 0.3,
    ) -> None:
        self.scraper = scraper
        self.max_sources = max_sources
        self.max_depth = max_depth
        self.relevance_threshold = relevance_threshold

    async def research(
        self,
        query: str,
        *,
        search_engine: str = "duckduckgo",
        follow_links: bool = False,
    ) -> ResearchReport:
        """
        Perform a research task.

        1. Search the web for the query
        2. Scrape top results
        3. Score relevance of each result
        4. Optionally follow promising links for deeper research
        5. Compile findings into a report
        """
        start = time.monotonic()
        report = ResearchReport(query=query)

        # Step 1: Search and scrape
        try:
            pages = await self.scraper.search_and_scrape(
                query,
                engine=search_engine,
                max_results=self.max_sources,
            )
        except Exception as exc:
            report.errors.append(f"Search failed: {exc}")
            logger.warning("Research search failed: %s", exc)
            pages = []

        # Step 2: Score and extract findings
        query_terms = set(query.lower().split())
        for page in pages:
            report.sources_checked += 1
            report.total_words_read += page.word_count

            if page.error:
                report.errors.append(f"{page.url}: {page.error}")
                report.source_outcomes.append(self._source_outcome(page, "error", 0.0, page.error))
                continue

            # Relevance scoring
            score = self._score_relevance(page, query_terms)
            if score < self.relevance_threshold:
                report.source_outcomes.append(self._source_outcome(page, "below_threshold", score))
                continue

            # Extract the most relevant portion of text
            relevant_text = self._extract_relevant_passage(page.text, query_terms)

            # Tag by content type
            tags = self._auto_tag(page)

            report.findings.append(
                ResearchFinding(
                    source_url=page.url,
                    title=page.title,
                    relevant_text=relevant_text,
                    confidence=min(1.0, score),
                    tags=tags,
                )
            )
            report.source_outcomes.append(self._source_outcome(page, "matched", score))

        # Step 3: Follow links for depth (if enabled and findings are thin)
        if follow_links and len(report.findings) < 3 and self.max_depth > 0:
            follow_urls = self._pick_follow_links(pages, query_terms)
            for url in follow_urls[:3]:
                try:
                    page = await self.scraper.scrape(url)
                    report.sources_checked += 1
                    report.total_words_read += page.word_count
                    if page.error:
                        report.errors.append(f"{page.url}: {page.error}")
                        report.source_outcomes.append(self._source_outcome(page, "error", 0.0, page.error))
                        continue
                    score = self._score_relevance(page, query_terms)
                    if score >= self.relevance_threshold:
                        report.findings.append(
                            ResearchFinding(
                                source_url=page.url,
                                title=page.title,
                                relevant_text=self._extract_relevant_passage(page.text, query_terms),
                                confidence=min(1.0, score),
                                tags=self._auto_tag(page) + ["followed-link"],
                            )
                        )
                        report.source_outcomes.append(self._source_outcome(page, "matched_followed_link", score))
                    else:
                        report.source_outcomes.append(self._source_outcome(page, "below_threshold_followed_link", score))
                except Exception as exc:
                    report.errors.append(f"Follow link {url}: {exc}")
                    report.source_outcomes.append(
                        {
                            "url": url,
                            "title": "",
                            "status": "error_followed_link",
                            "score": 0.0,
                            "word_count": 0,
                            "reason": str(exc),
                        }
                    )

        # Sort findings by confidence
        report.findings.sort(key=lambda f: f.confidence, reverse=True)

        report.duration_seconds = time.monotonic() - start
        report.summary = self._generate_summary(report)

        logger.info(
            "Research '%s': %d findings from %d sources in %.1fs",
            query,
            len(report.findings),
            report.sources_checked,
            report.duration_seconds,
        )
        return report

    async def compare_sources(
        self,
        urls: List[str],
        topic: str,
    ) -> Dict[str, Any]:
        """
        Read multiple specific URLs and compare their content on a topic.
        Returns a structured comparison.
        """
        pages = await self.scraper.scrape_many(urls)
        topic_terms = set(topic.lower().split())

        comparison = {
            "topic": topic,
            "sources": [],
            "common_themes": [],
            "unique_claims": [],
        }

        all_headings = []
        for page in pages:
            score = self._score_relevance(page, topic_terms)
            source = {
                "url": page.url,
                "title": page.title,
                "word_count": page.word_count,
                "relevance": round(score, 2),
                "key_points": [h["text"] for h in page.headings if any(t in h["text"].lower() for t in topic_terms)][
                    :5
                ],
                "text_preview": self._extract_relevant_passage(page.text, topic_terms)[:500],
            }
            comparison["sources"].append(source)
            all_headings.extend(h["text"].lower() for h in page.headings)

        # Find common themes (headings appearing in multiple sources)
        from collections import Counter

        heading_words = Counter()
        for h in all_headings:
            for w in h.split():
                if len(w) > 3:
                    heading_words[w] += 1
        comparison["common_themes"] = [w for w, c in heading_words.most_common(10) if c > 1]

        return comparison

    async def monitor_sites(
        self,
        urls: List[str],
        *,
        extract_text: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Quick read of multiple sites. Returns structured summaries.
        Good for dashboards and monitoring workflows.
        """
        pages = await self.scraper.scrape_many(urls, extract_text=extract_text, delay_ms=300)
        return [p.summary() for p in pages]

    # -- internal scoring ----------------------------------------------------

    def _score_relevance(self, page, query_terms: set) -> float:
        """Score 0-1 how relevant a page is to the query.

        Composite of presence (text+title), continuous tie-breakers
        (term-frequency density, length, first-match position), phrase
        bonus, and short-page penalty. The continuous tie-breakers
        prevent same-pattern pages from collapsing to identical scores.
        """
        import math

        if not page.text:
            return 0.0
        if not query_terms:
            return 0.5

        text_lower = page.text.lower()
        title_lower = (page.title or "").lower()

        # Presence: fraction of query terms found.
        text_hits = sum(1 for t in query_terms if t in text_lower)
        title_hits = sum(1 for t in query_terms if t in title_lower)
        text_score = text_hits / len(query_terms)
        title_score = title_hits / len(query_terms)

        # Continuous tie-breakers (max combined ~0.16 so they refine
        # rather than dominate the presence headline).
        total_occurrences = sum(text_lower.count(t) for t in query_terms)
        density = total_occurrences / max(page.word_count / 1000.0, 0.1)
        density_signal = min(0.08, math.log1p(density) * 0.04)

        length_signal = min(0.04, math.log10(max(page.word_count, 1) / 100.0) * 0.02)
        length_signal = max(0.0, length_signal)

        first_positions = [text_lower.find(t) for t in query_terms if t in text_lower]
        if first_positions:
            first_pos = min(first_positions)
            position_signal = max(0.0, 0.04 - (first_pos / max(len(text_lower), 1)) * 0.04)
        else:
            position_signal = 0.0

        score = (
            (text_score * 0.4)
            + (title_score * 0.6)
            + density_signal
            + length_signal
            + position_signal
        )

        # Bonus for exact phrase match
        query_phrase = " ".join(sorted(query_terms))
        if query_phrase in text_lower:
            score += 0.2

        # Penalty for very short pages
        if page.word_count < 100:
            score *= 0.5

        return max(0.0, min(1.0, score))

    def _extract_relevant_passage(self, text: str, query_terms: set, window: int = 500) -> str:
        """Extract the most relevant passage from text."""
        if not text or not query_terms:
            return text[:window] if text else ""

        text_lower = text.lower()
        best_pos = 0
        best_score = 0

        # Sliding window to find densest region of query terms
        for term in query_terms:
            pos = text_lower.find(term)
            while pos != -1:
                # Count terms in window around this position
                start = max(0, pos - window // 2)
                end = min(len(text), pos + window // 2)
                chunk = text_lower[start:end]
                score = sum(1 for t in query_terms if t in chunk)
                if score > best_score:
                    best_score = score
                    best_pos = start
                pos = text_lower.find(term, pos + 1)

        start = max(0, best_pos)
        end = min(len(text), start + window)

        # Extend to sentence boundaries
        while start > 0 and text[start] not in ".!?\n":
            start -= 1
        if start > 0:
            start += 1
        while end < len(text) and text[end] not in ".!?\n":
            end += 1

        return text[start:end].strip()

    def _auto_tag(self, page) -> List[str]:
        """Auto-tag a page by content type."""
        tags = []
        url = page.url.lower()

        if "arxiv.org" in url:
            tags.append("academic")
        if "github.com" in url:
            tags.append("code")
        if any(w in url for w in ["news", "blog", "medium.com", "substack"]):
            tags.append("article")
        if any(w in url for w in ["docs", "documentation", "wiki"]):
            tags.append("documentation")
        if page.jsonld:
            for item in page.jsonld:
                if isinstance(item, dict) and "Article" in str(item.get("@type", "")):
                    tags.append("article")

        if page.tables:
            tags.append("has-tables")
        if page.word_count > 2000:
            tags.append("long-form")
        if page.word_count < 300:
            tags.append("short")

        return list(set(tags))

    def _pick_follow_links(self, pages, query_terms: set) -> List[str]:
        """Pick the best links to follow for deeper research."""
        candidates = []
        seen = {p.url for p in pages}

        for page in pages:
            for link in page.links[:20]:
                href = link.get("href", "")
                text = link.get("text", "").lower()
                if href in seen or not href.startswith("http"):
                    continue
                # Score by query term presence in link text
                score = sum(1 for t in query_terms if t in text)
                if score > 0:
                    candidates.append((score, href))
                    seen.add(href)

        candidates.sort(reverse=True)
        return [url for _, url in candidates[:5]]

    def _source_outcome(self, page, status: str, score: float, reason: str = "") -> Dict[str, Any]:
        """Compact per-source receipt for dashboard/debugging without storing full page text."""
        return {
            "url": page.url,
            "title": page.title,
            "status": status,
            "score": round(float(score), 4),
            "word_count": int(page.word_count or 0),
            "reason": reason,
        }

    def _generate_summary(self, report: ResearchReport) -> str:
        """Generate a one-line summary."""
        if not report.findings:
            return f"No relevant findings for '{report.query}' across {report.sources_checked} sources."
        top = report.findings[0]
        return (
            f"Found {len(report.findings)} relevant sources for '{report.query}'. "
            f"Top result: {top.title} ({top.confidence:.0%} confidence). "
            f"Read {report.total_words_read:,} words across {report.sources_checked} pages."
        )
