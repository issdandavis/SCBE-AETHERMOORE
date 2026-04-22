"""Site Profile Builder -- probes a domain for robots.txt, anti-scraping
defences, and rate-limit parameters.

Fetches robots.txt via urllib.request, parses allowed/disallowed paths and
Crawl-delay manually (no urllib.robotparser), then probes headers for
Cloudflare, captcha walls, and JavaScript-required pages.

All pure stdlib.  No external dependencies.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# ------------------------------------------------------------------
# Rate-limit state
# ------------------------------------------------------------------

@dataclass
class RateLimitState:
    """Tracks request cadence and exponential backoff for a single domain."""

    requests_made: int = 0
    last_request_time: float = 0.0
    backoff_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    max_backoff: float = 60.0

    def wait_if_needed(self) -> None:
        """Sleep if the minimum interval since the last request has not elapsed."""
        if self.last_request_time <= 0.0:
            return
        elapsed = time.time() - self.last_request_time
        remaining = self.backoff_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def record_429(self) -> None:
        """Increase backoff after receiving a 429 Too Many Requests."""
        self.backoff_seconds = min(
            self.backoff_seconds * self.backoff_multiplier,
            self.max_backoff,
        )
        self.last_request_time = time.time()

    def record_success(self) -> None:
        """Decay backoff toward 1 s after a successful request."""
        self.requests_made += 1
        self.last_request_time = time.time()
        # Slowly decay toward the floor
        self.backoff_seconds = max(1.0, self.backoff_seconds * 0.8)


# ------------------------------------------------------------------
# Site profile
# ------------------------------------------------------------------

@dataclass
class SiteProfile:
    """Aggregated reconnaissance data for a single domain."""

    domain: str
    robots_allowed_paths: List[str] = field(default_factory=list)
    robots_disallowed_paths: List[str] = field(default_factory=list)
    crawl_delay: float = 2.0
    rate_limit: RateLimitState = field(default_factory=RateLimitState)
    has_cloudflare: bool = False
    has_captcha: bool = False
    requires_js: bool = False
    has_cookie_wall: bool = False
    domain_risk: float = 0.0
    last_probed: str = ""


# ------------------------------------------------------------------
# Builder
# ------------------------------------------------------------------

_USER_AGENT = "SCBE-ObsidianResearcher/1.0 (+https://github.com/issdandavis/SCBE-AETHERMOORE)"

_ROBOTS_DISALLOW_RE = re.compile(r"^Disallow:\s*(.+)", re.IGNORECASE)
_ROBOTS_ALLOW_RE = re.compile(r"^Allow:\s*(.+)", re.IGNORECASE)
_ROBOTS_DELAY_RE = re.compile(r"^Crawl-delay:\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
_CAPTCHA_RE = re.compile(
    r"captcha|recaptcha|hcaptcha|g-recaptcha|cf-turnstile",
    re.IGNORECASE,
)
_JS_REQUIRED_RE = re.compile(
    r"<noscript[^>]*>.*?(enable\s+javascript|javascript\s+required)",
    re.IGNORECASE | re.DOTALL,
)


class SiteProfileBuilder:
    """Build a :class:`SiteProfile` by probing a domain.

    Parameters
    ----------
    timeout : float
        HTTP request timeout in seconds.
    """

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, domain: str) -> SiteProfile:
        """Probe *domain* and return a populated :class:`SiteProfile`."""
        profile = SiteProfile(domain=domain)

        # 1. Fetch and parse robots.txt
        self._parse_robots(profile)

        # 2. Probe the home page for anti-scraping signals
        self._probe_homepage(profile)

        # 3. Compute domain risk (heuristic 0-1)
        profile.domain_risk = self._compute_risk(profile)

        # 4. Set the rate-limit backoff to at least the crawl-delay
        profile.rate_limit.backoff_seconds = max(
            profile.rate_limit.backoff_seconds,
            profile.crawl_delay,
        )

        profile.last_probed = datetime.now(timezone.utc).isoformat()
        return profile

    # ------------------------------------------------------------------
    # Internal: robots.txt
    # ------------------------------------------------------------------

    def _parse_robots(self, profile: SiteProfile) -> None:
        """Fetch ``/robots.txt`` and populate allowed/disallowed paths."""
        url = f"https://{profile.domain}/robots.txt"
        body = self._fetch_text(url)
        if body is None:
            return

        in_wildcard_block = False
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Detect User-agent blocks -- only honour wildcard (*)
            if line.lower().startswith("user-agent:"):
                agent = line.split(":", 1)[1].strip()
                in_wildcard_block = agent == "*"
                continue

            if not in_wildcard_block:
                continue

            m_dis = _ROBOTS_DISALLOW_RE.match(line)
            if m_dis:
                profile.robots_disallowed_paths.append(m_dis.group(1).strip())
                continue

            m_allow = _ROBOTS_ALLOW_RE.match(line)
            if m_allow:
                profile.robots_allowed_paths.append(m_allow.group(1).strip())
                continue

            m_delay = _ROBOTS_DELAY_RE.match(line)
            if m_delay:
                try:
                    profile.crawl_delay = float(m_delay.group(1))
                except ValueError:
                    pass

    # ------------------------------------------------------------------
    # Internal: homepage probe
    # ------------------------------------------------------------------

    def _probe_homepage(self, profile: SiteProfile) -> None:
        """Fetch the homepage and inspect headers / body for defences."""
        url = f"https://{profile.domain}/"
        try:
            req = Request(url, headers={"User-Agent": _USER_AGENT})
            with urlopen(req, timeout=self._timeout) as resp:
                headers = {k.lower(): v for k, v in resp.getheaders()}
                body = resp.read(200_000).decode("utf-8", errors="replace")
        except (HTTPError, URLError, OSError):
            return

        # Cloudflare detection
        if "cf-ray" in headers or "cf-cache-status" in headers:
            profile.has_cloudflare = True

        # Cookie wall detection
        if "set-cookie" in headers and "consent" in headers.get("set-cookie", "").lower():
            profile.has_cookie_wall = True

        # Captcha detection
        if _CAPTCHA_RE.search(body):
            profile.has_captcha = True

        # JavaScript-required detection
        if _JS_REQUIRED_RE.search(body):
            profile.requires_js = True

    # ------------------------------------------------------------------
    # Internal: risk heuristic
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_risk(profile: SiteProfile) -> float:
        """Return a 0-1 risk score.  Higher means harder to scrape ethically."""
        risk = 0.0
        if profile.has_cloudflare:
            risk += 0.2
        if profile.has_captcha:
            risk += 0.3
        if profile.requires_js:
            risk += 0.15
        if profile.has_cookie_wall:
            risk += 0.1
        if len(profile.robots_disallowed_paths) > 20:
            risk += 0.15
        if profile.crawl_delay > 10:
            risk += 0.1
        return min(1.0, risk)

    # ------------------------------------------------------------------
    # Internal: HTTP helper
    # ------------------------------------------------------------------

    def _fetch_text(self, url: str) -> Optional[str]:
        """Fetch *url* and return decoded body text, or ``None`` on error."""
        try:
            req = Request(url, headers={"User-Agent": _USER_AGENT})
            with urlopen(req, timeout=self._timeout) as resp:
                return resp.read(500_000).decode("utf-8", errors="replace")
        except (HTTPError, URLError, OSError):
            return None
