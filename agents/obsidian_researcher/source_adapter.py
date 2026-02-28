"""Pluggable source interface for research ingestion.

Mirrors the PlatformPublisher pattern from web_agent/buffer_integration.py.
Each concrete adapter handles fetching and normalization for a specific
data source (arXiv, Reddit, Obsidian vault, web pages, user brainstorms).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceType(str, Enum):
    """Known research source types."""
    ARXIV = "arxiv"
    REDDIT = "reddit"
    VAULT = "vault"
    WEB_PAGE = "web_page"
    BRAINSTORM = "brainstorm"
    USPTO = "uspto"
    GITHUB = "github"
    ORCID = "orcid"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    CROSSREF = "crossref"
    WEB = "web"
    FORUM = "forum"


@dataclass
class IngestionResult:
    """Normalized output from any source adapter."""
    source_type: SourceType
    raw_content: str
    title: str
    authors: List[str] = field(default_factory=list)
    url: Optional[str] = None
    timestamp: str = ""
    identifiers: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    scbe_relevance: Dict[str, float] = field(default_factory=dict)


class SourceAdapter(ABC):
    """Abstract base class for all research sources."""

    def __init__(self, source_type: SourceType, config: Dict[str, Any]) -> None:
        self.source_type = source_type
        self.config = config

    @abstractmethod
    def fetch(self, query: str, **kwargs: Any) -> List[IngestionResult]:
        """Fetch results matching query."""
        ...

    @abstractmethod
    def fetch_by_id(self, identifier: str) -> Optional[IngestionResult]:
        """Fetch a single item by its unique identifier."""
        ...

    def health_check(self) -> bool:
        """Verify the source is reachable."""
        return True
