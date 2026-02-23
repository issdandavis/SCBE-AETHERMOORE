"""In-Memory Cache Per Domain -- caches fetched pages, skeletons, and link
graphs with TTL-based expiration and byte-budget eviction.

Provides an ``export_to_obsidian`` method that converts cached domain data
into Obsidian markdown notes with YAML frontmatter and wikilinks.

All pure stdlib.  No external dependencies.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .recon_goggles import SemanticSkeleton


# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------

@dataclass
class CachedPage:
    """A single fetched and optionally analysed page."""

    url: str
    html: str
    skeleton: Optional[SemanticSkeleton] = None
    fetched_at: float = 0.0


@dataclass
class DomainCache:
    """All cached data for a single domain."""

    domain: str
    profile: Optional[Any] = None  # SiteProfile (avoid circular import)
    pages: Dict[str, CachedPage] = field(default_factory=dict)
    link_graph: Dict[str, List[str]] = field(default_factory=dict)
    total_bytes: int = 0


# ------------------------------------------------------------------
# SiteSkimmer
# ------------------------------------------------------------------

class SiteSkimmer:
    """In-memory page cache with TTL expiration and byte-budget eviction.

    Parameters
    ----------
    ttl_seconds : float
        Time-to-live for cached pages (default 1 hour).
    max_bytes : int
        Maximum total bytes across all domains (default 50 MB).
    """

    def __init__(
        self,
        ttl_seconds: float = 3600.0,
        max_bytes: int = 50_000_000,
    ) -> None:
        self._ttl = ttl_seconds
        self._max_bytes = max_bytes
        self._domains: Dict[str, DomainCache] = {}

    # ------------------------------------------------------------------
    # Cache operations
    # ------------------------------------------------------------------

    def cache_page(
        self,
        url: str,
        html: str,
        skeleton: Optional[SemanticSkeleton] = None,
    ) -> CachedPage:
        """Store a fetched page in the cache.

        If the byte budget is exceeded after insertion, the oldest pages
        across all domains are evicted until the budget is met.
        """
        domain = self._domain_of(url)
        dc = self._ensure_domain(domain)

        page = CachedPage(
            url=url,
            html=html,
            skeleton=skeleton,
            fetched_at=time.time(),
        )
        html_bytes = len(html.encode("utf-8", errors="replace"))

        # Remove old version if present
        old = dc.pages.get(url)
        if old is not None:
            old_bytes = len(old.html.encode("utf-8", errors="replace"))
            dc.total_bytes -= old_bytes

        dc.pages[url] = page
        dc.total_bytes += html_bytes

        # Update link graph from skeleton
        if skeleton is not None:
            dc.link_graph[url] = list(skeleton.links)

        # Evict if over budget
        self._evict_if_needed()

        return page

    def get_cached(self, url: str) -> Optional[CachedPage]:
        """Return the cached page for *url*, or ``None`` if missing / expired."""
        domain = self._domain_of(url)
        dc = self._domains.get(domain)
        if dc is None:
            return None

        page = dc.pages.get(url)
        if page is None:
            return None

        # TTL check
        if time.time() - page.fetched_at > self._ttl:
            self._remove_page(dc, url)
            return None

        return page

    def evict_expired(self) -> int:
        """Remove all pages that have exceeded their TTL.

        Returns the number of pages evicted.
        """
        now = time.time()
        evicted = 0

        for dc in list(self._domains.values()):
            expired_urls = [
                url for url, page in dc.pages.items()
                if now - page.fetched_at > self._ttl
            ]
            for url in expired_urls:
                self._remove_page(dc, url)
                evicted += 1

        return evicted

    # ------------------------------------------------------------------
    # Domain summary
    # ------------------------------------------------------------------

    def get_domain_summary(self, domain: str) -> Dict[str, Any]:
        """Return a summary dict for *domain*."""
        dc = self._domains.get(domain)
        if dc is None:
            return {"domain": domain, "cached_pages": 0, "total_bytes": 0}

        return {
            "domain": domain,
            "cached_pages": len(dc.pages),
            "total_bytes": dc.total_bytes,
            "urls": sorted(dc.pages.keys()),
            "link_graph_edges": sum(len(v) for v in dc.link_graph.values()),
            "has_profile": dc.profile is not None,
        }

    # ------------------------------------------------------------------
    # Obsidian export
    # ------------------------------------------------------------------

    def export_to_obsidian(self, domain: str) -> str:
        """Convert cached domain data to an Obsidian markdown note.

        Produces YAML frontmatter, a page index with wikilinks, the link
        graph, and per-page skeleton summaries.
        """
        dc = self._domains.get(domain)
        if dc is None:
            return f"# {domain}\n\n_No cached data for this domain._\n"

        now_iso = datetime.now(timezone.utc).isoformat()

        lines: List[str] = [
            "---",
            f"title: \"Web Recon -- {domain}\"",
            f"date: {now_iso}",
            "type: web-recon",
            f"domain: {domain}",
            f"cached_pages: {len(dc.pages)}",
            f"total_bytes: {dc.total_bytes}",
            "---\n",
            f"# Web Recon -- {domain}\n",
        ]

        # Profile summary
        if dc.profile is not None:
            profile = dc.profile
            lines.append("## Site Profile\n")
            lines.append(f"- **Crawl delay:** {getattr(profile, 'crawl_delay', 'N/A')}s")
            lines.append(f"- **Cloudflare:** {getattr(profile, 'has_cloudflare', False)}")
            lines.append(f"- **Captcha:** {getattr(profile, 'has_captcha', False)}")
            lines.append(f"- **JS required:** {getattr(profile, 'requires_js', False)}")
            lines.append(f"- **Domain risk:** {getattr(profile, 'domain_risk', 0.0):.2f}")
            disallowed = getattr(profile, "robots_disallowed_paths", [])
            lines.append(f"- **Disallowed paths:** {len(disallowed)}\n")

        # Page index
        lines.append("## Cached Pages\n")
        if dc.pages:
            for url, page in sorted(dc.pages.items()):
                age_s = time.time() - page.fetched_at
                age_str = f"{age_s:.0f}s ago" if age_s < 3600 else f"{age_s / 3600:.1f}h ago"
                archetype = ""
                if page.skeleton is not None:
                    archetype = f" ({page.skeleton.page_archetype})"
                safe_title = url.replace("|", "-")
                lines.append(f"- [[{safe_title}]]{archetype} -- fetched {age_str}")
        else:
            lines.append("_No pages cached._")

        lines.append("")

        # Link graph
        lines.append("## Link Graph\n")
        if dc.link_graph:
            for source_url, targets in sorted(dc.link_graph.items()):
                lines.append(f"### {source_url}\n")
                for target in targets[:20]:  # cap at 20 per page
                    lines.append(f"- {target}")
                if len(targets) > 20:
                    lines.append(f"- _...and {len(targets) - 20} more_")
                lines.append("")
        else:
            lines.append("_No link graph data._\n")

        # Skeleton summaries
        lines.append("## Page Skeletons\n")
        for url, page in sorted(dc.pages.items()):
            if page.skeleton is None:
                continue
            sk = page.skeleton
            dist = sk.tongue_distribution
            lines.append(f"### {url}\n")
            lines.append(f"- **Archetype:** {sk.page_archetype}")
            lines.append(f"- **Headings:** {len(sk.headings)}")
            lines.append(f"- **Links:** {len(sk.links)}")
            lines.append(f"- **Forms:** {sk.forms}  |  **Tables:** {sk.tables}  |  **Media:** {sk.media}")
            tongue_str = "  ".join(f"{t}={v:.0%}" for t, v in dist.items() if v > 0)
            lines.append(f"- **Tongue distribution:** {tongue_str}")
            lines.append(f"- **Structure hash:** `{sk.structure_hash}`\n")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_domain(self, domain: str) -> DomainCache:
        """Return the :class:`DomainCache` for *domain*, creating if needed."""
        if domain not in self._domains:
            self._domains[domain] = DomainCache(domain=domain)
        return self._domains[domain]

    @staticmethod
    def _domain_of(url: str) -> str:
        """Extract the domain from *url*."""
        try:
            return urlparse(url).netloc or url
        except Exception:
            return url

    def _remove_page(self, dc: DomainCache, url: str) -> None:
        """Remove a single page from the domain cache."""
        page = dc.pages.pop(url, None)
        if page is not None:
            dc.total_bytes -= len(page.html.encode("utf-8", errors="replace"))
            dc.total_bytes = max(0, dc.total_bytes)
        dc.link_graph.pop(url, None)

    def _total_bytes(self) -> int:
        """Sum total_bytes across all domains."""
        return sum(dc.total_bytes for dc in self._domains.values())

    def _evict_if_needed(self) -> None:
        """Evict oldest pages globally until under byte budget."""
        while self._total_bytes() > self._max_bytes:
            # Find the oldest page across all domains
            oldest_url: Optional[str] = None
            oldest_dc: Optional[DomainCache] = None
            oldest_time = float("inf")

            for dc in self._domains.values():
                for url, page in dc.pages.items():
                    if page.fetched_at < oldest_time:
                        oldest_time = page.fetched_at
                        oldest_url = url
                        oldest_dc = dc

            if oldest_dc is None or oldest_url is None:
                break  # nothing left to evict

            self._remove_page(oldest_dc, oldest_url)
