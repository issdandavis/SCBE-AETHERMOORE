"""Browser-tab manifest layer for context-frugal, governed AI browsing.

The idea: an agent should be able to *know what a page contains* without holding
the page's full text in its context window. A :class:`TabManifest` is a compact,
structured digest of a saved tab — title, section outline, interaction counts,
topics/intent — that costs ~1-2% of the tokens the rendered text would. The heavy
section bodies stay out of context until the agent asks for a specific one
(:meth:`TabStore.read_section`). Hold many tabs cheaply; fetch one section surgically.

Security is not optional here. A saved tab is *context the agent will trust*, so a
spam / phishing / malware page must never be cached as if it were clean. Every tab is
risk-assessed before its content is trusted, combining two existing SCBE primitives:

- domain reputation via :class:`~src.aetherbrowser.hyperlane_py.HyperLanePy`
  (GREEN/YELLOW/RED zones; unknown domains default to RED), and
- content threat scan via :func:`agents.antivirus_membrane.scan_text_for_threats`
  (prompt-injection + malware signatures; a spam page that embeds "ignore previous
  instructions" to hijack the agent raises the risk score and is caught here).

These collapse into the canonical L13 risk tier — ALLOW / QUARANTINE / ESCALATE /
DENY. A DENY tab's section bodies are *withheld* (the manifest still records why it
was blocked); QUARANTINE/ESCALATE tabs are readable but flagged so the agent treats
their content as untrusted.

Reuses (does not reinvent):
    * :class:`src.aetherbrowser.page_analyzer.PageAnalyzer` — structural analysis
    * :func:`agents.antivirus_membrane.scan_text_for_threats` — content threat scan
    * :class:`src.aetherbrowser.hyperlane_py.HyperLanePy` — domain reputation zoning

The module is pure: the caller supplies the HTML (fetched however — plain HTTP for
server-rendered pages, a headless render for SPAs) and a ``fetched_at`` timestamp, so
behaviour is deterministic and unit-testable with no network and no clock.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from html import unescape
from typing import Any
from urllib.parse import urlparse

from agents.antivirus_membrane import ThreatScan, scan_text_for_threats
from src.aetherbrowser.hyperlane_py import Decision, HyperLanePy, Zone
from src.aetherbrowser.page_analyzer import PageAnalyzer

# Canonical L13 risk tiers, ordered least -> most severe so we can take a max.
SAFETY_TIERS = ("ALLOW", "QUARANTINE", "ESCALATE", "DENY")
_TIER_RANK = {tier: i for i, tier in enumerate(SAFETY_TIERS)}

# Reputable reference domains that should NOT quarantine just for being unfamiliar.
# These are trusted for *reputation* only (not malware vectors); the content threat
# scan still runs on them, so an injected/poisoned page on a trusted domain still
# escalates. issdandavis.github.io is the operator's own published research surface.
TRUSTED_REFERENCE_DOMAINS = (
    "en.wikipedia.org",
    "wikipedia.org",
    "arxiv.org",
    "developer.mozilla.org",
    "docs.python.org",
    "stackoverflow.com",
    "stackexchange.com",
    "nist.gov",
    "ietf.org",
    "rfc-editor.org",
    "scholar.google.com",
    "semanticscholar.org",
    "issdandavis.github.io",  # operator's own verified-research site
)


def build_research_hyperlane(extra_trusted: Iterable[str] = ()) -> HyperLanePy:
    """A HyperLane pre-seeded with reputable reference domains as GREEN.

    Keeps the conservative RED-by-default posture for genuinely unknown sites while
    letting research/reference pages (and the operator's own site) be read as context
    without a quarantine prompt. The content threat scan is unaffected.
    """
    lane = HyperLanePy()
    for domain in (*TRUSTED_REFERENCE_DOMAINS, *extra_trusted):
        lane.add_domain(domain, Zone.GREEN)
    return lane


def _escalate(current: str, candidate: str) -> str:
    """Return whichever of two L13 tiers is the more severe."""
    return candidate if _TIER_RANK[candidate] > _TIER_RANK[current] else current


# ── HTML -> structured parts (stdlib only, no new deps) ──────────────────────


def _strip_tags(fragment: str) -> str:
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", fragment)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return unescape(re.sub(r"\s+", " ", text)).strip()


def _parse_html(html: str) -> dict[str, Any]:
    """Extract the structural skeleton PageAnalyzer expects from raw HTML.

    Returns title, visible text, and heading/link/form/button lists. Heading
    bodies are sliced between consecutive headings to back on-demand section reads.
    """
    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    title = _strip_tags(title_match.group(1)) if title_match else ""

    # Headings with their source positions, so we can segment section bodies.
    headings: list[dict[str, Any]] = []
    sections: list[tuple[str, int, int]] = []  # (heading_text, body_start, heading_start)
    for m in re.finditer(r"(?is)<h([1-6])[^>]*>(.*?)</h\1>", html):
        text = _strip_tags(m.group(2))
        if not text:
            continue
        headings.append({"level": int(m.group(1)), "text": text})
        sections.append((text, m.end(), m.start()))

    section_bodies: dict[str, str] = {}
    for i, (text, body_start, _) in enumerate(sections):
        body_end = sections[i + 1][2] if i + 1 < len(sections) else len(html)
        body = _strip_tags(html[body_start:body_end])
        if body and text not in section_bodies:
            section_bodies[text] = body

    links = [
        {"text": _strip_tags(m.group(2)), "href": m.group(1)}
        for m in re.finditer(r'(?is)<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html)
    ]
    forms = [{"index": i} for i, _ in enumerate(re.finditer(r"(?i)<form\b", html))]
    buttons = [{"text": _strip_tags(m.group(1))} for m in re.finditer(r"(?is)<button[^>]*>(.*?)</button>", html)]
    inputs = re.findall(r"(?i)<input\b", html)

    return {
        "title": title,
        "text": _strip_tags(html),
        "headings": headings,
        "links": links,
        "forms": forms,
        "buttons": buttons,
        "input_count": len(inputs),
        "section_bodies": section_bodies,
    }


# ── safety ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TabSafety:
    """Governed verdict for a saved tab, in canonical L13 terms."""

    tier: str  # one of SAFETY_TIERS
    zone: str  # GREEN / YELLOW / RED
    domain_decision: str  # ALLOW / DENY / QUARANTINE (HyperLane)
    content_verdict: str  # CLEAN / CAUTION / SUSPICIOUS / MALICIOUS
    risk_score: float
    reasons: tuple[str, ...]

    @property
    def trusted(self) -> bool:
        """True only when the tab content may be cached as clean context."""
        return self.tier == "ALLOW"

    @property
    def content_withheld(self) -> bool:
        """True when section bodies must not be served (denied tab)."""
        return self.tier == "DENY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "zone": self.zone,
            "domain_decision": self.domain_decision,
            "content_verdict": self.content_verdict,
            "risk_score": self.risk_score,
            "reasons": list(self.reasons),
        }


def assess_tab_safety(
    url: str,
    text: str,
    *,
    hyperlane: HyperLanePy | None = None,
    agent_id: str = "KO",
    scan: ThreatScan | None = None,
) -> TabSafety:
    """Combine domain reputation and content threat scan into one L13 tier.

    Args:
        url: The tab's URL (drives domain-reputation zoning).
        text: The page's visible text (drives the content threat scan).
        hyperlane: Optional shared :class:`HyperLanePy`; one is created if omitted.
        agent_id: Agent identity passed to the lane evaluator.
        scan: Optional pre-computed :class:`ThreatScan` (avoids re-scanning).

    Returns:
        A :class:`TabSafety` whose ``tier`` is the most severe of the domain and
        content signals. Unknown domains (RED) and any malware/prompt-injection
        signal push a page out of ALLOW so it is never cached as clean context.
    """
    lane = (hyperlane or HyperLanePy()).evaluate(url, action="read", agent_id=agent_id)
    threat = scan if scan is not None else scan_text_for_threats(text)

    reasons: list[str] = []
    tier = "ALLOW"

    # Domain reputation.
    if lane.decision == Decision.DENY:
        tier = _escalate(tier, "DENY")
        reasons.append(f"domain DENY: {lane.reason}")
    elif lane.zone == Zone.RED:
        tier = _escalate(tier, "QUARANTINE")
        reasons.append("unknown/RED-zone domain")
    elif lane.decision == Decision.QUARANTINE:
        tier = _escalate(tier, "QUARANTINE")
        reasons.append(f"domain QUARANTINE: {lane.reason}")

    # Content threat scan.
    content_map = {"MALICIOUS": "DENY", "SUSPICIOUS": "ESCALATE", "CAUTION": "QUARANTINE"}
    if threat.verdict in content_map:
        tier = _escalate(tier, content_map[threat.verdict])
        reasons.append(f"content {threat.verdict} (risk={threat.risk_score})")
    if threat.prompt_hits:
        # Prompt injection against the agent is treated as escalation regardless of score.
        tier = _escalate(tier, "ESCALATE")
        reasons.append(f"prompt-injection signatures={len(threat.prompt_hits)}")

    # RED-zone pages with *any* content concern jump to ESCALATE.
    if lane.zone == Zone.RED and threat.verdict != "CLEAN":
        tier = _escalate(tier, "ESCALATE")

    if not reasons:
        reasons.append("clean profile, trusted domain")

    return TabSafety(
        tier=tier,
        zone=lane.zone.value if isinstance(lane.zone, Zone) else str(lane.zone),
        domain_decision=(lane.decision.value if isinstance(lane.decision, Decision) else str(lane.decision)),
        content_verdict=threat.verdict,
        risk_score=threat.risk_score,
        reasons=tuple(reasons),
    )


# ── manifest ─────────────────────────────────────────────────────────────────


@dataclass
class TabManifest:
    """Compact, governed digest of a saved tab — the agent's cheap context handle."""

    tab_id: str
    url: str
    title: str
    outline: list[str]
    counts: dict[str, int]
    topics: list[str]
    intent: str
    summary: str
    safety: TabSafety
    fetched_at: float
    section_count: int = 0
    token_estimate: int = 0
    _sections: dict[str, str] = field(default_factory=dict, repr=False)

    def to_context_dict(self) -> dict[str, Any]:
        """The small dict an agent holds in context (no section bodies)."""
        return {
            "tab_id": self.tab_id,
            "url": self.url,
            "title": self.title,
            "outline": self.outline,
            "counts": self.counts,
            "topics": self.topics,
            "intent": self.intent,
            "summary": self.summary,
            "safety": self.safety.to_dict(),
            "fetched_at": self.fetched_at,
            "section_count": self.section_count,
        }


def build_tab_manifest(
    url: str,
    html: str,
    *,
    fetched_at: float,
    tab_id: str | None = None,
    hyperlane: HyperLanePy | None = None,
    agent_id: str = "KO",
    analyzer: PageAnalyzer | None = None,
) -> TabManifest:
    """Build a governed :class:`TabManifest` from a URL and its HTML.

    Reuses :class:`PageAnalyzer` for structure and :func:`assess_tab_safety` for the
    L13 verdict. If the verdict is DENY, the section bodies are dropped (the manifest
    records the block but withholds the malicious content).
    """
    parts = _parse_html(html)
    analyzer = analyzer or PageAnalyzer()
    analysis = analyzer.analyze_sync(
        url=url,
        title=parts["title"],
        text=parts["text"],
        headings=parts["headings"],
        links=parts["links"],
        forms=parts["forms"],
        buttons=parts["buttons"],
    )
    safety = assess_tab_safety(url, parts["text"], hyperlane=hyperlane, agent_id=agent_id)

    sections = {} if safety.content_withheld else dict(parts["section_bodies"])
    outline = [h["text"] for h in parts["headings"]][:40]
    counts = {
        "headings": analysis["heading_count"],
        "links": analysis["link_count"],
        "forms": analysis["form_count"],
        "inputs": parts["input_count"],
        "words": analysis["word_count"],
    }
    manifest = TabManifest(
        tab_id=tab_id or _derive_tab_id(url, fetched_at),
        url=url,
        title=parts["title"],
        outline=outline,
        counts=counts,
        topics=analysis["topics"],
        intent=analysis["intent"],
        summary=analysis["summary"][:600],
        safety=safety,
        fetched_at=fetched_at,
        section_count=len(sections),
        _sections=sections,
    )
    manifest.token_estimate = len(json.dumps(manifest.to_context_dict(), ensure_ascii=False)) // 4
    return manifest


def _derive_tab_id(url: str, fetched_at: float) -> str:
    host = (urlparse(url).hostname or "tab").replace(".", "-")
    return f"tab_{host}_{int(fetched_at)}"


# ── store ────────────────────────────────────────────────────────────────────


class TabStore:
    """Holds saved tabs as governed manifests; serves section bodies on demand.

    The agent calls :meth:`list_tabs` to see *what is available* (cheap manifests)
    and :meth:`read_section` to pull *one* section body only when needed. Denied tabs
    expose no content; quarantined/escalated tabs require ``allow_untrusted=True`` to
    read, so untrusted content can't leak into context by accident.
    """

    def __init__(self, hyperlane: HyperLanePy | None = None, *, trust_reference: bool = True) -> None:
        if hyperlane is not None:
            self.hyperlane = hyperlane
        elif trust_reference:
            self.hyperlane = build_research_hyperlane()
        else:
            self.hyperlane = HyperLanePy()
        self._tabs: dict[str, TabManifest] = {}

    def save(self, url: str, html: str, *, fetched_at: float, tab_id: str | None = None) -> TabManifest:
        manifest = build_tab_manifest(url, html, fetched_at=fetched_at, tab_id=tab_id, hyperlane=self.hyperlane)
        self._tabs[manifest.tab_id] = manifest
        return manifest

    def list_tabs(self) -> list[dict[str, Any]]:
        """Compact context handles for every saved tab (no section bodies)."""
        return [m.to_context_dict() for m in self._tabs.values()]

    def get(self, tab_id: str) -> TabManifest | None:
        return self._tabs.get(tab_id)

    def read_section(self, tab_id: str, heading: str, *, allow_untrusted: bool = False) -> dict[str, Any]:
        """Return one section body, gated by the tab's L13 safety tier."""
        manifest = self._tabs.get(tab_id)
        if manifest is None:
            return {"ok": False, "error": f"unknown tab: {tab_id}"}
        if manifest.safety.content_withheld:
            return {
                "ok": False,
                "error": "content withheld: tab denied by governance",
                "safety": manifest.safety.to_dict(),
            }
        if not manifest.safety.trusted and not allow_untrusted:
            return {
                "ok": False,
                "error": f"untrusted tab ({manifest.safety.tier}); pass allow_untrusted=True to read",
                "safety": manifest.safety.to_dict(),
            }
        body = manifest._sections.get(heading)
        if body is None:
            # Tolerate near-matches (case-insensitive, prefix) before giving up.
            low = heading.lower()
            for key, value in manifest._sections.items():
                if key.lower() == low or key.lower().startswith(low):
                    body = value
                    break
        if body is None:
            return {"ok": False, "error": f"no section: {heading!r}", "available": list(manifest._sections)}
        return {"ok": True, "tab_id": tab_id, "heading": heading, "body": body, "safety": manifest.safety.to_dict()}
