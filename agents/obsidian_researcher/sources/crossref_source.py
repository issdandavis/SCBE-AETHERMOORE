"""CrossRef source adapter for the Obsidian researcher agent.

Queries the CrossRef REST API (https://api.crossref.org/) for DOI metadata,
works, and publisher information. 140M+ records, completely free.

Polite pool: include mailto in User-Agent for faster responses.

@layer Layer 1 (identity), Layer 14 (telemetry)
@component ResearchPipeline.CrossRef
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from ..source_adapter import IngestionResult, SourceAdapter, SourceType

logger = logging.getLogger(__name__)

_API_BASE = "https://api.crossref.org"
_USER_AGENT = "SCBE-AETHERMOORE/1.0 (mailto:issdandavis7795@aethermoorgames.com)"
_DEFAULT_TIMEOUT = 15
_DEFAULT_ROWS = 10


class CrossRefSource(SourceAdapter):
    """Adapter that queries the CrossRef REST API for DOI metadata.

    Parameters
    ----------
    config : dict
        Optional keys:

        * ``timeout``  -- HTTP timeout in seconds (default 15)
        * ``rows``     -- default results per query (default 10)
        * ``mailto``   -- email for polite pool (faster responses)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(source_type=SourceType.CROSSREF, config=config or {})
        self._timeout: int = int(self.config.get("timeout", _DEFAULT_TIMEOUT))
        self._rows: int = int(self.config.get("rows", _DEFAULT_ROWS))
        self._mailto: str = self.config.get(
            "mailto", "issdandavis7795@aethermoorgames.com"
        )

    def _get_json(self, url: str) -> Optional[Any]:
        """GET request returning parsed JSON."""
        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        }
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            logger.warning("CrossRef HTTP error for %s: %s", url, exc)
            return None
        except Exception:
            logger.exception("CrossRef unexpected error for %s", url)
            return None

    def fetch(self, query: str, **kwargs: Any) -> List[IngestionResult]:
        """Search CrossRef works matching query."""
        rows = int(kwargs.get("rows", self._rows))
        filter_str = kwargs.get("filter", "")
        sort = kwargs.get("sort", "relevance")

        params: Dict[str, str] = {
            "query": query,
            "rows": str(min(rows, 100)),
            "sort": sort,
            "mailto": self._mailto,
        }
        if filter_str:
            params["filter"] = filter_str

        url = f"{_API_BASE}/works?{urllib.parse.urlencode(params)}"
        data = self._get_json(url)
        if not data:
            return []

        message = data.get("message", {})
        items = message.get("items", [])
        return [self._work_to_result(w) for w in items if w]

    def fetch_by_id(self, identifier: str) -> Optional[IngestionResult]:
        """Fetch a work by DOI.

        Accepts: full DOI (10.xxxx/yyyy) or DOI URL (https://doi.org/10.xxxx/yyyy).
        """
        doi = identifier.strip()
        if doi.startswith("https://doi.org/"):
            doi = doi[len("https://doi.org/"):]
        if doi.startswith("http://doi.org/"):
            doi = doi[len("http://doi.org/"):]
        if not doi:
            return None

        url = f"{_API_BASE}/works/{urllib.parse.quote(doi, safe='/')}?mailto={self._mailto}"
        data = self._get_json(url)
        if not data:
            return None

        message = data.get("message", {})
        if not message:
            return None

        return self._work_to_result(message)

    def fetch_journal(self, issn: str) -> Optional[Dict[str, Any]]:
        """Fetch journal metadata by ISSN."""
        url = f"{_API_BASE}/journals/{urllib.parse.quote(issn)}?mailto={self._mailto}"
        data = self._get_json(url)
        if not data:
            return None
        return data.get("message")

    def fetch_funder_works(self, funder_id: str, query: str = "", rows: int = 10) -> List[IngestionResult]:
        """Fetch works funded by a specific funder (e.g., NSF, NIH)."""
        params: Dict[str, str] = {
            "rows": str(min(rows, 100)),
            "mailto": self._mailto,
        }
        if query:
            params["query"] = query

        url = f"{_API_BASE}/funders/{urllib.parse.quote(funder_id)}/works?{urllib.parse.urlencode(params)}"
        data = self._get_json(url)
        if not data:
            return []

        message = data.get("message", {})
        items = message.get("items", [])
        return [self._work_to_result(w) for w in items if w]

    def health_check(self) -> bool:
        """Verify CrossRef API is reachable."""
        url = f"{_API_BASE}/works?query=test&rows=1&mailto={self._mailto}"
        try:
            data = self._get_json(url)
            return data is not None and "message" in data
        except Exception:
            return False

    @staticmethod
    def _work_to_result(work: Dict[str, Any]) -> IngestionResult:
        """Convert a CrossRef work object to IngestionResult."""
        # Title
        titles = work.get("title", [])
        title = titles[0] if titles else ""

        # Authors
        authors = []
        for a in work.get("author", []):
            given = a.get("given", "")
            family = a.get("family", "")
            name = f"{given} {family}".strip()
            if name:
                authors.append(name)

        # DOI
        doi = work.get("DOI", "")
        identifiers: Dict[str, str] = {}
        if doi:
            identifiers["doi"] = doi

        # ISSNs
        issns = work.get("ISSN", [])
        if issns:
            identifiers["issn"] = issns[0]

        # Date
        pub_date = ""
        date_parts = work.get("published-print", work.get("published-online", {}))
        if isinstance(date_parts, dict):
            parts = date_parts.get("date-parts", [[]])
            if parts and parts[0]:
                pub_date = "-".join(str(p) for p in parts[0] if p)

        # Abstract
        abstract = work.get("abstract", "") or ""
        # CrossRef abstracts often contain JATS XML
        if abstract.startswith("<jats:"):
            import re
            abstract = re.sub(r"<[^>]+>", "", abstract)

        # Container (journal/conference)
        container = work.get("container-title", [])
        journal = container[0] if container else ""

        # Tags
        tags = ["crossref"]
        work_type = work.get("type", "")
        if work_type:
            tags.append(f"type:{work_type}")
        subjects = work.get("subject", [])
        for subj in subjects[:5]:
            tags.append(f"subject:{subj}")

        # Citation count
        ref_count = work.get("is-referenced-by-count", 0)

        return IngestionResult(
            source_type=SourceType.CROSSREF,
            raw_content=abstract or title,
            title=title,
            authors=authors,
            url=f"https://doi.org/{doi}" if doi else "",
            timestamp=pub_date,
            identifiers=identifiers,
            tags=tags,
            metadata={
                "journal": journal,
                "publisher": work.get("publisher", ""),
                "type": work_type,
                "citation_count": ref_count,
                "reference_count": work.get("references-count", 0),
                "subjects": subjects,
                "issns": issns,
                "license": [lic.get("URL", "") for lic in work.get("license", [])],
            },
            summary=abstract[:500] if abstract else title,
        )
