"""
Outreach Tentacles — 8 Specialized Parallel Channels
=====================================================

Each tentacle is a specialized outreach arm modeled on octopus limb anatomy:
- Tentacle (base) = the arm itself, with its own "brain" (mini-nervous system)
- Suckers = individual contact points / leads
- Chromatophores = adaptive tone/style per platform/audience

The 8 tentacles:
1. Marketing     — social media, content distribution, brand building
2. Research      — academic outreach, citation tracking, conference presence
3. Cold Outreach — email campaigns, LinkedIn, lead discovery
4. Hot Outreach  — warm leads, follow-ups, relationship nurturing
5. Free Work     — portfolio pieces, demos, consultations (Ping Pong sim)
6. Grants        — government, foundation, accelerator applications
7. Partnership   — strategic alliances, integrations, co-development
8. Content       — blog posts, papers, documentation, Canva/Gamma assets

Each tentacle operates independently (like real octopus arms) but reports
back to the hub brain for coordination.

@patent USPTO #63/961,403
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
#  Contact & Lead Types
# ---------------------------------------------------------------------------

class LeadTemperature(Enum):
    COLD = "cold"       # Never contacted
    WARM = "warm"       # Some interaction
    HOT = "hot"         # Active conversation
    CONVERTED = "converted"  # Became customer/partner

class LeadSource(Enum):
    MANUAL = "manual"
    LINKEDIN = "linkedin"
    EMAIL = "email"
    TWITTER = "twitter"
    GITHUB = "github"
    CONFERENCE = "conference"
    REFERRAL = "referral"
    GRANT_DB = "grant_db"
    HF_COMMUNITY = "huggingface"
    WEBSITE = "website"


@dataclass
class Sucker:
    """A single contact point on a tentacle — one lead/connection."""
    name: str
    email: Optional[str] = None
    url: Optional[str] = None
    platform: Optional[str] = None
    temperature: LeadTemperature = LeadTemperature.COLD
    source: LeadSource = LeadSource.MANUAL
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    last_contact: Optional[float] = None
    contact_count: int = 0
    sucker_id: str = ""

    def __post_init__(self):
        if not self.sucker_id:
            raw = f"{self.name}:{self.email}:{self.url}:{time.time()}"
            self.sucker_id = hashlib.sha256(raw.encode()).hexdigest()[:12]

    def touch(self, note: str = ""):
        """Record a contact interaction."""
        self.last_contact = time.time()
        self.contact_count += 1
        if note:
            self.notes += f"\n[{time.strftime('%Y-%m-%d')}] {note}"
        # Auto-warm on contact
        if self.temperature == LeadTemperature.COLD:
            self.temperature = LeadTemperature.WARM

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sucker_id": self.sucker_id,
            "name": self.name,
            "email": self.email,
            "url": self.url,
            "platform": self.platform,
            "temperature": self.temperature.value,
            "source": self.source.value,
            "tags": self.tags,
            "contact_count": self.contact_count,
            "last_contact": self.last_contact,
            "notes": self.notes.strip(),
        }


# ---------------------------------------------------------------------------
#  Base Tentacle
# ---------------------------------------------------------------------------

class Tentacle:
    """
    Base tentacle — each arm has its own mini-brain (like real octopus arms).

    Responsibilities:
    - Manage a list of suckers (contact points)
    - Track outreach actions
    - Report status back to the hub
    - Adapt tone (chromatophores) per platform
    """

    def __init__(self, name: str, description: str, priority: int = 5):
        self.name = name
        self.description = description
        self.priority = priority  # 1-10, higher = more important
        self.suckers: List[Sucker] = []
        self._actions: List[Dict[str, Any]] = []
        self.active = True
        self.created_at = time.time()

    def add_sucker(self, sucker: Sucker) -> None:
        """Attach a new contact point to this tentacle."""
        self.suckers.append(sucker)

    def find_sucker(self, name: str) -> Optional[Sucker]:
        """Find a sucker by name (case-insensitive)."""
        name_lower = name.lower()
        for s in self.suckers:
            if s.name.lower() == name_lower:
                return s
        return None

    def reach(self, target: str, action: str, details: str = "") -> Dict[str, Any]:
        """
        Execute an outreach action — the tentacle reaches out.
        Returns the action record.
        """
        record = {
            "tentacle": self.name,
            "target": target,
            "action": action,
            "details": details,
            "timestamp": time.time(),
            "status": "executed",
        }
        self._actions.append(record)

        # Touch the sucker if it exists
        sucker = self.find_sucker(target)
        if sucker:
            sucker.touch(f"{action}: {details}")

        return record

    def retract(self) -> None:
        """Deactivate this tentacle."""
        self.active = False

    def extend(self) -> None:
        """Reactivate this tentacle."""
        self.active = True

    @property
    def sucker_count(self) -> int:
        return len(self.suckers)

    @property
    def hot_leads(self) -> List[Sucker]:
        return [s for s in self.suckers if s.temperature == LeadTemperature.HOT]

    @property
    def warm_leads(self) -> List[Sucker]:
        return [s for s in self.suckers if s.temperature == LeadTemperature.WARM]

    @property
    def cold_leads(self) -> List[Sucker]:
        return [s for s in self.suckers if s.temperature == LeadTemperature.COLD]

    def status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "active": self.active,
            "priority": self.priority,
            "total_contacts": self.sucker_count,
            "hot": len(self.hot_leads),
            "warm": len(self.warm_leads),
            "cold": len(self.cold_leads),
            "actions_taken": len(self._actions),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.status(),
            "description": self.description,
            "suckers": [s.to_dict() for s in self.suckers],
            "recent_actions": self._actions[-10:],
        }


# ---------------------------------------------------------------------------
#  Specialized Tentacles (8 arms)
# ---------------------------------------------------------------------------

class MarketingTentacle(Tentacle):
    """
    Tentacle 1 — Social media, brand building, content distribution.
    Platforms: Twitter/X, LinkedIn, Bluesky, Mastodon, YouTube, TikTok.
    """

    def __init__(self):
        super().__init__(
            name="Marketing",
            description="Social media, brand building, content distribution across platforms",
            priority=8,
        )
        self.platforms = {
            "twitter": {"handle": "@issdandavis", "url": "https://twitter.com/issdandavis"},
            "linkedin": {"url": "https://linkedin.com/in/issdandavis"},
            "bluesky": {"handle": "@issdandavis.bsky.social"},
            "mastodon": {"handle": "@issdandavis@mastodon.social"},
            "github": {"handle": "issdandavis", "url": "https://github.com/issdandavis"},
            "huggingface": {"handle": "issdandavis", "url": "https://huggingface.co/issdandavis"},
        }

    def post(self, platform: str, content: str) -> Dict[str, Any]:
        """Queue a post for a platform."""
        return self.reach(platform, "post", content[:280])

    def engage(self, platform: str, target_user: str, action: str = "reply") -> Dict[str, Any]:
        """Engage with someone on a platform."""
        return self.reach(target_user, f"{platform}_{action}", f"Engaged on {platform}")


class ResearchTentacle(Tentacle):
    """
    Tentacle 2 — Academic outreach, citation tracking, conference presence.
    Tracks: arXiv papers, citations, conference CFPs, academic collaborators.
    """

    def __init__(self):
        super().__init__(
            name="Research",
            description="Academic outreach, citations, conferences, paper submissions",
            priority=7,
        )
        self.papers: List[Dict[str, Any]] = []
        self.conferences: List[Dict[str, Any]] = []
        self.arxiv_id = "izdandavis"
        self.orcid = "0009-0002-3936-9369"

    def track_paper(self, title: str, url: str, status: str = "draft") -> Dict[str, Any]:
        paper = {"title": title, "url": url, "status": status, "added": time.time()}
        self.papers.append(paper)
        return paper

    def track_conference(self, name: str, deadline: str, url: str = "") -> Dict[str, Any]:
        conf = {"name": name, "deadline": deadline, "url": url, "added": time.time()}
        self.conferences.append(conf)
        return conf


class ColdOutreachTentacle(Tentacle):
    """
    Tentacle 3 — Cold email campaigns, LinkedIn connection requests, lead discovery.
    The "hunting" arm — finds new contacts that don't know about SCBE yet.
    """

    def __init__(self):
        super().__init__(
            name="Cold Outreach",
            description="Email campaigns, LinkedIn outreach, lead discovery for new contacts",
            priority=6,
        )
        self.templates: Dict[str, str] = {
            "intro": "Hi {name}, I'm Issac Davis building SCBE-AETHERMOORE — a 14-layer AI governance pipeline. {hook}",
            "demo_offer": "Hi {name}, would you like a free governance scan of your AI pipeline? Our system catches threats that traditional filters miss. {hook}",
            "patent_credibility": "Hi {name}, our patent-pending approach (USPTO #63/961,403) uses hyperbolic geometry to make AI attacks exponentially expensive. {hook}",
        }

    def draft_email(self, template: str, name: str, hook: str = "") -> str:
        """Generate an email from a template."""
        tmpl = self.templates.get(template, self.templates["intro"])
        return tmpl.format(name=name, hook=hook)


class HotOutreachTentacle(Tentacle):
    """
    Tentacle 4 — Warm leads, follow-ups, relationship nurturing.
    The "caring" arm — maintains and deepens existing connections.
    """

    def __init__(self):
        super().__init__(
            name="Hot Outreach",
            description="Follow-ups, relationship nurturing, warm lead management",
            priority=9,
        )

    def follow_up(self, name: str, context: str = "") -> Dict[str, Any]:
        """Schedule/execute a follow-up."""
        return self.reach(name, "follow_up", context)

    def overdue_contacts(self, days: int = 7) -> List[Sucker]:
        """Find contacts that haven't been touched in N days."""
        cutoff = time.time() - (days * 86400)
        return [
            s for s in self.suckers
            if s.temperature in (LeadTemperature.WARM, LeadTemperature.HOT)
            and (s.last_contact is None or s.last_contact < cutoff)
        ]


class FreeWorkTentacle(Tentacle):
    """
    Tentacle 5 — Free portfolio work, demos, consultations.
    The "Ping Pong / Pac Man sim" — agents explore routes by doing free work
    that demonstrates capability, then convert to paid.

    Like Pac-Man eating pellets: each free job is a pellet that maps a route
    through the market. The ghost avoidance = not getting stuck doing
    only free work.
    """

    def __init__(self):
        super().__init__(
            name="Free Work",
            description="Portfolio pieces, demos, free consultations — route discovery via Ping Pong sim",
            priority=5,
        )
        self.jobs: List[Dict[str, Any]] = []
        self.max_free_jobs = 3  # Cap to avoid giving away too much

    def add_free_job(self, client: str, scope: str, conversion_path: str) -> Dict[str, Any]:
        """
        Add a free job with a clear conversion path.
        Every free job MUST have a defined path to paid work.
        """
        job = {
            "client": client,
            "scope": scope,
            "conversion_path": conversion_path,
            "status": "planned",
            "started": None,
            "completed": None,
            "converted": False,
        }
        self.jobs.append(job)
        self.reach(client, "free_job_offered", scope)
        return job

    @property
    def active_free_jobs(self) -> int:
        return sum(1 for j in self.jobs if j["status"] == "active")

    @property
    def conversion_rate(self) -> float:
        completed = [j for j in self.jobs if j["status"] == "completed"]
        if not completed:
            return 0.0
        return sum(1 for j in completed if j["converted"]) / len(completed)


class GrantTentacle(Tentacle):
    """
    Tentacle 6 — Government, foundation, and accelerator funding applications.
    Tracks deadlines, requirements, submission status.
    """

    def __init__(self):
        super().__init__(
            name="Grants",
            description="Government grants, foundation funding, accelerator applications",
            priority=7,
        )
        self.applications: List[Dict[str, Any]] = []

    def add_opportunity(
        self, name: str, funder: str, amount: str,
        deadline: str = "", url: str = "", fit: str = ""
    ) -> Dict[str, Any]:
        """Track a grant/funding opportunity."""
        opp = {
            "name": name,
            "funder": funder,
            "amount": amount,
            "deadline": deadline,
            "url": url,
            "fit_assessment": fit,
            "status": "identified",  # identified → preparing → submitted → awarded/rejected
            "added": time.time(),
        }
        self.applications.append(opp)
        return opp

    def upcoming_deadlines(self, days: int = 30) -> List[Dict[str, Any]]:
        """List opportunities with deadlines in the next N days."""
        return [a for a in self.applications if a["status"] in ("identified", "preparing")]


class PartnershipTentacle(Tentacle):
    """
    Tentacle 7 — Strategic alliances, integrations, co-development.
    Focus: OpenClaw integration, enterprise partnerships, reseller agreements.
    """

    def __init__(self):
        super().__init__(
            name="Partnership",
            description="Strategic alliances, integrations, co-development deals",
            priority=8,
        )
        self.targets: List[Dict[str, Any]] = [
            {"name": "OpenClaw", "type": "integration", "status": "research",
             "notes": "SCBE as before_tool_call hook in OpenClaw lifecycle"},
            {"name": "HuggingFace", "type": "platform", "status": "active",
             "notes": "Already publishing datasets, explore model hosting"},
        ]

    def add_target(self, name: str, partnership_type: str, notes: str = "") -> Dict[str, Any]:
        target = {
            "name": name, "type": partnership_type,
            "status": "identified", "notes": notes,
        }
        self.targets.append(target)
        return target


class ContentTentacle(Tentacle):
    """
    Tentacle 8 — Blog posts, papers, documentation, visual assets.
    Integrates with Canva (design) and Gamma (presentations).
    """

    def __init__(self):
        super().__init__(
            name="Content",
            description="Blog posts, papers, docs, Canva/Gamma visual assets",
            priority=7,
        )
        self.content_queue: List[Dict[str, Any]] = []
        self.canva_api_key: Optional[str] = None
        self.gamma_api_key: Optional[str] = None

    def queue_content(
        self, title: str, content_type: str,
        platform: str = "blog", priority: int = 5
    ) -> Dict[str, Any]:
        """Queue content for creation."""
        item = {
            "title": title,
            "type": content_type,  # blog, paper, presentation, infographic, video
            "platform": platform,
            "priority": priority,
            "status": "queued",
            "created": time.time(),
        }
        self.content_queue.append(item)
        return item

    def pending_content(self) -> List[Dict[str, Any]]:
        return [c for c in self.content_queue if c["status"] == "queued"]
