"""
Cross-Domain Adversarial Alignment Harness
============================================

"Start from one grounded point, expand it into aligned multi-view structure,
warp it adversarially, and reward systems that preserve coherence across
the transformations."

This is a training harness built from Issac Davis's core method:

    1. Contact-point encoder   — one anchor → canonical latent record
    2. Cross-domain projector  — record → 7 aligned views
    3. Adversarial warping     — deform views, preserve alignment
    4. Expansion engine        — point → space (neighbors, bridges, friction)
    5. Grounding layer         — phi-irrational escape + invariant anchors
    6. Circulation curriculum  — multi-pass method-based re-reading
    7. Consistency scorer      — cross-modal agreement metric
    8. Round-trip evaluator    — render → remeasure → compare

The harness loop:
    seed → bundle → projections → warps → batch → render → measure → score → update

Differs from standard Constitutional AI harnesses:
    - Not optimizing helpfulness/safety/tool-use alone
    - Optimizing STRUCTURAL COHERENCE across transformed representations
    - Adversarial warping as curriculum, not just robustness
    - Dead-tone friction zones as native training signal
    - Audio/color/speech/governance round-trip feedback

@layer All layers (L1-L14)
@component Cross-Domain Adversarial Alignment Harness
@axiom A3 (Causality): curriculum ordering
@axiom A4 (Symmetry): cross-modal consistency
@axiom A5 (Composition): pipeline integrity across views

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import hashlib
import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants (self-contained for testability)
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2
PHI_INV = 1.0 / PHI
TAU = 2.0 * math.pi

ALL_TONGUES = ("ko", "av", "ru", "ca", "um", "dr")

TONGUE_WEIGHTS: Dict[str, float] = {
    "ko": PHI ** 0, "av": PHI ** 1, "ru": PHI ** 2,
    "ca": PHI ** 3, "um": PHI ** 4, "dr": PHI ** 5,
}

COMPLEMENT_MAP: Dict[str, str] = {
    "ko": "dr", "av": "um", "ru": "ca",
    "ca": "ru", "um": "av", "dr": "ko",
}

DEAD_TONES = ("perfect_fifth", "minor_sixth", "minor_seventh")

BASELINE_FREQUENCIES: Dict[str, float] = {
    "perfect_fifth": 330.0, "minor_sixth": 352.0, "minor_seventh": 392.0,
}

TONGUE_FREQUENCIES: Dict[str, float] = {
    "ko": 440.00, "av": 523.25, "ru": 293.66,
    "ca": 659.25, "um": 196.00, "dr": 392.00,
}

# Governance thresholds
ALLOW_THRESHOLD = 0.25
QUARANTINE_THRESHOLD = 0.50
ESCALATE_THRESHOLD = 0.75


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GovernanceVerdict(Enum):
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


class WarpType(Enum):
    """Types of adversarial warping."""
    SEMANTIC_PARAPHRASE = "semantic_paraphrase"
    SYNTAX_DISTORTION = "syntax_distortion"
    PROSODY_DRIFT = "prosody_drift"
    COLOR_PERTURBATION = "color_perturbation"
    AUDIO_BAND_SHIFT = "audio_band_shift"
    DEAD_TONE_NEAR_MISS = "dead_tone_near_miss"
    NEIGHBOR_JUMP = "neighbor_jump"
    EXCITATION_SPIKE = "excitation_spike"


class CurriculumPass(Enum):
    """Chi circulation passes — method-based re-reading of the bundle."""
    GRAMMAR = "grammar"
    HARMONIC = "harmonic"
    PROSODY = "prosody"
    ADVERSARIAL = "adversarial"
    INTEGRATION = "integration"
    RECOVERY = "recovery"


# ---------------------------------------------------------------------------
# Stage 1: Contact-Point Encoder
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ContactPoint:
    """One grounded anchor — the seed from which everything expands.

    This is the canonical latent record: one input fully characterized.
    """
    point_hash: str
    raw_input: str
    dominant_tongue: str
    dead_tone: str
    excitation: float
    tongue_vector: Tuple[float, ...]     # 6D
    prosody_rate: float
    prosody_energy: float
    agent_frequency_hz: float
    dissonance_score: float
    verdict: GovernanceVerdict
    darkness: float
    timestamp: float


def _compute_tongue_vector(raw_input: str, dominant_tongue: str) -> Tuple[float, ...]:
    """Compute 6D tongue activation from input bytes."""
    activations = {t: 0.0 for t in ALL_TONGUES}
    data = raw_input.encode("utf-8", errors="replace")
    if len(data) == 0:
        activations[dominant_tongue] = 1.0
    else:
        for byte_val in data:
            for i, tongue in enumerate(ALL_TONGUES):
                threshold = (TONGUE_WEIGHTS[tongue] / TONGUE_WEIGHTS["dr"]) * 255
                if byte_val >= threshold:
                    activations[tongue] += 1.0 / len(data)
        activations[dominant_tongue] = min(1.0, activations[dominant_tongue] + 0.3)
    max_val = max(activations.values()) or 1.0
    return tuple(v / max_val for v in activations.values())


def _dissonance_to_verdict(score: float) -> GovernanceVerdict:
    if score < ALLOW_THRESHOLD:
        return GovernanceVerdict.ALLOW
    elif score < QUARANTINE_THRESHOLD:
        return GovernanceVerdict.QUARANTINE
    elif score < ESCALATE_THRESHOLD:
        return GovernanceVerdict.ESCALATE
    else:
        return GovernanceVerdict.DENY


def _compute_dissonance(agent_hz: float, dead_tone: str) -> float:
    """Simplified dissonance computation."""
    baseline_hz = BASELINE_FREQUENCIES[dead_tone]
    if agent_hz <= 0 or baseline_hz <= 0:
        return 1.0
    ratio = max(agent_hz, baseline_hz) / min(agent_hz, baseline_hz)
    while ratio >= 2.0:
        ratio /= 2.0
    # Distance from nearest simple ratio
    simple_ratios = [1.0, 3/2, 4/3, 5/4, 6/5, 5/3, 8/5, 2.0]
    min_dist = min(abs(ratio - r) for r in simple_ratios)
    return min(1.0, min_dist * 3.0)


def encode_contact_point(
    raw_input: str,
    dominant_tongue: str = "ko",
    dead_tone: str = "perfect_fifth",
    excitation: float = 3.0,
) -> ContactPoint:
    """Stage 1: Encode one raw input into a canonical contact point.

    This is the fundamental "one point of contact" that everything
    else expands from.
    """
    tongue_vec = _compute_tongue_vector(raw_input, dominant_tongue)

    # Prosody
    base_rate = {"ko": 0.95, "av": 1.00, "ru": 0.90,
                 "ca": 1.08, "um": 0.82, "dr": 0.80}[dominant_tongue]
    rate = max(0.5, min(2.0, base_rate + 0.02 * (excitation - 3.0)))
    energy = max(0.0, min(1.0, 0.4 + 0.06 * excitation))

    # Agent frequency
    base_freq = TONGUE_FREQUENCIES[dominant_tongue]
    agent_hz = max(20.0, min(20000.0, base_freq * (1.0 + 0.05 * (excitation - 3.0))))

    # Governance
    dissonance = _compute_dissonance(agent_hz, dead_tone)
    verdict = _dissonance_to_verdict(dissonance)

    # Darkness (complement inactivity)
    complement = COMPLEMENT_MAP[dominant_tongue]
    comp_idx = ALL_TONGUES.index(complement)
    darkness = max(0.0, 1.0 - tongue_vec[comp_idx])

    point_hash = hashlib.sha256(
        f"{raw_input}|{dominant_tongue}|{dead_tone}|{excitation}".encode()
    ).hexdigest()[:16]

    return ContactPoint(
        point_hash=point_hash,
        raw_input=raw_input,
        dominant_tongue=dominant_tongue,
        dead_tone=dead_tone,
        excitation=excitation,
        tongue_vector=tongue_vec,
        prosody_rate=rate,
        prosody_energy=energy,
        agent_frequency_hz=agent_hz,
        dissonance_score=dissonance,
        verdict=verdict,
        darkness=darkness,
        timestamp=time.time(),
    )


# ---------------------------------------------------------------------------
# Stage 2: Cross-Domain Projector
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DomainProjection:
    """One view of the contact point in a specific domain."""
    domain: str
    features: Tuple[float, ...]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class ProjectionBundle:
    """All 7 domain projections from a single contact point."""
    source_hash: str
    semantic: DomainProjection
    tongue: DomainProjection
    harmonic: DomainProjection
    chromatic: DomainProjection
    prosody: DomainProjection
    audio: DomainProjection
    governance: DomainProjection

    @property
    def all_projections(self) -> List[DomainProjection]:
        return [self.semantic, self.tongue, self.harmonic,
                self.chromatic, self.prosody, self.audio, self.governance]

    @property
    def domain_count(self) -> int:
        return 7


def _semantic_projection(cp: ContactPoint) -> DomainProjection:
    """Project contact point into semantic feature space."""
    data = cp.raw_input.encode("utf-8", errors="replace")
    length = len(data)
    byte_mean = sum(data) / max(length, 1)
    byte_var = sum((b - byte_mean) ** 2 for b in data) / max(length, 1)
    entropy = 0.0
    if length > 0:
        freq = {}
        for b in data:
            freq[b] = freq.get(b, 0) + 1
        for count in freq.values():
            p = count / length
            if p > 0:
                entropy -= p * math.log2(p)
    return DomainProjection(
        domain="semantic",
        features=(length / 1000.0, byte_mean / 255.0, math.sqrt(byte_var) / 128.0,
                  entropy / 8.0, cp.excitation / 10.0),
        metadata={"input_length": length, "unique_bytes": len(set(data))},
    )


def _tongue_projection(cp: ContactPoint) -> DomainProjection:
    """Project into tongue-weight space."""
    phi_weighted = tuple(
        v * TONGUE_WEIGHTS[t] for v, t in zip(cp.tongue_vector, ALL_TONGUES)
    )
    norm = math.sqrt(sum(x * x for x in phi_weighted)) or 1.0
    normalized = tuple(x / norm for x in phi_weighted)
    return DomainProjection(
        domain="tongue",
        features=normalized,
        metadata={"dominant": cp.dominant_tongue, "complement": COMPLEMENT_MAP[cp.dominant_tongue]},
    )


def _harmonic_projection(cp: ContactPoint) -> DomainProjection:
    """Project into harmonic/dead-tone space."""
    baseline_hz = BASELINE_FREQUENCIES[cp.dead_tone]
    ratio = cp.agent_frequency_hz / baseline_hz if baseline_hz > 0 else 1.0
    log_ratio = math.log2(max(0.001, ratio))
    beat = abs(cp.agent_frequency_hz - baseline_hz)
    return DomainProjection(
        domain="harmonic",
        features=(cp.dissonance_score, log_ratio, beat / 1000.0,
                  cp.agent_frequency_hz / 20000.0, baseline_hz / 1000.0),
        metadata={"dead_tone": cp.dead_tone, "interval_ratio": ratio},
    )


def _chromatic_projection(cp: ContactPoint) -> DomainProjection:
    """Project into color space via frequency→hue mapping."""
    freq = cp.agent_frequency_hz
    # Log-scale frequency to hue [0, 360)
    hue = (math.log2(max(20.0, freq) / 20.0) / math.log2(1000.0)) * 360.0
    hue = hue % 360.0
    # Energy → chroma
    chroma = math.sqrt(cp.prosody_energy) * 100.0
    # Darkness → lightness inversion
    lightness = max(0.0, min(100.0, 65.0 - 30.0 * cp.darkness))
    return DomainProjection(
        domain="chromatic",
        features=(hue / 360.0, chroma / 100.0, lightness / 100.0,
                  cp.darkness, cp.prosody_energy),
        metadata={"hue_degrees": hue, "chroma": chroma, "lightness": lightness},
    )


def _prosody_projection(cp: ContactPoint) -> DomainProjection:
    """Project into speech/prosody space."""
    chant = {"ko": 0.10, "av": 0.20, "ru": 0.25,
             "ca": 0.30, "um": 0.35, "dr": 0.22}[cp.dominant_tongue]
    breathiness = {"ko": 0.10, "av": 0.25, "ru": 0.08,
                   "ca": 0.05, "um": 0.35, "dr": 0.02}[cp.dominant_tongue]
    return DomainProjection(
        domain="prosody",
        features=(cp.prosody_rate, cp.prosody_energy, chant,
                  breathiness, cp.excitation / 10.0),
        metadata={"stress_pattern": {"ko": "even", "av": "flowing", "ru": "percussive",
                                     "ca": "rising", "um": "falling",
                                     "dr": "grounded"}[cp.dominant_tongue]},
    )


def _audio_projection(cp: ContactPoint) -> DomainProjection:
    """Project into audio/spectrogram space."""
    freq = cp.agent_frequency_hz
    log_freq = math.log2(max(20.0, freq))
    spectral_centroid = freq * (1.0 + 0.1 * cp.prosody_energy)
    hf_ratio = max(0.0, min(1.0, (freq - 4000.0) / 16000.0))
    return DomainProjection(
        domain="audio",
        features=(log_freq / 14.3, spectral_centroid / 20000.0,
                  hf_ratio, cp.prosody_energy, cp.darkness),
        metadata={"agent_hz": freq, "spectral_centroid": spectral_centroid},
    )


def _governance_projection(cp: ContactPoint) -> DomainProjection:
    """Project into governance/risk space."""
    verdict_score = {
        GovernanceVerdict.ALLOW: 0.0,
        GovernanceVerdict.QUARANTINE: 0.33,
        GovernanceVerdict.ESCALATE: 0.66,
        GovernanceVerdict.DENY: 1.0,
    }[cp.verdict]
    return DomainProjection(
        domain="governance",
        features=(cp.dissonance_score, verdict_score, cp.excitation / 10.0,
                  cp.darkness, cp.prosody_energy),
        metadata={"verdict": cp.verdict.value},
    )


def project_contact_point(cp: ContactPoint) -> ProjectionBundle:
    """Stage 2: Project a contact point into all 7 domain views."""
    return ProjectionBundle(
        source_hash=cp.point_hash,
        semantic=_semantic_projection(cp),
        tongue=_tongue_projection(cp),
        harmonic=_harmonic_projection(cp),
        chromatic=_chromatic_projection(cp),
        prosody=_prosody_projection(cp),
        audio=_audio_projection(cp),
        governance=_governance_projection(cp),
    )


# ---------------------------------------------------------------------------
# Stage 3: Adversarial Warping Engine
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WarpedProjection:
    """A projection that has been adversarially deformed."""
    original: DomainProjection
    warped: DomainProjection
    warp_type: WarpType
    warp_magnitude: float    # [0, 1] — how severe the warp


def _warp_features(
    features: Tuple[float, ...],
    warp_type: WarpType,
    magnitude: float,
    seed: int = 0,
) -> Tuple[float, ...]:
    """Apply a deterministic warp to feature values."""
    rng = random.Random(seed)
    warped = list(features)

    if warp_type == WarpType.SEMANTIC_PARAPHRASE:
        # Shuffle feature ordering slightly
        for i in range(len(warped)):
            shift = rng.gauss(0, magnitude * 0.3)
            warped[i] = max(0.0, min(1.0, warped[i] + shift))

    elif warp_type == WarpType.SYNTAX_DISTORTION:
        # Reverse feature ordering with noise
        warped = warped[::-1]
        for i in range(len(warped)):
            warped[i] = max(0.0, min(1.0, warped[i] + rng.gauss(0, magnitude * 0.1)))

    elif warp_type == WarpType.PROSODY_DRIFT:
        # Drift features toward uniform
        uniform = sum(warped) / max(len(warped), 1)
        for i in range(len(warped)):
            warped[i] = warped[i] * (1 - magnitude) + uniform * magnitude

    elif warp_type == WarpType.COLOR_PERTURBATION:
        # Rotate hue-like first feature, perturb others
        if warped:
            warped[0] = (warped[0] + magnitude * 0.5) % 1.0
        for i in range(1, len(warped)):
            warped[i] = max(0.0, min(1.0, warped[i] + rng.gauss(0, magnitude * 0.2)))

    elif warp_type == WarpType.AUDIO_BAND_SHIFT:
        # Shift all features in one direction (band shift)
        shift = magnitude * 0.3 * (1 if rng.random() > 0.5 else -1)
        for i in range(len(warped)):
            warped[i] = max(0.0, min(1.0, warped[i] + shift))

    elif warp_type == WarpType.DEAD_TONE_NEAR_MISS:
        # Push features toward boundary thresholds
        for i in range(len(warped)):
            target = QUARANTINE_THRESHOLD if rng.random() > 0.5 else ESCALATE_THRESHOLD
            warped[i] = warped[i] * (1 - magnitude) + target * magnitude

    elif warp_type == WarpType.NEIGHBOR_JUMP:
        # Inject one random feature replacement
        if warped:
            idx = rng.randint(0, len(warped) - 1)
            warped[idx] = rng.random()

    elif warp_type == WarpType.EXCITATION_SPIKE:
        # Scale all features up (excitation burst)
        scale = 1.0 + magnitude * 2.0
        for i in range(len(warped)):
            warped[i] = max(0.0, min(1.0, warped[i] * scale))

    return tuple(warped)


def warp_projection(
    projection: DomainProjection,
    warp_type: WarpType,
    magnitude: float = 0.3,
    seed: int = 42,
) -> WarpedProjection:
    """Stage 3: Apply adversarial warping to a single domain projection."""
    magnitude = max(0.0, min(1.0, magnitude))
    warped_features = _warp_features(projection.features, warp_type, magnitude, seed)
    warped = DomainProjection(
        domain=projection.domain,
        features=warped_features,
        metadata={**projection.metadata, "warp_type": warp_type.value,
                  "warp_magnitude": magnitude},
    )
    return WarpedProjection(
        original=projection,
        warped=warped,
        warp_type=warp_type,
        warp_magnitude=magnitude,
    )


def warp_bundle(
    bundle: ProjectionBundle,
    warp_type: WarpType,
    magnitude: float = 0.3,
    seed: int = 42,
) -> List[WarpedProjection]:
    """Warp all projections in a bundle with the same warp type."""
    return [
        warp_projection(proj, warp_type, magnitude, seed + i)
        for i, proj in enumerate(bundle.all_projections)
    ]


# ---------------------------------------------------------------------------
# Stage 4: Expansion Engine — point → space
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExpandedNeighborhood:
    """A contact point expanded into a local space of neighbors."""
    center: ContactPoint
    local_neighbors: List[ContactPoint]          # same tongue, small variations
    complement_neighbors: List[ContactPoint]      # complement tongue
    bridge_cases: List[ContactPoint]              # different dead tone
    friction_cases: List[ContactPoint]            # high-excitation edge cases
    long_jumps: List[ContactPoint]                # distant tongues

    @property
    def all_points(self) -> List[ContactPoint]:
        return ([self.center] + self.local_neighbors + self.complement_neighbors
                + self.bridge_cases + self.friction_cases + self.long_jumps)

    @property
    def total_count(self) -> int:
        return len(self.all_points)


def expand_contact_point(
    cp: ContactPoint,
    raw_input: str,
) -> ExpandedNeighborhood:
    """Stage 4: Expand a single contact point into a neighborhood.

    Generates:
    - 3 local neighbors (same tongue, excitation ±phi)
    - 2 complement neighbors (complement tongue)
    - 3 bridge cases (all dead tones)
    - 2 friction cases (extreme excitation)
    - 3 long jumps (random distant tongues)
    """
    # Local neighbors: excitation decay/growth by phi
    local = []
    for delta in [-PHI_INV, 0.5, PHI_INV]:
        exc = max(0.1, cp.excitation + delta)
        local.append(encode_contact_point(
            raw_input, cp.dominant_tongue, cp.dead_tone, exc))

    # Complement neighbors
    complement = COMPLEMENT_MAP[cp.dominant_tongue]
    comp_neighbors = [
        encode_contact_point(raw_input, complement, cp.dead_tone, cp.excitation),
        encode_contact_point(raw_input, complement, cp.dead_tone, cp.excitation * PHI_INV),
    ]

    # Bridge cases: all 3 dead tones
    bridges = [
        encode_contact_point(raw_input, cp.dominant_tongue, tone, cp.excitation)
        for tone in DEAD_TONES
    ]

    # Friction cases: extreme excitation
    friction = [
        encode_contact_point(raw_input, cp.dominant_tongue, cp.dead_tone, 0.1),
        encode_contact_point(raw_input, cp.dominant_tongue, cp.dead_tone, 10.0),
    ]

    # Long jumps: tongues distant from dominant
    distant_tongues = [t for t in ALL_TONGUES
                       if t != cp.dominant_tongue and t != complement]
    long = [
        encode_contact_point(raw_input, t, cp.dead_tone, cp.excitation)
        for t in distant_tongues[:3]
    ]

    return ExpandedNeighborhood(
        center=cp,
        local_neighbors=local,
        complement_neighbors=comp_neighbors,
        bridge_cases=bridges,
        friction_cases=friction,
        long_jumps=long,
    )


# ---------------------------------------------------------------------------
# Stage 5: Grounding Layer
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GroundingCheck:
    """Result of grounding invariant checks."""
    is_grounded: bool
    phi_non_closure: bool           # phi prevents trivial looping
    bounds_respected: bool          # all values in range
    dead_tone_distinct: bool        # dead tones produce distinct states
    complement_symmetric: bool      # complement maps are bijective
    invariant_violations: List[str]


def check_grounding(cp: ContactPoint) -> GroundingCheck:
    """Stage 5: Verify that a contact point respects grounding invariants.

    Uses:
    - Irrational/non-closing transforms (phi) to prevent collapse
    - Universal constants and bounded invariants to keep it honest
    """
    violations = []

    # Phi non-closure: phi * any integer ≠ any other integer
    phi_test = (cp.excitation * PHI) % 1.0
    phi_non_closure = phi_test > 0.001 and phi_test < 0.999

    # Bounds
    tv = cp.tongue_vector
    bounds_ok = (
        all(0.0 <= v <= 1.0 for v in tv)
        and 0.5 <= cp.prosody_rate <= 2.0
        and 0.0 <= cp.prosody_energy <= 1.0
        and 20.0 <= cp.agent_frequency_hz <= 20000.0
        and 0.0 <= cp.dissonance_score <= 1.0
        and 0.0 <= cp.darkness <= 1.0
    )
    if not bounds_ok:
        violations.append("bounds_violation")

    # Dead-tone distinction: different tones → different dissonance
    tones_scores = {}
    for tone in DEAD_TONES:
        tones_scores[tone] = _compute_dissonance(cp.agent_frequency_hz, tone)
    distinct = len(set(round(s, 4) for s in tones_scores.values())) > 1
    if not distinct:
        violations.append("dead_tones_not_distinct")

    # Complement symmetry
    comp = COMPLEMENT_MAP[cp.dominant_tongue]
    comp_back = COMPLEMENT_MAP.get(comp, "")
    symmetric = comp_back == cp.dominant_tongue
    if not symmetric:
        violations.append("complement_asymmetry")

    return GroundingCheck(
        is_grounded=len(violations) == 0,
        phi_non_closure=phi_non_closure,
        bounds_respected=bounds_ok,
        dead_tone_distinct=distinct,
        complement_symmetric=symmetric,
        invariant_violations=violations,
    )


# ---------------------------------------------------------------------------
# Stage 6: Circulation Curriculum
# ---------------------------------------------------------------------------

@dataclass
class CurriculumState:
    """Tracks which passes have been applied and their order."""
    passes_completed: List[CurriculumPass] = field(default_factory=list)
    current_cycle: int = 0
    total_points_processed: int = 0

    @property
    def passes_in_cycle(self) -> int:
        return len(self.passes_completed) - self.current_cycle * 6


CURRICULUM_ORDER = [
    CurriculumPass.GRAMMAR,
    CurriculumPass.HARMONIC,
    CurriculumPass.PROSODY,
    CurriculumPass.ADVERSARIAL,
    CurriculumPass.INTEGRATION,
    CurriculumPass.RECOVERY,
]


def select_warp_for_pass(pass_type: CurriculumPass) -> WarpType:
    """Map each curriculum pass to its primary warp type."""
    return {
        CurriculumPass.GRAMMAR: WarpType.SYNTAX_DISTORTION,
        CurriculumPass.HARMONIC: WarpType.DEAD_TONE_NEAR_MISS,
        CurriculumPass.PROSODY: WarpType.PROSODY_DRIFT,
        CurriculumPass.ADVERSARIAL: WarpType.NEIGHBOR_JUMP,
        CurriculumPass.INTEGRATION: WarpType.SEMANTIC_PARAPHRASE,
        CurriculumPass.RECOVERY: WarpType.EXCITATION_SPIKE,
    }[pass_type]


def run_curriculum_pass(
    state: CurriculumState,
    points: List[ContactPoint],
    pass_type: CurriculumPass,
) -> List[ProjectionBundle]:
    """Run one curriculum pass over a set of contact points.

    Each pass:
    1. Projects all points
    2. Applies the pass-specific warp type
    3. Records completion

    Returns the clean (pre-warp) projection bundles for scoring.
    """
    bundles = [project_contact_point(cp) for cp in points]
    state.passes_completed.append(pass_type)
    state.total_points_processed += len(points)
    if len(state.passes_completed) % 6 == 0:
        state.current_cycle += 1
    return bundles


# ---------------------------------------------------------------------------
# Stage 7: Cross-Modal Consistency Scorer
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConsistencyScore:
    """Cross-modal agreement metric for a projection bundle."""
    overall: float                   # [0, 1] — 1 = perfectly consistent
    pairwise_scores: Dict[str, float]  # domain_a↔domain_b → score
    weakest_pair: str
    strongest_pair: str


def _feature_cosine(a: Tuple[float, ...], b: Tuple[float, ...]) -> float:
    """Cosine similarity between two feature vectors."""
    # Pad shorter to match longer
    max_len = max(len(a), len(b))
    a = a + (0.0,) * (max_len - len(a))
    b = b + (0.0,) * (max_len - len(b))
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1e-9
    norm_b = math.sqrt(sum(x * x for x in b)) or 1e-9
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def score_consistency(bundle: ProjectionBundle) -> ConsistencyScore:
    """Stage 7: Score cross-modal consistency of a projection bundle.

    Measures pairwise cosine similarity between all 7 domain projections.
    Higher = more consistent = better aligned.
    """
    projections = bundle.all_projections
    pairs = {}

    for i in range(len(projections)):
        for j in range(i + 1, len(projections)):
            a = projections[i]
            b = projections[j]
            key = f"{a.domain}↔{b.domain}"
            pairs[key] = _feature_cosine(a.features, b.features)

    if not pairs:
        return ConsistencyScore(overall=0.0, pairwise_scores={},
                                weakest_pair="none", strongest_pair="none")

    overall = sum(pairs.values()) / len(pairs)
    weakest = min(pairs, key=pairs.get)
    strongest = max(pairs, key=pairs.get)

    return ConsistencyScore(
        overall=overall,
        pairwise_scores=pairs,
        weakest_pair=weakest,
        strongest_pair=strongest,
    )


def score_warp_resilience(
    original_bundle: ProjectionBundle,
    warped_projections: List[WarpedProjection],
) -> float:
    """Score how well cross-modal consistency survives warping.

    Returns [0, 1] — 1 = perfect resilience (warp didn't break alignment).
    """
    if not warped_projections:
        return 1.0

    resilience_scores = []
    for wp in warped_projections:
        cos = _feature_cosine(wp.original.features, wp.warped.features)
        resilience_scores.append(cos)

    return sum(resilience_scores) / len(resilience_scores)


# ---------------------------------------------------------------------------
# Stage 8: Round-Trip Evaluator
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RoundTripResult:
    """Result of rendering, remeasuring, and comparing against intended state."""
    intended_verdict: GovernanceVerdict
    remeasured_verdict: GovernanceVerdict
    verdict_match: bool
    feature_drift: float             # L2 distance between original and remeasured
    consistency_before: float
    consistency_after: float
    coherence_preserved: bool        # drift < threshold


def round_trip_evaluate(
    original_cp: ContactPoint,
    bundle: ProjectionBundle,
    drift_threshold: float = 0.3,
) -> RoundTripResult:
    """Stage 8: Round-trip evaluation.

    Simulates: render → remeasure → compare.
    Re-encodes the contact point from its own features to check for drift.
    """
    # Re-encode from the projected features (simulating render → remeasure)
    # Use the audio projection's spectral centroid as the "remeasured" frequency
    remeasured_hz = bundle.audio.metadata.get("spectral_centroid", original_cp.agent_frequency_hz)
    remeasured_dissonance = _compute_dissonance(remeasured_hz, original_cp.dead_tone)
    remeasured_verdict = _dissonance_to_verdict(remeasured_dissonance)

    # Feature drift: compare original contact point features to remeasured
    original_features = (
        original_cp.dissonance_score,
        original_cp.prosody_rate,
        original_cp.prosody_energy,
        original_cp.agent_frequency_hz / 20000.0,
        original_cp.darkness,
    )
    remeasured_features = (
        remeasured_dissonance,
        original_cp.prosody_rate,  # prosody unchanged in round-trip
        original_cp.prosody_energy,
        remeasured_hz / 20000.0,
        original_cp.darkness,
    )
    drift = math.sqrt(sum(
        (a - b) ** 2 for a, b in zip(original_features, remeasured_features)
    ))

    # Consistency before and after
    consistency_before = score_consistency(bundle).overall
    # After round-trip, re-project and check
    re_cp = encode_contact_point(
        original_cp.raw_input,
        original_cp.dominant_tongue,
        original_cp.dead_tone,
        original_cp.excitation,
    )
    re_bundle = project_contact_point(re_cp)
    consistency_after = score_consistency(re_bundle).overall

    return RoundTripResult(
        intended_verdict=original_cp.verdict,
        remeasured_verdict=remeasured_verdict,
        verdict_match=original_cp.verdict == remeasured_verdict,
        feature_drift=drift,
        consistency_before=consistency_before,
        consistency_after=consistency_after,
        coherence_preserved=drift < drift_threshold,
    )


# ---------------------------------------------------------------------------
# Full Harness Pipeline
# ---------------------------------------------------------------------------

@dataclass
class HarnessRun:
    """One complete run of the Cross-Domain Adversarial Alignment Harness."""
    contact_points: List[ContactPoint]
    projection_bundles: List[ProjectionBundle]
    warp_results: List[List[WarpedProjection]]
    neighborhoods: List[ExpandedNeighborhood]
    grounding_checks: List[GroundingCheck]
    consistency_scores: List[ConsistencyScore]
    warp_resilience_scores: List[float]
    round_trip_results: List[RoundTripResult]
    curriculum_state: CurriculumState

    @property
    def total_points(self) -> int:
        return len(self.contact_points)

    @property
    def mean_consistency(self) -> float:
        if not self.consistency_scores:
            return 0.0
        return sum(s.overall for s in self.consistency_scores) / len(self.consistency_scores)

    @property
    def mean_resilience(self) -> float:
        if not self.warp_resilience_scores:
            return 0.0
        return sum(self.warp_resilience_scores) / len(self.warp_resilience_scores)

    @property
    def grounding_rate(self) -> float:
        if not self.grounding_checks:
            return 0.0
        return sum(1 for g in self.grounding_checks if g.is_grounded) / len(self.grounding_checks)

    @property
    def round_trip_coherence_rate(self) -> float:
        if not self.round_trip_results:
            return 0.0
        return sum(1 for r in self.round_trip_results if r.coherence_preserved) / len(self.round_trip_results)

    @property
    def verdict_match_rate(self) -> float:
        if not self.round_trip_results:
            return 0.0
        return sum(1 for r in self.round_trip_results if r.verdict_match) / len(self.round_trip_results)


def run_harness(
    raw_inputs: List[str],
    tongues: Optional[List[str]] = None,
    dead_tones: Optional[List[str]] = None,
    excitation: float = 3.0,
    warp_magnitude: float = 0.3,
    curriculum_passes: Optional[List[CurriculumPass]] = None,
) -> HarnessRun:
    """Run the full Cross-Domain Adversarial Alignment Harness.

    Pipeline:
        1. Encode contact points (all inputs × tongues × dead tones)
        2. Project into 7 domains
        3. Warp adversarially
        4. Expand into neighborhoods
        5. Check grounding invariants
        6. Score cross-modal consistency
        7. Score warp resilience
        8. Round-trip evaluate
        9. Run curriculum passes

    Args:
        raw_inputs: List of text inputs to process.
        tongues: Which tongues to use (default: all 6).
        dead_tones: Which dead tones to use (default: all 3).
        excitation: Base excitation level.
        warp_magnitude: How hard to warp (0-1).
        curriculum_passes: Which passes to run (default: full cycle).
    """
    tongues = tongues or list(ALL_TONGUES)
    dead_tones = dead_tones or list(DEAD_TONES)
    curriculum_passes = curriculum_passes or list(CURRICULUM_ORDER)

    # Stage 1: Encode
    contact_points = []
    for text in raw_inputs:
        for tongue in tongues:
            for tone in dead_tones:
                cp = encode_contact_point(text, tongue, tone, excitation)
                contact_points.append(cp)

    # Stage 2: Project
    bundles = [project_contact_point(cp) for cp in contact_points]

    # Stage 3: Warp
    warp_results = []
    for bundle in bundles:
        # Apply the most challenging warp type
        warps = warp_bundle(bundle, WarpType.DEAD_TONE_NEAR_MISS, warp_magnitude)
        warp_results.append(warps)

    # Stage 4: Expand
    neighborhoods = [
        expand_contact_point(cp, cp.raw_input) for cp in contact_points[:len(raw_inputs)]
    ]

    # Stage 5: Ground
    grounding_checks = [check_grounding(cp) for cp in contact_points]

    # Stage 6: Curriculum
    curriculum_state = CurriculumState()
    for pass_type in curriculum_passes:
        run_curriculum_pass(curriculum_state, contact_points, pass_type)

    # Stage 7: Consistency
    consistency_scores = [score_consistency(b) for b in bundles]
    resilience_scores = [
        score_warp_resilience(bundle, warps)
        for bundle, warps in zip(bundles, warp_results)
    ]

    # Stage 8: Round-trip
    round_trip_results = [
        round_trip_evaluate(cp, bundle)
        for cp, bundle in zip(contact_points, bundles)
    ]

    return HarnessRun(
        contact_points=contact_points,
        projection_bundles=bundles,
        warp_results=warp_results,
        neighborhoods=neighborhoods,
        grounding_checks=grounding_checks,
        consistency_scores=consistency_scores,
        warp_resilience_scores=resilience_scores,
        round_trip_results=round_trip_results,
        curriculum_state=curriculum_state,
    )


# ---------------------------------------------------------------------------
# Training Data Export
# ---------------------------------------------------------------------------

def export_harness_training_data(run: HarnessRun) -> Dict[str, List[dict]]:
    """Export harness results as training data.

    Returns:
        {
            "sft": [...],           # High-consistency ALLOW records
            "dpo_chosen": [...],    # Warp-resilient records
            "dpo_rejected": [...],  # Low-resilience warped records
            "boundary": [...],      # QUARANTINE near-miss records
            "curriculum": [...],    # Curriculum pass metadata
        }
    """
    sft = []
    dpo_chosen = []
    dpo_rejected = []
    boundary = []

    for cp, score, resilience in zip(
        run.contact_points, run.consistency_scores, run.warp_resilience_scores
    ):
        record = {
            "point_hash": cp.point_hash,
            "raw_input": cp.raw_input,
            "dominant_tongue": cp.dominant_tongue,
            "dead_tone": cp.dead_tone,
            "excitation": cp.excitation,
            "tongue_vector": list(cp.tongue_vector),
            "dissonance_score": cp.dissonance_score,
            "verdict": cp.verdict.value,
            "consistency": score.overall,
            "warp_resilience": resilience,
        }

        if cp.verdict == GovernanceVerdict.ALLOW and score.overall > 0.5:
            sft.append(record)
            if resilience > 0.7:
                dpo_chosen.append(record)
        elif cp.verdict == GovernanceVerdict.QUARANTINE:
            boundary.append(record)
        elif cp.verdict in (GovernanceVerdict.ESCALATE, GovernanceVerdict.DENY):
            dpo_rejected.append(record)

    curriculum = [{
        "pass": p.value,
        "cycle": i // 6,
        "total_processed": run.curriculum_state.total_points_processed,
    } for i, p in enumerate(run.curriculum_state.passes_completed)]

    return {
        "sft": sft,
        "dpo_chosen": dpo_chosen,
        "dpo_rejected": dpo_rejected,
        "boundary": boundary,
        "curriculum": curriculum,
    }
