"""USPTO Open Data Portal source adapter for the Obsidian researcher agent.

Queries the USPTO Open Data Portal (ODP) APIs for patent applications,
prior art, and competitive intelligence relevant to SCBE-AETHERMOORE.

Uses stdlib HTTP — no extra dependencies required.  Authentication is via
``x-api-key`` header (free tier, register at https://data.uspto.gov/myodp).

Supported endpoints (data.uspto.gov):
  - GET  /applications/search      — query-parameter patent search
  - POST /applications/search      — structured JSON patent search
  - GET  /{applicationNumberText}  — single application by number
  - POST /patent/applications/text-to-search — semantic text search

API docs / Swagger: https://data.uspto.gov/swagger/index.html
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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_API_BASE = "https://data.uspto.gov"
_SEARCH_GET = _API_BASE + "/applications/search"
_SEARCH_POST = _API_BASE + "/applications/search"
_APP_BY_NUMBER = _API_BASE + "/{app_number}"
_TEXT_TO_SEARCH = _API_BASE + "/patent/applications/text-to-search"

_USER_AGENT = "SCBE-AETHERMOORE-HYDRA/1.0 (patent-intelligence)"
_DEFAULT_TIMEOUT = 20
_DEFAULT_ROWS = 10

# CPC classes relevant to SCBE research
_SCBE_CPC_CLASSES = [
    "G06F21",   # Security arrangements for protecting computers
    "G06N3",    # Computing arrangements based on biological models
    "G06N20",   # Machine learning
    "H04L9",    # Cryptographic mechanisms or arrangements
    "H04L63",   # Network security
    "G06F16",   # Information retrieval / database structures
    "G09C1",    # Apparatus or methods for generating codes
]


class USPTOSource(SourceAdapter):
    """Adapter that queries the USPTO Open Data Portal and emits
    :class:`IngestionResult` records suitable for vault ingestion.

    Parameters
    ----------
    config : dict
        Optional keys:

        * ``api_key``      -- USPTO ODP API key (default: env
          ``USPTO_API_KEY``). Sent as ``x-api-key`` header.
        * ``timeout``      -- HTTP timeout in seconds (default 20).
        * ``rows``         -- default results per query (default 10).
        * ``user_agent``   -- custom User-Agent string.
        * ``cpc_classes``  -- list of CPC class prefixes to filter on.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(source_type=SourceType.USPTO, config=config or {})

        self._api_key: str = self.config.get(
            "api_key", os.environ.get("USPTO_API_KEY", "")
        )
        self._timeout: int = int(self.config.get("timeout", _DEFAULT_TIMEOUT))
        self._rows: int = int(self.config.get("rows", _DEFAULT_ROWS))
        self._user_agent: str = self.config.get("user_agent", _USER_AGENT)
        self._cpc_classes: List[str] = list(
            self.config.get("cpc_classes", _SCBE_CPC_CLASSES)
        )

    # ------------------------------------------------------------------
    # SourceAdapter interface
    # ------------------------------------------------------------------

    def fetch(self, query: str, **kwargs: Any) -> List[IngestionResult]:
        """Search USPTO for patents matching *query* using GET endpoint.

        Extra keyword arguments:

        * ``rows``         -- override the per-query result count.
        * ``start``        -- pagination offset.
        * ``sort``         -- sort field.
        * ``filters``      -- filter expression string.
        * ``range_filters`` -- range filter expression string.
        """
        rows = int(kwargs.get("rows", self._rows))
        start = int(kwargs.get("start", 0))

        params: Dict[str, str] = {
            "q": query,
            "rows": str(rows),
            "start": str(start),
        }
        for key in ("sort", "filters", "rangeFilters"):
            if key in kwargs and kwargs[key]:
                params[key] = str(kwargs[key])

        url = f"{_SEARCH_GET}?{urllib.parse.urlencode(params)}"
        data = self._get_json(url)
        if data is None:
            return []

        return self._parse_search_results(data)

    def fetch_advanced(self, query: str, **kwargs: Any) -> List[IngestionResult]:
        """Search USPTO using the POST endpoint with structured JSON payload.

        This supports more complex queries with filters, range filters,
        pagination, and field selection.
        """
        rows = int(kwargs.get("rows", self._rows))
        start = int(kwargs.get("start", 0))

        payload: Dict[str, Any] = {
            "q": query,
            "rows": rows,
            "start": start,
        }
        if "filters" in kwargs:
            payload["filters"] = kwargs["filters"]
        if "rangeFilters" in kwargs:
            payload["rangeFilters"] = kwargs["rangeFilters"]
        if "fields" in kwargs:
            payload["fl"] = kwargs["fields"]
        if "sort" in kwargs:
            payload["sort"] = kwargs["sort"]

        data = self._post_json(_SEARCH_POST, payload)
        if data is None:
            return []

        return self._parse_search_results(data)

    def fetch_by_id(self, identifier: str) -> Optional[IngestionResult]:
        """Fetch a single patent by application number.

        Accepts formats like ``63/961,403``, ``63961403``, ``16123456``.
        """
        cleaned = identifier.strip().replace(",", "").replace("/", "")
        if not cleaned:
            return None

        url = _APP_BY_NUMBER.format(app_number=urllib.parse.quote(cleaned, safe=""))
        data = self._get_json(url)
        if data is None:
            return None

        # Single-application response — wrap in list for parsing
        if isinstance(data, dict) and not data.get("results"):
            result = self._patent_to_result(data)
            return result

        results = self._parse_search_results(data)
        return results[0] if results else None

    def health_check(self) -> bool:
        """Verify the USPTO ODP API is reachable."""
        if not self._api_key:
            logger.warning("USPTO health check: no API key configured")
            return False

        params = urllib.parse.urlencode({"q": "test", "rows": "1"})
        url = f"{_SEARCH_GET}?{params}"
        try:
            data = self._get_json(url)
            return data is not None
        except Exception:
            logger.debug("USPTO health check failed", exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Semantic search
    # ------------------------------------------------------------------

    def text_to_search(self, text: str, rows: int = 10) -> List[IngestionResult]:
        """Use the text-to-search endpoint for semantic patent matching.

        Accepts freeform text (like an abstract or invention description)
        and returns matching patent applications. Great for prior-art
        analysis — paste your own claims text and see what comes back.
        """
        payload = {"text": text, "rows": rows}
        data = self._post_json(_TEXT_TO_SEARCH, payload)
        if data is None:
            return []

        return self._parse_search_results(data)

    # ------------------------------------------------------------------
    # Prior art search helpers
    # ------------------------------------------------------------------

    def search_prior_art(
        self,
        keywords: List[str],
        cpc_classes: Optional[List[str]] = None,
        date_from: str = "2020-01-01",
        max_results: int = 25,
    ) -> List[IngestionResult]:
        """Convenience method for patent prior-art searches.

        Searches across multiple CPC classes with date filtering.
        """
        classes = cpc_classes or self._cpc_classes
        query = " AND ".join(f'"{kw}"' for kw in keywords)

        all_results: List[IngestionResult] = []
        for cpc in classes[:5]:
            cpc_query = f"{query} AND cpc:{cpc}"
            results = self.fetch(cpc_query, rows=max_results)
            all_results.extend(results)

        # Deduplicate by application number
        seen: set = set()
        unique: List[IngestionResult] = []
        for r in all_results:
            doc_id = (
                r.identifiers.get("application_number")
                or r.identifiers.get("patent_number", "")
            )
            if doc_id and doc_id not in seen:
                seen.add(doc_id)
                unique.append(r)

        return unique[:max_results]

    def search_competitors(
        self,
        assignee: str,
        keywords: Optional[List[str]] = None,
        max_results: int = 20,
    ) -> List[IngestionResult]:
        """Search for patents by a specific assignee/company."""
        query = f'assignee:"{assignee}"'
        if keywords:
            kw_part = " AND ".join(f'"{kw}"' for kw in keywords)
            query = f"{query} AND ({kw_part})"

        return self.fetch(query, rows=max_results)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with API key auth."""
        headers: Dict[str, str] = {
            "User-Agent": self._user_agent,
            "Accept": "application/json",
        }
        if self._api_key:
            headers["x-api-key"] = self._api_key
        return headers

    def _get_json(self, url: str) -> Optional[Any]:
        """GET request returning parsed JSON, or None on failure."""
        req = urllib.request.Request(url, headers=self._build_headers())
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                content_type = resp.headers.get("Content-Type", "")
                raw = resp.read()
                if "json" not in content_type and raw[:1] != b"{" and raw[:1] != b"[":
                    logger.warning("USPTO returned non-JSON for %s (CT: %s)", url, content_type)
                    return None
                return json.loads(raw)
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            logger.warning("USPTO HTTP error for %s: %s", url, exc)
            return None
        except json.JSONDecodeError as exc:
            logger.warning("USPTO JSON parse error for %s: %s", url, exc)
            return None
        except Exception:
            logger.exception("Unexpected error fetching %s", url)
            return None

    def _post_json(self, url: str, payload: Dict[str, Any]) -> Optional[Any]:
        """POST JSON request returning parsed JSON, or None on failure."""
        body = json.dumps(payload).encode("utf-8")
        headers = self._build_headers()
        headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read()
                return json.loads(raw)
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            logger.warning("USPTO POST error for %s: %s", url, exc)
            return None
        except json.JSONDecodeError as exc:
            logger.warning("USPTO POST JSON parse error for %s: %s", url, exc)
            return None
        except Exception:
            logger.exception("Unexpected POST error for %s", url)
            return None

    def _parse_search_results(self, data: Any) -> List[IngestionResult]:
        """Parse USPTO API response into IngestionResult list."""
        results: List[IngestionResult] = []

        if not isinstance(data, dict):
            return []

        # Try several known response shapes
        patents = (
            data.get("results")
            or data.get("patents")
            or data.get("response", {}).get("docs")
            or data.get("items")
            or []
        )
        if not isinstance(patents, list):
            # Single result wrapped in dict
            if isinstance(data.get("applicationNumberText"), str):
                r = self._patent_to_result(data)
                return [r] if r else []
            logger.debug("USPTO: unexpected response shape: %s", list(data.keys()))
            return []

        for patent in patents:
            result = self._patent_to_result(patent)
            if result is not None:
                results.append(result)

        return results

    @staticmethod
    def _patent_to_result(patent: Dict[str, Any]) -> Optional[IngestionResult]:
        """Convert a USPTO patent record to an ``IngestionResult``."""
        title = (
            patent.get("inventionTitle")
            or patent.get("title")
            or patent.get("patent_title")
            or patent.get("patentTitle")
            or ""
        )
        if not title:
            return None

        abstract = (
            patent.get("abstractText")
            or patent.get("abstract")
            or patent.get("patent_abstract")
            or ""
        )

        # Identifiers
        app_num = (
            patent.get("applicationNumberText")
            or patent.get("applicationNumber")
            or patent.get("appl_id")
            or ""
        )
        patent_num = (
            patent.get("patentNumber")
            or patent.get("patent_number")
            or ""
        )
        pub_num = patent.get("publicationNumber", "")

        identifiers: Dict[str, str] = {}
        if app_num:
            identifiers["application_number"] = str(app_num)
        if patent_num:
            identifiers["patent_number"] = str(patent_num)
        if pub_num:
            identifiers["publication_number"] = str(pub_num)

        # Inventors
        inventors = patent.get("inventors", patent.get("inventor", []))
        authors: List[str] = []
        if isinstance(inventors, list):
            for inv in inventors:
                if isinstance(inv, dict):
                    name = (
                        inv.get("inventorName")
                        or inv.get("nameLineOne")
                        or "{} {}".format(
                            inv.get("inventor_first_name", ""),
                            inv.get("inventor_last_name", ""),
                        ).strip()
                    )
                    if name:
                        authors.append(name)
                elif isinstance(inv, str):
                    authors.append(inv)

        # Assignee
        assignee = (
            patent.get("assignee")
            or patent.get("assigneeName")
            or patent.get("assigneeEntityName")
            or ""
        )
        if isinstance(assignee, list) and assignee:
            assignee = assignee[0] if isinstance(assignee[0], str) else str(assignee[0])

        # Dates
        pub_date = (
            patent.get("publicationDate")
            or patent.get("patent_date")
            or patent.get("datePublished")
            or ""
        )
        filing_date = (
            patent.get("filingDate")
            or patent.get("app_date")
            or patent.get("applicationFilingDate")
            or ""
        )

        # CPC classifications
        cpc_codes = patent.get("cpcCodes", patent.get("cpcs", []))
        tags: List[str] = ["uspto:application"]
        if isinstance(cpc_codes, list):
            for cpc in cpc_codes[:10]:
                if isinstance(cpc, dict):
                    code = cpc.get("cpcCode") or cpc.get("cpc_group_id", "")
                elif isinstance(cpc, str):
                    code = cpc
                else:
                    continue
                if code:
                    tags.append(f"cpc:{code}")

        # Status
        status = patent.get("applicationStatusDescriptionText") or patent.get("status", "")

        # Build URL
        url = None
        if patent_num:
            url = f"https://patents.google.com/patent/US{patent_num}"
        elif pub_num:
            url = f"https://patents.google.com/patent/{pub_num}"
        elif app_num:
            clean_num = str(app_num).replace("/", "").replace(",", "")
            url = f"https://data.uspto.gov/{clean_num}"

        # Raw content
        raw_parts = [title]
        if abstract:
            raw_parts.append(f"\nAbstract:\n{abstract}")
        if authors:
            raw_parts.append(f"\nInventors: {', '.join(authors)}")
        if assignee:
            raw_parts.append(f"\nAssignee: {assignee}")
        raw_content = "\n".join(raw_parts)

        return IngestionResult(
            source_type=SourceType.USPTO,
            raw_content=raw_content,
            title=title,
            authors=authors,
            url=url,
            timestamp=str(pub_date),
            identifiers=identifiers,
            tags=tags,
            metadata={
                "assignee": str(assignee) if assignee else "",
                "filing_date": str(filing_date),
                "publication_date": str(pub_date),
                "status": str(status),
                "abstract": abstract,
            },
            summary=abstract[:500] if abstract else title,
        )
