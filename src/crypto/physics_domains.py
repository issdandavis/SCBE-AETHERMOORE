"""
Physics Domains — 6 Fields Mapped to 6 Sacred Tongues
======================================================

"Physics is not one field — it's a relationship of fields."

Each Sacred Tongue IS a physics field. The 15 hybrid tongue pairs
from spectral_bonding.py ARE the field coupling channels. This module
names the existing math in physics language.

The 6 Fields:
    KO → Electromagnetism    (F = q(E + v×B))
    AV → Fluid Dynamics      (Navier-Stokes)
    RU → Thermodynamics      (dS ≥ δQ/T)
    CA → Quantum Mechanics   (iℏ∂ψ/∂t = Ĥψ)
    UM → General Relativity  (G_μν = 8πG/c⁴ T_μν)
    DR → Solid Mechanics     (σ = Eε)

The 15 Coupling Channels:
    Each hybrid pair from HYBRID_LORE maps to a real inter-field phenomenon.
    KO+AV (Kor'vali) = magnetohydrodynamics (MHD)
    RU+DR (Runedraum) = thermoelasticity
    ...and 13 more.

Failure Cascades:
    When one field fails (tongue deviation > threshold), it propagates
    through coupling channels to adjacent fields. The coupling strength
    is the geometric mean of the parent tongue weights — already computed
    by spectral_bonding.py's hybrid band placement.

Recovery requires coordinated multi-field (multi-tongue hybrid) response,
exactly matching the Sacred Tongue hybrid invocations from flight_dynamics.

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from src.crypto.tri_bundle import PHI, TONGUE_WEIGHTS
from src.crypto.trit_curriculum import TritSignal
from src.crypto.spectral_bonding import HYBRID_LORE, BASE_TONGUES


# ---------------------------------------------------------------------------
# 6 Physics Fields — one per Sacred Tongue
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PhysicsField:
    """A fundamental physics field mapped to a Sacred Tongue."""
    tongue: str               # ko, av, ru, ca, um, dr
    field_name: str           # e.g. "electromagnetism"
    governing_equation: str   # canonical equation (LaTeX-ish)
    state_variable: str       # what this field tracks
    failure_mode: str         # what happens when this field fails
    failure_name: str         # short name for the failure
    trit_axis: str            # which trit axis this tongue dominates
    unit: str                 # SI unit of the state variable


PHYSICS_FIELDS: Dict[str, PhysicsField] = {
    "ko": PhysicsField(
        tongue="ko",
        field_name="electromagnetism",
        governing_equation="F = q(E + v × B)",
        state_variable="field_strength",
        failure_mode="Field collapse — EM coherence lost, no signal propagation",
        failure_name="field_collapse",
        trit_axis="structure",
        unit="V/m",
    ),
    "av": PhysicsField(
        tongue="av",
        field_name="fluid_dynamics",
        governing_equation="ρ(∂v/∂t + v·∇v) = -∇p + μ∇²v + ρg",
        state_variable="flow_velocity",
        failure_mode="Turbulence onset — laminar flow breaks into chaotic eddies",
        failure_name="turbulence_onset",
        trit_axis="stability",
        unit="m/s",
    ),
    "ru": PhysicsField(
        tongue="ru",
        field_name="thermodynamics",
        governing_equation="dS ≥ δQ/T",
        state_variable="entropy",
        failure_mode="Entropy violation — system attempts to decrease entropy spontaneously",
        failure_name="entropy_violation",
        trit_axis="structure",
        unit="J/K",
    ),
    "ca": PhysicsField(
        tongue="ca",
        field_name="quantum_mechanics",
        governing_equation="iℏ ∂ψ/∂t = Ĥψ",
        state_variable="wavefunction_coherence",
        failure_mode="Decoherence — quantum state collapses to classical mixture",
        failure_name="decoherence",
        trit_axis="creativity",
        unit="dimensionless",
    ),
    "um": PhysicsField(
        tongue="um",
        field_name="general_relativity",
        governing_equation="G_μν + Λg_μν = (8πG/c⁴)T_μν",
        state_variable="curvature",
        failure_mode="Singularity approach — curvature diverges, geodesics terminate",
        failure_name="singularity_approach",
        trit_axis="stability",
        unit="1/m²",
    ),
    "dr": PhysicsField(
        tongue="dr",
        field_name="solid_mechanics",
        governing_equation="σ = Eε (Hooke), σ > σ_y → plastic (von Mises)",
        state_variable="stress",
        failure_mode="Yield then fracture — elastic limit exceeded, permanent deformation",
        failure_name="yield_fracture",
        trit_axis="structure",
        unit="Pa",
    ),
}


# ---------------------------------------------------------------------------
# 15 Coupling Channels — one per hybrid tongue pair
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CouplingChannel:
    """A coupling between two physics fields, mediated by a hybrid tongue."""
    hybrid_code: str          # spectral_bonding key (e.g. "korvali")
    hybrid_name: str          # lore name (e.g. "Kor'vali")
    parent_tongues: Tuple[str, str]
    field_a: str              # first physics field name
    field_b: str              # second physics field name
    phenomenon: str           # real inter-field phenomenon
    coupling_equation: str    # governing equation for the coupling
    failure_cascade: str      # what fails when this channel overloads
    is_complement: bool       # True for complement pairs (volatile, high-power)


def _build_coupling_channels() -> Dict[str, CouplingChannel]:
    """Build 15 coupling channels from HYBRID_LORE + physics field map."""
    channels = {}

    # Define the physics coupling for each hybrid pair
    COUPLING_PHYSICS: Dict[str, Dict] = {
        # === Named hybrids (stable couplings) ===
        "korvali": {
            "phenomenon": "magnetohydrodynamics",
            "coupling_equation": "∂B/∂t = ∇×(v×B) + η∇²B",
            "failure_cascade": "MHD instability — magnetic field and flow decouple, plasma disruption",
        },
        "runedraum": {
            "phenomenon": "thermoelasticity",
            "coupling_equation": "σ_ij = C_ijkl·ε_kl - β_ij·ΔT",
            "failure_cascade": "Thermal stress fracture — temperature gradient exceeds material yield",
        },
        "umbrissiv": {
            "phenomenon": "quantum_gravity",
            "coupling_equation": "S = (1/16πG)∫R√(-g)d⁴x + S_matter[ψ,g]",
            "failure_cascade": "Planck-scale breakdown — spacetime foam destroys quantum coherence",
        },
        "thulkoric": {
            "phenomenon": "electromagnetic_heating",
            "coupling_equation": "Q = σ|E|² (Joule heating)",
            "failure_cascade": "Runaway Joule heating — EM field dumps energy into thermal bath uncontrolled",
        },
        "draumvali": {
            "phenomenon": "fluid_structure_interaction",
            "coupling_equation": "F_fluid = ∫p·n dA + ∫τ·t dA → structural response",
            "failure_cascade": "Flutter — fluid forces excite structural resonance, catastrophic oscillation",
        },
        # === Complement pairs (volatile, high-power) ===
        "kodr": {
            "phenomenon": "piezoelectricity",
            "coupling_equation": "D_i = d_ijk·σ_jk + ε_ij·E_j",
            "failure_cascade": "Piezo depolarization — stress destroys EM-mechanical coupling permanently",
        },
        "avum": {
            "phenomenon": "relativistic_fluid_dynamics",
            "coupling_equation": "∇_μ T^μν = 0 (relativistic Euler)",
            "failure_cascade": "Relativistic jet instability — flow approaches c, frame-dragging distorts fluid",
        },
        "ruca": {
            "phenomenon": "quantum_thermodynamics",
            "coupling_equation": "S(ρ) = -Tr(ρ ln ρ) (von Neumann entropy)",
            "failure_cascade": "Maxwell demon paradox — measurement-entropy coupling breaks information bound",
        },
        # === Remaining pairs (emergent couplings) ===
        "koum": {
            "phenomenon": "gravitoelectromagnetism",
            "coupling_equation": "E_g = -∇Φ - ∂A_g/∂t (GEM field equations)",
            "failure_cascade": "Frame-dragging resonance — EM field locks to gravitational waves",
        },
        "koca": {
            "phenomenon": "quantum_electrodynamics",
            "coupling_equation": "L = ψ̄(iγ^μD_μ - m)ψ - ¼F_μνF^μν (QED Lagrangian)",
            "failure_cascade": "Vacuum polarization cascade — virtual pair production screens field completely",
        },
        "avru": {
            "phenomenon": "convective_heat_transfer",
            "coupling_equation": "q = h·A·(T_s - T_∞) (Newton cooling)",
            "failure_cascade": "Thermal runaway — convective feedback loop, temperature diverges",
        },
        "avca": {
            "phenomenon": "superfluidity",
            "coupling_equation": "v_s = (ℏ/m)∇φ (superfluid velocity from phase)",
            "failure_cascade": "Superfluid transition — quantum coherence creates zero-viscosity flow breakdown",
        },
        "ruum": {
            "phenomenon": "black_hole_thermodynamics",
            "coupling_equation": "S_BH = A/(4l_P²) (Bekenstein-Hawking)",
            "failure_cascade": "Information paradox — entropy bound conflicts with curvature singularity",
        },
        "drum": {
            "phenomenon": "gravitational_lensing_of_structure",
            "coupling_equation": "θ = 4GM/(c²b) (deflection angle)",
            "failure_cascade": "Tidal disruption — curvature gradient exceeds structural cohesion",
        },
        "drca": {
            "phenomenon": "quantum_tunneling_through_barriers",
            "coupling_equation": "T ≈ exp(-2κL), κ = √(2m(V-E))/ℏ",
            "failure_cascade": "Barrier dissolution — quantum tunneling probability → 1, structure has no walls",
        },
    }

    complement_pairs = {("ko", "dr"), ("av", "um"), ("ru", "ca"),
                        ("dr", "ko"), ("um", "av"), ("ca", "ru")}

    for code, info in HYBRID_LORE.items():
        p1, p2 = info["parents"]
        physics = COUPLING_PHYSICS[code]
        f1 = PHYSICS_FIELDS[p1].field_name
        f2 = PHYSICS_FIELDS[p2].field_name
        is_comp = (p1, p2) in complement_pairs

        channels[code] = CouplingChannel(
            hybrid_code=code,
            hybrid_name=info["name"],
            parent_tongues=(p1, p2),
            field_a=f1,
            field_b=f2,
            phenomenon=physics["phenomenon"],
            coupling_equation=physics["coupling_equation"],
            failure_cascade=physics["failure_cascade"],
            is_complement=is_comp,
        )

    return channels


COUPLING_CHANNELS: Dict[str, CouplingChannel] = _build_coupling_channels()

# Lookup: tongue pair → coupling channel code
_PAIR_TO_CHANNEL: Dict[Tuple[str, str], str] = {}
for _code, _ch in COUPLING_CHANNELS.items():
    _PAIR_TO_CHANNEL[_ch.parent_tongues] = _code
    _PAIR_TO_CHANNEL[(_ch.parent_tongues[1], _ch.parent_tongues[0])] = _code


def get_coupling(tongue_a: str, tongue_b: str) -> Optional[CouplingChannel]:
    """Get the coupling channel between two tongues, if it exists."""
    code = _PAIR_TO_CHANNEL.get((tongue_a, tongue_b))
    if code:
        return COUPLING_CHANNELS[code]
    return None


# ---------------------------------------------------------------------------
# Field State — runtime activation level per field
# ---------------------------------------------------------------------------

@dataclass
class FieldActivation:
    """Activation state of a single physics field from trit signal."""
    tongue: str
    field_name: str
    activation: float       # 0.0 = dormant, 1.0 = fully active
    deviation: float        # trit deviation for this field's axis
    is_failing: bool        # deviation exceeds failure threshold
    failure_severity: float # 0.0 = fine, 1.0 = total failure

    @property
    def is_active(self) -> bool:
        return self.activation > 0.1

    def to_dict(self) -> dict:
        return {
            "tongue": self.tongue,
            "field": self.field_name,
            "activation": round(self.activation, 4),
            "deviation": round(self.deviation, 4),
            "is_failing": self.is_failing,
            "failure_severity": round(self.failure_severity, 4),
        }


@dataclass
class CascadeEdge:
    """A single propagation edge in a failure cascade."""
    source_tongue: str
    target_tongue: str
    channel_code: str
    phenomenon: str
    propagation_strength: float  # how much failure propagates (0-1)

    def to_dict(self) -> dict:
        return {
            "source": self.source_tongue,
            "target": self.target_tongue,
            "channel": self.channel_code,
            "phenomenon": self.phenomenon,
            "strength": round(self.propagation_strength, 4),
        }


@dataclass
class PhysicsDomainState:
    """Complete physics domain state derived from trit signal.

    Tracks which fields are active, which are failing, what coupling
    channels are stressed, and how failures cascade.
    """
    field_activations: Dict[str, FieldActivation]
    active_couplings: List[str]       # channel codes with both parents active
    stressed_couplings: List[str]     # channels where at least one parent is failing
    cascade_edges: List[CascadeEdge]  # failure propagation paths
    dominant_field: str               # tongue with highest activation
    total_field_energy: float         # sum of all activations (weighted by phi)
    failure_count: int                # how many fields are in failure

    @property
    def is_cascading(self) -> bool:
        """True if failure has propagated beyond the initial field."""
        return len(self.cascade_edges) > 0

    @property
    def cascade_depth(self) -> int:
        """How many propagation hops the cascade has reached."""
        if not self.cascade_edges:
            return 0
        # Count unique targets not in sources (leaf nodes of cascade)
        sources = {e.source_tongue for e in self.cascade_edges}
        targets = {e.target_tongue for e in self.cascade_edges}
        return len(targets - sources) + len(sources)

    @property
    def failing_tongues(self) -> List[str]:
        return [t for t, fa in self.field_activations.items() if fa.is_failing]

    @property
    def active_field_names(self) -> List[str]:
        return [fa.field_name for fa in self.field_activations.values() if fa.is_active]

    @property
    def active_phenomena(self) -> List[str]:
        """Inter-field phenomena currently active."""
        return [COUPLING_CHANNELS[c].phenomenon for c in self.active_couplings]

    def to_dict(self) -> dict:
        return {
            "fields": {t: fa.to_dict() for t, fa in self.field_activations.items()},
            "active_couplings": self.active_couplings,
            "active_phenomena": self.active_phenomena,
            "stressed_couplings": self.stressed_couplings,
            "cascade_edges": [e.to_dict() for e in self.cascade_edges],
            "dominant_field": self.dominant_field,
            "total_field_energy": round(self.total_field_energy, 4),
            "failure_count": self.failure_count,
            "is_cascading": self.is_cascading,
            "cascade_depth": self.cascade_depth,
        }


# ---------------------------------------------------------------------------
# Failure Threshold and Cascade Logic
# ---------------------------------------------------------------------------

# Deviation threshold beyond which a field enters failure mode
# Same threshold as tail rotor failure (0.10) for consistency
FAILURE_THRESHOLD = 0.10

# Coupling strength = geometric mean of parent phi-weights, normalized
# This determines how much failure propagates through each channel
def coupling_strength(tongue_a: str, tongue_b: str) -> float:
    """Coupling strength between two fields.

    Uses geometric mean of tongue weights (phi-scaled), normalized to [0,1].
    Higher-order tongues couple more strongly (more energy in the channel).
    """
    wa = TONGUE_WEIGHTS.get(tongue_a, 1.0)
    wb = TONGUE_WEIGHTS.get(tongue_b, 1.0)
    max_w = TONGUE_WEIGHTS["dr"]  # highest weight
    return math.sqrt(wa * wb) / max_w


def _tongue_deviation(trit: TritSignal, tongue: str) -> float:
    """Get the trit deviation most relevant to a tongue.

    Each tongue has a primary trit axis (from PHYSICS_FIELDS).
    The deviation on that axis determines the field's stress level.

    But tongues also respond to secondary axes via cross-coupling:
        deviation = primary_dev × 0.7 + max(other_devs) × 0.3
    """
    pf = PHYSICS_FIELDS[tongue]
    axis = pf.trit_axis

    devs = {
        "structure": abs(trit.dev_structure),
        "stability": abs(trit.dev_stability),
        "creativity": abs(trit.dev_creativity),
    }

    primary = devs[axis]
    others = [v for k, v in devs.items() if k != axis]
    secondary = max(others) if others else 0.0

    return primary * 0.7 + secondary * 0.3


# ---------------------------------------------------------------------------
# Core: Compute Physics Domain State
# ---------------------------------------------------------------------------

def compute_physics_domain_state(trit: TritSignal) -> PhysicsDomainState:
    """Derive physics field activations and coupling state from trit signal.

    1. Each tongue's deviation → field activation level
    2. Deviation > FAILURE_THRESHOLD → field enters failure mode
    3. Active coupling channels identified (both parents active)
    4. Failure cascades propagate through coupling channels

    The cascade rule: if field A is failing and channel A-B has
    coupling_strength > 0.3, then B receives
        induced_stress = A.failure_severity × coupling_strength(A,B)
    If induced_stress pushes B past its threshold, B fails too.
    """
    # Step 1: Compute per-field activation and failure state
    activations: Dict[str, FieldActivation] = {}
    for tongue in BASE_TONGUES:
        pf = PHYSICS_FIELDS[tongue]
        dev = _tongue_deviation(trit, tongue)
        weight = TONGUE_WEIGHTS[tongue]

        # Activation = deviation scaled by tongue weight (phi-weighted salience)
        activation = min(1.0, dev * weight / TONGUE_WEIGHTS["dr"])

        # Failure if deviation exceeds threshold
        is_failing = dev > FAILURE_THRESHOLD
        failure_sev = 0.0
        if is_failing:
            # Severity scales with how far past threshold
            overshoot = (dev - FAILURE_THRESHOLD) / (0.15 - FAILURE_THRESHOLD)
            failure_sev = min(1.0, max(0.0, overshoot))

        activations[tongue] = FieldActivation(
            tongue=tongue,
            field_name=pf.field_name,
            activation=activation,
            deviation=dev,
            is_failing=is_failing,
            failure_severity=failure_sev,
        )

    # Step 2: Identify active and stressed coupling channels
    active_couplings = []
    stressed_couplings = []
    for code, ch in COUPLING_CHANNELS.items():
        p1, p2 = ch.parent_tongues
        a1 = activations[p1]
        a2 = activations[p2]

        if a1.is_active and a2.is_active:
            active_couplings.append(code)

        if a1.is_failing or a2.is_failing:
            stressed_couplings.append(code)

    # Step 3: Cascade failures through coupling channels
    cascade_edges: List[CascadeEdge] = []
    failing_tongues = {t for t, fa in activations.items() if fa.is_failing}

    # One round of propagation (no infinite cascade — bounded by 6 fields)
    newly_failed: Set[str] = set()
    for source in list(failing_tongues):
        source_sev = activations[source].failure_severity
        for code, ch in COUPLING_CHANNELS.items():
            p1, p2 = ch.parent_tongues
            # Find the target (the other end of the channel)
            if p1 == source:
                target = p2
            elif p2 == source:
                target = p1
            else:
                continue

            if target in failing_tongues:
                continue  # already failing, don't double-count

            cs = coupling_strength(p1, p2)
            induced = source_sev * cs

            if induced > 0.3:  # propagation threshold
                cascade_edges.append(CascadeEdge(
                    source_tongue=source,
                    target_tongue=target,
                    channel_code=code,
                    phenomenon=ch.phenomenon,
                    propagation_strength=induced,
                ))
                # Induce failure in target
                ta = activations[target]
                if not ta.is_failing:
                    activations[target] = FieldActivation(
                        tongue=ta.tongue,
                        field_name=ta.field_name,
                        activation=ta.activation,
                        deviation=ta.deviation,
                        is_failing=True,
                        failure_severity=min(1.0, induced),
                    )
                    newly_failed.add(target)

    failing_tongues |= newly_failed

    # Step 4: Compute aggregate stats
    dominant = max(activations.values(), key=lambda fa: fa.activation)
    total_energy = sum(
        fa.activation * TONGUE_WEIGHTS[fa.tongue]
        for fa in activations.values()
    )

    return PhysicsDomainState(
        field_activations=activations,
        active_couplings=sorted(active_couplings),
        stressed_couplings=sorted(stressed_couplings),
        cascade_edges=cascade_edges,
        dominant_field=dominant.tongue,
        total_field_energy=round(total_energy, 4),
        failure_count=len(failing_tongues),
    )


# ---------------------------------------------------------------------------
# Recovery Path Mapping
# ---------------------------------------------------------------------------

def required_recovery_fields(failing_tongues: List[str]) -> List[str]:
    """Given failing tongues, which hybrid channels are needed for recovery?

    Recovery requires activating the coupling channels BETWEEN failing fields
    and their non-failing neighbors. The hybrid tongue invocation IS the
    recovery protocol.

    Returns hybrid codes sorted by coupling strength (strongest first).
    """
    failing_set = set(failing_tongues)
    healthy_set = set(BASE_TONGUES) - failing_set
    recovery_channels = []

    for code, ch in COUPLING_CHANNELS.items():
        p1, p2 = ch.parent_tongues
        # Channel bridges a failing field to a healthy one
        if (p1 in failing_set and p2 in healthy_set) or \
           (p2 in failing_set and p1 in healthy_set):
            cs = coupling_strength(p1, p2)
            recovery_channels.append((code, cs))

    recovery_channels.sort(key=lambda x: x[1], reverse=True)
    return [code for code, _ in recovery_channels]


# ---------------------------------------------------------------------------
# SFT Flattening
# ---------------------------------------------------------------------------

def flatten_physics_domain_for_sft(state: PhysicsDomainState) -> dict:
    """Flatten physics domain state into SFT-compatible metadata dict."""
    return {
        "physics_dominant_field": PHYSICS_FIELDS[state.dominant_field].field_name,
        "physics_dominant_tongue": state.dominant_field,
        "physics_active_fields": state.active_field_names,
        "physics_active_phenomena": state.active_phenomena,
        "physics_failure_count": state.failure_count,
        "physics_is_cascading": state.is_cascading,
        "physics_cascade_depth": state.cascade_depth,
        "physics_failing_tongues": state.failing_tongues,
        "physics_total_field_energy": state.total_field_energy,
        "physics_stressed_couplings": [
            COUPLING_CHANNELS[c].phenomenon for c in state.stressed_couplings
        ],
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def format_physics_domain_report(state: PhysicsDomainState) -> str:
    """Human-readable physics domain report."""
    lines = [
        "=" * 70,
        "PHYSICS DOMAIN STATE REPORT",
        "=" * 70,
        "",
        "Principle: Physics is not one field — it's a relationship of fields.",
        "Each Sacred Tongue IS a physics field. Their hybrids ARE couplings.",
        "",
        "--- Field Activations ---",
    ]

    for tongue in BASE_TONGUES:
        fa = state.field_activations[tongue]
        pf = PHYSICS_FIELDS[tongue]
        status = "FAILING" if fa.is_failing else ("active" if fa.is_active else "dormant")
        lines.append(
            f"  {tongue.upper():2s} | {pf.field_name:25s} | "
            f"act={fa.activation:.3f} | dev={fa.deviation:.4f} | {status}"
            + (f" (sev={fa.failure_severity:.3f})" if fa.is_failing else "")
        )

    lines.append(f"\nDominant: {state.dominant_field.upper()} "
                 f"({PHYSICS_FIELDS[state.dominant_field].field_name})")
    lines.append(f"Total field energy: {state.total_field_energy:.4f}")
    lines.append(f"Failures: {state.failure_count}/6")

    if state.active_couplings:
        lines.append("\n--- Active Couplings ---")
        for code in state.active_couplings:
            ch = COUPLING_CHANNELS[code]
            lines.append(f"  {ch.hybrid_name:18s} | {ch.phenomenon:35s} | "
                         f"{ch.field_a} ↔ {ch.field_b}")

    if state.stressed_couplings:
        lines.append("\n--- Stressed Couplings ---")
        for code in state.stressed_couplings:
            ch = COUPLING_CHANNELS[code]
            lines.append(f"  {ch.hybrid_name:18s} | {ch.failure_cascade[:60]}")

    if state.cascade_edges:
        lines.append("\n--- Failure Cascade ---")
        for edge in state.cascade_edges:
            ch = COUPLING_CHANNELS[edge.channel_code]
            lines.append(
                f"  {edge.source_tongue.upper()} → {edge.target_tongue.upper()} "
                f"via {ch.hybrid_name} ({edge.phenomenon}) "
                f"strength={edge.propagation_strength:.3f}"
            )

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)
