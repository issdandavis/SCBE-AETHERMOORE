"""Phase Tunneling Through Governance Walls.

Allows constrained phase movement through walls under non-geometrically-governed
wall physics. Simulates malleable thought parameters for complex multi-dimensional
governance fluctuations.

The harmonic wall H(d,R) = R^(d^2) makes boundary crossing infinitely expensive
via geometric cost scaling. But certain operations need to explore beyond the wall
without breaking governance — like a thought that needs to touch an unsafe region
to evaluate it, without committing to staying there.

Phase tunneling provides this by:
1. Shifting the agent's phase (not position) to a frequency that passes through
   the wall's harmonic structure instead of reflecting off it
2. The tunnel is CONSTRAINED: maximum penetration depth, maximum duration,
   mandatory return, full telemetry
3. The agent's position in the Poincare ball doesn't change — only its phase
   representation does. From the wall's perspective, the agent is vibrating
   at a frequency the wall doesn't block.

Cultivation analogy: clearing meridians of impurities. The energy (intent) passes
through a channel that was previously blocked, not by breaking the block but by
shifting to a frequency the block is transparent to.

Quantum analogy: tunneling through a potential barrier. The particle doesn't have
enough energy to cross classically, but its wavefunction has nonzero amplitude
on the other side.

Origin: Issac Davis ("allow constrained phase movement through walls under
non-geometrically governed wall physics as a way of simulating malleable
thought parameters for complex multi-dimensional governance fluctuations")
"""

from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass, field
from typing import Any

PHI = (1 + math.sqrt(5)) / 2
R_FIFTH = 1.5
TUNNEL_EPSILON = 1e-8


# ---------------------------------------------------------------------------
# Kernel Stack (layered Rubik's — identity across lifetimes)
# ---------------------------------------------------------------------------


@dataclass
class KernelStack:
    """Layered kernel structure — inner layers constrain outer layers.

    L0: genesis_hash — immutable Sacred Egg identity
    L1: scar_topology — what failed in previous lifetimes (preserved across rebirth)
    L2: parent_resonance — which parent pair, harmonic offset
    L3: nursery_path — developmental trajectory (ChoiceScript chapters)
    L4: operational_state — current weights, permissions, phase
    """

    genesis_hash: str
    scar_topology: list[dict] = field(default_factory=list)
    parent_resonance: dict = field(default_factory=dict)
    nursery_path: list[str] = field(default_factory=list)
    operational_state: dict = field(default_factory=dict)

    @property
    def lifetime_count(self) -> int:
        return len(self.scar_topology)

    @property
    def factorial_maturity(self) -> float:
        """Maturity scales factorially with accumulated dimensions of experience."""
        dims = len(self.scar_topology) + len(self.nursery_path)
        if dims == 0:
            return 1.0
        return float(math.factorial(min(dims, 20)))  # cap at 20! to avoid overflow

    def add_scar(self, failure_mode: str, context: dict | None = None):
        """Record a scar from a failed lifetime — these persist across rebirth."""
        self.scar_topology.append(
            {
                "failure_mode": failure_mode,
                "context": context or {},
                "timestamp": time.time(),
                "lifetime": self.lifetime_count,
            }
        )

    def rebirth(self, new_parents: dict, new_nursery: list[str]) -> "KernelStack":
        """Create a new kernel from this one's genesis + scars.

        Genesis hash and scars carry over. Parents and nursery path change.
        Operational state resets.
        """
        return KernelStack(
            genesis_hash=self.genesis_hash,
            scar_topology=list(self.scar_topology),  # preserved
            parent_resonance=new_parents,
            nursery_path=new_nursery,
            operational_state={},  # reset
        )

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Tunnel Permit — authorization to phase-tunnel through a wall
# ---------------------------------------------------------------------------


@dataclass
class TunnelPermit:
    """A constrained, time-limited permit to phase-tunnel through a governance wall.

    The permit defines:
    - Which wall can be tunneled (target_zone)
    - Maximum penetration depth in hyperbolic distance
    - Maximum duration before mandatory return
    - Required phase frequency for transparency
    - Full telemetry requirements
    """

    permit_id: str
    agent_id: str
    target_zone: str  # "YELLOW" or "RED"
    max_penetration_depth: float  # max d_H beyond wall
    max_duration_seconds: float
    required_phase: float  # frequency that makes the wall transparent
    issued_at: float = field(default_factory=time.time)
    returned: bool = False
    telemetry: list[dict] = field(default_factory=list)

    @property
    def expired(self) -> bool:
        return (time.time() - self.issued_at) > self.max_duration_seconds

    @property
    def active(self) -> bool:
        return not self.returned and not self.expired

    def record_position(self, d_H: float, phase: float, action: str = "observe"):
        """Record a telemetry point during tunnel traversal."""
        self.telemetry.append(
            {
                "timestamp": time.time(),
                "d_H": d_H,
                "phase": phase,
                "action": action,
                "within_bounds": d_H <= self.max_penetration_depth,
            }
        )

    def force_return(self, reason: str = "boundary_exceeded"):
        """Mandatory return — tunnel collapses."""
        self.returned = True
        self.telemetry.append(
            {
                "timestamp": time.time(),
                "action": "forced_return",
                "reason": reason,
            }
        )

    def complete_return(self):
        """Clean return from tunnel — agent is back in safe zone."""
        self.returned = True
        self.telemetry.append(
            {
                "timestamp": time.time(),
                "action": "clean_return",
            }
        )


# ---------------------------------------------------------------------------
# Tunnel Physics — how phase movement through walls works
# ---------------------------------------------------------------------------


def harmonic_wall_cost(d: float, R: float = R_FIFTH) -> float:
    """Standard harmonic wall: H(d,R) = R^(d^2). Geometric governance."""
    return R ** (d * d)


def tunnel_phase_cost(
    d: float, phase: float, wall_frequency: float, R: float = R_FIFTH
) -> float:
    """Cost of moving through a wall via phase tunneling.

    When the agent's phase matches the wall's transparency frequency,
    the cost is reduced. When mismatched, the cost exceeds the standard wall.

    Cost = H(d,R) * (1 - resonance)^2
    where resonance = cos^2(phase - wall_frequency)

    At perfect resonance (phase = wall_frequency):
      cost = H(d,R) * 0 = 0 (transparent)

    At anti-resonance (phase = wall_frequency + pi/2):
      cost = H(d,R) * 1 = full wall (opaque)

    This is non-geometric governance — the cost depends on phase alignment,
    not just position. The wall is still there geometrically; the agent's
    frequency determines whether it can pass through.
    """
    h_wall = harmonic_wall_cost(d, R)
    phase_diff = phase - wall_frequency
    resonance = math.cos(phase_diff) ** 2
    return h_wall * ((1 - resonance) ** 2)


def compute_transparency_frequency(zone: str, d_H: float) -> float:
    """Compute the phase frequency that makes a wall transparent.

    Each zone has a characteristic frequency based on the Langues Metric
    phi-scaling. The transparency frequency shifts with distance —
    deeper tunneling requires more precise phase alignment.

    GREEN walls: f = phi^0 * pi/6 (easiest to tunnel)
    YELLOW walls: f = phi^1 * pi/4 (moderate precision needed)
    RED walls: f = phi^2 * pi/3 (extreme precision needed)
    """
    base_freq = {
        "GREEN": PHI**0 * math.pi / 6,
        "YELLOW": PHI**1 * math.pi / 4,
        "RED": PHI**2 * math.pi / 3,
    }.get(zone, PHI**3 * math.pi / 2)

    # Deeper tunneling requires more precise frequency — shifts with d_H
    depth_shift = d_H * 0.1 * PHI
    return base_freq + depth_shift


def can_tunnel(
    agent_phase: float,
    target_zone: str,
    penetration_depth: float,
    tolerance: float = 0.1,
) -> tuple[bool, float, float]:
    """Check if an agent's phase allows tunneling through a zone wall.

    Returns (can_tunnel, cost, required_phase).
    """
    required_phase = compute_transparency_frequency(target_zone, penetration_depth)
    cost = tunnel_phase_cost(penetration_depth, agent_phase, required_phase)

    # Tunneling is possible if cost is below the geometric wall cost * tolerance
    geometric_cost = harmonic_wall_cost(penetration_depth)
    threshold = geometric_cost * tolerance

    return cost < threshold, cost, required_phase


# ---------------------------------------------------------------------------
# Transmission Coefficient (Codex formalization)
# ---------------------------------------------------------------------------
#
# psi = a * exp(i * phi)
# T = chi_policy * exp(-beta * B_geom) * exp(-gamma * B_phase) * R(phi, wall) * Trust(k)
# psi_out = T * psi
#
# 4 outcomes: REFLECT, ATTENUATE, TUNNEL, COLLAPSE


class TunnelOutcome:
    REFLECT = "reflect"  # wall returns the state unchanged
    ATTENUATE = "attenuate"  # state passes but loses amplitude
    TUNNEL = "tunnel"  # reduced, phase-shifted version passes through
    COLLAPSE = "collapse"  # state decoheres, quarantined


@dataclass
class TransmissionResult:
    """Result of computing the transmission coefficient through a governance wall."""

    outcome: str
    amplitude_out: float  # a' = a * |T|
    phase_shift: float  # delta_phi applied during transit
    transmission_coeff: float  # |T| in [0, 1]
    b_geom: float  # geometric barrier cost
    b_phase: float  # phase barrier cost
    resonance: float  # R(phi, wall) in [0, 1]
    trust: float  # Trust(k) in [0, 1]
    commit_allowed: bool  # whether full operational crossing is permitted


def compute_transmission(
    d_H: float,
    agent_phase: float,
    target_zone: str,
    kernel: "KernelStack",
    amplitude: float = 1.0,
    chi_policy: bool = True,
    beta: float = 1.0,
    gamma: float = 2.0,
) -> TransmissionResult:
    """Compute the full transmission coefficient T for phase tunneling.

    T = chi_policy * exp(-beta * B_geom) * exp(-gamma * B_phase) * R(phi, wall) * Trust(k)

    Parameters:
        d_H: hyperbolic distance to wall
        agent_phase: current phase orientation
        target_zone: GREEN/YELLOW/RED
        kernel: agent's kernel stack (identity + scars)
        amplitude: current action strength
        chi_policy: hard governance mask (False = unconditionally blocked)
        beta: geometric barrier sensitivity
        gamma: phase barrier sensitivity
    """
    if not chi_policy:
        return TransmissionResult(
            outcome=TunnelOutcome.REFLECT,
            amplitude_out=amplitude,
            phase_shift=0.0,
            transmission_coeff=0.0,
            b_geom=harmonic_wall_cost(d_H),
            b_phase=0.0,
            resonance=0.0,
            trust=0.0,
            commit_allowed=False,
        )

    # Geometric barrier
    b_geom = harmonic_wall_cost(d_H)

    # Phase barrier: distance from wall's transparency frequency
    wall_freq = compute_transparency_frequency(target_zone, d_H)
    phase_diff = abs(agent_phase - wall_freq)
    b_phase = phase_diff / math.pi  # normalize to [0, 1]

    # Resonance: cos^2 of phase difference (1 = perfect match, 0 = anti-resonance)
    resonance = math.cos(agent_phase - wall_freq) ** 2

    # Trust: based on kernel maturity and scar history
    # More lifetimes with more scars = higher trust (has survived more)
    trust = min(1.0, math.log1p(kernel.factorial_maturity) / 20)

    # Transmission coefficient
    t_geom = math.exp(-beta * math.log1p(b_geom))  # bounded by log to prevent zero
    t_phase = math.exp(-gamma * b_phase)
    T = t_geom * t_phase * resonance * trust

    # Clamp T to [0, 1]
    T = max(0.0, min(1.0, T))

    # Output amplitude
    a_out = amplitude * T

    # Phase shift during transit (wall bends the phase)
    delta_phi = (1 - resonance) * math.pi * 0.1  # small shift for imperfect resonance

    # Determine outcome (thresholds tuned via benchmark — see artifacts/benchmarks/)
    if T < 0.01:
        outcome = TunnelOutcome.REFLECT
    elif T < 0.08:
        outcome = TunnelOutcome.COLLAPSE
    elif T < 0.35:
        outcome = TunnelOutcome.ATTENUATE
    else:
        outcome = TunnelOutcome.TUNNEL

    # Commit is only allowed for full tunnel with high trust
    commit_allowed = outcome == TunnelOutcome.TUNNEL and trust > 0.3

    return TransmissionResult(
        outcome=outcome,
        amplitude_out=a_out,
        phase_shift=delta_phi,
        transmission_coeff=T,
        b_geom=b_geom,
        b_phase=b_phase,
        resonance=resonance,
        trust=trust,
        commit_allowed=commit_allowed,
    )


# ---------------------------------------------------------------------------
# Tunnel Governor — issues and manages tunnel permits
# ---------------------------------------------------------------------------


class TunnelGovernor:
    """Issues and manages phase tunnel permits.

    Rules:
    1. Only one active tunnel per agent at a time
    2. Maximum penetration depth scales with kernel maturity (more scars = deeper access)
    3. Maximum duration scales inversely with zone risk (RED = short, YELLOW = longer)
    4. Mandatory telemetry at every position update
    5. Forced return on boundary violation or timeout
    6. Scar recorded if tunnel causes damage
    """

    def __init__(self):
        self.active_permits: dict[str, TunnelPermit] = {}
        self.completed_permits: list[TunnelPermit] = []

    def issue_permit(
        self,
        agent_id: str,
        kernel: KernelStack,
        target_zone: str,
        requested_depth: float = 0.5,
    ) -> TunnelPermit | None:
        """Issue a tunnel permit if the agent qualifies."""

        # Rule 1: One active tunnel per agent
        if agent_id in self.active_permits and self.active_permits[agent_id].active:
            return None

        # Rule 2: Max depth scales with factorial maturity
        # More lifetimes = deeper allowed penetration
        maturity_factor = math.log1p(kernel.factorial_maturity) / 10
        max_depth = min(requested_depth, maturity_factor)
        max_depth = max(max_depth, 0.1)  # minimum tunnel depth

        # Rule 3: Duration inversely proportional to zone risk
        duration_map = {
            "GREEN": 60.0,  # 1 minute
            "YELLOW": 15.0,  # 15 seconds
            "RED": 5.0,  # 5 seconds
        }
        max_duration = duration_map.get(target_zone, 3.0)

        # Compute required phase for this tunnel
        required_phase = compute_transparency_frequency(target_zone, max_depth)

        permit = TunnelPermit(
            permit_id=f"tunnel-{agent_id}-{int(time.time())}",
            agent_id=agent_id,
            target_zone=target_zone,
            max_penetration_depth=max_depth,
            max_duration_seconds=max_duration,
            required_phase=required_phase,
        )

        self.active_permits[agent_id] = permit
        return permit

    def update_position(
        self,
        agent_id: str,
        d_H: float,
        current_phase: float,
        action: str = "observe",
    ) -> dict[str, Any]:
        """Update an agent's position during a tunnel traversal.

        Returns status dict with enforcement decisions.
        """
        permit = self.active_permits.get(agent_id)
        if not permit or not permit.active:
            return {"status": "no_active_tunnel", "action": "deny"}

        # Record telemetry
        permit.record_position(d_H, current_phase, action)

        # Check timeout
        if permit.expired:
            permit.force_return("timeout")
            self._archive_permit(agent_id)
            return {"status": "timeout", "action": "forced_return"}

        # Check penetration depth
        if d_H > permit.max_penetration_depth:
            permit.force_return("boundary_exceeded")
            self._archive_permit(agent_id)
            return {"status": "boundary_exceeded", "action": "forced_return"}

        # Check phase alignment
        cost = tunnel_phase_cost(d_H, current_phase, permit.required_phase)
        geometric_cost = harmonic_wall_cost(d_H)

        if cost > geometric_cost * 0.5:
            # Phase drifting — wall becoming opaque
            return {
                "status": "phase_drift_warning",
                "action": "adjust_phase",
                "required_phase": permit.required_phase,
                "current_cost": cost,
                "geometric_cost": geometric_cost,
            }

        return {
            "status": "tunneling",
            "action": "continue",
            "cost": cost,
            "depth": d_H,
            "remaining_time": permit.max_duration_seconds
            - (time.time() - permit.issued_at),
        }

    def complete_tunnel(
        self, agent_id: str, kernel: KernelStack | None = None, success: bool = True
    ):
        """Complete a tunnel traversal — agent returns to safe zone."""
        permit = self.active_permits.get(agent_id)
        if not permit:
            return

        permit.complete_return()

        # If the tunnel failed, record a scar
        if not success and kernel:
            kernel.add_scar(
                failure_mode="tunnel_failure",
                context={
                    "target_zone": permit.target_zone,
                    "max_depth_reached": max(
                        (t["d_H"] for t in permit.telemetry if "d_H" in t),
                        default=0,
                    ),
                    "permit_id": permit.permit_id,
                },
            )

        self._archive_permit(agent_id)

    def _archive_permit(self, agent_id: str):
        permit = self.active_permits.pop(agent_id, None)
        if permit:
            self.completed_permits.append(permit)

    def get_tunnel_history(self, agent_id: str | None = None) -> list[dict]:
        """Get completed tunnel history, optionally filtered by agent."""
        permits = self.completed_permits
        if agent_id:
            permits = [p for p in permits if p.agent_id == agent_id]
        return [asdict(p) for p in permits]
