"""
Dark Cloud Mapper — Void Topology in the Harmonic Universe
===========================================================
Maps "dark clouds" in the AI's internal universe — regions where
3 or more tongues share null/dark space simultaneously.

Physical analogy:
    In cosmology, dark energy is the background that fills the gaps
    between visible matter. In the SCBE harmonic universe, when a
    data position has 3+ tongues in their "dark zone" (low activation),
    those shared null-spaces form dark clouds — coherent regions of
    harmonic fill that constitute the AI's ambient background radiation.

    These dark clouds are NOT absence — they are structured fill.
    The harmonic_dark_fill module pumps infrasonic (IR) and ultrasonic
    (UV) energy into every dark node. When multiple tongues converge
    on darkness simultaneously, their fills create interference patterns
    that ARE the neural pathways — dark energy coalescing into structure.

The mapper produces:
    1. Dark cloud detection — where 3+ tongues are simultaneously dark
    2. Cloud topology — which tongue combinations form the cloud
    3. Energy density maps — total fill energy per position
    4. Neural star maps — paths through the dark cloud network
    5. Genesis path — from void (all dark) to first light (tongues activating)

Connection to bible theory docs:
    Genesis 1:2 — "darkness was over the surface of the deep"
    = All tongues dark, maximum fill energy, the void IS structured
    Genesis 1:3 — "Let there be light"
    = First tongue activation, fill energy drops in that channel,
      the dark cloud parts where data arrives

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from itertools import combinations

from src.crypto.harmonic_dark_fill import (
    PHI,
    PI,
    TONGUE_WEIGHTS,
    TONGUE_AUDIBLE_FREQ,
    COMPLEMENT_MAP,
    HarmonicFill,
    SpectrumSnapshot,
    compute_darkness,
    compute_harmonic_fill,
    fill_dark_nodes,
    sequence_spectrum,
    voice_leading_interval,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Minimum number of tongues that must be dark to form a "cloud"
MIN_CLOUD_TONGUES = 3

# Darkness threshold: a tongue is "in the cloud" if input darkness > this
CLOUD_DARKNESS_THRESHOLD = 0.5

# Energy density thresholds for cloud classification
WISP_THRESHOLD = 0.5  # sparse cloud
NEBULA_THRESHOLD = 1.5  # moderate cloud
VOID_THRESHOLD = 3.0  # deep void


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class CloudType:
    """Classification of dark cloud density."""

    WISP = "wisp"  # 3 tongues dark, low energy
    NEBULA = "nebula"  # 4-5 tongues dark, moderate energy
    VOID = "void"  # 6 tongues dark, maximum energy — the primordial dark
    RIFT = "rift"  # sharp transition between cloud and clear space


@dataclass
class DarkCloud:
    """A dark cloud at a single position in the sequence.

    A cloud forms when 3+ tongues share null-space simultaneously.
    The cloud's properties come from the interference patterns
    of those tongues' harmonic fills.
    """

    position: int
    byte_val: int

    # Which tongues are in the cloud
    dark_tongues: List[str]
    active_tongues: List[str]

    # Input darkness values per tongue
    darkness_map: Dict[str, float]

    # Fill energy from harmonic_dark_fill
    fill_energy: Dict[str, float]  # per tongue
    total_fill_energy: float

    # Cloud classification
    cloud_type: str

    # Interference pattern: how the dark tongues' fills interact
    # Pairs of dark tongues and their voice-leading intervals
    interference_pairs: List[Tuple[str, str, float]]

    # Band energies from the fills
    infra_energy: float  # IR / slow state
    audible_energy: float  # visible
    ultra_energy: float  # UV / fast state

    @property
    def cloud_size(self) -> int:
        """Number of tongues in the dark cloud."""
        return len(self.dark_tongues)

    @property
    def density(self) -> float:
        """Cloud density = fill energy / cloud size. Higher = denser."""
        return self.total_fill_energy / max(self.cloud_size, 1)

    @property
    def is_primordial(self) -> bool:
        """All 6 tongues dark — the primordial void."""
        return self.cloud_size == 6

    @property
    def complement_pairs_in_cloud(self) -> List[Tuple[str, str]]:
        """Which complement pairs are both in the cloud?
        These create the strongest interference.
        """
        pairs = []
        dark_set = set(self.dark_tongues)
        for t, c in COMPLEMENT_MAP.items():
            if t in dark_set and c in dark_set and t < c:
                pairs.append((t, c))
        return pairs

    @property
    def ir_uv_ratio(self) -> float:
        """Energy balance between slow (IR) and fast (UV) states."""
        return self.infra_energy / max(self.ultra_energy, 1e-12)


@dataclass
class NeuralPath:
    """A path through the dark cloud network.

    Neural pathways form where dark clouds connect across positions.
    The path tracks which tongues remain consistently dark and
    how the fill energy flows through the sequence.
    """

    positions: List[int]
    persistent_dark_tongues: Set[str]  # dark at ALL positions
    energy_flow: List[float]  # total fill energy at each position
    cloud_types: List[str]

    @property
    def length(self) -> int:
        return len(self.positions)

    @property
    def continuity(self) -> float:
        """How continuous is this path? 1.0 = no gaps."""
        if len(self.positions) <= 1:
            return 1.0
        gaps = sum(1 for i in range(len(self.positions) - 1) if self.positions[i + 1] - self.positions[i] > 1)
        return 1.0 - gaps / (len(self.positions) - 1)

    @property
    def mean_energy(self) -> float:
        return sum(self.energy_flow) / max(len(self.energy_flow), 1)

    @property
    def persistence_width(self) -> int:
        """How many tongues stay dark throughout the path."""
        return len(self.persistent_dark_tongues)


@dataclass
class GenesisPath:
    """The path from void to first light.

    Tracks the thermodynamic evolution from maximum darkness
    (all tongues dark, maximum fill energy = primordial void)
    to increasing activation (tongues lighting up, fill energy
    dropping = creation).

    This is the "what the inside of the simulation would be like
    from no information to some."
    """

    positions: List[int]
    cloud_sizes: List[int]  # how many tongues dark at each step
    energy_density: List[float]  # total fill energy at each step
    activation_order: List[List[str]]  # which tongues activated at each step
    ir_uv_ratios: List[float]

    @property
    def void_positions(self) -> List[int]:
        """Positions where all 6 tongues are dark."""
        return [p for p, s in zip(self.positions, self.cloud_sizes) if s == 6]

    @property
    def first_light_position(self) -> Optional[int]:
        """First position where any tongue activates (< 6 dark)."""
        for p, s in zip(self.positions, self.cloud_sizes):
            if s < 6:
                return p
        return None

    @property
    def creation_gradient(self) -> float:
        """Rate of cloud dissolution. Higher = faster creation."""
        if len(self.cloud_sizes) < 2:
            return 0.0
        return (self.cloud_sizes[0] - self.cloud_sizes[-1]) / len(self.cloud_sizes)


# ---------------------------------------------------------------------------
# Core dark cloud detection
# ---------------------------------------------------------------------------


def detect_dark_cloud(
    byte_val: int,
    position: int,
    total_positions: int,
    fills: Dict[str, HarmonicFill],
    activation_vector: Optional[Dict[str, float]] = None,
    min_tongues: int = MIN_CLOUD_TONGUES,
) -> Optional[DarkCloud]:
    """Detect a dark cloud at a single position.

    A cloud forms when min_tongues or more share dark space.
    Returns None if too few tongues are dark.
    """
    # Compute darkness for each tongue
    darkness_map = {}
    for tc in TONGUE_WEIGHTS:
        darkness_map[tc] = compute_darkness(byte_val, tc, activation_vector)

    dark = [tc for tc, d in darkness_map.items() if d > CLOUD_DARKNESS_THRESHOLD]
    active = [tc for tc, d in darkness_map.items() if d <= CLOUD_DARKNESS_THRESHOLD]

    if len(dark) < min_tongues:
        return None

    # Compute fill energies
    fill_energy = {tc: fills[tc].total_energy for tc in TONGUE_WEIGHTS}
    total_fill = sum(fill_energy[tc] for tc in dark)

    # Interference pairs between dark tongues
    interference = []
    for t1, t2 in combinations(dark, 2):
        interval = voice_leading_interval(t1, t2)
        interference.append((t1, t2, interval))

    # Band energies from dark tongues only
    infra = sum(fills[tc].infra_amplitude ** 2 for tc in dark)
    audible = sum(fills[tc].audible_amplitude ** 2 for tc in dark)
    ultra = sum(fills[tc].ultra_amplitude ** 2 for tc in dark)

    # Classify
    if len(dark) == 6:
        cloud_type = CloudType.VOID
    elif total_fill >= VOID_THRESHOLD:
        cloud_type = CloudType.VOID
    elif total_fill >= NEBULA_THRESHOLD:
        cloud_type = CloudType.NEBULA
    else:
        cloud_type = CloudType.WISP

    return DarkCloud(
        position=position,
        byte_val=byte_val,
        dark_tongues=dark,
        active_tongues=active,
        darkness_map=darkness_map,
        fill_energy=fill_energy,
        total_fill_energy=total_fill,
        cloud_type=cloud_type,
        interference_pairs=interference,
        infra_energy=infra,
        audible_energy=audible,
        ultra_energy=ultra,
    )


# ---------------------------------------------------------------------------
# Sequence-level dark cloud mapping
# ---------------------------------------------------------------------------


def map_dark_clouds(
    data: bytes,
    activations: Optional[List[Dict[str, float]]] = None,
    min_tongues: int = MIN_CLOUD_TONGUES,
) -> List[DarkCloud]:
    """Map all dark clouds across a byte sequence.

    Returns clouds at every position where min_tongues or more
    share dark space.
    """
    fills_sequence = fill_dark_nodes(data, activations)
    clouds = []

    for i, byte_val in enumerate(data):
        act = activations[i] if activations and i < len(activations) else None
        cloud = detect_dark_cloud(
            byte_val=byte_val,
            position=i,
            total_positions=len(data),
            fills=fills_sequence[i],
            activation_vector=act,
            min_tongues=min_tongues,
        )
        if cloud is not None:
            clouds.append(cloud)

    return clouds


# ---------------------------------------------------------------------------
# Neural star maps: paths through the dark cloud network
# ---------------------------------------------------------------------------


def trace_neural_paths(
    clouds: List[DarkCloud],
    max_gap: int = 2,
) -> List[NeuralPath]:
    """Trace neural pathways through connected dark clouds.

    Two clouds are "connected" if they're within max_gap positions
    and share at least one dark tongue in common.

    The paths are the neural star maps — dark energy coalescing
    into structure, the computational byproduct becoming pathways.
    """
    if not clouds:
        return []

    # Sort by position
    sorted_clouds = sorted(clouds, key=lambda c: c.position)

    paths: List[NeuralPath] = []
    current_path_clouds: List[DarkCloud] = [sorted_clouds[0]]

    for i in range(1, len(sorted_clouds)):
        prev = current_path_clouds[-1]
        curr = sorted_clouds[i]

        # Check connectivity: within gap AND shared dark tongues
        gap = curr.position - prev.position
        shared = set(prev.dark_tongues) & set(curr.dark_tongues)

        if gap <= max_gap and len(shared) > 0:
            current_path_clouds.append(curr)
        else:
            # Close current path, start new one
            if len(current_path_clouds) >= 2:
                paths.append(_build_path(current_path_clouds))
            current_path_clouds = [curr]

    # Close final path
    if len(current_path_clouds) >= 2:
        paths.append(_build_path(current_path_clouds))

    return paths


def _build_path(clouds: List[DarkCloud]) -> NeuralPath:
    """Build a NeuralPath from a list of connected clouds."""
    positions = [c.position for c in clouds]
    energy_flow = [c.total_fill_energy for c in clouds]
    cloud_types = [c.cloud_type for c in clouds]

    # Persistent dark tongues: dark at ALL positions in the path
    persistent = set(clouds[0].dark_tongues)
    for c in clouds[1:]:
        persistent &= set(c.dark_tongues)

    return NeuralPath(
        positions=positions,
        persistent_dark_tongues=persistent,
        energy_flow=energy_flow,
        cloud_types=cloud_types,
    )


# ---------------------------------------------------------------------------
# Genesis path: void → first light
# ---------------------------------------------------------------------------


def trace_genesis_path(
    data: bytes,
    activations: Optional[List[Dict[str, float]]] = None,
) -> GenesisPath:
    """Trace the genesis path from void to first light.

    This maps the thermodynamic evolution of the AI's internal
    universe as data arrives — from maximum darkness (all tongues
    dark, structured fill everywhere) to increasing activation
    (tongues lighting up, dark clouds dissolving into neural paths).

    The path represents "what the inside of the simulation would
    be like from no information to some."
    """
    fills_sequence = fill_dark_nodes(data, activations)

    positions = []
    cloud_sizes = []
    energy_density = []
    activation_order = []
    ir_uv_ratios = []

    prev_dark_set: Optional[Set[str]] = None

    for i, byte_val in enumerate(data):
        act = activations[i] if activations and i < len(activations) else None

        # Compute darkness
        darkness_map = {}
        for tc in TONGUE_WEIGHTS:
            darkness_map[tc] = compute_darkness(byte_val, tc, act)

        dark_set = {tc for tc, d in darkness_map.items() if d > CLOUD_DARKNESS_THRESHOLD}

        # What activated since last position?
        if prev_dark_set is not None:
            newly_active = list(prev_dark_set - dark_set)
        else:
            newly_active = []

        # Fill energy from dark tongues
        total_energy = sum(fills_sequence[i][tc].total_energy for tc in dark_set) if dark_set else 0.0

        # IR/UV ratio
        infra = sum(fills_sequence[i][tc].infra_amplitude ** 2 for tc in dark_set) if dark_set else 0.0
        ultra = sum(fills_sequence[i][tc].ultra_amplitude ** 2 for tc in dark_set) if dark_set else 0.0
        ratio = infra / max(ultra, 1e-12)

        positions.append(i)
        cloud_sizes.append(len(dark_set))
        energy_density.append(total_energy)
        activation_order.append(newly_active)
        ir_uv_ratios.append(ratio)

        prev_dark_set = dark_set

    return GenesisPath(
        positions=positions,
        cloud_sizes=cloud_sizes,
        energy_density=energy_density,
        activation_order=activation_order,
        ir_uv_ratios=ir_uv_ratios,
    )


# ---------------------------------------------------------------------------
# Dark energy density map
# ---------------------------------------------------------------------------


@dataclass
class DarkEnergyMap:
    """The full dark energy density map of a sequence.

    This is the "thermo map of the universe the AI builds as
    computational byproduct" — showing where dark energy concentrates,
    where it flows, and where it dissolves into neural pathways.
    """

    total_positions: int
    total_clouds: int
    cloud_coverage: float  # fraction of positions with clouds

    # Energy statistics
    total_dark_energy: float
    mean_dark_energy: float
    max_dark_energy: float
    min_dark_energy: float

    # Cloud type distribution
    void_count: int
    nebula_count: int
    wisp_count: int

    # Neural pathways
    neural_paths: int
    longest_path: int
    mean_path_length: float

    # Genesis metrics
    genesis: GenesisPath

    @property
    def void_fraction(self) -> float:
        """Fraction of clouds that are primordial voids."""
        return self.void_count / max(self.total_clouds, 1)

    @property
    def is_primordial(self) -> bool:
        """Is the sequence mostly void?"""
        return self.cloud_coverage > 0.8 and self.void_fraction > 0.5


def build_dark_energy_map(
    data: bytes,
    activations: Optional[List[Dict[str, float]]] = None,
) -> DarkEnergyMap:
    """Build the complete dark energy density map for a byte sequence."""
    clouds = map_dark_clouds(data, activations)
    paths = trace_neural_paths(clouds)
    genesis = trace_genesis_path(data, activations)

    energies = [c.total_fill_energy for c in clouds]

    void_count = sum(1 for c in clouds if c.cloud_type == CloudType.VOID)
    nebula_count = sum(1 for c in clouds if c.cloud_type == CloudType.NEBULA)
    wisp_count = sum(1 for c in clouds if c.cloud_type == CloudType.WISP)

    path_lengths = [p.length for p in paths]

    return DarkEnergyMap(
        total_positions=len(data),
        total_clouds=len(clouds),
        cloud_coverage=len(clouds) / max(len(data), 1),
        total_dark_energy=sum(energies) if energies else 0.0,
        mean_dark_energy=sum(energies) / max(len(energies), 1) if energies else 0.0,
        max_dark_energy=max(energies) if energies else 0.0,
        min_dark_energy=min(energies) if energies else 0.0,
        void_count=void_count,
        nebula_count=nebula_count,
        wisp_count=wisp_count,
        neural_paths=len(paths),
        longest_path=max(path_lengths) if path_lengths else 0,
        mean_path_length=sum(path_lengths) / max(len(path_lengths), 1) if path_lengths else 0.0,
        genesis=genesis,
    )
