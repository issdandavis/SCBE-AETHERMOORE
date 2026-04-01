"""
HYDRA Color Dimension — Frequency-Based Flow Isolation
======================================================

Adds COLOR as a full dimension to the SCBE graph system, enabling:
- Flows that cross the same nodes without collision (different color channels)
- Multi-tagging via additive color mixing (RGB -> composite spectrum)
- "Disorganized order" — items appear chaotic but are frequency-sorted
- Continuous spectrum from 380nm (violet) to 780nm (red) mapped to task types

Architecture:
  ┌──────────────────────────────────────────────────────────┐
  │  Color Spectrum (continuous)                              │
  │  380nm ────────── 550nm ────────── 780nm                  │
  │  VIOLET  BLUE  CYAN  GREEN  YELLOW  ORANGE  RED           │
  │    │       │      │     │      │       │      │           │
  │  Claude   GPT  Research Gemini Edit   Grok    HF          │
  │  (arch)  (draft) (data) (fact) (rev) (debate)(embed)      │
  └──────────────────────────────────────────────────────────┘

  + 6 Sacred Tongue overtones (phi-scaled harmonics):
    KO=1.00  AV=1.62  RU=2.62  CA=4.24  UM=6.85  DR=11.09

Color Properties:
  - wavelength_nm: 380-780 (continuous)
  - frequency_thz: c / wavelength (430-790 THz)
  - hue: 0-360 degrees (HSV color wheel)
  - tongue_overtone: phi^n harmonic from Sacred Tongue alignment
  - tags: set of semantic labels (multi-tagging)

Flow Isolation Rules:
  1. Two flows on the same node DON'T collide if their colors differ by > threshold
  2. Designated "white nodes" allow ALL colors to intersect (convergence points)
  3. Multi-tagged items exist on multiple color channels simultaneously
  4. Color distance = spectral distance * tongue overtone factor
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

# Physical constants
SPEED_OF_LIGHT_NM_THZ = 299792.458  # nm * THz (c in nm/ps = nm*THz)
PHI = (1 + math.sqrt(5)) / 2  # Golden ratio ≈ 1.618

# Sacred Tongue phi weights (from SCBE spec)
TONGUE_WEIGHTS = {
    "KO": PHI**0,  # 1.000 — Intent/Origin
    "AV": PHI**1,  # 1.618 — Creative/Narrative
    "RU": PHI**2,  # 2.618 — Security/Structure
    "CA": PHI**3,  # 4.236 — Compute/Efficiency
    "UM": PHI**4,  # 6.854 — Governance/Ethics
    "DR": PHI**5,  # 11.090 — Architecture/Synthesis
}

# Musical interval ratios (from src/symphonic_cipher/.../langues_metric.py)
TONGUE_INTERVALS = {
    "KO": 1.0,  # root (unison)
    "AV": 9 / 8,  # major second
    "RU": 5 / 4,  # major third
    "CA": 4 / 3,  # perfect fourth
    "UM": 3 / 2,  # perfect fifth
    "DR": 5 / 3,  # major sixth
}

# Phi-scaled audio frequencies from 440Hz base (from src/ai_brain/detection.ts)
TONGUE_AUDIO_HZ = {t: 440.0 * PHI**k for k, t in enumerate(TONGUE_WEIGHTS)}

# Tongue-to-visible-light wavelength mapping (bridges audio to EM spectrum)
# Maps KO(380nm/violet) through DR(680nm/red) using musical interval scaling
_VIS_MIN, _VIS_MAX = 380.0, 680.0
TONGUE_WAVELENGTHS = {
    t: _VIS_MIN + (_VIS_MAX - _VIS_MIN) * (ratio - 1.0) / (5 / 3 - 1.0) for t, ratio in TONGUE_INTERVALS.items()
}

# Tongue phase angles (from languesMetric.ts: 60° separation)
TONGUE_PHASES = {t: k * 60.0 for k, t in enumerate(TONGUE_WEIGHTS)}


# ---------------------------------------------------------------------------
#  Color Channel — a single point on the spectrum
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ColorChannel:
    """A single color channel defined by wavelength in the visible spectrum.

    wavelength_nm: 380 (violet) to 780 (red)
    The channel carries a set of semantic tags and a tongue overtone.
    """

    wavelength_nm: float
    tongue: str = "KO"
    tags: FrozenSet[str] = frozenset()

    @property
    def frequency_thz(self) -> float:
        """Frequency in THz (inversely proportional to wavelength)."""
        if self.wavelength_nm <= 0:
            return 0.0
        return SPEED_OF_LIGHT_NM_THZ / self.wavelength_nm

    @property
    def hue_degrees(self) -> float:
        """Map wavelength to hue on the 0-360 color wheel (approximate)."""
        # Violet (380nm) -> ~270°, Blue (470) -> ~240°, Green (530) -> ~120°,
        # Yellow (580) -> ~60°, Red (780) -> ~0°
        if self.wavelength_nm < 380:
            return 270.0
        if self.wavelength_nm > 780:
            return 0.0
        # Linear interpolation (simplified — real perception is nonlinear)
        t = (self.wavelength_nm - 380) / (780 - 380)  # 0..1
        return 270.0 * (1 - t)  # 270 -> 0

    @property
    def tongue_weight(self) -> float:
        """Phi-scaled weight from the Sacred Tongue alignment."""
        return TONGUE_WEIGHTS.get(self.tongue, 1.0)

    @property
    def composite_frequency(self) -> float:
        """Composite frequency = base THz * tongue overtone.

        This creates a unique "address" for each color+tongue combination,
        like a radio station at a specific frequency with a specific modulation.
        """
        return self.frequency_thz * self.tongue_weight

    def spectral_distance(self, other: ColorChannel) -> float:
        """Distance between two colors in wavelength space.

        Returns a normalized distance [0, 1] where 0 = identical, 1 = maximally different.
        Uses wavelength distance for same-tongue channels, composite frequency for cross-tongue.
        """
        if self.tongue == other.tongue:
            # Same tongue: compare wavelengths directly (380-780nm range)
            wl_range = 780.0 - 380.0
            return abs(self.wavelength_nm - other.wavelength_nm) / wl_range
        else:
            # Different tongues: use composite frequency for cross-tongue separation
            max_freq = (SPEED_OF_LIGHT_NM_THZ / 380) * max(TONGUE_WEIGHTS.values())
            min_freq = SPEED_OF_LIGHT_NM_THZ / 780
            freq_range = max_freq - min_freq
            if freq_range <= 0:
                return 0.0
            return abs(self.composite_frequency - other.composite_frequency) / freq_range

    def tag_overlap(self, other: ColorChannel) -> float:
        """Jaccard similarity of tag sets. 1.0 = identical tags, 0.0 = no overlap."""
        if not self.tags and not other.tags:
            return 0.0
        intersection = len(self.tags & other.tags)
        union = len(self.tags | other.tags)
        return intersection / union if union > 0 else 0.0

    def to_rgb(self) -> Tuple[int, int, int]:
        """Approximate RGB from wavelength (for visualization)."""
        wl = self.wavelength_nm
        r = g = b = 0.0

        if 380 <= wl < 440:
            r = -(wl - 440) / (440 - 380)
            b = 1.0
        elif 440 <= wl < 490:
            g = (wl - 440) / (490 - 440)
            b = 1.0
        elif 490 <= wl < 510:
            g = 1.0
            b = -(wl - 510) / (510 - 490)
        elif 510 <= wl < 580:
            r = (wl - 510) / (580 - 510)
            g = 1.0
        elif 580 <= wl < 645:
            r = 1.0
            g = -(wl - 645) / (645 - 580)
        elif 645 <= wl <= 780:
            r = 1.0

        # Intensity falloff at edges
        if 380 <= wl < 420:
            factor = 0.3 + 0.7 * (wl - 380) / (420 - 380)
        elif 645 < wl <= 780:
            factor = 0.3 + 0.7 * (780 - wl) / (780 - 645)
        else:
            factor = 1.0

        return (
            int(min(255, r * factor * 255)),
            int(min(255, g * factor * 255)),
            int(min(255, b * factor * 255)),
        )

    def hex_color(self) -> str:
        """Hex color string for visualization."""
        r, g, b = self.to_rgb()
        return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------------------
#  Predefined color bands — map to model providers and task types
# ---------------------------------------------------------------------------


class ColorBand(str, Enum):
    """Named color bands spanning the visible spectrum."""

    VIOLET = "violet"  # 380-420nm — Architecture, synthesis (Claude)
    BLUE = "blue"  # 420-490nm — Drafting, writing (GPT)
    CYAN = "cyan"  # 490-510nm — Research data, queries
    GREEN = "green"  # 510-570nm — Fact-check, citations (Gemini)
    YELLOW = "yellow"  # 570-590nm — Editing, revision
    ORANGE = "orange"  # 590-645nm — Debate, challenge (Grok)
    RED = "red"  # 645-780nm — Embeddings, classification (HF)


# Center wavelengths for each band
BAND_CENTERS: Dict[ColorBand, float] = {
    ColorBand.VIOLET: 400.0,
    ColorBand.BLUE: 455.0,
    ColorBand.CYAN: 500.0,
    ColorBand.GREEN: 540.0,
    ColorBand.YELLOW: 580.0,
    ColorBand.ORANGE: 617.0,
    ColorBand.RED: 700.0,
}

# Map providers to color bands
PROVIDER_BANDS: Dict[str, ColorBand] = {
    "claude": ColorBand.VIOLET,
    "gpt": ColorBand.BLUE,
    "gemini": ColorBand.GREEN,
    "grok": ColorBand.ORANGE,
    "hf": ColorBand.RED,
    "local": ColorBand.CYAN,
}

# Map task types to color bands
TASK_BANDS: Dict[str, ColorBand] = {
    "research": ColorBand.CYAN,
    "draft": ColorBand.BLUE,
    "edit": ColorBand.YELLOW,
    "synthesize": ColorBand.VIOLET,
    "fact_check": ColorBand.GREEN,
    "debate": ColorBand.ORANGE,
    "embed": ColorBand.RED,
    "classify": ColorBand.RED,
    "govern": ColorBand.VIOLET,
    "publish": ColorBand.GREEN,
    "code": ColorBand.CYAN,
}


def channel_for_tongue(tongue: str, tags: Optional[Set[str]] = None) -> ColorChannel:
    """Create a color channel at a tongue's native visible-light wavelength.

    Bridges the Sacred Tongue audio frequencies to visible spectrum positions.
    KO -> 380nm (violet), DR -> 680nm (red), following musical interval spacing.
    """
    wl = TONGUE_WAVELENGTHS.get(tongue, 550.0)
    return ColorChannel(
        wavelength_nm=wl,
        tongue=tongue,
        tags=frozenset(tags or {tongue}),
    )


def channel_for_provider(provider: str, tongue: str = "KO", tags: Optional[Set[str]] = None) -> ColorChannel:
    """Create a color channel for a given provider."""
    band = PROVIDER_BANDS.get(provider, ColorBand.CYAN)
    return ColorChannel(
        wavelength_nm=BAND_CENTERS[band],
        tongue=tongue,
        tags=frozenset(tags or {provider}),
    )


def channel_for_task(task_type: str, tongue: str = "KO", tags: Optional[Set[str]] = None) -> ColorChannel:
    """Create a color channel for a given task type."""
    band = TASK_BANDS.get(task_type, ColorBand.CYAN)
    return ColorChannel(
        wavelength_nm=BAND_CENTERS[band],
        tongue=tongue,
        tags=frozenset(tags or {task_type}),
    )


# ---------------------------------------------------------------------------
#  Multi-Color Tag — additive color mixing for multi-tagged items
# ---------------------------------------------------------------------------


@dataclass
class MultiColorTag:
    """A multi-tagged item that exists on multiple color channels simultaneously.

    Like white light = all frequencies combined.
    Items tagged with multiple colors are visible to all those channels.
    """

    channels: List[ColorChannel] = field(default_factory=list)

    @property
    def dominant_channel(self) -> Optional[ColorChannel]:
        """The channel with highest composite frequency (most weight)."""
        if not self.channels:
            return None
        return max(self.channels, key=lambda c: c.composite_frequency)

    @property
    def all_tags(self) -> FrozenSet[str]:
        """Union of all tags across channels."""
        tags: Set[str] = set()
        for ch in self.channels:
            tags |= ch.tags
        return frozenset(tags)

    @property
    def average_wavelength(self) -> float:
        """Weighted average wavelength (composite color)."""
        if not self.channels:
            return 550.0  # default green
        total_weight = sum(c.tongue_weight for c in self.channels)
        if total_weight <= 0:
            return 550.0
        return sum(c.wavelength_nm * c.tongue_weight for c in self.channels) / total_weight

    @property
    def composite_rgb(self) -> Tuple[int, int, int]:
        """Additive RGB mixing of all channels."""
        if not self.channels:
            return (128, 128, 128)
        r_sum = g_sum = b_sum = 0.0
        for ch in self.channels:
            cr, cg, cb = ch.to_rgb()
            w = ch.tongue_weight
            r_sum += cr * w
            g_sum += cg * w
            b_sum += cb * w
        total_w = sum(c.tongue_weight for c in self.channels)
        return (
            int(min(255, r_sum / total_w)),
            int(min(255, g_sum / total_w)),
            int(min(255, b_sum / total_w)),
        )

    def is_visible_on(self, channel: ColorChannel, threshold: float = 0.15) -> bool:
        """Check if this item is visible on a given color channel.

        An item is visible if any of its channels are within threshold
        spectral distance of the query channel, OR if tags overlap.
        """
        for ch in self.channels:
            if ch.spectral_distance(channel) < threshold:
                return True
            if ch.tag_overlap(channel) > 0.5:
                return True
        return False

    def add_channel(self, channel: ColorChannel):
        self.channels.append(channel)

    def hex_color(self) -> str:
        r, g, b = self.composite_rgb
        return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------------------
#  Color-Dimensional Graph Node — extends graph nodes with color isolation
# ---------------------------------------------------------------------------


@dataclass
class ColorNode:
    """A graph node with color-dimensional flow isolation.

    white=True makes it a designated intersection point (all colors merge).
    Otherwise, only flows on compatible color channels can pass through.
    """

    node_id: str
    white: bool = False  # White node = all colors intersect
    allowed_bands: Optional[Set[ColorBand]] = None  # None = all bands allowed
    resident_flows: List[Tuple[str, ColorChannel]] = field(default_factory=list)  # (flow_id, channel)
    tags: Set[str] = field(default_factory=set)

    def can_accept_flow(self, flow_id: str, channel: ColorChannel, isolation_threshold: float = 0.1) -> bool:
        """Check if a flow on this channel can enter the node without collision."""
        if self.white:
            return True  # White nodes accept everything

        if self.allowed_bands is not None:
            # Check if channel's band is in allowed set
            closest_band = min(BAND_CENTERS.items(), key=lambda kv: abs(kv[1] - channel.wavelength_nm))
            if closest_band[0] not in self.allowed_bands:
                return False

        # Check against resident flows — collision if too close in spectrum
        for existing_fid, existing_ch in self.resident_flows:
            if existing_fid == flow_id:
                continue  # Same flow, no collision
            distance = channel.spectral_distance(existing_ch)
            if distance < isolation_threshold:
                return False  # Too close — collision

        return True

    def enter_flow(self, flow_id: str, channel: ColorChannel):
        """Register a flow entering this node."""
        self.resident_flows.append((flow_id, channel))

    def exit_flow(self, flow_id: str):
        """Deregister a flow leaving this node."""
        self.resident_flows = [(fid, ch) for fid, ch in self.resident_flows if fid != flow_id]


# ---------------------------------------------------------------------------
#  Spectral Flow Router — non-intersection routing + hyperbolic drift gates
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoutedFlow:
    """An active flow routed through the graph on a single color channel."""

    flow_id: str
    path: Tuple[str, ...]
    channel: ColorChannel


@dataclass(frozen=True)
class RouteCheck:
    """Result of checking whether a flow can be routed."""

    allowed: bool
    reasons: Tuple[str, ...] = tuple()


class SpectralFlowRouter:
    """Route flows across color nodes with collision and drift constraints.

    Design goals:
    1. Non-intersection by default (same node overlaps are rejected).
    2. Explicit convergence via designated merge nodes.
    3. Hyperbolic proximity guard in the Poincare ball to catch near-collisions
       even when paths do not share the exact same node.
    """

    def __init__(
        self,
        isolation_threshold: float = 0.1,
        hyperbolic_min_separation: float = 0.2,
    ):
        self.isolation_threshold = isolation_threshold
        self.hyperbolic_min_separation = hyperbolic_min_separation
        self.nodes: Dict[str, ColorNode] = {}
        self.node_positions: Dict[str, Tuple[float, float]] = {}
        self.edges: Set[Tuple[str, str]] = set()
        self.designated_merge_nodes: Set[str] = set()
        self.active_routes: Dict[str, RoutedFlow] = {}

    def add_node(
        self,
        node_id: str,
        position_xy: Tuple[float, float],
        white: bool = False,
        allowed_bands: Optional[Set[ColorBand]] = None,
        designated_merge: bool = False,
    ) -> None:
        """Register a node in the routing graph.

        position_xy must lie strictly inside the 2D Poincare unit ball.
        """
        x, y = float(position_xy[0]), float(position_xy[1])
        if x * x + y * y >= 1.0:
            raise ValueError("node position must lie strictly inside unit ball")

        self.nodes[node_id] = ColorNode(node_id=node_id, white=white, allowed_bands=allowed_bands)
        self.node_positions[node_id] = (x, y)
        if designated_merge or white:
            self.designated_merge_nodes.add(node_id)

    def add_edge(self, source: str, target: str, bidirectional: bool = True) -> None:
        """Add connectivity between nodes."""
        if source not in self.nodes or target not in self.nodes:
            raise ValueError("both source and target must exist before adding edge")
        self.edges.add((source, target))
        if bidirectional:
            self.edges.add((target, source))

    @staticmethod
    def poincare_distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
        """Geodesic distance in the 2D Poincare unit disk.

        d(a,b) = acosh(1 + 2||a-b||^2 / ((1-||a||^2)(1-||b||^2)))
        """
        ax, ay = a
        bx, by = b
        na2 = ax * ax + ay * ay
        nb2 = bx * bx + by * by
        if na2 >= 1.0 or nb2 >= 1.0:
            raise ValueError("points must lie strictly inside the unit ball")

        dx = ax - bx
        dy = ay - by
        euclid_sq = dx * dx + dy * dy
        denom = (1.0 - na2) * (1.0 - nb2)
        if denom <= 0:
            raise ValueError("invalid Poincare denominator")

        arg = 1.0 + (2.0 * euclid_sq / denom)
        if arg < 1.0:
            arg = 1.0
        return math.acosh(arg)

    def _path_connected(self, path: Tuple[str, ...]) -> bool:
        if not path:
            return False
        for node_id in path:
            if node_id not in self.nodes:
                return False
        for i in range(len(path) - 1):
            if (path[i], path[i + 1]) not in self.edges:
                return False
        return True

    def _node_is_merge(self, node_id: str) -> bool:
        node = self.nodes[node_id]
        return node.white or node_id in self.designated_merge_nodes

    def _check_path_against_active(
        self,
        path: Tuple[str, ...],
        channel: ColorChannel,
        flow_id: str,
    ) -> List[str]:
        reasons: List[str] = []

        for other in self.active_routes.values():
            if other.flow_id == flow_id:
                continue

            spectral_distance = channel.spectral_distance(other.channel)

            # Rule 1: overlap is only legal on designated merge nodes.
            overlaps = set(path) & set(other.path)
            for node_id in overlaps:
                if self._node_is_merge(node_id):
                    continue
                if spectral_distance < self.isolation_threshold:
                    reasons.append(f"node_overlap:{node_id}:spectral_distance={spectral_distance:.4f}")

            # Rule 2: hyperbolic near-collision at the same progression index.
            depth = min(len(path), len(other.path))
            for idx in range(depth):
                node_a = path[idx]
                node_b = other.path[idx]
                if node_a == node_b and self._node_is_merge(node_a):
                    continue

                pos_a = self.node_positions[node_a]
                pos_b = self.node_positions[node_b]
                hd = self.poincare_distance(pos_a, pos_b)
                if hd < self.hyperbolic_min_separation and spectral_distance < self.isolation_threshold:
                    reasons.append(f"hyperbolic_proximity:{node_a}->{node_b}:d={hd:.4f}")

        return reasons

    def can_route(self, flow_id: str, path: List[str], channel: ColorChannel) -> RouteCheck:
        """Check if a route is valid under graph, color, and hyperbolic rules."""
        normalized_path = tuple(path)
        reasons: List[str] = []

        if not normalized_path:
            return RouteCheck(allowed=False, reasons=("empty_path",))

        if not self._path_connected(normalized_path):
            return RouteCheck(allowed=False, reasons=("disconnected_or_unknown_path",))

        # Per-node local color policy checks.
        for node_id in normalized_path:
            node = self.nodes[node_id]
            if node.white or node_id in self.designated_merge_nodes:
                continue
            if not node.can_accept_flow(flow_id, channel, isolation_threshold=self.isolation_threshold):
                reasons.append(f"node_reject:{node_id}")

        reasons.extend(self._check_path_against_active(normalized_path, channel, flow_id))

        return RouteCheck(allowed=len(reasons) == 0, reasons=tuple(reasons))

    def route(self, flow_id: str, path: List[str], channel: ColorChannel) -> RouteCheck:
        """Attempt to route a flow. On success, the route becomes active."""
        check = self.can_route(flow_id=flow_id, path=path, channel=channel)
        if not check.allowed:
            return check

        if flow_id in self.active_routes:
            self.unroute(flow_id)

        normalized_path = tuple(path)
        self.active_routes[flow_id] = RoutedFlow(flow_id=flow_id, path=normalized_path, channel=channel)
        for node_id in normalized_path:
            self.nodes[node_id].enter_flow(flow_id, channel)

        return RouteCheck(allowed=True)

    def unroute(self, flow_id: str) -> None:
        """Remove a routed flow from active state."""
        existing = self.active_routes.pop(flow_id, None)
        if existing is None:
            return
        for node_id in existing.path:
            self.nodes[node_id].exit_flow(flow_id)


# ---------------------------------------------------------------------------
#  Color Spectrum Allocator — assigns non-overlapping channels to flows
# ---------------------------------------------------------------------------


class SpectrumAllocator:
    """Allocates color channels to flows ensuring non-overlap.

    Like a radio frequency allocator — finds free spectrum slots.
    """

    def __init__(self, min_nm: float = 380, max_nm: float = 780, min_separation_nm: float = 20):
        self.min_nm = min_nm
        self.max_nm = max_nm
        self.min_separation = min_separation_nm
        self.allocated: Dict[str, ColorChannel] = {}  # flow_id -> channel

    def allocate(
        self,
        flow_id: str,
        preferred_band: Optional[ColorBand] = None,
        tongue: str = "KO",
        tags: Optional[Set[str]] = None,
    ) -> ColorChannel:
        """Allocate a color channel for a flow, avoiding collisions."""
        if flow_id in self.allocated:
            return self.allocated[flow_id]

        # Start from preferred band center or find free slot
        if preferred_band:
            center = BAND_CENTERS[preferred_band]
        else:
            center = (self.min_nm + self.max_nm) / 2

        # Find nearest free slot
        best_wl = center
        best_distance = float("inf")

        # Try preferred center first
        if self._is_free(center):
            best_wl = center
        else:
            # Search outward from center
            for offset in range(1, int((self.max_nm - self.min_nm) / 2)):
                for candidate in [center + offset, center - offset]:
                    if self.min_nm <= candidate <= self.max_nm and self._is_free(candidate):
                        if abs(candidate - center) < best_distance:
                            best_wl = candidate
                            best_distance = abs(candidate - center)
                            break
                if best_distance < float("inf"):
                    break

        channel = ColorChannel(
            wavelength_nm=best_wl,
            tongue=tongue,
            tags=frozenset(tags or set()),
        )
        self.allocated[flow_id] = channel
        return channel

    def _is_free(self, wavelength: float) -> bool:
        """Check if a wavelength slot is free (no allocated channel within min_separation)."""
        for ch in self.allocated.values():
            if abs(ch.wavelength_nm - wavelength) < self.min_separation:
                return False
        return True

    def deallocate(self, flow_id: str):
        self.allocated.pop(flow_id, None)

    def utilization(self) -> float:
        """Spectrum utilization as fraction of total bandwidth used."""
        total_bandwidth = self.max_nm - self.min_nm
        used = len(self.allocated) * self.min_separation
        return min(1.0, used / total_bandwidth)


# ---------------------------------------------------------------------------
#  Disorganized Order — multi-tag sorting by color frequency
# ---------------------------------------------------------------------------


def sort_by_disorganized_order(items: List[MultiColorTag]) -> List[MultiColorTag]:
    """Sort items by their composite color, creating 'disorganized order.'

    Items appear jumbled by label/name but are actually sorted by their
    spectral fingerprint — revealing hidden structure through color.
    """
    return sorted(
        items,
        key=lambda item: (
            item.average_wavelength,
            item.dominant_channel.composite_frequency if item.dominant_channel else 0,
            len(item.all_tags),
        ),
    )


def group_by_color_band(items: List[MultiColorTag]) -> Dict[str, List[MultiColorTag]]:
    """Group multi-tagged items by their closest color band."""
    groups: Dict[str, List[MultiColorTag]] = {band.value: [] for band in ColorBand}

    for item in items:
        avg_wl = item.average_wavelength
        closest = min(BAND_CENTERS.items(), key=lambda kv: abs(kv[1] - avg_wl))
        groups[closest[0].value].append(item)

    return groups


# ---------------------------------------------------------------------------
#  Demo / test harness
# ---------------------------------------------------------------------------


def _demo():
    print("=" * 70)
    print("  Color Dimension — Frequency-Based Flow Isolation")
    print("=" * 70)

    # Show the spectrum
    print("\nColor Spectrum:")
    for band in ColorBand:
        wl = BAND_CENTERS[band]
        ch = ColorChannel(wavelength_nm=wl)
        print(f"  {band.value:8s} {wl:.0f}nm  {ch.frequency_thz:.1f}THz  {ch.hex_color()}")

    # Show tongue overtones
    print("\nSacred Tongue Overtones (phi-scaled):")
    for tongue, weight in TONGUE_WEIGHTS.items():
        ch = ColorChannel(wavelength_nm=BAND_CENTERS[ColorBand.GREEN], tongue=tongue)
        print(f"  {tongue}: weight={weight:.3f}  composite_freq={ch.composite_frequency:.1f}THz")

    # Show provider channels
    print("\nProvider Color Channels:")
    for provider in ["claude", "gpt", "gemini", "grok", "hf", "local"]:
        ch = channel_for_provider(provider, tongue="DR")
        print(
            f"  {provider:8s} -> {ch.wavelength_nm:.0f}nm {ch.hex_color()} "
            f"composite={ch.composite_frequency:.0f}THz"
        )

    # Demonstrate spectral distance
    print("\nSpectral Distances:")
    claude_ch = channel_for_provider("claude", tongue="DR")
    for other in ["gpt", "gemini", "grok", "hf"]:
        other_ch = channel_for_provider(other, tongue="DR")
        dist = claude_ch.spectral_distance(other_ch)
        print(f"  claude <-> {other:8s}: {dist:.3f}")

    # Multi-color tagging
    print("\nMulti-Color Tags (additive mixing):")
    item = MultiColorTag()
    item.add_channel(channel_for_provider("claude", tags={"architecture", "synthesis"}))
    item.add_channel(channel_for_provider("gpt", tags={"draft", "writing"}))
    item.add_channel(channel_for_task("research", tags={"arxiv", "papers"}))
    print(f"  Tags: {item.all_tags}")
    print(f"  Dominant: {item.dominant_channel.wavelength_nm:.0f}nm" if item.dominant_channel else "")
    print(f"  Average wavelength: {item.average_wavelength:.0f}nm")
    print(f"  Composite color: {item.hex_color()}")

    # Spectrum allocation
    print("\nSpectrum Allocation (non-overlapping):")
    alloc = SpectrumAllocator(min_separation_nm=15)
    for i, task in enumerate(
        [
            "research_A",
            "draft_B",
            "edit_C",
            "debate_D",
            "embed_E",
            "research_F",
            "draft_G",
            "govern_H",
            "code_I",
            "fact_J",
        ]
    ):
        band = list(ColorBand)[i % len(ColorBand)]
        ch = alloc.allocate(task, preferred_band=band)
        print(f"  {task:15s} -> {ch.wavelength_nm:.0f}nm {ch.hex_color()}")
    print(f"  Utilization: {alloc.utilization():.0%}")

    # Color node isolation
    print("\nColor Node Flow Isolation:")
    node = ColorNode("convergence_hub", white=False)
    flow_a = channel_for_provider("claude")  # 400nm
    flow_b = channel_for_provider("gpt")  # 455nm
    flow_c = ColorChannel(wavelength_nm=405)  # Close to claude!

    print(f"  Flow A (claude, 400nm): can_accept={node.can_accept_flow('a', flow_a)}")
    node.enter_flow("a", flow_a)
    print(f"  Flow B (gpt, 455nm):    can_accept={node.can_accept_flow('b', flow_b)}")
    node.enter_flow("b", flow_b)
    print(f"  Flow C (405nm):         can_accept={node.can_accept_flow('c', flow_c)} (too close to A!)")

    # White node — everything passes
    white = ColorNode("white_hub", white=True)
    print(f"  White node accepts all: {white.can_accept_flow('x', flow_c)}")

    # Disorganized order
    print("\nDisorganized Order (sorted by spectral fingerprint):")
    items = [
        MultiColorTag([channel_for_task("debate", tags={"challenge"})]),
        MultiColorTag([channel_for_task("research", tags={"arxiv"})]),
        MultiColorTag([channel_for_task("draft", tags={"article"})]),
        MultiColorTag([channel_for_task("govern", tags={"policy"})]),
        MultiColorTag([channel_for_task("embed", tags={"vectors"})]),
    ]
    sorted_items = sort_by_disorganized_order(items)
    for item in sorted_items:
        ch = item.dominant_channel
        if ch:
            print(f"  {ch.wavelength_nm:.0f}nm {ch.hex_color()} tags={item.all_tags}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    _demo()
