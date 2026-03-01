"""
Outreach Central Hub — The Octopus Brain
==========================================

The central coordinator that manages all 8 tentacles.
Modeled on octopus neurology:
- 500 million neurons, 2/3 in the arms (tentacles have autonomous control)
- Central brain coordinates strategy, arms execute independently
- Chromatophores adapt appearance per context (platform tone adaptation)

Hub manages:
- Contact database across all tentacles
- Campaign orchestration (multi-tentacle coordinated actions)
- Pipeline routing (which tentacle handles which lead)
- Analytics (conversion rates, response rates, ROI)
- Governance gate (all outreach passes through SCBE content filter)

@patent USPTO #63/961,403
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .tentacles import (
    Tentacle, Sucker, LeadTemperature, LeadSource,
    MarketingTentacle, ResearchTentacle,
    ColdOutreachTentacle, HotOutreachTentacle,
    FreeWorkTentacle, GrantTentacle,
    PartnershipTentacle, ContentTentacle,
)


# ---------------------------------------------------------------------------
#  Types
# ---------------------------------------------------------------------------

class TentacleType(Enum):
    MARKETING = "marketing"
    RESEARCH = "research"
    COLD_OUTREACH = "cold_outreach"
    HOT_OUTREACH = "hot_outreach"
    FREE_WORK = "free_work"
    GRANTS = "grants"
    PARTNERSHIP = "partnership"
    CONTENT = "content"


@dataclass
class ContactPoint:
    """A unified contact across tentacles — one person may appear on multiple arms."""
    name: str
    emails: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)
    platforms: Dict[str, str] = field(default_factory=dict)  # platform → handle/url
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    tentacles: List[str] = field(default_factory=list)  # Which tentacles know this contact
    contact_id: str = ""

    def __post_init__(self):
        if not self.contact_id:
            raw = f"{self.name}:{','.join(self.emails)}:{time.time()}"
            self.contact_id = hashlib.sha256(raw.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contact_id": self.contact_id,
            "name": self.name,
            "emails": self.emails,
            "urls": self.urls,
            "platforms": self.platforms,
            "tags": self.tags,
            "tentacles": self.tentacles,
            "notes": self.notes,
        }


@dataclass
class OutreachCampaign:
    """A coordinated multi-tentacle campaign."""
    name: str
    description: str
    tentacles: List[TentacleType]
    targets: List[str] = field(default_factory=list)  # Contact names or IDs
    status: str = "planned"  # planned → active → paused → completed
    created: float = field(default_factory=time.time)
    campaign_id: str = ""

    def __post_init__(self):
        if not self.campaign_id:
            raw = f"{self.name}:{self.created}"
            self.campaign_id = hashlib.sha256(raw.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "description": self.description,
            "tentacles": [t.value for t in self.tentacles],
            "targets": self.targets,
            "status": self.status,
        }


# ---------------------------------------------------------------------------
#  The Hub (Octopus Brain)
# ---------------------------------------------------------------------------

class OutreachHub:
    """
    Central octopus brain — coordinates all 8 tentacles.

    Octopus anatomy mapping:
    - Brain (this class) = strategy + coordination
    - Mantle = governance core (SCBE pipeline)
    - Beak = quality gate (filters bad content before sending)
    - Ink sac = antivirus membrane (defense against inbound threats)
    - Arms 1-8 = specialized tentacles
    - Suckers = individual contact points
    - Chromatophores = tone adaptation per platform
    """

    def __init__(self, data_dir: Optional[str] = None):
        # Initialize all 8 tentacles
        self.tentacles: Dict[TentacleType, Tentacle] = {
            TentacleType.MARKETING: MarketingTentacle(),
            TentacleType.RESEARCH: ResearchTentacle(),
            TentacleType.COLD_OUTREACH: ColdOutreachTentacle(),
            TentacleType.HOT_OUTREACH: HotOutreachTentacle(),
            TentacleType.FREE_WORK: FreeWorkTentacle(),
            TentacleType.GRANTS: GrantTentacle(),
            TentacleType.PARTNERSHIP: PartnershipTentacle(),
            TentacleType.CONTENT: ContentTentacle(),
        }

        # Unified contact database
        self.contacts: Dict[str, ContactPoint] = {}

        # Campaigns
        self.campaigns: List[OutreachCampaign] = []

        # Key links and emails
        self.identity = {
            "name": "Issac Davis",
            "alias": "MoeShaun",
            "company": "AethermoorGames",
            "patent": "USPTO #63/961,403",
            "github": "https://github.com/issdandavis/SCBE-AETHERMOORE",
            "huggingface": "https://huggingface.co/issdandavis",
            "orcid": "0009-0002-3936-9369",
            "arxiv": "izdandavis",
        }

        # Data persistence
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "artifacts", "outreach"
        )

    # -------------------------------------------------------------------
    #  Contact Management
    # -------------------------------------------------------------------

    def add_contact(self, contact: ContactPoint) -> ContactPoint:
        """Add a unified contact to the hub."""
        self.contacts[contact.contact_id] = contact
        return contact

    def find_contact(self, name: str) -> Optional[ContactPoint]:
        """Find a contact by name."""
        name_lower = name.lower()
        for c in self.contacts.values():
            if c.name.lower() == name_lower:
                return c
        return None

    def route_contact(self, contact: ContactPoint, tentacle_type: TentacleType) -> None:
        """Route a contact to a specific tentacle."""
        tentacle = self.tentacles[tentacle_type]
        sucker = Sucker(
            name=contact.name,
            email=contact.emails[0] if contact.emails else None,
            url=contact.urls[0] if contact.urls else None,
        )
        tentacle.add_sucker(sucker)
        if tentacle_type.value not in contact.tentacles:
            contact.tentacles.append(tentacle_type.value)

    # -------------------------------------------------------------------
    #  Tentacle Access
    # -------------------------------------------------------------------

    def arm(self, tentacle_type: TentacleType) -> Tentacle:
        """Get a specific tentacle by type."""
        return self.tentacles[tentacle_type]

    @property
    def marketing(self) -> MarketingTentacle:
        return self.tentacles[TentacleType.MARKETING]

    @property
    def research(self) -> ResearchTentacle:
        return self.tentacles[TentacleType.RESEARCH]

    @property
    def cold_outreach(self) -> ColdOutreachTentacle:
        return self.tentacles[TentacleType.COLD_OUTREACH]

    @property
    def hot_outreach(self) -> HotOutreachTentacle:
        return self.tentacles[TentacleType.HOT_OUTREACH]

    @property
    def free_work(self) -> FreeWorkTentacle:
        return self.tentacles[TentacleType.FREE_WORK]

    @property
    def grants(self) -> GrantTentacle:
        return self.tentacles[TentacleType.GRANTS]

    @property
    def partnership(self) -> PartnershipTentacle:
        return self.tentacles[TentacleType.PARTNERSHIP]

    @property
    def content(self) -> ContentTentacle:
        return self.tentacles[TentacleType.CONTENT]

    # -------------------------------------------------------------------
    #  Campaigns
    # -------------------------------------------------------------------

    def create_campaign(
        self, name: str, description: str,
        tentacles: List[TentacleType], targets: List[str] = None,
    ) -> OutreachCampaign:
        """Create a multi-tentacle campaign."""
        campaign = OutreachCampaign(
            name=name,
            description=description,
            tentacles=tentacles,
            targets=targets or [],
        )
        self.campaigns.append(campaign)
        return campaign

    # -------------------------------------------------------------------
    #  Analytics / Status
    # -------------------------------------------------------------------

    def diagnostics(self) -> Dict[str, Any]:
        """Full octopus health check — status of all tentacles."""
        tentacle_status = {}
        total_contacts = 0
        total_actions = 0

        for ttype, tentacle in self.tentacles.items():
            status = tentacle.status()
            tentacle_status[ttype.value] = status
            total_contacts += status["total_contacts"]
            total_actions += status["actions_taken"]

        return {
            "brain": "active",
            "tentacles_active": sum(1 for t in self.tentacles.values() if t.active),
            "tentacles_total": len(self.tentacles),
            "total_contacts": total_contacts,
            "unified_contacts": len(self.contacts),
            "total_actions": total_actions,
            "campaigns": len(self.campaigns),
            "campaigns_active": sum(1 for c in self.campaigns if c.status == "active"),
            "tentacle_detail": tentacle_status,
            "identity": self.identity,
        }

    # -------------------------------------------------------------------
    #  Persistence
    # -------------------------------------------------------------------

    def save(self) -> str:
        """Save hub state to disk."""
        os.makedirs(self.data_dir, exist_ok=True)
        path = os.path.join(self.data_dir, "hub_state.json")

        state = {
            "contacts": {cid: c.to_dict() for cid, c in self.contacts.items()},
            "campaigns": [c.to_dict() for c in self.campaigns],
            "tentacles": {t.value: self.tentacles[t].to_dict() for t in TentacleType},
            "identity": self.identity,
            "saved_at": time.time(),
        }

        with open(path, "w") as f:
            json.dump(state, f, indent=2)
        return path

    def load(self) -> bool:
        """Load hub state from disk."""
        path = os.path.join(self.data_dir, "hub_state.json")
        if not os.path.exists(path):
            return False

        with open(path) as f:
            state = json.load(f)

        # Restore contacts
        for cid, cdata in state.get("contacts", {}).items():
            contact = ContactPoint(
                name=cdata["name"],
                emails=cdata.get("emails", []),
                urls=cdata.get("urls", []),
                platforms=cdata.get("platforms", {}),
                tags=cdata.get("tags", []),
                notes=cdata.get("notes", ""),
                tentacles=cdata.get("tentacles", []),
                contact_id=cid,
            )
            self.contacts[cid] = contact

        return True

    # -------------------------------------------------------------------
    #  Seed Data — Pre-populate with known contacts and targets
    # -------------------------------------------------------------------

    def seed_initial_data(self) -> Dict[str, int]:
        """
        Populate the hub with initial contacts, targets, and opportunities.
        Returns counts of what was seeded.
        """
        counts = {"contacts": 0, "grants": 0, "partnerships": 0, "content": 0}

        # --- Key Contacts ---
        sbdc = self.add_contact(ContactPoint(
            name="SharonAnn Hamilton",
            emails=["sharonann.hamilton@wsu.edu"],
            tags=["sbdc", "advisor", "business"],
            notes="Washington SBDC at WSU. Port of Port Angeles (Tue/Wed), WorkSource Sequim (Mon).",
        ))
        self.route_contact(sbdc, TentacleType.HOT_OUTREACH)
        counts["contacts"] += 1

        # --- Grant Opportunities ---
        grant_arm = self.grants
        grant_arm.add_opportunity(
            name="NSF SBIR Phase I",
            funder="National Science Foundation",
            amount="$275,000",
            deadline="Quarterly (Jun, Sep, Dec, Mar)",
            url="https://seedfund.nsf.gov/",
            fit="Strong — AI safety/governance innovation fits NSF's AI research priorities",
        )
        grant_arm.add_opportunity(
            name="NIST AI Safety Institute Collaboration",
            funder="NIST",
            amount="Varies",
            url="https://www.nist.gov/artificial-intelligence/ai-safety-institute",
            fit="Direct alignment — SCBE implements measurable AI governance metrics",
        )
        grant_arm.add_opportunity(
            name="Open Philanthropy AI Safety Grants",
            funder="Open Philanthropy",
            amount="$50K-$500K",
            url="https://www.openphilanthropy.org/focus/transformative-artificial-intelligence/",
            fit="Strong — mathematical AI safety framework with exponential cost model",
        )
        grant_arm.add_opportunity(
            name="Washington SBDC Resources",
            funder="WA State SBDC",
            amount="Free advising + grant navigation",
            url="https://wsbdc.org/",
            fit="Already connected via SharonAnn Hamilton",
        )
        grant_arm.add_opportunity(
            name="DARPA AI Forward",
            funder="DARPA",
            amount="$1M+",
            url="https://www.darpa.mil/",
            fit="High — adversarial AI defense with mathematical guarantees",
        )
        counts["grants"] = len(grant_arm.applications)

        # --- Partnership Targets ---
        partner_arm = self.partnership
        partner_arm.add_target("OpenClaw", "integration",
            "SCBE as before_tool_call hook — 150K+ stars, massive governance gap")
        partner_arm.add_target("HuggingFace", "platform",
            "Already publishing datasets. Explore inference endpoints + model hosting")
        partner_arm.add_target("Anthropic", "integration",
            "SCBE as external governance layer for Claude deployment")
        partner_arm.add_target("n8n", "integration",
            "Already built bridge. Explore marketplace listing")
        counts["partnerships"] = len(partner_arm.targets)

        # --- Content Queue ---
        content_arm = self.content
        content_arm.queue_content(
            "SCBE: Mathematical AI Governance That Costs Attackers Exponentially More",
            "blog", "medium", priority=9,
        )
        content_arm.queue_content(
            "Why Your AI Safety Filter Is a Regex (And Why That's Dangerous)",
            "blog", "linkedin", priority=8,
        )
        content_arm.queue_content(
            "Fibonacci Spiral Verification: Audio Proof of AI Governance",
            "paper", "arxiv", priority=7,
        )
        content_arm.queue_content(
            "SCBE Enterprise One-Pager (Gamma Presentation)",
            "presentation", "gamma", priority=9,
        )
        content_arm.queue_content(
            "Interactive Governance Demo (HuggingFace Space)",
            "demo", "huggingface", priority=10,
        )
        counts["content"] = len(content_arm.content_queue)

        # --- Research Targets ---
        research_arm = self.research
        research_arm.track_paper(
            "SCBE: Hyperbolic AI Governance with Exponential Cost Scaling",
            "draft — Google Docs",
            status="drafting",
        )
        research_arm.track_conference("AAAI 2026", "Sep 2026", "https://aaai.org/")
        research_arm.track_conference("NeurIPS 2026", "May 2026", "https://neurips.cc/")
        research_arm.track_conference("IEEE S&P 2027", "Dec 2026", "https://www.ieee-security.org/")

        return counts
