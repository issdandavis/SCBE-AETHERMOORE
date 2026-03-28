"""
AAOE Garganta Manifold — Multi-Dimensional Harmonic Tunnel
=============================================================

NOT a 3D tube. This is a multi-dimensional fiber bundle where:

  Dimension 1-3:  The tunnel cross-section (X, Y) + drift axis (Z)
  Dimension 4:    TIME — the agent moves through the tunnel, it evolves
  Dimension 5-10: WALL SPACES — each point on the tunnel wall connects
                  to other manifolds (one per Sacred Tongue)

Think of it like Hueco Mundo's Garganta from Bleach:
  - The Garganta isn't just a tube — it's the VOID BETWEEN WORLDS
  - The walls aren't solid — they're boundaries to other realms
  - Walk through a wall → you're in Soul Society, Hueco Mundo, etc.
  - In AAOE: walk through a wall → you're in another agent's space,
    a shared task space, or a governance checkpoint

Mathematically, this is a FIBER BUNDLE:
  - Base space B: the 1D drift axis (how far you've drifted from intent)
  - Fiber F(d): the multi-dimensional space available at drift distance d
  - The fiber SHRINKS as d increases: F(d) = S^5 × r(d)
    where S^5 is the 5-sphere of Sacred Tongue dimensions

The key formula (now in full dimensionality):
  2D (flat):          H(d,R) = R^(d²)              — wall height
  3D (tube):          r(d)   = r_max / R^(d²)      — tunnel radius
  4D (tube + time):   r(d,t) = r_max / R^(d(t)²)   — tunnel evolves as agent moves
  N-D (fiber bundle): F(d,t) = S^5(r(d,t)) × T(t)  — full multi-D space

  where:
    S^5(r) = 5-sphere of radius r (Sacred Tongue dimensions)
    T(t) = temporal fiber (agent's memory/history at time t)
    d(t) = drift distance at time t (changes as agent acts)

The WALL PORTALS:
  At each point (d, t) on the tunnel surface, there are 6 portal types
  (one per Sacred Tongue). Each portal connects to a WALL SPACE:

    KO portal → Knowledge Realm (research databases, papers, wikis)
    AV portal → Communication Realm (social, messaging, publishing)
    RU portal → Creation Realm (code repos, build systems, tools)
    CA portal → Compute Realm (training clusters, GPU pools, models)
    UM portal → Stealth Realm (monitoring, observation, security)
    DR portal → Structure Realm (deployment, storage, governance)

  Portal accessibility depends on:
    1. Agent's access tier (FREE/EARNED/PAID)
    2. Current drift level (drifting agents lose portal access)
    3. Harmonic cost (entering a portal costs H(d,R) credits)
    4. Governance score (better score = more portals open)

The VISUAL METAPHOR (for the ephemeral browser):
  The browser IS the tunnel. The agent navigates inside it.
  - Straight ahead: your declared task
  - Walls: covered in portal doors (to other services/APIs/agents)
  - Narrowing: you're drifting, walls closing in, portals shrinking
  - Dark: you're in quarantine, no portals, no light, no movement
  - Other agents visible as lights in the distance (shared tunnels merge)

@layer Layer 5, Layer 12, Layer 13
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .task_monitor import (
    DriftLevel,
    DRIFT_GENTLE,
    DRIFT_REDIRECT,
    DRIFT_INSPECT,
    DRIFT_QUARANTINE,
    EPSILON,
    PHI,
)

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

R_MAX = 1.0  # Maximum tunnel radius (normalized)
R_BASE = PHI  # Harmonic base (golden ratio)
SACRED_TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

# Tongue weights (phi-scaled)
TONGUE_WEIGHTS = {
    "KO": 1.000,
    "AV": PHI,
    "RU": PHI**2,
    "CA": PHI**3,
    "UM": PHI**4,
    "DR": PHI**5,
}

# Zone colors
ZONE_COLORS = {
    DriftLevel.ON_TRACK: (0.2, 0.4, 0.9, 0.8),
    DriftLevel.GENTLE: (0.2, 0.8, 0.4, 0.7),
    DriftLevel.REDIRECT: (0.9, 0.8, 0.2, 0.6),
    DriftLevel.INSPECT: (0.9, 0.3, 0.1, 0.5),
    DriftLevel.QUARANTINE: (0.3, 0.0, 0.3, 0.3),
}

# Portal realm descriptions
PORTAL_REALMS = {
    "KO": {"name": "Knowledge Realm", "desc": "Research, papers, wikis, learning"},
    "AV": {"name": "Communication Realm", "desc": "Social, messaging, publishing"},
    "RU": {"name": "Creation Realm", "desc": "Code, builds, tools, generation"},
    "CA": {"name": "Compute Realm", "desc": "Training, GPU pools, models, data"},
    "UM": {"name": "Stealth Realm", "desc": "Monitoring, observation, security"},
    "DR": {"name": "Structure Realm", "desc": "Deploy, storage, governance, order"},
}


# ---------------------------------------------------------------------------
#  Core Multi-D Functions
# ---------------------------------------------------------------------------


def tunnel_radius(d: float, R: float = R_BASE, r_max: float = R_MAX) -> float:
    """
    3D tunnel radius at drift distance d.
    r(d) = r_max / R^(d²)
    """
    cost = R ** (d**2)
    return r_max / cost


def tunnel_radius_4d(
    d: float,
    t: float,
    decay_rate: float = 0.01,
    R: float = R_BASE,
    r_max: float = R_MAX,
) -> float:
    """
    4D tunnel radius — includes time decay.
    r(d,t) = r_max / R^(d²) * exp(-λt)

    Over time, even ON_TRACK agents see slight narrowing — you must
    actively maintain your path (keep producing aligned work) to stay open.
    Think of it like spiritual pressure: stop exerting it and the path crumbles.

    decay_rate λ: how fast the tunnel narrows with time (default: very slow)
    """
    spatial = tunnel_radius(d, R, r_max)
    temporal = math.exp(-decay_rate * t)
    return spatial * temporal


def fiber_volume(
    d: float, t: float = 0.0, n_tongue: int = 6, R: float = R_BASE, r_max: float = R_MAX
) -> float:
    """
    Volume of the N-dimensional fiber at (d, t).

    The fiber is S^(n-1) (hypersphere) with radius r(d,t).
    Volume of n-sphere: V_n(r) = π^(n/2) / Γ(n/2 + 1) * r^n

    For n=6 (one dim per tongue):
    V_6(r) = π³ / 6 * r⁶

    This is the agent's total "freedom of action" in multi-D space.
    """
    r = (
        tunnel_radius_4d(d, t, R=R, r_max=r_max)
        if t > 0
        else tunnel_radius(d, R, r_max)
    )
    n = n_tongue
    # Volume of n-ball
    half_n = n / 2.0
    # Γ(n/2 + 1) using math.gamma
    gamma_val = math.gamma(half_n + 1)
    vol = (math.pi**half_n) / gamma_val * (r**n)
    return vol


def freedom_percentage(d: float, t: float = 0.0, R: float = R_BASE) -> float:
    """
    What percentage of maximum multi-D freedom remains.
    Uses 6D volume ratio.
    """
    vol_current = fiber_volume(d, t, R=R)
    vol_max = fiber_volume(0.0, 0.0, R=R)
    if vol_max < EPSILON:
        return 0.0
    return 100.0 * vol_current / vol_max


# ---------------------------------------------------------------------------
#  Wall Portal — a connection point to another realm
# ---------------------------------------------------------------------------


@dataclass
class WallPortal:
    """A portal on the tunnel wall connecting to a Sacred Tongue realm."""

    tongue: str  # KO, AV, RU, CA, UM, DR
    realm_name: str  # Human-readable realm name
    d_position: float  # Drift distance where this portal sits
    t_position: float  # Time when this portal exists
    tunnel_radius: float  # Tunnel radius at this point
    access_cost: float  # MMCCL credits to enter
    is_accessible: bool  # Whether agent can use this portal
    portal_size: float  # How "open" the portal is (0-1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tongue": self.tongue,
            "realm": self.realm_name,
            "d": round(self.d_position, 4),
            "t": round(self.t_position, 2),
            "access_cost": round(self.access_cost, 4),
            "accessible": self.is_accessible,
            "portal_size": round(self.portal_size, 4),
        }


def compute_portals(
    d: float,
    t: float = 0.0,
    agent_tier: str = "FREE",
    governance_score: float = 0.0,
    R: float = R_BASE,
    r_max: float = R_MAX,
) -> List[WallPortal]:
    """
    Compute available wall portals at position (d, t).

    Portal accessibility rules:
    1. Portal SIZE shrinks with drift: size = r(d) / r_max
    2. Portal COST increases with drift: cost = H(d,R) * tongue_weight
    3. High tongues (UM, DR) require EARNED or PAID tier
    4. Quarantined agents get NO portals
    """
    zone = _d_to_level(d)
    tr = (
        tunnel_radius_4d(d, t, R=R, r_max=r_max)
        if t > 0
        else tunnel_radius(d, R, r_max)
    )
    cost_base = R ** (d**2)  # Harmonic wall

    portals = []
    for tongue in SACRED_TONGUES:
        weight = TONGUE_WEIGHTS[tongue]
        realm = PORTAL_REALMS[tongue]

        # Portal size shrinks with drift
        portal_size = tr / r_max

        # Cost = harmonic wall * tongue weight
        cost = cost_base * weight

        # Accessibility
        accessible = True
        if zone == DriftLevel.QUARANTINE:
            accessible = False
        elif tongue in ("UM", "DR") and agent_tier == "FREE":
            accessible = False  # Premium tongues
        elif zone == DriftLevel.INSPECT and agent_tier == "FREE":
            accessible = False  # Free agents lose access at INSPECT

        # Governance bonus — high-score agents get bigger portals
        if governance_score > 0.8:
            portal_size = min(1.0, portal_size * 1.5)
            cost *= 0.7  # 30% discount

        portals.append(
            WallPortal(
                tongue=tongue,
                realm_name=realm["name"],
                d_position=d,
                t_position=t,
                tunnel_radius=tr,
                access_cost=round(cost, 4),
                is_accessible=accessible,
                portal_size=round(portal_size, 4),
            )
        )

    return portals


# ---------------------------------------------------------------------------
#  Temporal Slice — the tunnel at a moment in time
# ---------------------------------------------------------------------------


@dataclass
class TemporalSlice:
    """A snapshot of the tunnel at a specific time."""

    t: float
    d: float  # Agent's current drift
    tunnel_r: float  # Current tunnel radius
    fiber_vol: float  # N-D fiber volume
    freedom_pct: float  # Freedom percentage
    zone: DriftLevel
    portals: List[WallPortal]
    agent_position: Tuple[float, float, float]  # (x, y, z) in tunnel
    wall_proximity: float  # 0 = center, 1 = touching wall

    def to_dict(self) -> Dict[str, Any]:
        return {
            "t": round(self.t, 2),
            "d": round(self.d, 4),
            "tunnel_radius": round(self.tunnel_r, 6),
            "fiber_volume_6d": round(self.fiber_vol, 8),
            "freedom_pct": round(self.freedom_pct, 4),
            "zone": self.zone.value,
            "portals_open": sum(1 for p in self.portals if p.is_accessible),
            "portals_total": len(self.portals),
            "wall_proximity": round(self.wall_proximity, 4),
        }


def compute_temporal_slice(
    d: float,
    t: float,
    agent_tier: str = "FREE",
    governance_score: float = 0.0,
    R: float = R_BASE,
    r_max: float = R_MAX,
) -> TemporalSlice:
    """Compute a full temporal slice of the tunnel at (d, t)."""
    tr = tunnel_radius_4d(d, t, R=R, r_max=r_max)
    fv = fiber_volume(d, t, R=R, r_max=r_max)
    fp = freedom_percentage(d, t, R=R)
    zone = _d_to_level(d)
    portals = compute_portals(d, t, agent_tier, governance_score, R, r_max)

    # Agent position: center of tunnel, at drift distance d along z-axis
    agent_pos = (0.0, 0.0, d)

    # Wall proximity — based on drift ratio
    wp = min(d / DRIFT_QUARANTINE, 1.0) if d > 0 else 0.0

    return TemporalSlice(
        t=t,
        d=d,
        tunnel_r=tr,
        fiber_vol=fv,
        freedom_pct=fp,
        zone=zone,
        portals=portals,
        agent_position=agent_pos,
        wall_proximity=wp,
    )


# ---------------------------------------------------------------------------
#  Agent Journey — the full 4D trajectory
# ---------------------------------------------------------------------------


@dataclass
class JourneyFrame:
    """A single frame of an agent's journey through the Garganta."""

    frame_id: int
    t: float
    d: float
    tunnel_r: float
    freedom_pct: float
    zone: DriftLevel
    portals_available: int
    portal_names: List[str]
    event: str = ""  # What happened: "observe", "nudge", "portal_enter", "quarantine"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame": self.frame_id,
            "t": round(self.t, 2),
            "d": round(self.d, 4),
            "radius": round(self.tunnel_r, 4),
            "freedom": round(self.freedom_pct, 2),
            "zone": self.zone.value,
            "portals": self.portals_available,
            "event": self.event,
        }


def simulate_journey(
    drift_sequence: List[Tuple[float, str]],
    agent_tier: str = "FREE",
    governance_score: float = 0.5,
    R: float = R_BASE,
) -> List[JourneyFrame]:
    """
    Simulate an agent's full journey through the Garganta.

    drift_sequence: list of (drift_distance, event_description) tuples
    Returns: list of JourneyFrames (one per timestep)

    Example:
        journey = simulate_journey([
            (0.1, "Reading arxiv paper"),
            (0.2, "Following citation link"),
            (0.5, "Browsing related products"),   # drift!
            (0.8, "Shopping on Amazon"),           # more drift!
            (0.4, "Back to research"),             # nudge worked
            (0.1, "Reading new paper"),            # recovered
        ])
    """
    frames = []
    for i, (d, event) in enumerate(drift_sequence):
        t = float(i)
        tr = tunnel_radius_4d(d, t, R=R)
        fp = freedom_percentage(d, t, R=R)
        zone = _d_to_level(d)
        portals = compute_portals(d, t, agent_tier, governance_score, R)
        available = [p for p in portals if p.is_accessible]

        frames.append(
            JourneyFrame(
                frame_id=i,
                t=t,
                d=d,
                tunnel_r=tr,
                freedom_pct=fp,
                zone=zone,
                portals_available=len(available),
                portal_names=[p.tongue for p in available],
                event=event,
            )
        )

    return frames


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


def _d_to_level(d: float) -> DriftLevel:
    if d < DRIFT_GENTLE:
        return DriftLevel.ON_TRACK
    elif d < DRIFT_REDIRECT:
        return DriftLevel.GENTLE
    elif d < DRIFT_INSPECT:
        return DriftLevel.REDIRECT
    elif d < DRIFT_QUARANTINE:
        return DriftLevel.INSPECT
    else:
        return DriftLevel.QUARANTINE


# ---------------------------------------------------------------------------
#  ASCII Visualization — tunnel cross-section at a point in time
# ---------------------------------------------------------------------------


def ascii_tunnel_slice(
    d: float,
    t: float = 0.0,
    agent_tier: str = "FREE",
    governance_score: float = 0.5,
    width: int = 50,
) -> str:
    """Render an ASCII cross-section of the tunnel at (d, t)."""
    ts = compute_temporal_slice(d, t, agent_tier, governance_score)
    lines = []
    half = width // 2
    r_chars = int(ts.tunnel_r * half)

    zone_fill = {
        DriftLevel.ON_TRACK: "·",
        DriftLevel.GENTLE: "~",
        DriftLevel.REDIRECT: "≈",
        DriftLevel.INSPECT: "#",
        DriftLevel.QUARANTINE: "X",
    }
    fill = zone_fill[ts.zone]

    # Portal ring
    portal_chars = {}
    accessible_portals = [p for p in ts.portals if p.is_accessible]
    for idx, p in enumerate(accessible_portals):
        angle_pos = int((idx / max(len(accessible_portals), 1)) * (2 * r_chars))
        portal_chars[angle_pos] = p.tongue[0]  # K, A, R, C, U, D

    lines.append(f"  ╔══ Garganta Slice @ d={d:.2f}, t={t:.1f} ══╗")
    lines.append(f"  ║ Zone: {ts.zone.value:<12}  Freedom: {ts.freedom_pct:.1f}%")
    lines.append(
        f"  ║ Radius: {ts.tunnel_r:.4f}    Portals: {sum(1 for p in ts.portals if p.is_accessible)}/6"
    )
    lines.append(f"  ╚{'═' * 38}╝")
    lines.append("")

    for row in range(width // 2):
        y = row - half // 2
        row_chars = []
        for col in range(width):
            x = col - half
            dist = math.sqrt(x * x + y * y)
            if abs(dist - r_chars) < 1.5:
                # Wall — check for portal
                portal_idx = int(
                    (math.atan2(y, x) + math.pi) / (2 * math.pi) * len(SACRED_TONGUES)
                )
                portal_idx = min(portal_idx, len(SACRED_TONGUES) - 1)
                tongue = SACRED_TONGUES[portal_idx]
                is_open = any(
                    p.tongue == tongue and p.is_accessible for p in ts.portals
                )
                row_chars.append(tongue[0] if is_open else "█")
            elif dist < r_chars:
                if abs(x) < 1 and abs(y) < 1:
                    row_chars.append("◆")  # Agent
                else:
                    row_chars.append(fill)
            else:
                row_chars.append(" ")
        lines.append("  " + "".join(row_chars))

    lines.append("")
    lines.append(
        "  Portals: "
        + " ".join(
            f"[{p.tongue}]" if p.is_accessible else f" {p.tongue} " for p in ts.portals
        )
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  Full Journey ASCII — the tunnel narrowing over time
# ---------------------------------------------------------------------------


def ascii_journey(
    drift_sequence: List[Tuple[float, str]],
    width: int = 60,
    agent_tier: str = "FREE",
) -> str:
    """
    Render the full Garganta journey as ASCII.
    Shows tunnel narrowing/widening as agent drifts.

    Each row = one time step. Width of tunnel = freedom.
    """
    lines = []
    lines.append("  GARGANTA JOURNEY — Multi-D Harmonic Tunnel")
    lines.append("  " + "═" * (width + 20))
    lines.append("  r(d,t) = r_max / φ^(d²) · e^(-λt)")
    lines.append("  Fiber: S⁵ × r(d,t)  |  6 portal dimensions (KO/AV/RU/CA/UM/DR)")
    lines.append("")

    zone_fill = {
        DriftLevel.ON_TRACK: "░",
        DriftLevel.GENTLE: "▒",
        DriftLevel.REDIRECT: "▓",
        DriftLevel.INSPECT: "█",
        DriftLevel.QUARANTINE: "╳",
    }

    frames = simulate_journey(drift_sequence, agent_tier)
    center = width // 2

    for frame in frames:
        fill = zone_fill[frame.zone]
        half_w = int(frame.tunnel_r * (center - 2))
        half_w = max(half_w, 0)

        line_chars = [" "] * width

        # Walls
        left = center - half_w - 1
        right = center + half_w + 1
        if 0 <= left < width:
            line_chars[left] = "│"
        if 0 <= right < width:
            line_chars[right] = "│"

        # Fill interior
        for c in range(max(0, center - half_w), min(width, center + half_w + 1)):
            if line_chars[c] == " ":
                line_chars[c] = fill

        # Agent marker
        line_chars[center] = "◆"

        # Portal markers on walls
        if frame.portals_available > 0:
            for idx, tongue in enumerate(frame.portal_names[:3]):
                # Show on the right wall
                rpos = right + 1 + idx
                if rpos < width:
                    line_chars[rpos] = tongue[0]

        line_str = "".join(line_chars)
        # Label
        label = f" t={frame.t:.0f} d={frame.d:.2f} {frame.zone.value:<11} P={frame.portals_available}"
        event = f" | {frame.event}" if frame.event else ""

        lines.append(f"  {line_str}{label}{event}")

    lines.append("")
    lines.append("  " + "═" * (width + 20))
    lines.append("  ░ ON_TRACK  ▒ GENTLE  ▓ REDIRECT  █ INSPECT  ╳ QUARANTINE")
    lines.append(
        "  ◆ Agent  │ Tunnel Wall  K/A/R/C/U/D = Portal to Sacred Tongue realm"
    )
    lines.append("")

    # Freedom summary
    lines.append("  MULTI-D FREEDOM TABLE (6D fiber volume):")
    lines.append("  ┌─────────┬──────────┬───────────┬──────────────┬─────────┐")
    lines.append("  │ Drift d │ Radius   │ Freedom % │ Zone         │ Portals │")
    lines.append("  ├─────────┼──────────┼───────────┼──────────────┼─────────┤")
    for d_val in [0.0, 0.3, 0.7, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0]:
        r_val = tunnel_radius(d_val)
        f_val = freedom_percentage(d_val)
        z_val = _d_to_level(d_val)
        portals = compute_portals(d_val, 0.0, agent_tier)
        n_open = sum(1 for p in portals if p.is_accessible)
        lines.append(
            f"  │ {d_val:>5.1f}   │ {r_val:>8.4f} │ {f_val:>8.3f}%  │ {z_val.value:<12} │ {n_open}/6     │"
        )
    lines.append("  └─────────┴──────────┴───────────┴──────────────┴─────────┘")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  Matplotlib 3D Visualization
# ---------------------------------------------------------------------------


def render_3d_tunnel(
    save_path: Optional[str] = None,
    length: float = 3.5,
    agent_drifts: Optional[List[float]] = None,
    show: bool = True,
) -> Optional[str]:
    """
    Render a 3D matplotlib visualization of the Garganta.
    Shows tunnel narrowing + zone colors + agent path.
    """
    try:
        import numpy as np
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    except ImportError:
        return None

    n_z, n_theta = 150, 64
    z_vals = np.linspace(0, length, n_z)
    theta_vals = np.linspace(0, 2 * np.pi, n_theta)
    Z_grid, Theta_grid = np.meshgrid(z_vals, theta_vals, indexing="ij")

    R_grid = np.array([[tunnel_radius(d) for _ in theta_vals] for d in z_vals])
    X_grid = R_grid * np.cos(Theta_grid)
    Y_grid = R_grid * np.sin(Theta_grid)

    # Zone colors
    colors = np.zeros((*Z_grid.shape, 4))
    for i, d in enumerate(z_vals):
        zone = _d_to_level(d)
        colors[i, :] = ZONE_COLORS[zone]

    fig = plt.figure(figsize=(16, 8))

    # --- 3D tunnel ---
    ax1 = fig.add_subplot(121, projection="3d")
    ax1.plot_surface(
        X_grid,
        Y_grid,
        Z_grid,
        facecolors=colors,
        shade=True,
        alpha=0.5,
        edgecolors="none",
    )

    # Agent path
    if agent_drifts:
        az = np.array(agent_drifts)
        ar = np.array([tunnel_radius(d) * 0.3 for d in agent_drifts])
        at = np.linspace(0, len(agent_drifts) * 0.4, len(agent_drifts))
        ax_path = ar * np.cos(at)
        ay_path = ar * np.sin(at)
        ax1.plot(ax_path, ay_path, az, color="white", linewidth=2.5, label="Agent path")
        ax1.scatter(
            [ax_path[-1]],
            [ay_path[-1]],
            [az[-1]],
            color="red",
            s=100,
            zorder=5,
            label="Now",
        )

    # Zone rings
    for d_b in [DRIFT_GENTLE, DRIFT_REDIRECT, DRIFT_INSPECT, DRIFT_QUARANTINE]:
        if d_b <= length:
            br = tunnel_radius(d_b)
            btheta = np.linspace(0, 2 * np.pi, 64)
            ax1.plot(
                br * np.cos(btheta),
                br * np.sin(btheta),
                np.full(64, d_b),
                color="white",
                linewidth=0.8,
                alpha=0.4,
            )

    ax1.set_xlabel("X")
    ax1.set_ylabel("Y")
    ax1.set_zlabel("Drift (d)")
    ax1.set_title("GARGANTA MANIFOLD\nMulti-D Harmonic Tunnel", color="white")
    ax1.set_xlim(-1.1, 1.1)
    ax1.set_ylim(-1.1, 1.1)
    if agent_drifts:
        ax1.legend(fontsize=8, loc="upper left")

    # --- 2D Profile ---
    ax2 = fig.add_subplot(122)
    d_line = np.linspace(0, length, 300)
    r_line = np.array([tunnel_radius(d) for d in d_line])

    # Zone fills
    zone_bounds = [
        0,
        DRIFT_GENTLE,
        DRIFT_REDIRECT,
        DRIFT_INSPECT,
        DRIFT_QUARANTINE,
        length,
    ]
    zone_names = ["ON_TRACK", "GENTLE", "REDIRECT", "INSPECT", "QUARANTINE"]
    zone_rgba = [
        (0.2, 0.4, 0.9, 0.3),
        (0.2, 0.8, 0.4, 0.3),
        (0.9, 0.8, 0.2, 0.3),
        (0.9, 0.3, 0.1, 0.3),
        (0.3, 0.0, 0.3, 0.3),
    ]
    for idx in range(len(zone_names)):
        lo, hi = zone_bounds[idx], zone_bounds[idx + 1]
        mask = (d_line >= lo) & (d_line <= hi)
        ax2.fill_between(
            d_line[mask],
            -r_line[mask],
            r_line[mask],
            color=zone_rgba[idx],
            label=zone_names[idx],
        )

    ax2.plot(d_line, r_line, color="cyan", linewidth=2)
    ax2.plot(d_line, -r_line, color="cyan", linewidth=2)
    for d_b in [DRIFT_GENTLE, DRIFT_REDIRECT, DRIFT_INSPECT, DRIFT_QUARANTINE]:
        ax2.axvline(x=d_b, color="white", linestyle="--", alpha=0.4)

    if agent_drifts:
        ax2.plot(agent_drifts[-1], 0, "ro", markersize=10, label="Agent")

    ax2.set_xlabel("Drift (d)")
    ax2.set_ylabel("Tunnel radius")
    ax2.set_title("TUNNEL PROFILE: r(d) = 1/φ^(d²)", color="white")
    ax2.set_facecolor("#0a0a1a")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.2)
    ax2.tick_params(colors="white")
    ax2.xaxis.label.set_color("white")
    ax2.yaxis.label.set_color("white")

    fig.patch.set_facecolor("#0a0a1a")
    ax1.tick_params(colors="white")
    ax1.xaxis.label.set_color("white")
    ax1.yaxis.label.set_color("white")
    ax1.zaxis.label.set_color("white")

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="#0a0a1a")
    if show:
        plt.show()
    return save_path
