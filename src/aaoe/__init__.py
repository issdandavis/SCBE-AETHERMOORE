"""
AAOE — AI Agent Operating Environment
========================================
Governed AI agent platform where agents come to play, create, interact.
Activity generates training data. Drift detection with ephemeral prompts.
Credit economy tied to training value. SCBE governance as the traffic cop.

Modules:
  task_monitor      — Drift detection between declared intent and observed actions
  ephemeral_prompt  — Contextual nudges that realign drifting agents
  agent_identity    — GeoSeal identity, entry tokens, access tiers
"""

from .task_monitor import TaskMonitor, AgentSession, DriftLevel
from .ephemeral_prompt import EphemeralPromptEngine, PromptSeverity, EphemeralNudge
from .agent_identity import GeoSeal, AccessTier, EntryToken, AgentRegistry
from .garganta_manifold import (
    tunnel_radius,
    tunnel_radius_4d,
    fiber_volume,
    freedom_percentage,
    compute_portals,
    compute_temporal_slice,
    simulate_journey,
    WallPortal,
    TemporalSlice,
    JourneyFrame,
)

__all__ = [
    "TaskMonitor",
    "AgentSession",
    "DriftLevel",
    "EphemeralPromptEngine",
    "PromptSeverity",
    "EphemeralNudge",
    "GeoSeal",
    "AccessTier",
    "EntryToken",
    "AgentRegistry",
    "tunnel_radius",
    "tunnel_radius_4d",
    "fiber_volume",
    "freedom_percentage",
    "compute_portals",
    "compute_temporal_slice",
    "simulate_journey",
    "WallPortal",
    "TemporalSlice",
    "JourneyFrame",
]
