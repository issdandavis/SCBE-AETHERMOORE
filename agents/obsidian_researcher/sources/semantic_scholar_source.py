"""Semantic Scholar source adapter for the Obsidian researcher agent.

Queries the Semantic Scholar Academic Graph API (https://api.semanticscholar.org/)
for papers, authors, and citations. 200M+ papers indexed.

Free tier: 1 req/sec, no API key required.
Authenticated: 10 req/sec with API key (env SEMANTIC_SCHOLAR_API_KEY).

@layer Layer 1 (identity), Layer 14 (telemetry)
@component ResearchPipeline.SemanticScholar
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from ..source_adapter import IngestionResult, SourceAdapter, SourceType

logger = logging.getLogger(__name__)

_API_BASE = "https://api.semanticscholar.org/graph/v1"
_USER_AGENT = "SCBE-AETHERMOORE/1.0 (mailto:issdandavis7795@aethermoorgames.com)"
_DEFAULT_TIMEOUT = 15
_DEFAULT_LIMIT = 10

# Fields to request from the API
_PAPER_FIELDS = ",".join([
    "paperId", "title", "abstract", "year", "citationCount",
    "influentialCitationCount", "referenceCount", "fieldsOfStudy",
    "authors", "externalIds", "url", "venue", "publicationDate",
    "openAccessPdf", "tldr",
])


class SemanticScholarSource(SourceAdapter):
    """Adapter that queries the Semantic Scholar Academic Graph API.

    Parameters
    ----------
    config : dict
        Optional keys:

        * ``api_key``   -- S2 API key (default: env SEMANTIC_SCHOLAR_API_KEY)
        * ``timeout``   -- HTTP timeout in seconds (default 15)
        * ``limit``     -- default results per query (default 10)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(source_type=SourceType.SEMANTIC_SCHOLAR, config=config or {})
        self._api_key: str = self.config.get(
            "api_key",
            os.environ.get("SEMANTIC_SCHOLAR_API_KEY", ""),
        )
        self._timeout: int = int(self.config.get("timeout", _DEFAULT_TIMEOUT))
        self._limit: int = int(self.config.get("limit", _DEFAULT_LIMIT))

    def _get_json(self, url: str) -> Optional[Any]:
        """GET request returning parsed JSON."""
        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        }
        if self._api_key:
            headers["x-api-key"] = self._api_key
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            logger.warning("S2 HTTP error for %s: %s", url, exc)
            return None
        except Exception:
            logger.exception("S2 unexpected error for %s", url)
            return None

    def fetch(self, query: str, **kwargs: Any) -> List[IngestionResult]:
        """Search Semantic Scholar for papers matching query."""
        limit = int(kwargs.get("limit", self._limit))
        year = kwargs.get("year", "")
        fields_of_study = kwargs.get("fields_of_study", "")

        params: Dict[str, str] = {
            "query": query,
            "limit": str(min(limit, 100)),
            "fields": _PAPER_FIELDS,
        }
        if year:
            params["year"] = str(year)
        if fields_of_study:
            params["fieldsOfStudy"] = fields_of_study

        url = f"{_API_BASE}/paper/search?{urllib.parse.urlencode(params)}"
        data = self._get_json(url)
        if not data:
            return []

        papers = data.get("data", [])
        return [self._paper_to_result(p) for p in papers if p]

    def fetch_by_id(self, identifier: str) -> Optional[IngestionResult]:
        """Fetch a paper by Semantic Scholar ID, DOI, or arXiv ID.

        Accepts formats: S2 paper ID, DOI:xxx, ARXIV:xxx, PMID:xxx
        """
        cleaned = identifier.strip()
        if not cleaned:
            return None

        url = f"{_API_BASE}/paper/{urllib.parse.quote(cleaned, safe=':/')}?fields={_PAPER_FIELDS}"
        data = self._get_json(url)
        if not data:
            return None

        return self._paper_to_result(data)

    def fetch_author(self, author_id: str) -> Optional[Dict[str, Any]]:
        """Fetch author profile by Semantic Scholar author ID."""
        fields = "authorId,name,affiliations,paperCount,citationCount,hIndex"
        url = f"{_API_BASE}/author/{urllib.parse.quote(author_id)}?fields={fields}"
        return self._get_json(url)

    def fetch_author_papers(self, author_id: str, limit: int = 20) -> List[IngestionResult]:
        """Fetch papers by a specific author."""
        params = urllib.parse.urlencode({
            "fields": _PAPER_FIELDS,
            "limit": str(min(limit, 100)),
        })
        url = f"{_API_BASE}/author/{urllib.parse.quote(author_id)}/papers?{params}"
        data = self._get_json(url)
        if not data:
            return []
        papers = data.get("data", [])
        return [self._paper_to_result(p) for p in papers if p]

    def fetch_recommendations(self, paper_id: str, limit: int = 10) -> List[IngestionResult]:
        """Get paper recommendations based on a seed paper."""
        params = urllib.parse.urlencode({
            "fields": _PAPER_FIELDS,
            "limit": str(min(limit, 100)),
        })
        url = f"https://api.semanticscholar.org/recommendations/v1/papers/forpaper/{urllib.parse.quote(paper_id)}?{params}"
        data = self._get_json(url)
        if not data:
            return []
        papers = data.get("recommendedPapers", [])
        return [self._paper_to_result(p) for p in papers if p]

    def fetch_citations(self, paper_id: str, limit: int = 20) -> List[IngestionResult]:
        """Fetch papers that cite a given paper."""
        params = urllib.parse.urlencode({
            "fields": "citingPaper." + _PAPER_FIELDS,
            "limit": str(min(limit, 100)),
        })
        url = f"{_API_BASE}/paper/{urllib.parse.quote(paper_id)}/citations?{params}"
        data = self._get_json(url)
        if not data:
            return []
        citing = data.get("data", [])
        results = []
        for entry in citing:
            paper = entry.get("citingPaper", {})
            if paper and paper.get("title"):
                results.append(self._paper_to_result(paper))
        return results

    def health_check(self) -> bool:
        """Verify Semantic Scholar API is reachable."""
        url = f"{_API_BASE}/paper/search?query=test&limit=1&fields=title"
        try:
            data = self._get_json(url)
            return data is not None and "data" in data
        except Exception:
            return False

    @staticmethod
    def _paper_to_result(paper: Dict[str, Any]) -> IngestionResult:
        """Convert a Semantic Scholar paper object to IngestionResult."""
        title = paper.get("title", "")
        abstract = paper.get("abstract", "") or ""
        paper_id = paper.get("paperId", "")

        # Authors
        authors = []
        for a in paper.get("authors", []) or []:
            name = a.get("name", "")
            if name:
                authors.append(name)

        # External IDs
        ext_ids = paper.get("externalIds", {}) or {}
        identifiers: Dict[str, str] = {"s2_paper_id": paper_id}
        if ext_ids.get("DOI"):
            identifiers["doi"] = ext_ids["DOI"]
        if ext_ids.get("ArXiv"):
            identifiers["arxiv_id"] = ext_ids["ArXiv"]
        if ext_ids.get("PMID"):
            identifiers["pmid"] = ext_ids["PMID"]
        if ext_ids.get("CorpusId"):
            identifiers["s2_corpus_id"] = str(ext_ids["CorpusId"])

        # Tags
        tags = ["semantic_scholar"]
        for field in paper.get("fieldsOfStudy", []) or []:
            tags.append(f"field:{field}")
        venue = paper.get("venue", "")
        if venue:
            tags.append(f"venue:{venue}")

        # TLDR
        tldr = paper.get("tldr", {}) or {}
        summary = tldr.get("text", "") or abstract[:500]

        # Open access PDF
        oa_pdf = paper.get("openAccessPdf", {}) or {}

        return IngestionResult(
            source_type=SourceType.SEMANTIC_SCHOLAR,
            raw_content=abstract or title,
            title=title,
            authors=authors,
            url=paper.get("url", ""),
            timestamp=paper.get("publicationDate", "") or str(paper.get("year", "")),
            identifiers=identifiers,
            tags=tags,
            metadata={
                "year": paper.get("year"),
                "venue": venue,
                "citation_count": paper.get("citationCount", 0),
                "influential_citation_count": paper.get("influentialCitationCount", 0),
                "reference_count": paper.get("referenceCount", 0),
                "fields_of_study": paper.get("fieldsOfStudy", []),
                "open_access_pdf": oa_pdf.get("url", ""),
            },
            summary=summary,
        )
