"""Perplexity Sonar source adapter — AI-powered web search + research.

Uses the Perplexity Sonar API (https://docs.perplexity.ai/) for fast,
citation-backed AI search. This is a Tier 1 source due to its ability
to synthesize and cite academic, news, and web sources in real time.

Env: PERPLEXITY_API_KEY (required)

Models:
    sonar            — fast, web-grounded, good for general queries
    sonar-pro        — deeper reasoning, more citations
    sonar-deep-research — multi-step research agent (slower, thorough)

@layer Layer 1 (identity), Layer 13 (governance), Layer 14 (telemetry)
@component ResearchPipeline.Perplexity
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..source_adapter import IngestionResult, SourceAdapter, SourceType

logger = logging.getLogger(__name__)

_API_BASE = "https://api.perplexity.ai"
_DEFAULT_TIMEOUT = 30
_DEFAULT_MODEL = "sonar"


class PerplexitySource(SourceAdapter):
    """Perplexity Sonar API adapter for AI-powered web research.

    Parameters
    ----------
    config : dict, optional
        Keys:
            api_key : str — Perplexity API key (overrides env)
            model : str — Model to use (sonar, sonar-pro, sonar-deep-research)
            timeout : int — Request timeout in seconds
            system_prompt : str — Custom system prompt for search context
            return_citations : bool — Include source URLs (default True)
            search_recency_filter : str — "month", "week", "day", "hour"
    """

    source_type = SourceType.WEB

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self._api_key = cfg.get("api_key") or os.environ.get("PERPLEXITY_API_KEY", "")
        self._model = cfg.get("model", _DEFAULT_MODEL)
        self._timeout = cfg.get("timeout", _DEFAULT_TIMEOUT)
        self._system_prompt = cfg.get(
            "system_prompt",
            "You are a research assistant. Provide detailed, factual answers "
            "with specific data points, dates, and citations. Focus on academic "
            "and technical accuracy. When discussing AI safety, cryptography, or "
            "governance frameworks, include relevant paper references."
        )
        self._return_citations = cfg.get("return_citations", True)
        self._recency_filter = cfg.get("search_recency_filter", "")

    # --- SourceAdapter interface ---

    def fetch(self, query: str, **kwargs: Any) -> List[IngestionResult]:
        """Search Perplexity for a query, return structured results."""
        if not self._api_key:
            logger.warning("No PERPLEXITY_API_KEY set")
            return []

        model = kwargs.get("model", self._model)
        recency = kwargs.get("recency", self._recency_filter)

        response = self._chat_completion(query, model=model, recency=recency)
        if not response:
            return []

        results = []
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        citations = response.get("citations", [])

        if not content:
            return []

        # Main synthesized result
        result = IngestionResult(
            source_type=SourceType.WEB,
            raw_content=content,
            title=f"Perplexity: {query[:80]}",
            authors=["Perplexity AI (synthesized)"],
            url=citations[0] if citations else None,
            timestamp=datetime.now(timezone.utc).isoformat(),
            identifiers={"perplexity_model": model},
            tags=["perplexity", f"model:{model}"],
            metadata={
                "source": "perplexity",
                "model": model,
                "citations": citations,
                "citation_count": len(citations),
                "usage": response.get("usage", {}),
                "query": query,
            },
            summary=content[:500],
        )
        results.append(result)

        # Also create individual results from each citation
        for i, url in enumerate(citations[:10]):
            cite_result = IngestionResult(
                source_type=SourceType.WEB,
                raw_content=f"[Citation {i+1}] Referenced in Perplexity response for: {query}",
                title=f"Citation: {url.split('/')[-1][:60] if '/' in url else url[:60]}",
                authors=[],
                url=url,
                timestamp=datetime.now(timezone.utc).isoformat(),
                identifiers={"perplexity_citation": url},
                tags=["perplexity", "citation"],
                metadata={
                    "source": "perplexity_citation",
                    "parent_query": query,
                    "citation_index": i,
                },
                summary=f"Source cited by Perplexity for query: {query[:200]}",
            )
            results.append(cite_result)

        return results

    def fetch_by_id(self, identifier: str, **kwargs: Any) -> Optional[IngestionResult]:
        """Use Perplexity to research a specific URL or topic."""
        if not self._api_key:
            return None

        prompt = f"Provide a detailed analysis of: {identifier}"
        response = self._chat_completion(prompt, model=self._model)
        if not response:
            return None

        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        citations = response.get("citations", [])

        return IngestionResult(
            source_type=SourceType.WEB,
            raw_content=content,
            title=f"Analysis: {identifier[:80]}",
            authors=["Perplexity AI"],
            url=identifier if identifier.startswith("http") else None,
            timestamp=datetime.now(timezone.utc).isoformat(),
            identifiers={"perplexity_lookup": identifier},
            tags=["perplexity", "analysis"],
            metadata={
                "source": "perplexity",
                "citations": citations,
                "usage": response.get("usage", {}),
            },
            summary=content[:500],
        )

    def health_check(self) -> bool:
        """Verify API key works with a minimal request."""
        if not self._api_key:
            return False
        try:
            response = self._chat_completion("ping", model="sonar")
            return response is not None and "choices" in response
        except Exception:
            return False

    # --- Extended API ---

    def research(
        self,
        topic: str,
        *,
        depth: str = "standard",
        focus: str = "general",
    ) -> Optional[IngestionResult]:
        """Deep research on a topic with model selection by depth.

        Parameters
        ----------
        topic : str
            Research topic or question.
        depth : str
            "quick" (sonar), "standard" (sonar-pro), "deep" (sonar-deep-research)
        focus : str
            Research focus hint added to system prompt.
        """
        if not self._api_key:
            return None

        model_map = {
            "quick": "sonar",
            "standard": "sonar-pro",
            "deep": "sonar-deep-research",
        }
        model = model_map.get(depth, "sonar-pro")

        system = (
            f"{self._system_prompt}\n\n"
            f"Research focus: {focus}. "
            "Provide comprehensive analysis with specific data, statistics, "
            "and paper references where available."
        )

        response = self._chat_completion(topic, model=model, system_override=system)
        if not response:
            return None

        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        citations = response.get("citations", [])

        return IngestionResult(
            source_type=SourceType.WEB,
            raw_content=content,
            title=f"Research [{depth}]: {topic[:60]}",
            authors=["Perplexity AI"],
            timestamp=datetime.now(timezone.utc).isoformat(),
            identifiers={"perplexity_research": topic[:100]},
            tags=["perplexity", "research", f"depth:{depth}", f"focus:{focus}"],
            metadata={
                "source": "perplexity",
                "model": model,
                "depth": depth,
                "focus": focus,
                "citations": citations,
                "citation_count": len(citations),
                "usage": response.get("usage", {}),
            },
            summary=content[:500],
        )

    def competitive_analysis(self, company_or_product: str) -> Optional[IngestionResult]:
        """Run competitive analysis on a company/product."""
        return self.research(
            f"Comprehensive competitive analysis of {company_or_product}. "
            "Include market position, key features, pricing, strengths, weaknesses, "
            "recent funding/growth, and comparison to alternatives.",
            depth="standard",
            focus="competitive intelligence",
        )

    def patent_landscape(self, technology: str) -> Optional[IngestionResult]:
        """Research patent landscape for a technology area."""
        return self.research(
            f"Patent landscape analysis for {technology}. "
            "Include key patents, major filers, recent trends, "
            "freedom to operate considerations, and emerging areas.",
            depth="standard",
            focus="patent intelligence",
        )

    def market_research(self, market: str) -> Optional[IngestionResult]:
        """Research market size, trends, and opportunities."""
        return self.research(
            f"Market research for {market}. "
            "Include TAM/SAM/SOM estimates, growth rate, key players, "
            "trends, barriers to entry, and revenue models.",
            depth="standard",
            focus="market intelligence",
        )

    # --- Internal ---

    def _chat_completion(
        self,
        query: str,
        *,
        model: str = "",
        recency: str = "",
        system_override: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Call the Perplexity chat completions endpoint."""
        model = model or self._model
        system = system_override or self._system_prompt

        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": query},
            ],
        }

        if self._return_citations:
            payload["return_citations"] = True

        if recency:
            payload["search_recency_filter"] = recency

        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{_API_BASE}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode() if exc.fp else ""
            logger.error("Perplexity API error %d: %s", exc.code, body[:300])
            return None
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            logger.error("Perplexity request failed: %s", exc)
            return None
