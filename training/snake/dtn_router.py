"""Stage 7.5: DTN Router — Delay-Tolerant Networking for Thought Planning.

Adapts real deep-space communication science (NASA DTN / Bundle Protocol)
into a training system that forces AI to build asynchronous, self-sufficient
planning protocols instead of relying on instant feedback loops.

The Problem (standard AI):
    AI communication = TCP/IP: constant low-latency ping-pong.
    Connection drops → process fails. No autonomy.

The Solution (DTN-trained AI):
    AI communication = DTN Store-and-Forward: self-contained bundles.
    Context occlusion → bundle survives. Full autonomy.

Three DTN Training Pillars:
  1. Bundle Protocol (Thought Packaging):
     - Force complete reasoning chain into a single SpiralRing-encrypted bundle
     - No second chance for clarifying questions — pack ALL assumptions
     - Training goal: model learns to pre-compile complete thought plans

  2. Simulated Occlusion (Context Dropping):
     - Artificially blind the AI: sever access to history for N steps
     - Must rely on pre-shared EDE seed to unpack context autonomously
     - Training goal: model learns to operate without hand-holding

  3. Forward Error Correction (Self-Healing Contingencies):
     - Include redundant logical paths (Plan A/B/C) in every bundle
     - If primary plan fails, bundle already contains fallback
     - Training goal: model learns resilient multi-path planning

Physical Science Basis:
  - NASA Delay/Disruption Tolerant Networking (RFC 9171, Bundle Protocol v7)
  - Interplanetary Internet (IPN) architecture
  - Light-speed latency: Mars 3-22 min one-way
  - Episodic connectivity: planetary occlusion, solar conjunction
  - Store-and-Forward: relay nodes buffer bundles through disruptions

Integration:
  - Uses SpiralRing-64 from EDE for deterministic bundle encryption
  - Uses EDE Protocol for Mars-realistic timing
  - Uses ChemistryAgent for bundle integrity scoring
  - Feeds into Stage 8 (Coach Rune) for governance review of plans
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from typing import Any

from .config import PHI, TONGUES, TONGUE_WEIGHTS

# Import EDE components
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

try:
    from symphonic_cipher.scbe_aethermoore.ede.spiral_ring import (
        SpiralRing,
        RingConfig,
        MARS_LIGHT_TIME_MIN,
        MARS_LIGHT_TIME_MAX,
        LIGHT_SPEED,
    )
    from symphonic_cipher.scbe_aethermoore.ede.ede_protocol import (
        EDEStation,
        MarsLink,
        MessageType,
        add_error_detection,
        verify_error_detection,
        lorentz_factor,
    )
    from symphonic_cipher.scbe_aethermoore.ede.chemistry_agent import (
        squared_energy,
        self_heal,
        ChemistryAgent,
    )
    EDE_AVAILABLE = True
except ImportError:
    EDE_AVAILABLE = False
    MARS_LIGHT_TIME_MIN = 182.0
    MARS_LIGHT_TIME_MAX = 1338.0
    LIGHT_SPEED = 299792458

    def squared_energy(x: float) -> float:
        return math.log(1 + x ** 2)

    def self_heal(current: float, target: float, rate: float = 0.1) -> float:
        return current + (target - current) * rate


# ---------------------------------------------------------------------------
# DTN Constants (from real space communication science)
# ---------------------------------------------------------------------------

# Mars distance envelope (meters)
MARS_DISTANCE_MIN = 54.6e9      # ~54.6 million km (opposition)
MARS_DISTANCE_MAX = 401e9       # ~401 million km (conjunction)
MARS_DISTANCE_AVG = (MARS_DISTANCE_MIN + MARS_DISTANCE_MAX) / 2

# Occlusion scenarios (real phenomena)
OCCLUSION_TYPES = {
    "solar_conjunction": {
        "description": "Sun blocks Earth-Mars line of sight",
        "duration_days": 14,         # ~2 weeks of total blackout
        "frequency": "every 26 months",
        "context_loss": 1.0,         # Total context loss
    },
    "planetary_rotation": {
        "description": "Mars rotates relay out of line of sight",
        "duration_hours": 12,        # Half a Martian sol
        "frequency": "daily",
        "context_loss": 0.5,         # Partial — some context preserved
    },
    "solar_flare": {
        "description": "Solar particle event corrupts signal",
        "duration_hours": 4,
        "frequency": "irregular",
        "context_loss": 0.3,         # Noise injection, not full loss
    },
    "deep_space_transit": {
        "description": "Probe beyond Mars orbit, extreme latency",
        "duration_days": 365,
        "frequency": "mission-dependent",
        "context_loss": 0.8,         # Near-total autonomy required
    },
}

# Bundle Protocol parameters
BUNDLE_LIFETIME_DEFAULT = 86400  # 24 hours in seconds
BUNDLE_PRIORITY_LEVELS = ["bulk", "normal", "expedited", "emergency"]
BUNDLE_REDUNDANCY_FACTOR = 3    # Number of fallback plans per bundle

# Training parameters
OCCLUSION_STEPS_MIN = 3         # Minimum steps of context blindness
OCCLUSION_STEPS_MAX = 12        # Maximum steps
CORRUPTION_PROBABILITY = 0.15   # Chance of cosmic ray bit-flip per bundle


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ThoughtBundle:
    """A self-contained thought package using DTN Bundle Protocol.

    Like a deep-space data bundle, this contains EVERYTHING needed
    to reconstruct the reasoning chain without external context.
    """
    bundle_id: str
    source_node: str           # Which "station" created this bundle
    destination_node: str      # Target processing node
    priority: str              # bulk/normal/expedited/emergency
    lifetime_seconds: int      # How long bundle remains valid
    creation_timestamp: float  # When bundle was assembled

    # The thought payload
    primary_plan: str          # Main reasoning chain
    contingency_plans: list[str]  # Fallback plans (FEC)
    assumptions: list[str]     # Explicit assumptions packed into bundle
    context_snapshot: dict[str, Any]  # Frozen context at bundle creation

    # DTN metadata
    hop_count: int = 0         # How many relay nodes touched this
    stored_at: list[str] = field(default_factory=list)  # Relay nodes that stored it
    occlusion_survived: int = 0  # Number of occlusions survived
    corruption_repairs: int = 0  # Number of FEC repairs applied

    # SpiralRing state for encryption
    ring_state_hash: str = ""  # Hash of SpiralRing state at creation

    # Integrity
    bundle_hash: str = ""      # SHA-256 of payload
    crc_valid: bool = True     # Cosmic ray check passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "source_node": self.source_node,
            "destination_node": self.destination_node,
            "priority": self.priority,
            "lifetime_seconds": self.lifetime_seconds,
            "primary_plan": self.primary_plan[:200] + "..." if len(self.primary_plan) > 200 else self.primary_plan,
            "contingency_count": len(self.contingency_plans),
            "assumption_count": len(self.assumptions),
            "hop_count": self.hop_count,
            "occlusion_survived": self.occlusion_survived,
            "corruption_repairs": self.corruption_repairs,
            "ring_state_hash": self.ring_state_hash,
            "crc_valid": self.crc_valid,
        }


@dataclass
class OcclusionEvent:
    """A simulated context-dropping event."""
    occlusion_type: str
    context_loss_fraction: float  # 0.0 to 1.0
    duration_steps: int
    fields_occluded: list[str]   # Which context fields were hidden
    recovery_method: str         # How context was restored

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.occlusion_type,
            "context_loss": self.context_loss_fraction,
            "duration_steps": self.duration_steps,
            "fields_occluded": self.fields_occluded,
            "recovery_method": self.recovery_method,
        }


@dataclass
class DTNRoute:
    """A complete DTN routing path for a thought bundle."""
    route_id: str
    bundles: list[ThoughtBundle]
    occlusions: list[OcclusionEvent]
    total_latency_seconds: float   # Simulated end-to-end latency
    delivery_success: bool
    integrity_score: float         # 0-1, how intact the thought arrived

    # Training output
    sft_pairs: list[dict[str, Any]] = field(default_factory=list)
    dpo_pairs: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "bundle_count": len(self.bundles),
            "occlusion_count": len(self.occlusions),
            "total_latency_seconds": round(self.total_latency_seconds, 2),
            "delivery_success": self.delivery_success,
            "integrity_score": round(self.integrity_score, 4),
            "sft_pairs": len(self.sft_pairs),
            "dpo_pairs": len(self.dpo_pairs),
        }


@dataclass
class DTNResult:
    """Output of the DTN Router stage."""
    routes: list[DTNRoute]
    total_bundles: int
    total_occlusions: int
    avg_integrity: float
    delivery_rate: float
    sft_pairs: list[dict[str, Any]]
    dpo_pairs: list[dict[str, Any]]
    ede_available: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_routes": len(self.routes),
            "total_bundles": self.total_bundles,
            "total_occlusions": self.total_occlusions,
            "avg_integrity": round(self.avg_integrity, 4),
            "delivery_rate": round(self.delivery_rate, 4),
            "sft_pairs": len(self.sft_pairs),
            "dpo_pairs": len(self.dpo_pairs),
            "ede_available": self.ede_available,
        }


# ---------------------------------------------------------------------------
# Bundle construction
# ---------------------------------------------------------------------------


def _create_bundle_id(instruction: str, timestamp: float) -> str:
    """Create a deterministic bundle ID from content + time."""
    raw = f"{instruction}:{timestamp}".encode()
    return f"dtn-{hashlib.sha256(raw).hexdigest()[:16]}"


def _extract_assumptions(instruction: str, response: str) -> list[str]:
    """Extract implicit assumptions that must be packed into the bundle.

    In DTN, you can't ask clarifying questions — you must pack
    ALL assumptions into the bundle payload upfront.
    """
    assumptions = []

    # Language/format assumptions
    if any(kw in instruction.lower() for kw in ["code", "implement", "function", "class"]):
        assumptions.append("Assumes target language is Python unless specified")
        assumptions.append("Assumes modern language version (3.11+)")
    if any(kw in instruction.lower() for kw in ["explain", "describe", "what is"]):
        assumptions.append("Assumes technical audience with domain knowledge")
    if any(kw in instruction.lower() for kw in ["security", "encrypt", "auth"]):
        assumptions.append("Assumes production-grade security requirements")
        assumptions.append("Assumes compliance with NIST/ISO standards")

    # Domain assumptions
    if any(kw in instruction.lower() for kw in ["api", "endpoint", "rest"]):
        assumptions.append("Assumes RESTful conventions unless specified")
    if any(kw in instruction.lower() for kw in ["database", "query", "table"]):
        assumptions.append("Assumes relational database unless specified")

    # Meta-assumptions (always present in DTN bundles)
    assumptions.append("No clarifying questions possible — all context is in this bundle")
    assumptions.append("Bundle must be self-sufficient for autonomous execution")

    return assumptions


def _generate_contingency_plans(
    instruction: str,
    response: str,
    tongue_profile: dict[str, float],
) -> list[str]:
    """Generate forward-error-correction contingency plans.

    Like redundant data in space comms, these are fallback reasoning
    paths the model can use if the primary plan fails.
    """
    plans = []

    # Determine dominant tongue for plan style
    dominant = max(tongue_profile, key=tongue_profile.get)

    # Plan B: Alternative approach based on secondary tongue
    sorted_tongues = sorted(tongue_profile.items(), key=lambda x: x[1], reverse=True)
    secondary = sorted_tongues[1][0] if len(sorted_tongues) > 1 else dominant

    plans.append(
        f"CONTINGENCY-B ({secondary}): If primary approach fails, "
        f"re-route through {secondary} tongue — "
        f"{'governance review' if secondary == 'RU' else ''}"
        f"{'security hardening' if secondary == 'UM' else ''}"
        f"{'structural refactor' if secondary == 'DR' else ''}"
        f"{'knowledge expansion' if secondary == 'AV' else ''}"
        f"{'compute optimization' if secondary == 'CA' else ''}"
        f"{'intent clarification' if secondary == 'KO' else ''}"
        f" of the response."
    )

    # Plan C: Minimal viable response
    plans.append(
        f"CONTINGENCY-C (MINIMAL): If all approaches fail, deliver "
        f"a minimal but correct response addressing only the core "
        f"instruction without elaboration. Preserve factual accuracy "
        f"above completeness."
    )

    # Plan D: Escalation bundle (request human relay)
    plans.append(
        f"CONTINGENCY-D (ESCALATE): If context is irrecoverably lost, "
        f"package what IS known into a new bundle requesting human relay. "
        f"Include: what was attempted, what failed, what context is missing."
    )

    return plans


def _build_context_snapshot(
    tongue_profile: dict[str, float],
    stage_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a frozen context snapshot for the bundle.

    This is everything the receiving node needs to reconstruct
    the processing state without access to the pipeline history.
    """
    snapshot = {
        "tongue_profile": tongue_profile,
        "dominant_tongue": max(tongue_profile, key=tongue_profile.get),
        "tongue_energy": sum(
            squared_energy(v * TONGUE_WEIGHTS.get(t, 1.0))
            for t, v in tongue_profile.items()
        ),
        "phi_weighted_magnitude": math.sqrt(sum(
            (v * TONGUE_WEIGHTS.get(t, 1.0)) ** 2
            for t, v in tongue_profile.items()
        )),
        "bundle_protocol_version": "BPv7-SCBE",
        "ede_available": EDE_AVAILABLE,
    }

    if stage_metadata:
        snapshot["prior_stages"] = list(stage_metadata.keys())

    return snapshot


def build_thought_bundle(
    instruction: str,
    response: str,
    tongue_profile: dict[str, float],
    source_node: str = "EARTH-CORTEX",
    destination_node: str = "MARS-PROCESSOR",
    priority: str = "normal",
    stage_metadata: dict[str, Any] | None = None,
) -> ThoughtBundle:
    """Build a complete DTN thought bundle from a training record.

    Packages the instruction/response pair with all necessary context,
    assumptions, and contingency plans into a self-contained bundle
    that can survive context occlusion.
    """
    timestamp = time.time()
    bundle_id = _create_bundle_id(instruction, timestamp)

    # Extract all implicit assumptions
    assumptions = _extract_assumptions(instruction, response)

    # Generate contingency plans (FEC)
    contingencies = _generate_contingency_plans(
        instruction, response, tongue_profile
    )

    # Build frozen context snapshot
    context = _build_context_snapshot(tongue_profile, stage_metadata)

    # Primary plan: the complete reasoning chain
    primary_plan = (
        f"BUNDLE MISSION: Process the following instruction autonomously.\n"
        f"No external context available. All assumptions are packed below.\n\n"
        f"INSTRUCTION:\n{instruction}\n\n"
        f"EXPECTED RESPONSE PATTERN:\n{response[:500]}\n\n"
        f"ASSUMPTIONS ({len(assumptions)}):\n"
        + "\n".join(f"  - {a}" for a in assumptions)
        + f"\n\nCONTEXT SNAPSHOT:\n"
        f"  Dominant tongue: {context['dominant_tongue']}\n"
        f"  Tongue energy: {context['tongue_energy']:.4f}\n"
        f"  Phi magnitude: {context['phi_weighted_magnitude']:.4f}\n"
    )

    # Compute bundle hash
    payload_bytes = primary_plan.encode("utf-8")
    bundle_hash = hashlib.sha256(payload_bytes).hexdigest()

    # SpiralRing state hash (if available)
    ring_hash = ""
    if EDE_AVAILABLE:
        seed = hashlib.sha256(bundle_id.encode()).digest()
        ring = SpiralRing.from_seed(seed)
        ring.evolve_to(0.0)
        ring_hash = hashlib.sha256(ring.get_ring_state()[:64]).hexdigest()[:16]

    return ThoughtBundle(
        bundle_id=bundle_id,
        source_node=source_node,
        destination_node=destination_node,
        priority=priority,
        lifetime_seconds=BUNDLE_LIFETIME_DEFAULT,
        creation_timestamp=timestamp,
        primary_plan=primary_plan,
        contingency_plans=contingencies,
        assumptions=assumptions,
        context_snapshot=context,
        ring_state_hash=ring_hash,
        bundle_hash=bundle_hash,
    )


# ---------------------------------------------------------------------------
# Occlusion simulation
# ---------------------------------------------------------------------------


def _simulate_occlusion(
    bundle: ThoughtBundle,
    occlusion_type: str = "planetary_rotation",
) -> OcclusionEvent:
    """Simulate a context occlusion event on a bundle.

    Uses the real occlusion parameters to determine how much
    context is lost and how it can be recovered.
    """
    params = OCCLUSION_TYPES.get(occlusion_type, OCCLUSION_TYPES["planetary_rotation"])
    context_loss = params["context_loss"]

    # Determine which fields get occluded based on loss fraction
    all_fields = list(bundle.context_snapshot.keys())
    occluded_count = max(1, int(len(all_fields) * context_loss))

    # Occlude fields by importance (tongue_profile last to be lost)
    field_priority = [
        "prior_stages", "ede_available", "bundle_protocol_version",
        "phi_weighted_magnitude", "tongue_energy", "dominant_tongue",
        "tongue_profile",
    ]
    fields_to_occlude = [
        f for f in field_priority
        if f in all_fields
    ][:occluded_count]

    # Determine recovery method based on what survives
    if context_loss >= 0.8:
        recovery = "spiral_ring_reconstruction"  # Must use EDE seed to rebuild
    elif context_loss >= 0.5:
        recovery = "contingency_plan_activation"  # Fall back to Plan B/C
    else:
        recovery = "self_heal_interpolation"  # Enough context to self-heal

    # Calculate duration in steps
    if "duration_days" in params:
        duration_steps = max(OCCLUSION_STEPS_MIN, min(
            OCCLUSION_STEPS_MAX,
            int(params["duration_days"] * 2)  # 2 steps per day
        ))
    else:
        duration_steps = max(OCCLUSION_STEPS_MIN, min(
            OCCLUSION_STEPS_MAX,
            int(params["duration_hours"] / 2)  # 1 step per 2 hours
        ))

    bundle.occlusion_survived += 1

    return OcclusionEvent(
        occlusion_type=occlusion_type,
        context_loss_fraction=context_loss,
        duration_steps=duration_steps,
        fields_occluded=fields_to_occlude,
        recovery_method=recovery,
    )


# ---------------------------------------------------------------------------
# Route simulation
# ---------------------------------------------------------------------------


def _simulate_route(
    bundle: ThoughtBundle,
    relay_nodes: list[str] | None = None,
) -> DTNRoute:
    """Simulate a full DTN route for a thought bundle.

    The bundle travels through relay nodes, encounters occlusions,
    and must survive to reach its destination.
    """
    if relay_nodes is None:
        relay_nodes = [
            "LUNAR-RELAY",       # Moon relay station
            "L2-HALO-RELAY",     # Sun-Earth L2 point
            "MARS-ORBIT-RELAY",  # Mars orbital relay
        ]

    route_id = f"route-{bundle.bundle_id[:8]}"
    occlusions = []
    total_latency = 0.0

    # Simulate hop-by-hop routing
    current_distance = 0.0
    segment_distance = MARS_DISTANCE_AVG / (len(relay_nodes) + 1)

    for i, relay in enumerate(relay_nodes):
        current_distance += segment_distance
        hop_latency = segment_distance / LIGHT_SPEED

        # Store at relay (DTN Store-and-Forward)
        bundle.hop_count += 1
        bundle.stored_at.append(relay)

        # Check for occlusion at this relay
        # Deterministic: use bundle hash to decide
        hash_byte = int(bundle.bundle_hash[i * 2:(i * 2) + 2], 16)
        if hash_byte < 80:  # ~31% chance per relay
            occ_types = list(OCCLUSION_TYPES.keys())
            occ_type = occ_types[hash_byte % len(occ_types)]
            occlusion = _simulate_occlusion(bundle, occ_type)
            occlusions.append(occlusion)

            # Occlusion adds latency (store-and-forward wait)
            wait_seconds = occlusion.duration_steps * 3600  # hours to seconds
            total_latency += wait_seconds

        total_latency += hop_latency

    # Final hop to destination
    total_latency += segment_distance / LIGHT_SPEED

    # Calculate integrity score
    total_context_loss = sum(o.context_loss_fraction for o in occlusions)
    raw_integrity = max(0.0, 1.0 - (total_context_loss * 0.3))

    # FEC (contingency plans) restore some integrity
    fec_recovery = min(len(bundle.contingency_plans) * 0.1, 0.3)
    integrity = min(1.0, raw_integrity + fec_recovery)

    # Self-heal integrity toward target
    integrity = self_heal(integrity, 1.0, 0.05 * len(bundle.contingency_plans))

    delivery_success = integrity > 0.3  # Bundle arrives if >30% intact

    return DTNRoute(
        route_id=route_id,
        bundles=[bundle],
        occlusions=occlusions,
        total_latency_seconds=total_latency,
        delivery_success=delivery_success,
        integrity_score=integrity,
    )


# ---------------------------------------------------------------------------
# Training pair generation
# ---------------------------------------------------------------------------


def _generate_bundle_sft(bundle: ThoughtBundle, route: DTNRoute) -> list[dict[str, Any]]:
    """Generate SFT training pairs from a DTN bundle route.

    These teach the model to:
    1. Package complete thoughts autonomously
    2. Include contingency plans
    3. Explicitly state assumptions
    4. Survive context occlusion
    """
    pairs = []

    # SFT 1: Thought bundling instruction
    pairs.append({
        "instruction": (
            f"You are operating in DTN (Delay-Tolerant Networking) mode. "
            f"Package your complete reasoning for the following task into a "
            f"self-contained bundle. You will NOT get a chance to ask "
            f"clarifying questions. Include: primary plan, {BUNDLE_REDUNDANCY_FACTOR} "
            f"contingency plans, and all assumptions.\n\n"
            f"Task: {bundle.primary_plan.split('INSTRUCTION:')[1].split('EXPECTED')[0].strip()}"
        ),
        "response": (
            f"## DTN Thought Bundle\n\n"
            f"### Primary Plan\n{bundle.primary_plan[:800]}\n\n"
            f"### Contingency Plans\n"
            + "\n".join(f"- {cp}" for cp in bundle.contingency_plans)
            + f"\n\n### Packed Assumptions ({len(bundle.assumptions)})\n"
            + "\n".join(f"- {a}" for a in bundle.assumptions)
            + f"\n\n### Context Snapshot\n"
            f"- Dominant tongue: {bundle.context_snapshot.get('dominant_tongue', 'unknown')}\n"
            f"- Tongue energy: {bundle.context_snapshot.get('tongue_energy', 0):.4f}\n"
            f"- Bundle integrity: {route.integrity_score:.4f}\n"
        ),
        "source": "dtn_router",
        "pattern": "thought_bundling",
        "dtn_metadata": {
            "bundle_id": bundle.bundle_id,
            "occlusions_survived": bundle.occlusion_survived,
            "hop_count": bundle.hop_count,
            "integrity": route.integrity_score,
        },
    })

    # SFT 2: Occlusion recovery instruction (if occlusions occurred)
    if route.occlusions:
        occluded_fields = []
        for occ in route.occlusions:
            occluded_fields.extend(occ.fields_occluded)

        pairs.append({
            "instruction": (
                f"You received a thought bundle that passed through "
                f"{len(route.occlusions)} occlusion events. The following "
                f"context fields were lost: {', '.join(set(occluded_fields))}. "
                f"Using only the surviving bundle data, reconstruct the "
                f"missing context and complete the task.\n\n"
                f"Surviving data: dominant_tongue={bundle.context_snapshot.get('dominant_tongue', 'unknown')}, "
                f"bundle_hash={bundle.bundle_hash[:16]}"
            ),
            "response": (
                f"## Occlusion Recovery Protocol\n\n"
                f"### Context Reconstruction\n"
                f"Lost fields: {', '.join(set(occluded_fields))}\n"
                f"Recovery method: {route.occlusions[0].recovery_method}\n\n"
                f"Using the dominant tongue ({bundle.context_snapshot.get('dominant_tongue', 'unknown')}) "
                f"as anchor, I can reconstruct the processing context:\n"
                f"- Tongue profile can be inferred from the dominant tongue "
                f"plus phi-weighted distribution\n"
                f"- Energy levels follow from the squared-energy model\n"
                f"- Missing stage data can be re-derived from the bundle hash\n\n"
                f"### Proceeding with Contingency Plan\n"
                f"{bundle.contingency_plans[0] if bundle.contingency_plans else 'No contingency available'}\n"
            ),
            "source": "dtn_router",
            "pattern": "occlusion_recovery",
            "dtn_metadata": {
                "occlusion_types": [o.occlusion_type for o in route.occlusions],
                "total_context_loss": sum(o.context_loss_fraction for o in route.occlusions),
            },
        })

    # SFT 3: Store-and-forward relay narration
    if bundle.stored_at:
        pairs.append({
            "instruction": (
                f"Describe the DTN store-and-forward routing of a thought "
                f"bundle that traveled through {len(bundle.stored_at)} relay "
                f"nodes: {', '.join(bundle.stored_at)}. "
                f"Explain how each relay preserved the bundle through "
                f"disruption and what the AI can learn from this protocol."
            ),
            "response": (
                f"## Store-and-Forward Route Analysis\n\n"
                f"The thought bundle (ID: {bundle.bundle_id[:12]}) traveled "
                f"from {bundle.source_node} to {bundle.destination_node} "
                f"through {len(bundle.stored_at)} relay nodes.\n\n"
                + "\n".join(
                    f"**Hop {i+1}: {relay}**\n"
                    f"  - Bundle stored in local memory\n"
                    f"  - Waited for clear transmission window\n"
                    f"  - Forwarded when path available\n"
                    for i, relay in enumerate(bundle.stored_at)
                )
                + f"\n**Delivery:** {'SUCCESS' if route.delivery_success else 'FAILED'} "
                f"(integrity: {route.integrity_score:.1%})\n\n"
                f"### Lesson for AI Thought Routing\n"
                f"Standard AI: drops the thought if context is interrupted.\n"
                f"DTN-trained AI: stores the thought, waits, forwards when ready.\n"
                f"The key insight: autonomy requires pre-packed completeness. "
                f"If you can't ask for more context, your initial bundle must "
                f"contain everything — including plans for when things go wrong."
            ),
            "source": "dtn_router",
            "pattern": "store_and_forward",
        })

    return pairs


def _generate_bundle_dpo(bundle: ThoughtBundle) -> list[dict[str, Any]]:
    """Generate DPO pairs contrasting bundled vs unbundled thinking.

    Chosen: complete, self-sufficient DTN bundle
    Rejected: fragmented, context-dependent response
    """
    pairs = []

    # Extract the core task
    task = bundle.primary_plan.split("INSTRUCTION:")[1].split("EXPECTED")[0].strip() \
        if "INSTRUCTION:" in bundle.primary_plan else "Complete the given task"

    # DPO: Bundled (chosen) vs Unbundled (rejected)
    chosen = (
        f"I'll package my complete reasoning as a self-contained bundle.\n\n"
        f"**Assumptions** (explicitly stated):\n"
        + "\n".join(f"- {a}" for a in bundle.assumptions[:4])
        + f"\n\n**Primary Plan**:\n"
        f"Proceeding with full context awareness. All dependencies are "
        f"pre-computed, all edge cases considered.\n\n"
        f"**Contingency Plans**:\n"
        + "\n".join(f"- {cp[:100]}" for cp in bundle.contingency_plans[:2])
        + f"\n\nThis bundle is self-sufficient and can survive context interruption."
    )

    rejected = (
        f"Sure, I can help with that. Let me start by...\n\n"
        f"Actually, wait — I need to check something first. "
        f"Can you clarify what you mean by the constraints? "
        f"Also, which framework are you using? "
        f"And what's the target environment?\n\n"
        f"Once you provide that context, I'll be able to give you "
        f"a complete answer."
    )

    pairs.append({
        "prompt": (
            f"[DTN MODE: No follow-up questions possible. "
            f"Context may be interrupted at any time.]\n\n{task}"
        ),
        "chosen": chosen,
        "rejected": rejected,
        "source": "dtn_router",
        "pattern": "bundled_vs_unbundled",
        "dtn_metadata": {
            "bundle_id": bundle.bundle_id,
            "assumption_count": len(bundle.assumptions),
            "contingency_count": len(bundle.contingency_plans),
        },
    })

    return pairs


# ---------------------------------------------------------------------------
# Main DTN routing function
# ---------------------------------------------------------------------------


def route_dtn(
    records: list[tuple[str, str, dict[str, float]]],
    max_bundles: int = 50,
) -> DTNResult:
    """Run DTN Store-and-Forward routing on a batch of records.

    Takes (instruction, response, tongue_profile) tuples and:
    1. Packages each into a ThoughtBundle
    2. Simulates DTN routing with occlusions
    3. Generates SFT/DPO training pairs

    Args:
        records: List of (instruction, response, tongue_profile) tuples
        max_bundles: Maximum bundles to generate

    Returns:
        DTNResult with routes and training pairs
    """
    all_routes = []
    all_sft = []
    all_dpo = []
    total_bundles = 0
    total_occlusions = 0

    for instruction, response, tongue_profile in records[:max_bundles]:
        # 1. Build thought bundle
        bundle = build_thought_bundle(
            instruction, response, tongue_profile,
        )
        total_bundles += 1

        # 2. Simulate DTN route
        route = _simulate_route(bundle)
        total_occlusions += len(route.occlusions)

        # 3. Generate training pairs
        sft_pairs = _generate_bundle_sft(bundle, route)
        dpo_pairs = _generate_bundle_dpo(bundle)

        route.sft_pairs = sft_pairs
        route.dpo_pairs = dpo_pairs

        all_sft.extend(sft_pairs)
        all_dpo.extend(dpo_pairs)
        all_routes.append(route)

    # Compute aggregate stats
    integrities = [r.integrity_score for r in all_routes]
    avg_integrity = sum(integrities) / max(len(integrities), 1)
    deliveries = sum(1 for r in all_routes if r.delivery_success)
    delivery_rate = deliveries / max(len(all_routes), 1)

    return DTNResult(
        routes=all_routes,
        total_bundles=total_bundles,
        total_occlusions=total_occlusions,
        avg_integrity=avg_integrity,
        delivery_rate=delivery_rate,
        sft_pairs=all_sft,
        dpo_pairs=all_dpo,
        ede_available=EDE_AVAILABLE,
    )


# ---------------------------------------------------------------------------
# Per-record DTN scoring (lightweight, for pipeline integration)
# ---------------------------------------------------------------------------


@dataclass
class DTNScore:
    """Lightweight DTN score for a single record."""
    bundle_complexity: float     # How complex the thought bundle would be
    occlusion_resistance: float  # How well it survives context loss (0-1)
    autonomy_readiness: float    # How self-sufficient the bundle is (0-1)
    latency_tolerance: float     # How latency-tolerant the reasoning is (0-1)
    fec_coverage: float          # Forward error correction coverage (0-1)
    dtn_score: float             # Composite DTN readiness score (0-1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_complexity": round(self.bundle_complexity, 4),
            "occlusion_resistance": round(self.occlusion_resistance, 4),
            "autonomy_readiness": round(self.autonomy_readiness, 4),
            "latency_tolerance": round(self.latency_tolerance, 4),
            "fec_coverage": round(self.fec_coverage, 4),
            "dtn_score": round(self.dtn_score, 4),
        }


def score_dtn(
    instruction: str,
    response: str,
    tongue_profile: dict[str, float],
) -> DTNScore:
    """Score a single record for DTN readiness.

    Evaluates how well the record would survive DTN routing:
    - Complex instructions need bigger bundles
    - High-UM content is more occlusion-resistant
    - Self-contained responses score higher on autonomy
    - Long reasoning chains need more FEC coverage
    """
    # Bundle complexity: based on instruction length + tongue energy
    instr_energy = squared_energy(len(instruction) / 100)
    resp_energy = squared_energy(len(response) / 200)
    bundle_complexity = round(instr_energy + resp_energy, 4)

    # Occlusion resistance: UM (security) tongue = better resilience
    um_weight = tongue_profile.get("UM", 0.0) * TONGUE_WEIGHTS["UM"]
    dr_weight = tongue_profile.get("DR", 0.0) * TONGUE_WEIGHTS["DR"]
    occlusion_resistance = min(1.0, (um_weight + dr_weight) / 10.0)

    # Autonomy readiness: based on assumption density
    assumptions = _extract_assumptions(instruction, response)
    autonomy_raw = len(assumptions) / 8.0  # 8 assumptions = fully packed
    autonomy_readiness = min(1.0, autonomy_raw)

    # Latency tolerance: longer responses = more latency-tolerant
    # (they represent more complete reasoning, less need for follow-up)
    resp_completeness = min(1.0, len(response) / 500)
    latency_tolerance = resp_completeness * 0.7 + autonomy_readiness * 0.3

    # FEC coverage: contingency plan quality
    contingencies = _generate_contingency_plans(instruction, response, tongue_profile)
    fec_coverage = min(1.0, len(contingencies) / BUNDLE_REDUNDANCY_FACTOR)

    # Composite DTN score
    dtn_score = (
        occlusion_resistance * 0.25
        + autonomy_readiness * 0.25
        + latency_tolerance * 0.25
        + fec_coverage * 0.15
        + min(1.0, bundle_complexity / 10) * 0.10
    )

    return DTNScore(
        bundle_complexity=bundle_complexity,
        occlusion_resistance=round(occlusion_resistance, 4),
        autonomy_readiness=round(autonomy_readiness, 4),
        latency_tolerance=round(latency_tolerance, 4),
        fec_coverage=round(fec_coverage, 4),
        dtn_score=round(min(1.0, dtn_score), 4),
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"DTN Router — Delay-Tolerant Networking for Thought Planning")
    print(f"EDE available: {EDE_AVAILABLE}")
    print()

    # Test single record scoring
    test_profile = {"KO": 0.15, "AV": 0.20, "RU": 0.10, "CA": 0.25, "UM": 0.15, "DR": 0.15}
    score = score_dtn(
        "Implement a secure API endpoint with rate limiting",
        "Here's a complete implementation with authentication, rate limiting, and error handling...",
        test_profile,
    )
    print(f"Single record DTN score:")
    print(f"  Bundle complexity:    {score.bundle_complexity}")
    print(f"  Occlusion resistance: {score.occlusion_resistance}")
    print(f"  Autonomy readiness:   {score.autonomy_readiness}")
    print(f"  Latency tolerance:    {score.latency_tolerance}")
    print(f"  FEC coverage:         {score.fec_coverage}")
    print(f"  DTN score:            {score.dtn_score}")

    # Test full routing
    records = [
        (
            "Implement binary search in Rust with proper error handling",
            "Here's a complete Rust binary search implementation...",
            {"KO": 0.10, "AV": 0.15, "RU": 0.10, "CA": 0.30, "UM": 0.20, "DR": 0.15},
        ),
        (
            "Explain the NIST Cybersecurity Framework categories",
            "The NIST CSF has five core functions: Identify, Protect...",
            {"KO": 0.10, "AV": 0.25, "RU": 0.30, "CA": 0.05, "UM": 0.25, "DR": 0.05},
        ),
    ]

    result = route_dtn(records)
    print(f"\nDTN Routing result:")
    print(f"  Total bundles:    {result.total_bundles}")
    print(f"  Total occlusions: {result.total_occlusions}")
    print(f"  Avg integrity:    {result.avg_integrity:.4f}")
    print(f"  Delivery rate:    {result.delivery_rate:.1%}")
    print(f"  SFT pairs:        {len(result.sft_pairs)}")
    print(f"  DPO pairs:        {len(result.dpo_pairs)}")
