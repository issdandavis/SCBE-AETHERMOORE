"""Unified Research Connector Service with tiered source filtration.

Orchestrates all source adapters into a single search pipeline with
4 quality tiers, deduplication, relevance scoring, and governance
scanning. This is the sellable service layer.

Tiers (highest trust first):
    Tier 1 — Academic:   arXiv, ORCID, USPTO, Semantic Scholar, CrossRef
    Tier 2 — Professional: GitHub, NotebookLM
    Tier 3 — General:    WebPage (with governance filter)
    Tier 4 — Community:  Reddit, forums (heavy filtration)

Usage::

    service = ResearchConnectorService()
    results = service.search("hyperbolic AI safety", tiers=[1, 2])
    results = service.search("LLM governance", max_results=20)
    health  = service.health_report()

@layer Layer 13 (governance), Layer 14 (telemetry)
@component ResearchPipeline.Service
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Set, Tuple

from .source_adapter import IngestionResult, SourceAdapter, SourceType

logger = logging.getLogger(__name__)


class Tier(IntEnum):
    """Source quality tiers, ordered by trust level."""
    ACADEMIC = 1
    PROFESSIONAL = 2
    GENERAL = 3
    COMMUNITY = 4


# Trust multiplier per tier — higher = more trusted
_TIER_TRUST: Dict[Tier, float] = {
    Tier.ACADEMIC: 1.0,
    Tier.PROFESSIONAL: 0.8,
    Tier.GENERAL: 0.5,
    Tier.COMMUNITY: 0.3,
}

# Quality thresholds — results below this score are filtered out
_TIER_THRESHOLD: Dict[Tier, float] = {
    Tier.ACADEMIC: 0.0,      # Academic sources always pass
    Tier.PROFESSIONAL: 0.1,  # Low bar for pro sources
    Tier.GENERAL: 0.3,       # Medium bar for general
    Tier.COMMUNITY: 0.5,     # High bar for community
}


@dataclass
class ScoredResult:
    """An IngestionResult with quality scoring metadata."""
    result: IngestionResult
    tier: Tier
    trust_score: float  # 0.0 - 1.0
    relevance_score: float  # 0.0 - 1.0
    composite_score: float  # trust * relevance
    source_name: str = ""
    deduplicated: bool = False


@dataclass
class SearchReport:
    """Structured output from a tiered search."""
    query: str
    results: List[ScoredResult]
    total_raw: int  # Total results before dedup/filter
    total_filtered: int  # Results after filtering
    tiers_searched: List[int]
    sources_queried: List[str]
    elapsed_ms: float
    errors: List[str] = field(default_factory=list)


@dataclass
class HealthReport:
    """Health status of all registered sources."""
    sources: Dict[str, bool]
    tiers: Dict[int, List[str]]
    total_healthy: int
    total_unhealthy: int


class ResearchConnectorService:
    """Unified research pipeline with tiered source filtration.

    Parameters
    ----------
    config : dict
        Per-source configuration dicts, keyed by source name.
        Example::

            {
                "arxiv": {"category": "cs.AI"},
                "semantic_scholar": {"limit": 20},
                "github": {"token": "ghp_..."},
            }
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._config = config or {}
        self._sources: Dict[str, Tuple[SourceAdapter, Tier]] = {}
        self._init_sources()

    def _init_sources(self) -> None:
        """Initialize all available source adapters.

        Sources that fail to import or initialize are logged and skipped.
        """
        # Tier 1 — Academic
        self._try_register("arxiv", Tier.ACADEMIC, self._make_arxiv)
        self._try_register("orcid", Tier.ACADEMIC, self._make_orcid)
        self._try_register("uspto", Tier.ACADEMIC, self._make_uspto)
        self._try_register("semantic_scholar", Tier.ACADEMIC, self._make_semantic_scholar)
        self._try_register("crossref", Tier.ACADEMIC, self._make_crossref)

        # Tier 2 — Professional
        self._try_register("github", Tier.PROFESSIONAL, self._make_github)
        self._try_register("notebook_lm", Tier.PROFESSIONAL, self._make_notebook_lm)

        # Tier 3 — General
        self._try_register("web_page", Tier.GENERAL, self._make_web_page)

        # Tier 4 — Community
        self._try_register("reddit", Tier.COMMUNITY, self._make_reddit)

    def _try_register(self, name: str, tier: Tier, factory: Any) -> None:
        """Attempt to create and register a source adapter."""
        try:
            adapter = factory()
            self._sources[name] = (adapter, tier)
        except Exception as exc:
            logger.debug("Skipping source %s: %s", name, exc)

    # --- Source factories ---

    def _make_arxiv(self) -> SourceAdapter:
        from .sources.arxiv_source import ArxivSource
        return ArxivSource(self._config.get("arxiv"))

    def _make_orcid(self) -> SourceAdapter:
        from .sources.orcid_source import ORCIDSource
        return ORCIDSource(self._config.get("orcid"))

    def _make_uspto(self) -> SourceAdapter:
        from .sources.uspto_source import USPTOSource
        return USPTOSource(self._config.get("uspto"))

    def _make_semantic_scholar(self) -> SourceAdapter:
        from .sources.semantic_scholar_source import SemanticScholarSource
        return SemanticScholarSource(self._config.get("semantic_scholar"))

    def _make_crossref(self) -> SourceAdapter:
        from .sources.crossref_source import CrossRefSource
        return CrossRefSource(self._config.get("crossref"))

    def _make_github(self) -> SourceAdapter:
        from .sources.github_source import GitHubSource
        return GitHubSource(self._config.get("github"))

    def _make_notebook_lm(self) -> SourceAdapter:
        from .sources.notebook_lm_source import NotebookLMSource
        return NotebookLMSource(self._config.get("notebook_lm"))

    def _make_web_page(self) -> SourceAdapter:
        from .sources.web_page_source import WebPageSource
        return WebPageSource(self._config.get("web_page"))

    def _make_reddit(self) -> SourceAdapter:
        from .sources.reddit_source import RedditSource
        return RedditSource(self._config.get("reddit"))

    # --- Public API ---

    @property
    def registered_sources(self) -> Dict[str, int]:
        """Map of source name -> tier number."""
        return {name: int(tier) for name, (_, tier) in self._sources.items()}

    def search(
        self,
        query: str,
        *,
        tiers: Optional[List[int]] = None,
        sources: Optional[List[str]] = None,
        max_results: int = 50,
        deduplicate: bool = True,
        min_score: Optional[float] = None,
        **kwargs: Any,
    ) -> SearchReport:
        """Search across all registered sources with tiered filtration.

        Parameters
        ----------
        query : str
            The search query.
        tiers : list[int], optional
            Which tiers to search (1-4). Default: all registered.
        sources : list[str], optional
            Specific source names to query. Overrides tiers.
        max_results : int
            Maximum results to return after filtering.
        deduplicate : bool
            Remove duplicate results (by title hash).
        min_score : float, optional
            Override per-tier minimum composite score.
        **kwargs
            Forwarded to individual source adapters.
        """
        start = time.time()
        allowed_tiers = set(Tier(t) for t in tiers) if tiers else set(Tier)
        errors: List[str] = []
        raw_results: List[ScoredResult] = []
        sources_queried: List[str] = []

        # Determine which sources to query
        targets = self._resolve_targets(allowed_tiers, sources)

        for name, (adapter, tier) in targets.items():
            sources_queried.append(name)
            try:
                results = adapter.fetch(query, **kwargs)
                for r in results:
                    scored = self._score_result(r, tier, name, query)
                    raw_results.append(scored)
            except Exception as exc:
                err_msg = f"{name}: {exc}"
                errors.append(err_msg)
                logger.warning("Source %s failed: %s", name, exc)

        total_raw = len(raw_results)

        # Filter by tier threshold or custom min_score
        filtered = []
        for sr in raw_results:
            threshold = min_score if min_score is not None else _TIER_THRESHOLD[sr.tier]
            if sr.composite_score >= threshold:
                filtered.append(sr)

        # Deduplicate by title hash
        if deduplicate:
            filtered = self._deduplicate(filtered)

        # Sort by composite score descending
        filtered.sort(key=lambda x: x.composite_score, reverse=True)

        # Limit
        filtered = filtered[:max_results]

        elapsed = (time.time() - start) * 1000

        return SearchReport(
            query=query,
            results=filtered,
            total_raw=total_raw,
            total_filtered=len(filtered),
            tiers_searched=sorted(int(t) for t in allowed_tiers),
            sources_queried=sources_queried,
            elapsed_ms=round(elapsed, 1),
            errors=errors,
        )

    def search_academic(self, query: str, max_results: int = 30, **kwargs: Any) -> SearchReport:
        """Convenience: search only Tier 1 (Academic) sources."""
        return self.search(query, tiers=[1], max_results=max_results, **kwargs)

    def search_all(self, query: str, max_results: int = 50, **kwargs: Any) -> SearchReport:
        """Convenience: search all tiers."""
        return self.search(query, max_results=max_results, **kwargs)

    def resolve_doi(self, doi: str) -> Optional[IngestionResult]:
        """Resolve a DOI using CrossRef, falling back to Semantic Scholar."""
        if "crossref" in self._sources:
            adapter, _ = self._sources["crossref"]
            result = adapter.fetch_by_id(doi)
            if result:
                return result
        if "semantic_scholar" in self._sources:
            adapter, _ = self._sources["semantic_scholar"]
            result = adapter.fetch_by_id(f"DOI:{doi}")
            if result:
                return result
        return None

    def health_report(self) -> HealthReport:
        """Run health checks on all sources."""
        statuses: Dict[str, bool] = {}
        tiers: Dict[int, List[str]] = {}
        healthy = 0
        unhealthy = 0

        for name, (adapter, tier) in self._sources.items():
            try:
                ok = adapter.health_check()
            except Exception:
                ok = False
            statuses[name] = ok
            tier_key = int(tier)
            tiers.setdefault(tier_key, []).append(f"{name}:{'ok' if ok else 'FAIL'}")
            if ok:
                healthy += 1
            else:
                unhealthy += 1

        return HealthReport(
            sources=statuses,
            tiers=tiers,
            total_healthy=healthy,
            total_unhealthy=unhealthy,
        )

    # --- Internal ---

    def _resolve_targets(
        self,
        allowed_tiers: Set[Tier],
        source_names: Optional[List[str]],
    ) -> Dict[str, Tuple[SourceAdapter, Tier]]:
        """Resolve which sources to actually query."""
        if source_names:
            return {
                name: self._sources[name]
                for name in source_names
                if name in self._sources
            }
        return {
            name: (adapter, tier)
            for name, (adapter, tier) in self._sources.items()
            if tier in allowed_tiers
        }

    @staticmethod
    def _score_result(
        result: IngestionResult,
        tier: Tier,
        source_name: str,
        query: str,
    ) -> ScoredResult:
        """Compute trust and relevance scores for a result."""
        trust = _TIER_TRUST[tier]

        # Relevance: simple keyword overlap scoring
        query_terms = set(query.lower().split())
        title_terms = set(result.title.lower().split()) if result.title else set()
        summary_terms = set(result.summary.lower().split()) if result.summary else set()

        all_terms = title_terms | summary_terms
        if query_terms and all_terms:
            overlap = len(query_terms & all_terms)
            relevance = min(1.0, overlap / len(query_terms))
        else:
            relevance = 0.5  # Unknown relevance

        # Boost for results with external identifiers (DOI, arXiv ID)
        if result.identifiers:
            id_types = set(result.identifiers.keys())
            if id_types & {"doi", "arxiv_id", "patent_number"}:
                relevance = min(1.0, relevance + 0.15)

        # Boost for citation count if available
        cite_count = result.metadata.get("citation_count", 0)
        if isinstance(cite_count, (int, float)) and cite_count > 10:
            relevance = min(1.0, relevance + 0.1)

        composite = trust * relevance

        return ScoredResult(
            result=result,
            tier=tier,
            trust_score=trust,
            relevance_score=round(relevance, 3),
            composite_score=round(composite, 3),
            source_name=source_name,
        )

    @staticmethod
    def _deduplicate(results: List[ScoredResult]) -> List[ScoredResult]:
        """Remove duplicates by title hash, keeping highest-scored version."""
        seen: Dict[str, ScoredResult] = {}
        for sr in results:
            key = hashlib.md5(sr.result.title.lower().strip().encode()).hexdigest()[:12]
            if key not in seen or sr.composite_score > seen[key].composite_score:
                seen[key] = sr
            else:
                sr.deduplicated = True
        return list(seen.values())

    def to_jsonl(self, report: SearchReport) -> str:
        """Export a SearchReport as JSONL (one line per result)."""
        import json
        lines = []
        for sr in report.results:
            entry = {
                "title": sr.result.title,
                "source": sr.source_name,
                "tier": int(sr.tier),
                "trust": sr.trust_score,
                "relevance": sr.relevance_score,
                "composite": sr.composite_score,
                "url": sr.result.url or "",
                "authors": sr.result.authors,
                "timestamp": sr.result.timestamp,
                "identifiers": sr.result.identifiers,
                "tags": sr.result.tags,
                "summary": sr.result.summary[:300],
            }
            lines.append(json.dumps(entry, ensure_ascii=False))
        return "\n".join(lines)
