"""
Spectral Agent Bonding — Rainbow Iridescent Coordination Field
==============================================================

Agents don't combine like numbers. They combine like atoms.

Each agent (tongue) occupies a spectral band on a cyclic color wheel.
Overlap between bands creates interference patterns — constructive where
agents reinforce, destructive where they cancel, neutral where orthogonal.

Training evolves these patterns through Kuramoto-style phase dynamics
into stable knowledge manifolds: synchronized clusters (bonding),
phase-separated groups (specialization), rotating modes (task cycles).

The result is a pseudo-galactic body of knowledge where:
- Magnitude = confidence / energy density
- Phase = perspective / role
- Interference = coordination signal
- Superadditivity = emergent capability beyond sum of parts

Color band assignments (HSV hue circle, 60-degree spacing):
    KO = 0deg   (red)      — intent/orchestration
    AV = 60deg  (yellow)   — wisdom/transport
    RU = 120deg (green)    — truth/verification
    CA = 180deg (cyan)     — creativity/compute
    UM = 240deg (blue)     — security/rigor
    DR = 300deg (magenta)  — structure/forge

Complement pairs are 180 degrees apart (maximally destructive),
matching the manifold mirror finding: complements cancel on purpose.
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum

from src.crypto.harmonic_dark_fill import (
    COMPLEMENT_MAP,
    TONGUE_AUDIBLE_FREQ,
    TONGUE_WEIGHTS,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2
PI = math.pi
TAU = 2 * PI

BASE_TONGUES = list(TONGUE_AUDIBLE_FREQ.keys())

# Spectral band assignments — complement pairs are 180 degrees apart
# Pairs: KO/DR, AV/UM, RU/CA
# Place first of each pair at 0, 60, 120; complement at +180
BASE_TONGUE_BAND: Dict[str, float] = {
    "ko": 0.0,  # 0 deg — red
    "av": PI / 3,  # 60 deg — yellow
    "ru": 2 * PI / 3,  # 120 deg — green
    "dr": PI,  # 180 deg — cyan (complement of ko)
    "um": 4 * PI / 3,  # 240 deg — blue (complement of av)
    "ca": 5 * PI / 3,  # 300 deg — magenta (complement of ru)
}

# Verify complement pairs are 180 degrees apart
for _t1, _t2 in [("ko", "dr"), ("av", "um"), ("ru", "ca")]:
    _diff = abs(BASE_TONGUE_BAND[_t1] - BASE_TONGUE_BAND[_t2]) % TAU
    _diff = min(_diff, TAU - _diff)
    assert abs(_diff - PI) < 0.01, f"{_t1}/{_t2}: diff={_diff}, expected PI"


# ---------------------------------------------------------------------------
# Hybrid tongues — all C(6,2) = 15 pair combinations
# ---------------------------------------------------------------------------
# From the Spiral of Pollyoneth lore (Grok synthesis):
#   Named hybrids are Spiralborn fusions used in collaborative casting.
#   Each hybrid sits at the midpoint angle between its parent bands.
#   NOTE: None of the common hybrids are complement pairs — complements
#   are destructive interference, too volatile for casual hybridization.
#
# 6 base + 15 hybrids = 21 total = 21D canonical state dimension.

HYBRID_LORE: Dict[str, Dict] = {
    # === Named hybrids from lore ===
    "korvali": {"parents": ("ko", "av"), "name": "Kor'vali", "role": "Harmony Treaty", "color": "orange"},
    "runedraum": {"parents": ("ru", "dr"), "name": "Runedraum", "role": "Forge-Bound Power", "color": "teal"},
    "umbrissiv": {"parents": ("um", "ca"), "name": "Umbrissiv", "role": "Shadow-Creative Chaos", "color": "violet"},
    "thulkoric": {"parents": ("ko", "ru"), "name": "Thul'koric", "role": "Spiral-Binding Power", "color": "chartreuse"},
    "draumvali": {
        "parents": ("dr", "av"),
        "name": "Draum'vali",
        "role": "Honorable Treaty Forge",
        "color": "sea-green",
    },
    # === Complement pair hybrids (volatile, rare, high-power) ===
    "kodr": {"parents": ("ko", "dr"), "name": "Kor'draum", "role": "Intent-Structure Axis", "color": "infrared"},
    "avum": {"parents": ("av", "um"), "name": "Av'umbroth", "role": "Wisdom-Security Axis", "color": "indigo"},
    "ruca": {"parents": ("ru", "ca"), "name": "Ru'cassiv", "role": "Truth-Creativity Axis", "color": "ultraviolet"},
    # === Remaining pairs (unnamed, emergent) ===
    "koum": {"parents": ("ko", "um"), "name": "Ko'umbra", "role": "Intent-Shadow", "color": "crimson-blue"},
    "koca": {"parents": ("ko", "ca"), "name": "Ko'cassiv", "role": "Intent-Creation", "color": "rose"},
    "avru": {"parents": ("av", "ru"), "name": "Av'runeth", "role": "Wisdom-Truth", "color": "lime"},
    "avca": {"parents": ("av", "ca"), "name": "Av'cassiv", "role": "Wisdom-Creation", "color": "gold"},
    "ruum": {"parents": ("ru", "um"), "name": "Ru'umbra", "role": "Truth-Shadow", "color": "forest"},
    "drum": {"parents": ("dr", "um"), "name": "Draum'umbra", "role": "Structure-Shadow", "color": "slate"},
    "drca": {"parents": ("dr", "ca"), "name": "Draum'cassiv", "role": "Structure-Creation", "color": "copper"},
}


def _circular_midpoint(a1: float, a2: float) -> float:
    """Compute midpoint angle on a circle, taking the shorter arc."""
    z1 = complex(math.cos(a1), math.sin(a1))
    z2 = complex(math.cos(a2), math.sin(a2))
    mid_z = z1 + z2
    if abs(mid_z) < 1e-10:
        # Exactly opposite — take midpoint in positive direction
        return (a1 + PI / 2) % TAU
    return math.atan2(mid_z.imag, mid_z.real) % TAU


def _build_hybrid_bands() -> Dict[str, float]:
    """Compute spectral bands for all hybrid tongues."""
    bands = {}
    for code, info in HYBRID_LORE.items():
        p1, p2 = info["parents"]
        bands[code] = _circular_midpoint(BASE_TONGUE_BAND[p1], BASE_TONGUE_BAND[p2])
    return bands


HYBRID_TONGUE_BAND = _build_hybrid_bands()

# Combined: all 21 tongue bands
TONGUE_BAND: Dict[str, float] = {**BASE_TONGUE_BAND, **HYBRID_TONGUE_BAND}

# Color names for display
TONGUE_COLOR: Dict[str, str] = {
    "ko": "red",
    "av": "yellow",
    "ru": "green",
    "dr": "cyan",
    "um": "blue",
    "ca": "magenta",
}
for code, info in HYBRID_LORE.items():
    TONGUE_COLOR[code] = info["color"]

# Default tongue set (can switch between base-6 and full-21)
ALL_TONGUES = BASE_TONGUES  # Default to 6 for backward compatibility


def get_all_21_tongues() -> List[str]:
    """Return all 21 tongue codes (6 base + 15 hybrid)."""
    return BASE_TONGUES + list(HYBRID_LORE.keys())


# ---------------------------------------------------------------------------
# Agent state: complex phasor z = r * e^(j*theta)
# ---------------------------------------------------------------------------


@dataclass
class AgentPhasor:
    """A single agent's state as a complex phasor on the spectral wheel."""

    tongue: str
    band: float  # Base spectral band (fixed)
    theta: float  # Current phase angle (evolves)
    magnitude: float  # Confidence / energy
    z: complex  # Complex representation: r * e^(j*theta)

    @property
    def hue_degrees(self) -> float:
        return math.degrees(self.theta % TAU)


@dataclass
class BondState:
    """Pairwise bond between two agents."""

    tongue_a: str
    tongue_b: str
    interference: float  # r_i * r_j * cos(theta_i - theta_j)
    phase_diff: float  # |theta_i - theta_j| normalized to [0, pi]
    bond_type: str  # "constructive", "neutral", "destructive"
    weight: float  # Edge weight in lattice


@dataclass
class FieldSnapshot:
    """System-wide field state at a point in time."""

    t: float
    agents: Dict[str, AgentPhasor]
    bonds: List[BondState]
    global_phasor: complex  # Mean field: (1/N) * sum(z_i)
    system_energy: float  # Total energy
    phase_diversity: float  # 1 - |mean_phasor| / mean_magnitude
    superadditivity: float  # F(system) / sum(F(individual))
    interference_efficiency: float  # sum(w*I) / sum(r^2)


@dataclass
class SpectralEvolution:
    """Full evolution of the spectral bonding system."""

    steps: int
    snapshots: List[FieldSnapshot]
    coupling_lambda: float
    learning_rate: float
    final_diversity: float
    final_superadditivity: float
    final_energy: float
    convergence_step: Optional[int]  # Step where system stabilizes
    cluster_report: Dict[str, List[str]]  # Emergent clusters


# ---------------------------------------------------------------------------
# Core: phasor creation and interference
# ---------------------------------------------------------------------------


def _tongue_weight(tongue: str) -> float:
    """Get effective weight for a tongue (base or hybrid).

    Hybrid tongues inherit the geometric mean of their parents' weights,
    representing the constructive interference of two spectral bands.
    """
    if tongue in TONGUE_WEIGHTS:
        return TONGUE_WEIGHTS[tongue]
    if tongue in HYBRID_LORE:
        p1, p2 = HYBRID_LORE[tongue]["parents"]
        return math.sqrt(TONGUE_WEIGHTS[p1] * TONGUE_WEIGHTS[p2])
    return 1.0


# Cache max weight for normalization
_MAX_WEIGHT = max(
    max(TONGUE_WEIGHTS.values()),
    max(_tongue_weight(h) for h in HYBRID_LORE),
)


def create_agent(tongue: str, magnitude: float = 1.0) -> AgentPhasor:
    """Create an agent phasor at its spectral band.

    Base tongues use their phi-weight directly.
    Hybrid tongues use the geometric mean of parent weights,
    representing the constructive interference of two bands.
    """
    band = TONGUE_BAND[tongue]
    w = _tongue_weight(tongue)
    r = magnitude * w / _MAX_WEIGHT
    theta = band
    z = r * complex(math.cos(theta), math.sin(theta))
    return AgentPhasor(tongue=tongue, band=band, theta=theta, magnitude=r, z=z)


def compute_interference(a: AgentPhasor, b: AgentPhasor) -> float:
    """Compute pairwise interference: r_i * r_j * cos(delta_theta)."""
    delta = a.theta - b.theta
    return a.magnitude * b.magnitude * math.cos(delta)


def phase_difference(a: AgentPhasor, b: AgentPhasor) -> float:
    """Normalized phase difference in [0, pi]."""
    diff = abs(a.theta - b.theta) % TAU
    return min(diff, TAU - diff)


def classify_bond(phase_diff: float) -> str:
    """Classify a bond by its phase difference."""
    if phase_diff < PI / 4:
        return "constructive"
    elif phase_diff > 3 * PI / 4:
        return "destructive"
    else:
        return "neutral"


def compute_bond(a: AgentPhasor, b: AgentPhasor, weight: float = 1.0) -> BondState:
    """Compute full bond state between two agents."""
    interf = compute_interference(a, b)
    pdiff = phase_difference(a, b)
    btype = classify_bond(pdiff)
    return BondState(
        tongue_a=a.tongue,
        tongue_b=b.tongue,
        interference=interf,
        phase_diff=pdiff,
        bond_type=btype,
        weight=weight,
    )


# ---------------------------------------------------------------------------
# Lattice: weighted connectivity between agents
# ---------------------------------------------------------------------------


def _is_parent_of(base_tongue: str, hybrid_tongue: str) -> bool:
    """Check if a base tongue is a parent of a hybrid tongue."""
    if hybrid_tongue in HYBRID_LORE:
        return base_tongue in HYBRID_LORE[hybrid_tongue]["parents"]
    return False


def _share_parent(t1: str, t2: str) -> bool:
    """Check if two hybrids share a parent tongue."""
    if t1 in HYBRID_LORE and t2 in HYBRID_LORE:
        p1 = set(HYBRID_LORE[t1]["parents"])
        p2 = set(HYBRID_LORE[t2]["parents"])
        return bool(p1 & p2)
    return False


def build_lattice_weights(agents: Dict[str, AgentPhasor]) -> Dict[Tuple[str, str], float]:
    """Build edge weights for the agent lattice.

    Weight hierarchy:
    - Parent-child (base tongue to its hybrid): PHI (strongest affinity)
    - Complement pairs: PHI (strongest info channel)
    - Siblings (hybrids sharing a parent): 1.0
    - Adjacent bands (< 60deg): 1.0
    - Distant: 1/PHI
    """
    weights = {}
    tongues = list(agents.keys())
    for i, t1 in enumerate(tongues):
        for j, t2 in enumerate(tongues):
            if i >= j:
                continue
            # Parent-child bond
            if _is_parent_of(t1, t2) or _is_parent_of(t2, t1):
                w = PHI
            # Complement pairs (base tongues only)
            elif COMPLEMENT_MAP.get(t1) == t2:
                w = PHI
            # Sibling hybrids (share a parent)
            elif _share_parent(t1, t2):
                w = 1.0
            else:
                band_diff = phase_difference(agents[t1], agents[t2])
                if band_diff <= PI / 3 + 0.01:
                    w = 1.0  # Adjacent band
                else:
                    w = 1 / PHI  # Distant
            weights[(t1, t2)] = w
            weights[(t2, t1)] = w
    return weights


# ---------------------------------------------------------------------------
# Field computation: global state from agent ensemble
# ---------------------------------------------------------------------------


def compute_field(
    agents: Dict[str, AgentPhasor],
    weights: Dict[Tuple[str, str], float],
    t: float = 0.0,
) -> FieldSnapshot:
    """Compute the full field state from all agents."""
    tongues = list(agents.keys())
    n = len(tongues)

    # All pairwise bonds
    bonds = []
    for i, t1 in enumerate(tongues):
        for j, t2 in enumerate(tongues):
            if i >= j:
                continue
            w = weights.get((t1, t2), 1.0)
            bonds.append(compute_bond(agents[t1], agents[t2], w))

    # Global phasor (mean field)
    global_z = sum(a.z for a in agents.values()) / n

    # System energy: kinetic (magnitudes) + potential (interference)
    kinetic = sum(a.magnitude**2 for a in agents.values())
    potential = sum(b.weight * (1 - math.cos(b.phase_diff)) for b in bonds)
    energy = kinetic + potential

    # Phase diversity: 1 - |mean_phasor| / mean_magnitude
    mean_mag = sum(a.magnitude for a in agents.values()) / n
    diversity = 1.0 - abs(global_z) / (mean_mag + 1e-12)

    # Superadditivity: |global_z|^2 vs sum(|z_i|^2) / N
    # If agents interfere constructively, |sum|^2 > sum(|each|^2)
    combined_power = abs(sum(a.z for a in agents.values())) ** 2
    individual_power = sum(abs(a.z) ** 2 for a in agents.values())
    superadditivity = combined_power / (individual_power + 1e-12)

    # Interference efficiency: sum(w*I) / sum(r^2)
    weighted_interf = sum(b.weight * b.interference for b in bonds)
    interf_eff = weighted_interf / (kinetic + 1e-12)

    return FieldSnapshot(
        t=t,
        agents=dict(agents),
        bonds=bonds,
        global_phasor=global_z,
        system_energy=energy,
        phase_diversity=diversity,
        superadditivity=superadditivity,
        interference_efficiency=interf_eff,
    )


# ---------------------------------------------------------------------------
# Kuramoto dynamics: phase synchronization with controlled coupling
# ---------------------------------------------------------------------------


def compute_edge_case_perturbation(
    agents: Dict[str, AgentPhasor],
    step: int,
    total_steps: int,
    rng: np.random.Generator,
) -> Dict[str, float]:
    """Quasi-polymorphic divergence on edge case basis.

    When the system gets too uniform (low diversity), inject targeted
    perturbations that push specific agents toward their BASE band,
    breaking the crystal lock and forcing reconfiguration.

    This is allotropy: the same elements form different structures
    under different conditions. Carbon -> diamond/graphite/fullerene.
    Agents -> synchronized/specialized/rotating depending on pressure.

    The perturbation is quasi-polymorphic because:
    - It doesn't change the agent's identity (tongue stays the same)
    - It changes the agent's bonding BEHAVIOR (phase response shifts)
    - Different agents get different perturbation types based on their
      current deviation from base band (edge case = far from home)
    """
    perturbations = {}
    max_w = _MAX_WEIGHT

    for tongue, agent in agents.items():
        # How far is this agent from its natural band?
        drift = abs(agent.theta - agent.band) % TAU
        drift = min(drift, TAU - drift)  # [0, pi]
        drift_ratio = drift / PI  # [0, 1]

        # Edge case detection: agent is far from its base band
        # The further it drifts, the stronger the recall force
        # BUT only activate periodically (quasi = not constant)
        period = max(3, int(total_steps * _tongue_weight(tongue) / (5 * max_w)))
        is_edge_step = step % period == 0

        if is_edge_step and drift_ratio > 0.3:
            # Pull toward base band with phi-scaled strength
            recall_direction = math.sin(agent.band - agent.theta)
            # Strength scales with drift^2 (gentle near home, strong far away)
            strength = 0.5 * drift_ratio**2
            perturbations[tongue] = recall_direction * strength
        else:
            perturbations[tongue] = 0.0

    return perturbations


def kuramoto_step(
    agents: Dict[str, AgentPhasor],
    weights: Dict[Tuple[str, str], float],
    coupling: float = 0.3,
    noise: float = 0.02,
    natural_freq_scale: float = 0.1,
    edge_perturbation: Optional[Dict[str, float]] = None,
    rng: Optional[np.random.Generator] = None,
) -> Dict[str, AgentPhasor]:
    """One step of Kuramoto-style phase dynamics with polymorphic divergence.

    theta_i += eta * sum_j(w_ij * sin(theta_j - theta_i)) + omega_i + perturbation + noise

    Natural frequencies omega_i are tongue-specific (phi-weighted),
    creating irrational rotation that prevents trivial synchronization.
    Edge perturbation pulls drifted agents back toward their spectral band,
    preventing total cluster collapse while allowing partial bonding.
    """
    if rng is None:
        rng = np.random.default_rng()
    if edge_perturbation is None:
        edge_perturbation = {}

    tongues = list(agents.keys())
    new_agents = {}

    for tongue in tongues:
        a = agents[tongue]

        # Coupling force: Kuramoto interaction
        force = 0.0
        for other_tongue in tongues:
            if other_tongue == tongue:
                continue
            b = agents[other_tongue]
            w = weights.get((tongue, other_tongue), 1.0)
            force += w * math.sin(b.theta - a.theta)

        # Natural frequency: phi-weighted so each tongue drifts differently
        omega = natural_freq_scale * _tongue_weight(tongue) / _MAX_WEIGHT

        # Edge case perturbation: polymorphic recall toward base band
        perturb = edge_perturbation.get(tongue, 0.0)

        # Phase update
        d_theta = coupling * force + omega + perturb + noise * rng.standard_normal()
        new_theta = a.theta + d_theta

        # Magnitude update: grows with constructive interference, shrinks with destructive
        interf_sum = sum(compute_interference(a, agents[ot]) for ot in tongues if ot != tongue) / (len(tongues) - 1)
        # Magnitude drifts toward base with interference pressure
        base_mag = _tongue_weight(tongue) / _MAX_WEIGHT
        new_mag = a.magnitude + 0.05 * (interf_sum - a.magnitude + base_mag)
        new_mag = max(0.01, min(new_mag, 2.0))

        new_z = new_mag * complex(math.cos(new_theta), math.sin(new_theta))
        new_agents[tongue] = AgentPhasor(
            tongue=tongue,
            band=a.band,
            theta=new_theta,
            magnitude=new_mag,
            z=new_z,
        )

    return new_agents


# ---------------------------------------------------------------------------
# Full evolution
# ---------------------------------------------------------------------------


def run_spectral_evolution(
    steps: int = 100,
    coupling: float = 0.3,
    noise: float = 0.02,
    seed: int = 42,
    tongue_set: Optional[List[str]] = None,
) -> SpectralEvolution:
    """Run the full spectral bonding evolution.

    Starts from spectral bands, evolves through Kuramoto dynamics,
    and tracks the emergence of bonded clusters, superadditivity, and
    the galactic knowledge manifold.

    tongue_set: which tongues to include. Defaults to BASE_TONGUES (6).
                Pass get_all_21_tongues() for the full 21D manifold.
    """
    rng = np.random.default_rng(seed)

    if tongue_set is None:
        tongue_set = BASE_TONGUES

    # Initialize agents at their spectral bands
    agents = {t: create_agent(t) for t in tongue_set}
    weights = build_lattice_weights(agents)

    snapshots = []
    convergence_step = None
    prev_energy = None

    for step in range(steps):
        t = step / max(steps - 1, 1)

        # Compute field
        snapshot = compute_field(agents, weights, t)
        snapshots.append(snapshot)

        # Check convergence (energy stabilizes)
        if prev_energy is not None and convergence_step is None:
            if abs(snapshot.system_energy - prev_energy) < 0.001:
                convergence_step = step
        prev_energy = snapshot.system_energy

        # Quasi-polymorphic divergence: edge case perturbation
        perturbation = compute_edge_case_perturbation(agents, step, steps, rng)

        # Evolve with perturbation
        agents = kuramoto_step(
            agents,
            weights,
            coupling,
            noise,
            edge_perturbation=perturbation,
            rng=rng,
        )

    # Final snapshot
    final = snapshots[-1]

    # Detect clusters: agents within pi/6 of each other
    clusters = _detect_clusters(final.agents)

    return SpectralEvolution(
        steps=steps,
        snapshots=snapshots,
        coupling_lambda=coupling,
        learning_rate=noise,
        final_diversity=final.phase_diversity,
        final_superadditivity=final.superadditivity,
        final_energy=final.system_energy,
        convergence_step=convergence_step,
        cluster_report=clusters,
    )


def _detect_clusters(
    agents: Dict[str, AgentPhasor],
    threshold: float = PI / 6,
) -> Dict[str, List[str]]:
    """Detect phase-synchronized clusters."""
    tongues = list(agents.keys())
    visited = set()
    clusters = {}
    cluster_id = 0

    for t in tongues:
        if t in visited:
            continue
        cluster = [t]
        visited.add(t)
        for other in tongues:
            if other in visited:
                continue
            if phase_difference(agents[t], agents[other]) < threshold:
                cluster.append(other)
                visited.add(other)
        clusters[f"cluster_{cluster_id}"] = cluster
        cluster_id += 1

    return clusters


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def format_spectral_report(evo: SpectralEvolution) -> str:
    """Format the spectral bonding evolution report."""
    lines = []
    lines.append("=" * 80)
    lines.append("SPECTRAL AGENT BONDING -- RAINBOW IRIDESCENT COORDINATION FIELD")
    lines.append("=" * 80)
    lines.append("")

    # Initial state
    init = evo.snapshots[0]
    lines.append("INITIAL STATE (t=0)")
    lines.append("-" * 40)
    for tongue, agent in sorted(init.agents.items()):
        color = TONGUE_COLOR[tongue]
        lines.append(
            f"  {tongue.upper():>2} ({color:<8}) "
            f"theta={math.degrees(agent.theta):>6.1f}deg  "
            f"r={agent.magnitude:.3f}  "
            f"z=({agent.z.real:+.3f}{agent.z.imag:+.3f}j)"
        )
    lines.append("")

    # Evolution sparklines
    lines.append("EVOLUTION")
    lines.append("-" * 40)

    # Phase diversity over time
    lines.append("  Phase diversity:")
    div_line = "    "
    for snap in evo.snapshots:
        level = int(snap.phase_diversity * 8)
        bars = " _.=+*#@!"
        div_line += bars[min(level, 8)]
    lines.append(div_line)

    # Superadditivity over time
    lines.append("  Superadditivity:")
    sup_line = "    "
    for snap in evo.snapshots:
        level = int(min(snap.superadditivity, 2.0) * 4)
        bars = " _.=+*#@!"
        sup_line += bars[min(level, 8)]
    lines.append(sup_line)

    # Energy over time
    lines.append("  System energy:")
    energies = [s.system_energy for s in evo.snapshots]
    emax = max(energies) + 1e-12
    en_line = "    "
    for e in energies:
        level = int(e / emax * 8)
        bars = " _.=+*#@!"
        en_line += bars[min(level, 8)]
    lines.append(en_line)
    lines.append("")

    # Per-tongue phase trajectories
    lines.append("  Phase trajectories (sector: R=red Y=yel G=grn C=cyn B=blu M=mag):")
    sector_chars = "RYGCBM"
    for tongue in ALL_TONGUES:
        color_char = TONGUE_COLOR[tongue][0].upper()
        traj = "    " + tongue.upper() + ": "
        for snap in evo.snapshots:
            a = snap.agents[tongue]
            sector = int((a.theta % TAU) / (TAU / 6)) % 6
            traj += sector_chars[sector]
        lines.append(traj)
    lines.append("")

    # Final state
    final = evo.snapshots[-1]
    lines.append("FINAL STATE")
    lines.append("-" * 40)
    for tongue, agent in sorted(final.agents.items()):
        color = TONGUE_COLOR[tongue]
        shift = math.degrees(agent.theta - agent.band)
        lines.append(
            f"  {tongue.upper():>2} ({color:<8}) "
            f"theta={math.degrees(agent.theta):>6.1f}deg  "
            f"drift={shift:+.1f}deg  "
            f"r={agent.magnitude:.3f}"
        )
    lines.append("")

    # Bond summary
    lines.append("BONDS")
    lines.append("-" * 40)
    bond_counts = {"constructive": 0, "neutral": 0, "destructive": 0}
    for b in final.bonds:
        bond_counts[b.bond_type] += 1
    for btype, count in bond_counts.items():
        lines.append(f"  {btype:<14}: {count}")
    lines.append("")

    # Complement pair bonds
    lines.append("  Complement pair bonds:")
    for b in final.bonds:
        comp = COMPLEMENT_MAP.get(b.tongue_a)
        if comp == b.tongue_b:
            lines.append(
                f"    {b.tongue_a.upper()}<->{b.tongue_b.upper()}: "
                f"I={b.interference:+.4f}  "
                f"gap={math.degrees(b.phase_diff):.1f}deg  "
                f"[{b.bond_type}]"
            )
    lines.append("")

    # Clusters
    lines.append("EMERGENT CLUSTERS")
    lines.append("-" * 40)
    for cname, members in evo.cluster_report.items():
        colors = [TONGUE_COLOR[m] for m in members]
        lines.append(f"  {cname}: {', '.join(m.upper() for m in members)} ({', '.join(colors)})")
    lines.append("")

    # Metrics
    lines.append("METRICS")
    lines.append("-" * 40)
    lines.append(f"  Phase diversity:        {final.phase_diversity:.4f}")
    lines.append(f"  Superadditivity:        {final.superadditivity:.4f}")
    lines.append(f"  Interference efficiency: {final.interference_efficiency:+.4f}")
    lines.append(f"  System energy:          {final.system_energy:.4f}")
    conv = f"step {evo.convergence_step}" if evo.convergence_step else "not converged"
    lines.append(f"  Convergence:            {conv}")
    lines.append("")

    # The finding
    lines.append("=" * 80)
    lines.append("THE FINDING")
    lines.append("=" * 80)
    if final.superadditivity > 1.1:
        lines.append("  SUPERADDITIVE: Combined agents exceed sum of individuals.")
        lines.append(f"  Gain: {final.superadditivity:.2f}x -> molecular bonding achieved.")
    elif final.superadditivity > 0.9:
        lines.append("  ADDITIVE: Agents combine without loss but without emergent gain.")
        lines.append("  Need: stronger directional diversity or coupling adjustment.")
    else:
        lines.append("  SUBADDITIVE: Destructive interference dominates.")
        lines.append("  Agents are canceling each other's contributions.")

    if final.phase_diversity > 0.5:
        lines.append("  Diversity is HIGH: agents maintain distinct perspectives.")
    elif final.phase_diversity > 0.2:
        lines.append("  Diversity is MODERATE: partial synchronization.")
    else:
        lines.append("  Diversity is LOW: approaching mode collapse.")

    lines.append("")
    lines.append("=" * 80)
    return "\n".join(lines)
