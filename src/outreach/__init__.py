# Outreach Central Hub — Octopus Architecture
#
# The Octopus: Polly (raven AI) sits on the head. Eight tentacles
# reach out in parallel, each specialized for a different outreach
# domain. The mantle (body) is the governance core. The beak is
# the content filter. The ink sac is the defense mechanism.
#
# Anatomy mapping:
#   Brain (head)   = Strategy engine + Polly AI coordinator
#   Mantle (body)  = Governance core + content pipeline
#   Beak           = Content quality gate (L14)
#   Ink sac        = Antivirus membrane (threat defense)
#   8 Tentacles    = Parallel outreach channels
#   Suckers        = Individual contact points on each tentacle
#   Chromatophores = Adaptive tone/style per platform
#
# Patent: USPTO #63/961,403 (Pending)

from .hub import OutreachHub, TentacleType, ContactPoint, OutreachCampaign
from .tentacles import (
    Tentacle,
    MarketingTentacle,
    ResearchTentacle,
    ColdOutreachTentacle,
    HotOutreachTentacle,
    FreeWorkTentacle,
    GrantTentacle,
    PartnershipTentacle,
    ContentTentacle,
)

__all__ = [
    "OutreachHub",
    "TentacleType",
    "ContactPoint",
    "OutreachCampaign",
    "Tentacle",
    "MarketingTentacle",
    "ResearchTentacle",
    "ColdOutreachTentacle",
    "HotOutreachTentacle",
    "FreeWorkTentacle",
    "GrantTentacle",
    "PartnershipTentacle",
    "ContentTentacle",
]
