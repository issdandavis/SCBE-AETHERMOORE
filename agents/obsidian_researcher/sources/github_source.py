"""GitHub source adapter for the Obsidian researcher agent.

Searches GitHub's public API for repositories, code, issues, and
discussions matching research queries.  Used for competitive intelligence
(OpenClaw, Moltbot, etc.) and general AI-safety/security research.

Uses stdlib HTTP with optional ``GITHUB_TOKEN`` for higher rate limits
(5000 req/hr authenticated vs 60 req/hr unauthenticated).
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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_API_BASE = "https://api.github.com"
_SEARCH_REPOS = _API_BASE + "/search/repositories"
_SEARCH_CODE = _API_BASE + "/search/code"
_SEARCH_ISSUES = _API_BASE + "/search/issues"

_USER_AGENT = "SCBE-AETHERMOORE-HYDRA/1.0 (research)"
_DEFAULT_TIMEOUT = 15
_DEFAULT_PER_PAGE = 10

# Repos to watch for competitive intelligence
_WATCH_REPOS: List[str] = [
    "openclaw/openclaw",
    "issdandavis/SCBE-AETHERMOORE",
]

# Topics to track
_DEFAULT_TOPICS: List[str] = [
    "ai-safety",
    "ai-governance",
    "post-quantum-cryptography",
    "hyperbolic-geometry",
    "llm-security",
]


class GitHubSource(SourceAdapter):
    """Adapter that queries GitHub's API and emits
    :class:`IngestionResult` records for vault ingestion.

    Parameters
    ----------
    config : dict
        Optional keys:

        * ``token``       -- GitHub PAT (default: env ``GITHUB_TOKEN``).
        * ``timeout``     -- HTTP timeout (default 15).
        * ``per_page``    -- results per query (default 10).
        * ``user_agent``  -- custom User-Agent.
        * ``search_type`` -- ``"repos"`` (default), ``"code"``, ``"issues"``.
        * ``watch_repos`` -- list of owner/repo strings to monitor.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(source_type=SourceType.GITHUB, config=config or {})

        self._token: str = self.config.get(
            "token", os.environ.get("GITHUB_TOKEN", "")
        )
        self._timeout: int = int(self.config.get("timeout", _DEFAULT_TIMEOUT))
        self._per_page: int = int(self.config.get("per_page", _DEFAULT_PER_PAGE))
        self._user_agent: str = self.config.get("user_agent", _USER_AGENT)
        self._search_type: str = self.config.get("search_type", "repos")
        self._watch_repos: List[str] = list(
            self.config.get("watch_repos", _WATCH_REPOS)
        )

    # ------------------------------------------------------------------
    # SourceAdapter interface
    # ------------------------------------------------------------------

    def fetch(self, query: str, **kwargs: Any) -> List[IngestionResult]:
        """Search GitHub for repositories, code, or issues matching *query*.

        Extra keyword arguments:

        * ``search_type`` -- ``"repos"``, ``"code"``, or ``"issues"``.
        * ``per_page``    -- override result count.
        * ``sort``        -- sort field (``"stars"``, ``"updated"``, etc.).
        * ``language``    -- filter by programming language.
        """
        search_type = kwargs.get("search_type", self._search_type)
        per_page = int(kwargs.get("per_page", self._per_page))
        sort = kwargs.get("sort", "best-match")
        language = kwargs.get("language")

        q = query
        if language:
            q = f"{q} language:{language}"

        if search_type == "code":
            url_base = _SEARCH_CODE
        elif search_type == "issues":
            url_base = _SEARCH_ISSUES
        else:
            url_base = _SEARCH_REPOS

        params = urllib.parse.urlencode({
            "q": q,
            "per_page": str(per_page),
            "sort": sort,
        })
        url = f"{url_base}?{params}"
        data = self._get_json(url)
        if data is None:
            return []

        items = data.get("items", [])
        if search_type == "code":
            return [self._code_to_result(item) for item in items if item]
        elif search_type == "issues":
            return [self._issue_to_result(item) for item in items if item]
        else:
            return [self._repo_to_result(item) for item in items if item]

    def fetch_by_id(self, identifier: str) -> Optional[IngestionResult]:
        """Fetch a single repo by ``owner/repo`` string."""
        cleaned = identifier.strip()
        if not cleaned or "/" not in cleaned:
            return None

        url = f"{_API_BASE}/repos/{urllib.parse.quote(cleaned, safe='/')}"
        data = self._get_json(url)
        if data is None:
            return None

        return self._repo_to_result(data)

    def health_check(self) -> bool:
        """Verify GitHub API is reachable."""
        try:
            data = self._get_json(f"{_API_BASE}/rate_limit")
            return data is not None
        except Exception:
            logger.debug("GitHub health check failed", exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Competitive intelligence helpers
    # ------------------------------------------------------------------

    def fetch_repo_activity(
        self, owner_repo: str, since_days: int = 7
    ) -> List[IngestionResult]:
        """Fetch recent commits + issues for a watched repo.

        Useful for tracking OpenClaw and other competitors.
        """
        results: List[IngestionResult] = []

        # Recent commits
        url = f"{_API_BASE}/repos/{owner_repo}/commits?per_page=10"
        data = self._get_json(url)
        if data and isinstance(data, list):
            for commit in data[:10]:
                msg = commit.get("commit", {}).get("message", "")
                sha = commit.get("sha", "")[:8]
                author = commit.get("commit", {}).get("author", {}).get("name", "")
                date = commit.get("commit", {}).get("author", {}).get("date", "")

                results.append(IngestionResult(
                    source_type=SourceType.GITHUB,
                    raw_content=f"[{owner_repo}] Commit {sha}: {msg}",
                    title=f"{owner_repo} commit: {msg[:80]}",
                    authors=[author] if author else [],
                    url=commit.get("html_url", ""),
                    timestamp=date,
                    identifiers={"repo": owner_repo, "sha": commit.get("sha", "")},
                    tags=["github:commit", f"repo:{owner_repo}"],
                    metadata={"repo": owner_repo, "sha": sha},
                    summary=msg[:200],
                ))

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_json(self, url: str) -> Optional[Any]:
        """Perform a GET request with optional auth, return parsed JSON."""
        headers = {
            "User-Agent": self._user_agent,
            "Accept": "application/vnd.github+json",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read()
                return json.loads(raw)
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            logger.warning("GitHub HTTP error for %s: %s", url, exc)
            return None
        except json.JSONDecodeError as exc:
            logger.warning("GitHub JSON parse error for %s: %s", url, exc)
            return None
        except Exception:
            logger.exception("Unexpected error fetching %s", url)
            return None

    @staticmethod
    def _repo_to_result(repo: Dict[str, Any]) -> IngestionResult:
        """Convert a GitHub repo object to ``IngestionResult``."""
        name = repo.get("full_name", repo.get("name", ""))
        desc = repo.get("description", "") or ""
        stars = repo.get("stargazers_count", 0)
        language = repo.get("language", "")
        topics = repo.get("topics", [])

        tags = ["github:repo"]
        if language:
            tags.append(f"lang:{language}")
        tags.extend(f"topic:{t}" for t in (topics or [])[:5])

        return IngestionResult(
            source_type=SourceType.GITHUB,
            raw_content=f"{name}\n\n{desc}",
            title=name,
            authors=[repo.get("owner", {}).get("login", "")],
            url=repo.get("html_url", ""),
            timestamp=repo.get("updated_at", ""),
            identifiers={"repo": name, "github_id": str(repo.get("id", ""))},
            tags=tags,
            metadata={
                "stars": stars,
                "forks": repo.get("forks_count", 0),
                "language": language,
                "topics": topics or [],
                "license": (repo.get("license") or {}).get("spdx_id", ""),
                "open_issues": repo.get("open_issues_count", 0),
            },
            summary=desc[:500] if desc else name,
        )

    @staticmethod
    def _code_to_result(item: Dict[str, Any]) -> IngestionResult:
        """Convert a GitHub code search result to ``IngestionResult``."""
        path = item.get("path", "")
        repo_name = item.get("repository", {}).get("full_name", "")
        name = f"{repo_name}/{path}" if repo_name else path

        return IngestionResult(
            source_type=SourceType.GITHUB,
            raw_content=f"Code match in {name}",
            title=name,
            authors=[repo_name.split("/")[0]] if "/" in repo_name else [],
            url=item.get("html_url", ""),
            timestamp="",
            identifiers={"repo": repo_name, "path": path},
            tags=["github:code"],
            metadata={"repo": repo_name, "path": path, "sha": item.get("sha", "")},
            summary=f"Code match: {path} in {repo_name}",
        )

    @staticmethod
    def _issue_to_result(item: Dict[str, Any]) -> IngestionResult:
        """Convert a GitHub issue/PR search result to ``IngestionResult``."""
        title = item.get("title", "")
        body = item.get("body", "") or ""
        user = item.get("user", {}).get("login", "")
        labels = [lbl.get("name", "") for lbl in item.get("labels", [])]

        tags = ["github:issue"]
        if item.get("pull_request"):
            tags = ["github:pr"]
        tags.extend(f"label:{l}" for l in labels[:5])

        return IngestionResult(
            source_type=SourceType.GITHUB,
            raw_content=f"{title}\n\n{body}",
            title=title,
            authors=[user] if user else [],
            url=item.get("html_url", ""),
            timestamp=item.get("created_at", ""),
            identifiers={
                "github_number": str(item.get("number", "")),
                "repo": item.get("repository_url", "").replace(_API_BASE + "/repos/", ""),
            },
            tags=tags,
            metadata={
                "state": item.get("state", ""),
                "comments": item.get("comments", 0),
                "labels": labels,
                "is_pr": bool(item.get("pull_request")),
            },
            summary=body[:500] if body else title,
        )
