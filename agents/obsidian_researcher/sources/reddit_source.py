"""Reddit source adapter for the Obsidian researcher agent.

Searches Reddit's public JSON API for posts matching a query across
one or more subreddits.  Pure-stdlib implementation (uses
:mod:`urllib.request` for HTTP and :mod:`json` for parsing).

No authentication is required — this uses the unauthenticated
``/.json`` endpoints which are rate-limited but sufficient for
periodic research polling.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..source_adapter import IngestionResult, SourceAdapter, SourceType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_URL = "https://www.reddit.com"
_SEARCH_TEMPLATE = (
    _BASE_URL + "/r/{subreddit}/search.json"
    "?q={query}&restrict_sr=1&sort=relevance&t=all&limit={limit}"
)
_BY_ID_TEMPLATE = _BASE_URL + "/by_id/t3_{post_id}.json"
_HEALTH_URL = _BASE_URL + "/.json?limit=1"

_USER_AGENT = "SCBE-ResearchAgent/1.0 (research only)"

_DEFAULT_SUBREDDITS: List[str] = [
    "MachineLearning",
    "crypto",
    "computersecurity",
    "CategoryTheory",
    # Dev security + AI safety
    "netsec",
    "AIsafety",
    "LocalLLaMA",
    "cybersecurity",
    # Game dev + AI experiment
    "gamedev",
    "indiegames",
    "reinforcementlearning",
    # Patent + IP
    "patents",
]

_DEFAULT_LIMIT = 10
_DEFAULT_TIMEOUT = 15


class RedditSource(SourceAdapter):
    """Adapter that queries Reddit's public JSON API and emits
    :class:`IngestionResult` records suitable for vault ingestion.

    Parameters
    ----------
    config : dict
        Optional keys:

        * ``subreddits`` -- list of subreddit names to search
          (default: MachineLearning, crypto, computersecurity,
          CategoryTheory).
        * ``limit`` -- max results per subreddit (default 10).
        * ``timeout`` -- HTTP timeout in seconds (default 15).
        * ``user_agent`` -- custom User-Agent string.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(source_type=SourceType.REDDIT, config=config or {})

        self._subreddits: List[str] = list(
            self.config.get("subreddits", _DEFAULT_SUBREDDITS)
        )
        self._limit: int = int(self.config.get("limit", _DEFAULT_LIMIT))
        self._timeout: int = int(self.config.get("timeout", _DEFAULT_TIMEOUT))
        self._user_agent: str = self.config.get("user_agent", _USER_AGENT)

    # ------------------------------------------------------------------
    # SourceAdapter interface
    # ------------------------------------------------------------------

    def fetch(self, query: str, **kwargs: Any) -> List[IngestionResult]:
        """Search each configured subreddit for *query* and return
        normalised ingestion results.

        Extra keyword arguments:

        * ``subreddits`` -- override the default list for this call.
        * ``limit`` -- override the per-subreddit result count.
        """
        subreddits = kwargs.get("subreddits", self._subreddits)
        limit = int(kwargs.get("limit", self._limit))

        results: List[IngestionResult] = []
        for sub in subreddits:
            url = _SEARCH_TEMPLATE.format(
                subreddit=urllib.parse.quote(sub, safe=""),
                query=urllib.parse.quote(query, safe=""),
                limit=limit,
            )
            data = self._get_json(url)
            if data is None:
                continue

            children = (
                data.get("data", {}).get("children", [])
                if isinstance(data, dict)
                else []
            )
            for child in children:
                post = child.get("data", {})
                result = self._post_to_result(post, sub)
                if result is not None:
                    results.append(result)

        return results

    def fetch_by_id(self, identifier: str) -> Optional[IngestionResult]:
        """Fetch a single Reddit post by its short ID (e.g. ``abc123``).

        Uses the ``/by_id/t3_{id}.json`` endpoint.
        """
        cleaned = identifier.strip()
        if not cleaned:
            return None

        url = _BY_ID_TEMPLATE.format(post_id=urllib.parse.quote(cleaned, safe=""))
        data = self._get_json(url)
        if data is None:
            return None

        children = (
            data.get("data", {}).get("children", [])
            if isinstance(data, dict)
            else []
        )
        if not children:
            return None

        post = children[0].get("data", {})
        subreddit = post.get("subreddit", "unknown")
        return self._post_to_result(post, subreddit)

    def health_check(self) -> bool:
        """Verify Reddit is reachable with a minimal JSON request."""
        try:
            data = self._get_json(_HEALTH_URL)
            return data is not None
        except Exception:
            logger.debug("Reddit health check failed", exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_json(self, url: str) -> Optional[Dict[str, Any]]:
        """Perform a GET request and return parsed JSON, or ``None`` on
        any failure."""
        req = urllib.request.Request(url, headers={"User-Agent": self._user_agent})
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read()
                return json.loads(raw)
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            logger.warning("Reddit HTTP error for %s: %s", url, exc)
            return None
        except json.JSONDecodeError as exc:
            logger.warning("Reddit JSON parse error for %s: %s", url, exc)
            return None
        except Exception:
            logger.exception("Unexpected error fetching %s", url)
            return None

    @staticmethod
    def _post_to_result(
        post: Dict[str, Any], subreddit: str
    ) -> Optional[IngestionResult]:
        """Convert a Reddit post JSON object to an ``IngestionResult``."""
        title = post.get("title", "")
        if not title:
            return None

        selftext = post.get("selftext", "")
        author = post.get("author", "")
        score = post.get("score", 0)
        num_comments = post.get("num_comments", 0)
        permalink = post.get("permalink", "")
        post_id = post.get("id", "")
        created_utc = post.get("created_utc", 0)

        # Convert epoch to ISO timestamp
        timestamp = ""
        if created_utc:
            try:
                timestamp = datetime.fromtimestamp(
                    float(created_utc), tz=timezone.utc
                ).isoformat()
            except (ValueError, OSError, OverflowError):
                pass

        full_url = f"{_BASE_URL}{permalink}" if permalink else None

        # Build content: title + selftext (selftext may be empty for link posts)
        raw_content = title
        if selftext:
            raw_content = f"{title}\n\n{selftext}"

        # Tags from subreddit and flair
        tags: List[str] = [f"r/{subreddit}"]
        flair = post.get("link_flair_text")
        if flair:
            tags.append(flair)

        return IngestionResult(
            source_type=SourceType.REDDIT,
            raw_content=raw_content,
            title=title,
            authors=[author] if author else [],
            url=full_url,
            timestamp=timestamp,
            identifiers={"reddit_id": post_id, "subreddit": subreddit},
            tags=tags,
            metadata={
                "subreddit": subreddit,
                "score": score,
                "num_comments": num_comments,
                "permalink": permalink,
                "is_self": post.get("is_self", True),
                "domain": post.get("domain", ""),
                "external_url": post.get("url", ""),
            },
            summary=selftext[:500] if selftext else title,
        )
