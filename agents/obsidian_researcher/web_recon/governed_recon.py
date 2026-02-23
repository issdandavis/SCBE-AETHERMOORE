"""SCBE-Governed Recon Orchestrator -- coordinates site profiling, page
analysis, caching, and extraction under governance constraints.

Every action is assigned a sensitivity score.  The governance function
``H(d, pd) = 1 / (1 + d + 2*pd)`` from the bounded safety variant gates
operations: higher sensitivity requires a lower safety threshold to
proceed.

All pure stdlib.  No external dependencies.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .recon_goggles import ReconGoggles, SemanticSkeleton
from .pixel_scanner import PixelScanner
from .site_recon import SiteProfile, SiteProfileBuilder
from .site_skimmer import SiteSkimmer
from .site_adapter import AdaptiveToolBuilder


# ------------------------------------------------------------------
# Sensitivity map
# ------------------------------------------------------------------

SENSITIVITY_MAP: Dict[str, float] = {
    "robots_check": 0.1,
    "profile_build": 0.2,
    "page_fetch": 0.3,
    "extraction": 0.3,
    "probing": 0.4,
    "form_interaction": 0.8,
}

_USER_AGENT = "SCBE-ObsidianResearcher/1.0 (+https://github.com/issdandavis/SCBE-AETHERMOORE)"


# ------------------------------------------------------------------
# Governance function
# ------------------------------------------------------------------

def _safety_score(depth: float, prior_danger: float) -> float:
    """Bounded safety score: H(d, pd) = 1 / (1 + d + 2*pd).

    Returns a value in (0, 1].  Higher is safer.
    """
    return 1.0 / (1.0 + depth + 2.0 * prior_danger)


# ------------------------------------------------------------------
# GovernedRecon
# ------------------------------------------------------------------

class GovernedRecon:
    """Orchestrate web reconnaissance under SCBE governance.

    Parameters
    ----------
    skimmer : SiteSkimmer
        In-memory page cache.
    goggles : ReconGoggles
        Semantic page analyser.
    scanner : PixelScanner
        Minimap renderer.
    safety_threshold : float
        Minimum safety score required to proceed (default 0.3).
    timeout : float
        HTTP request timeout in seconds (default 10).
    """

    def __init__(
        self,
        skimmer: SiteSkimmer,
        goggles: ReconGoggles,
        scanner: PixelScanner,
        safety_threshold: float = 0.3,
        timeout: float = 10.0,
    ) -> None:
        self._skimmer = skimmer
        self._goggles = goggles
        self._scanner = scanner
        self._threshold = safety_threshold
        self._timeout = timeout
        self._profiler = SiteProfileBuilder(timeout=timeout)
        self._adapter_builder = AdaptiveToolBuilder()
        self._profiles: Dict[str, SiteProfile] = {}

    # ------------------------------------------------------------------
    # Governance gate
    # ------------------------------------------------------------------

    def _gate(self, action: str, domain_risk: float) -> Tuple[bool, str, float]:
        """Evaluate whether *action* is permitted given *domain_risk*.

        Returns ``(allowed, reason, score)``.
        """
        sensitivity = SENSITIVITY_MAP.get(action, 0.5)
        score = _safety_score(sensitivity, domain_risk)
        if score >= self._threshold:
            return True, f"ALLOW: {action} (score={score:.3f} >= {self._threshold})", score
        return False, f"DENY: {action} (score={score:.3f} < {self._threshold})", score

    # ------------------------------------------------------------------
    # Should-visit check
    # ------------------------------------------------------------------

    def should_visit(self, url: str) -> Tuple[bool, str]:
        """Determine whether *url* may be visited.

        Checks: governance gate, robots.txt compliance, rate limits,
        anti-scraping signals, and domain risk.
        """
        domain = self._domain_of(url)
        profile = self._get_or_build_profile(domain)

        # 1. Governance gate for page_fetch
        allowed, reason, _ = self._gate("page_fetch", profile.domain_risk)
        if not allowed:
            return False, reason

        # 2. Robots.txt compliance
        path = urlparse(url).path or "/"
        for disallowed in profile.robots_disallowed_paths:
            if path.startswith(disallowed):
                # Check if explicitly allowed (Allow overrides Disallow)
                explicitly_allowed = any(
                    path.startswith(ap) for ap in profile.robots_allowed_paths
                )
                if not explicitly_allowed:
                    return False, f"DENY: robots.txt disallows {disallowed}"

        # 3. Anti-scraping warnings
        if profile.has_captcha:
            return False, "DENY: captcha detected -- manual interaction required"

        # 4. Rate-limit readiness
        profile.rate_limit.wait_if_needed()

        return True, "ALLOW: all checks passed"

    # ------------------------------------------------------------------
    # Recon page
    # ------------------------------------------------------------------

    def recon_page(self, url: str) -> Dict[str, Any]:
        """Perform full reconnaissance on a single page.

        Steps:
        1. Check ``should_visit``.
        2. Return cached data if available.
        3. Fetch page via urllib.
        4. Build semantic skeleton via goggles.
        5. Cache in skimmer.
        6. Generate minimap.
        7. Get or learn adapter.
        8. Extract content via adapter rules.

        Returns a dict with keys: ``url``, ``allowed``, ``reason``,
        ``skeleton``, ``minimap``, ``profile``, ``adapter``, ``extracted``.
        """
        result: Dict[str, Any] = {"url": url, "allowed": False, "reason": ""}

        # Step 1: should_visit
        allowed, reason = self.should_visit(url)
        result["allowed"] = allowed
        result["reason"] = reason
        if not allowed:
            return result

        # Step 2: check cache
        cached = self._skimmer.get_cached(url)
        if cached is not None and cached.skeleton is not None:
            domain = self._domain_of(url)
            profile = self._get_or_build_profile(domain)
            adapter = self._adapter_builder.get_adapter(domain)
            result["skeleton"] = cached.skeleton
            result["minimap"] = self._scanner.render_minimap(cached.skeleton)
            result["profile"] = profile
            result["adapter"] = adapter
            result["extracted"] = self._adapter_builder.extract(cached.html, adapter)
            result["from_cache"] = True
            return result

        # Step 3: fetch
        domain = self._domain_of(url)
        profile = self._get_or_build_profile(domain)
        html = self._fetch_page(url)
        if html is None:
            result["reason"] = "FAIL: unable to fetch page"
            result["allowed"] = False
            profile.rate_limit.record_success()
            return result

        profile.rate_limit.record_success()

        # Step 4: semantic skeleton
        skeleton = self._goggles.analyze(html, url=url)

        # Step 5: cache
        self._skimmer.cache_page(url, html, skeleton=skeleton)

        # Step 6: minimap
        minimap = self._scanner.render_minimap(skeleton)

        # Step 7: adapter
        adapter = self._adapter_builder.get_adapter(domain)
        if adapter.domain != domain or not adapter.extraction_rules:
            adapter = self._adapter_builder.learn_from_skeleton(skeleton, domain)

        # Step 8: extract
        extracted = self._adapter_builder.extract(html, adapter)

        result.update({
            "skeleton": skeleton,
            "minimap": minimap,
            "profile": profile,
            "adapter": adapter,
            "extracted": extracted,
            "from_cache": False,
        })
        return result

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_research(self, domain: str) -> str:
        """Export all cached data for *domain* as an Obsidian note.

        Includes site profile, page skeletons, link graph, and extracted
        content summaries.
        """
        # Attach profile to the skimmer's domain cache for richer export
        profile = self._profiles.get(domain)
        dc = self._skimmer._domains.get(domain)
        if dc is not None and profile is not None:
            dc.profile = profile

        return self._skimmer.export_to_obsidian(domain)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_build_profile(self, domain: str) -> SiteProfile:
        """Return the cached profile for *domain*, building if needed."""
        if domain not in self._profiles:
            self._profiles[domain] = self._profiler.build(domain)
        return self._profiles[domain]

    @staticmethod
    def _domain_of(url: str) -> str:
        """Extract the domain from *url*."""
        try:
            return urlparse(url).netloc or url
        except Exception:
            return url

    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch *url* and return the decoded body, or ``None``."""
        try:
            req = Request(url, headers={"User-Agent": _USER_AGENT})
            with urlopen(req, timeout=self._timeout) as resp:
                status = resp.getcode()
                if status == 429:
                    domain = self._domain_of(url)
                    profile = self._profiles.get(domain)
                    if profile is not None:
                        profile.rate_limit.record_429()
                    return None
                return resp.read(2_000_000).decode("utf-8", errors="replace")
        except HTTPError as exc:
            if exc.code == 429:
                domain = self._domain_of(url)
                profile = self._profiles.get(domain)
                if profile is not None:
                    profile.rate_limit.record_429()
            return None
        except (URLError, OSError):
            return None
