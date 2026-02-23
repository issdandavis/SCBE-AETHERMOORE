"""arXiv source adapter for the Obsidian researcher agent.

Wraps the existing ``ArxivClient`` from ``hydra/arxiv_retrieval.py``
and converts its ``ArxivPaper`` dataclasses into the generic
``IngestionResult`` used by the cross-reference engine.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..source_adapter import IngestionResult, SourceAdapter, SourceType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy import of ArxivClient — httpx is required at runtime but we must not
# blow up at *import* time so that tests and other adapters keep working.
# ---------------------------------------------------------------------------

_ArxivClient: Optional[type] = None
_ArxivPaper: Optional[type] = None
_IMPORT_ERROR: Optional[str] = None

try:
    from hydra.arxiv_retrieval import ArxivClient as _AC, ArxivPaper as _AP

    _ArxivClient = _AC
    _ArxivPaper = _AP
except ImportError as exc:  # pragma: no cover
    _IMPORT_ERROR = (
        f"ArxivClient unavailable — httpx or hydra.arxiv_retrieval could "
        f"not be imported: {exc}"
    )


class ArxivSource(SourceAdapter):
    """Adapter that queries arXiv via ``ArxivClient`` and emits
    :class:`IngestionResult` records suitable for vault ingestion.

    Parameters
    ----------
    config : dict
        Optional keys forwarded to ``ArxivClient``:

        * ``api_url``            -- override the default arXiv endpoint
        * ``timeout_seconds``    -- HTTP timeout (default 20)
        * ``min_delay_seconds``  -- polite delay between requests (default 3)
        * ``user_agent``         -- custom User-Agent header
        * ``max_results``        -- default page size for ``fetch()`` (default 10)
        * ``category``           -- default arXiv category filter (e.g. ``cs.AI``)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(source_type=SourceType.ARXIV, config=config or {})

        if _ArxivClient is None:
            raise ImportError(
                _IMPORT_ERROR
                or "ArxivClient is not available (unknown import error)"
            )

        client_kwargs: Dict[str, Any] = {}
        for key in ("api_url", "timeout_seconds", "min_delay_seconds", "user_agent"):
            if key in self.config:
                client_kwargs[key] = self.config[key]

        self._client = _ArxivClient(**client_kwargs)
        self._default_max_results: int = int(self.config.get("max_results", 10))
        self._default_category: Optional[str] = self.config.get("category")

    # ------------------------------------------------------------------
    # SourceAdapter interface
    # ------------------------------------------------------------------

    def fetch(self, query: str, **kwargs: Any) -> List[IngestionResult]:
        """Search arXiv and return normalised ingestion results.

        Extra keyword arguments are forwarded to ``ArxivClient.search``.
        Recognised overrides: ``category``, ``max_results``, ``start``,
        ``sort_by``, ``sort_order``, ``raw_query``.
        """
        search_kwargs: Dict[str, Any] = {
            "category": kwargs.get("category", self._default_category),
            "max_results": int(kwargs.get("max_results", self._default_max_results)),
        }
        for passthrough in ("start", "sort_by", "sort_order", "raw_query"):
            if passthrough in kwargs:
                search_kwargs[passthrough] = kwargs[passthrough]

        # Remove None category so ArxivClient does not append "cat:None"
        if search_kwargs.get("category") is None:
            search_kwargs.pop("category", None)

        try:
            result = self._client.search(query, **search_kwargs)
        except Exception:
            logger.exception("arXiv search failed for query=%r", query)
            return []

        return [self._paper_to_result(paper) for paper in result.papers]

    def fetch_by_id(self, identifier: str) -> Optional[IngestionResult]:
        """Fetch a single arXiv paper by its ID (e.g. ``2301.12345``).

        Uses the ``id_list`` raw-query mechanism exposed by the arXiv API.
        """
        cleaned = identifier.strip()
        if not cleaned:
            return None

        try:
            result = self._client.search(
                f"id_list:{cleaned}",
                max_results=1,
                raw_query=True,
            )
        except Exception:
            logger.exception("arXiv fetch_by_id failed for id=%r", identifier)
            return None

        if not result.papers:
            return None
        return self._paper_to_result(result.papers[0])

    def health_check(self) -> bool:
        """Verify arXiv API is reachable with a minimal query."""
        try:
            result = self._client.search("test", max_results=1)
            return result.total_results >= 0
        except Exception:
            logger.debug("arXiv health check failed", exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _paper_to_result(paper: Any) -> IngestionResult:
        """Convert an ``ArxivPaper`` dataclass to ``IngestionResult``."""
        identifiers: Dict[str, str] = {"arxiv_id": paper.arxiv_id}
        if paper.pdf_url:
            identifiers["pdf_url"] = paper.pdf_url

        tags: List[str] = list(paper.categories) if paper.categories else []
        if paper.primary_category and paper.primary_category not in tags:
            tags.insert(0, paper.primary_category)

        metadata: Dict[str, Any] = {}
        if paper.comment:
            metadata["comment"] = paper.comment
        if paper.updated:
            metadata["updated"] = paper.updated

        return IngestionResult(
            source_type=SourceType.ARXIV,
            raw_content=paper.summary,
            title=paper.title,
            authors=list(paper.authors) if paper.authors else [],
            url=paper.abs_url,
            timestamp=paper.published or "",
            identifiers=identifiers,
            tags=tags,
            metadata=metadata,
            summary=paper.summary,
        )
