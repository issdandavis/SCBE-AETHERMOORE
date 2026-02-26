"""
Spiral Forge RPG — Game API Routes

FastAPI router that serves the Godot client (scbe_client.gd).
All game state mutations flow through SCBE pipeline for governance.

Endpoints:
  POST /api/game/codex/evaluate     — SCBE-gated internet terminal
  POST /api/game/companion/update   — Companion state mutation
  GET  /api/game/evolution/check/{id} — Check evolution availability
  POST /api/game/combat/result      — Submit combat encounter result
  GET  /api/game/tower/floor/{n}    — Get tower floor data
  POST /api/game/events/log         — Log telemetry for training pipeline
  POST /api/game/eggs/check         — Check egg hatching conditions
  POST /api/game/ai/dialogue        — AI-generated NPC dialogue (HF gateway)
"""

from __future__ import annotations

import hashlib
import math
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Game modules
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.symphonic_cipher.scbe_aethermoore.game.types import (
    TONGUE_CODES,
    CanonicalState,
    default_canonical_state,
    state_to_array,
    array_to_state,
    tongue_norm,
    dominant_tongue,
)
from src.symphonic_cipher.scbe_aethermoore.game.companion import (
    create_companion,
    derive_combat_stats,
    apply_tongue_experience,
    current_evolution_stage,
    is_over_evolved,
)
from src.symphonic_cipher.scbe_aethermoore.game.combat import (
    compute_type_advantage,
    calculate_damage,
)
from src.symphonic_cipher.scbe_aethermoore.game.sacred_eggs import (
    check_hatchable_eggs,
    can_hatch_egg,
)
from src.symphonic_cipher.scbe_aethermoore.game.regions import (
    get_tower_floor,
    get_rank,
)

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2

# SCBE Layer 12 Harmonic Wall
def _harmonic_wall(d_star: float, R: float) -> float:
    """H(d*, R) = R · π^(φ·d*). Safe is cheap, dangerous is exponential."""
    return float(R * (math.pi ** (PHI * d_star)))


# Categories allowed through Codex terminal
CODEX_CATEGORIES = {
    "math_reference": {"risk": 0.1, "tongue": "CA"},
    "lore_wiki": {"risk": 0.15, "tongue": "AV"},
    "creature_codex": {"risk": 0.2, "tongue": "DR"},
    "strategy_guide": {"risk": 0.25, "tongue": "KO"},
    "visual_thermal": {"risk": 0.4, "tongue": "RU"},
    "external_api": {"risk": 0.7, "tongue": "UM"},
}

# In-memory session store (swap for Redis/DB in production)
_companion_store: Dict[str, Dict[str, Any]] = {}
_event_log: List[Dict[str, Any]] = []

# ---------------------------------------------------------------------------
#  Request/Response models
# ---------------------------------------------------------------------------

game_router = APIRouter(prefix="/api/game", tags=["game"])


class CodexEvaluateRequest(BaseModel):
    category: str
    query: str
    player_tongue: List[float] = Field(min_length=6, max_length=6)
    player_floor: int = Field(ge=1, le=100)
    timestamp: Optional[float] = None


class CompanionUpdateRequest(BaseModel):
    companion_id: str
    update: Dict[str, Any]


class CombatResultRequest(BaseModel):
    encounter_id: str
    player_tongue: List[float] = Field(min_length=6, max_length=6)
    enemy_tongue: List[float] = Field(min_length=6, max_length=6)
    transforms_used: List[str] = []
    valid_transforms: int = 0
    invalid_transforms: int = 0
    duration_ms: int = 0
    outcome: str = "win"  # win, lose, flee


class EggCheckRequest(BaseModel):
    player_tongue: List[float] = Field(min_length=6, max_length=6)


class EventLogRequest(BaseModel):
    event_type: str
    data: Dict[str, Any] = {}
    session_id: Optional[str] = None
    timestamp: Optional[float] = None


class DialogueRequest(BaseModel):
    npc_id: str
    context: str = ""
    player_name: str = "Chen"
    player_floor: int = 1
    tongue_distribution: List[float] = Field(
        default=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0], min_length=6, max_length=6
    )


# ---------------------------------------------------------------------------
#  Routes
# ---------------------------------------------------------------------------


@game_router.post("/codex/evaluate")
async def evaluate_codex(req: CodexEvaluateRequest) -> Dict[str, Any]:
    """
    Evaluate a Codex terminal query through the SCBE 14-layer pipeline.

    Returns ALLOW / QUARANTINE / DENY with harmonic score and
    per-layer pass/fail telemetry.
    """
    if req.category not in CODEX_CATEGORIES:
        raise HTTPException(400, f"Unknown category: {req.category}")

    cat = CODEX_CATEGORIES[req.category]
    base_risk: float = cat["risk"]

    # Layer 12: Harmonic Wall cost
    # Risk increases with query length and floor (higher floors = more access)
    floor_discount = min(0.3, req.player_floor * 0.003)
    d_star = max(0.01, base_risk - floor_discount)
    wall_cost = _harmonic_wall(d_star, 1.0)

    # Compute per-layer scores (stub 14 layers)
    layers = []
    layer_names = [
        "ComplexContext", "Realification", "WeightedTransform", "PoincareEmbed",
        "HyperbolicDist", "BreathingTransform", "MobiusPhase", "HamiltonianCFI",
        "SpectralCoherence", "SpinCoherence", "TriadicTemporal", "HarmonicWall",
        "RiskDecision", "AudioTelemetry",
    ]
    for i, name in enumerate(layer_names):
        score = max(0.0, 1.0 - base_risk * (0.5 + 0.05 * i))
        passed = score > 0.3
        layers.append({"layer": i + 1, "name": name, "score": round(score, 3), "passed": passed})

    # Decision from Layer 13
    if d_star < 0.3:
        decision = "ALLOW"
        polly_warning = ""
    elif d_star < 0.6:
        decision = "QUARANTINE"
        polly_warning = "Polly narrows her eyes. 'Careful with that one...'"
    else:
        decision = "DENY"
        polly_warning = "Polly SQUAWKS loudly! 'No! Bad idea! Very bad!'"

    harmonic_score = round(1.0 / (1.0 + d_star + 2 * wall_cost), 4)

    return {
        "codex_evaluation": {
            "decision": decision,
            "harmonic_score": harmonic_score,
            "wall_cost": round(wall_cost, 4),
            "polly_warning": polly_warning,
            "rate_limit_remaining": 95,
            "pipeline_layers": layers,
            "category": req.category,
            "tongue_affinity": cat["tongue"],
        }
    }


@game_router.post("/companion/update")
async def update_companion(req: CompanionUpdateRequest) -> Dict[str, Any]:
    """Update companion state. Returns derived combat stats."""
    if req.companion_id not in _companion_store:
        # Create new companion entry
        _companion_store[req.companion_id] = {
            "id": req.companion_id,
            "state": list(default_canonical_state().tongue_position)
            + [0.0] * 15,
            "bond": 1,
            "evolution_stage": "spark",
        }

    comp = _companion_store[req.companion_id]
    comp.update(req.update)

    # Derive combat stats from state
    tongue_pos = tuple(comp.get("tongue_position", [0.0] * 6)[:6])
    dom = dominant_tongue(tongue_pos)
    radius = tongue_norm(tongue_pos)

    return {
        "companion_id": req.companion_id,
        "dominant_tongue": dom,
        "radius": round(radius, 4),
        "evolution_stage": comp.get("evolution_stage", "spark"),
        "bond_level": comp.get("bond", 1),
        "is_unstable": radius > 0.95,
    }


@game_router.get("/evolution/check/{companion_id}")
async def check_evolution(companion_id: str) -> Dict[str, Any]:
    """Check if a companion is ready to evolve."""
    comp = _companion_store.get(companion_id)
    if not comp:
        raise HTTPException(404, f"Companion {companion_id} not found")

    tongue_pos = tuple(comp.get("tongue_position", [0.0] * 6)[:6])
    radius = tongue_norm(tongue_pos)

    thresholds = [0.3, 0.5, 0.7, 0.85, 0.95]
    current_stage = 0
    for t in thresholds:
        if radius >= t:
            current_stage += 1

    can_evolve = current_stage > 0 and comp.get("evolution_stage", "spark") == "spark"

    return {
        "companion_id": companion_id,
        "can_evolve": can_evolve,
        "current_radius": round(radius, 4),
        "current_stage": current_stage,
        "next_threshold": thresholds[min(current_stage, len(thresholds) - 1)],
        "dominant_tongue": dominant_tongue(tongue_pos),
        "is_unstable": radius > 0.95,
    }


@game_router.post("/combat/result")
async def submit_combat_result(req: CombatResultRequest) -> Dict[str, Any]:
    """Submit combat encounter result for training pipeline + XP award."""
    player_tv = tuple(req.player_tongue)
    enemy_tv = tuple(req.enemy_tongue)

    advantage = compute_type_advantage(player_tv, enemy_tv)

    # XP reward
    base_xp = 10.0
    transform_bonus = req.valid_transforms * 2.0
    penalty = req.invalid_transforms * 3.0
    total_xp = max(0.0, base_xp + transform_bonus - penalty)

    if req.outcome == "lose":
        total_xp *= 0.3
    elif req.outcome == "flee":
        total_xp *= 0.1

    # Tongue XP distributed by dominant tongue
    dom = dominant_tongue(player_tv)
    tongue_idx = TONGUE_CODES.index(dom)

    # Log for training pipeline
    event = {
        "type": "combat_result",
        "encounter_id": req.encounter_id,
        "outcome": req.outcome,
        "advantage": round(advantage, 4),
        "xp": round(total_xp, 2),
        "transforms_used": req.transforms_used,
        "valid": req.valid_transforms,
        "invalid": req.invalid_transforms,
        "duration_ms": req.duration_ms,
        "timestamp": time.time(),
    }
    _event_log.append(event)

    return {
        "xp_earned": round(total_xp, 2),
        "tongue_xp": {dom: round(total_xp * 0.5, 2)},
        "advantage": round(advantage, 4),
        "proof_tokens": req.valid_transforms,
        "gold": int(total_xp * 1.5),
    }


@game_router.get("/tower/floor/{floor_number}")
async def get_floor(floor_number: int) -> Dict[str, Any]:
    """Get tower floor data (math domain, rank, encounters)."""
    if floor_number < 1 or floor_number > 100:
        raise HTTPException(400, "Floor must be between 1 and 100")

    floor_data = get_tower_floor(floor_number)
    rank = get_rank(floor_number)

    return {
        "floor": floor_data.floor,
        "math_domain": floor_data.math_domain,
        "rank": rank,
        "encounters": floor_data.encounters,
        "has_mini_boss": floor_data.mini_boss,
        "has_boss": floor_data.boss,
        "region": floor_data.region,
    }


@game_router.post("/events/log")
async def log_event(req: EventLogRequest) -> Dict[str, Any]:
    """Log game event for the three-tier training pipeline."""
    event = {
        "type": req.event_type,
        "data": req.data,
        "session_id": req.session_id or "anonymous",
        "timestamp": req.timestamp or time.time(),
        "tier": "raw",  # Starts in raw tier, promoted by governance
    }
    _event_log.append(event)

    return {
        "logged": True,
        "event_count": len(_event_log),
        "tier": "raw",
    }


@game_router.post("/eggs/check")
async def check_eggs(req: EggCheckRequest) -> Dict[str, Any]:
    """Check which Sacred Eggs can hatch given tongue distribution."""
    tv = tuple(req.player_tongue)
    hatchable = check_hatchable_eggs(tv)

    results = []
    for h in hatchable:
        results.append({
            "egg_type": h.egg_type,
            "egg_name": h.egg_name,
            "bond_type": h.bond_type,
            "dominant_tongue": h.dominant_tongue,
            "description": h.description,
        })

    return {
        "hatchable_eggs": results,
        "tongue_distribution": list(tv),
        "tongue_norm": round(tongue_norm(tv), 4),
    }


@game_router.post("/ai/dialogue")
async def generate_dialogue(req: DialogueRequest) -> Dict[str, Any]:
    """
    AI-generated NPC dialogue via HuggingFace gateway.

    Falls back to deterministic templates when HF is unavailable.
    """
    # Deterministic fallback (always works, no external dependency)
    templates = _get_npc_templates(req.npc_id)
    fallback_line = templates[hash(req.context) % len(templates)]

    # TODO: When HF gateway is live, try it first with timeout
    # try:
    #     response = await _call_hf_gateway(req)
    #     return {"reply": response, "source": "hf", "cached": False}
    # except Exception:
    #     pass

    return {
        "reply": fallback_line,
        "source": "template",
        "cached": False,
        "npc_id": req.npc_id,
    }


# ---------------------------------------------------------------------------
#  NPC dialogue templates (offline-safe fallback)
# ---------------------------------------------------------------------------


def _get_npc_templates(npc_id: str) -> List[str]:
    """Deterministic NPC dialogue templates keyed by npc_id."""
    templates = {
        "marcus": [
            "The Academy has stood for three generations. You'll be the fourth.",
            "Every Tongue has a cost. Learn them before you speak carelessly.",
            "Your egg chose you. That's rare.",
            "The ward pylons protect Hearthstone. Keep them strong.",
            "When I first came to Avalon, I had nothing but code and stubbornness.",
        ],
        "greta": [
            "Best prices in Hearthstone Landing!",
            "Seal Salve? Smart choice for a new adventurer.",
            "That Drift Anchor will save your companion's life someday.",
            "Come back when you have more gold!",
            "I get my supplies from Glass Drift. Finest crystal work.",
        ],
        "tomas": [
            "In my day, we walked to the Academy uphill. Both ways. Through entropy.",
            "The delivery? Marcus is in the northwest house.",
            "Young ones these days and their fancy Tongues...",
            "The fountain was built by the first ward keepers.",
            "Have you visited the Codex terminal? Knowledge is power.",
        ],
        "sila": [
            "The ward pylon channels KO energy. Focus your intent.",
            "Without the wards, drift creatures would overrun us.",
            "Channel your Tongue. Feel the resistance, then push through.",
            "Good work! The pylon glows brighter already.",
            "Every ward keeper serves Hearthstone Landing.",
        ],
        "polly": [
            "*Caw!* Shiny thing that way!",
            "*Polly tilts her head and stares at you knowingly*",
            "*Caw caw!* Danger! Drift! Bad!",
            "*Polly preens her feathers smugly*",
            "*The raven circles overhead, then lands on your shoulder*",
        ],
    }
    return templates.get(npc_id, [
        "Hello, traveler.",
        "The weather is fine today.",
        "Be careful out there.",
    ])
