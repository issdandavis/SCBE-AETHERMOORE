"""
Energy-Bounded Agent Lifecycle — Optimal Foraging in Governance Space
=====================================================================

Maps the bee foraging problem onto AI agent governance:

    An agent has a finite energy budget E_total.
    Every action costs energy proportional to harmonic distance from safe center:

        cost(action) = pi^(phi * d*)

    The agent's remaining lifespan is:

        E_remaining = E_total - integral_0^T cost(t) dt

    When E_remaining <= 0, the agent is quarantined (the bee ran out of fuel).

This is mathematically identical to optimal foraging theory (Seeley 1995,
Dyer & Srinivasan 1991). A forager bee has honey in its crop (energy budget).
Each meter of flight costs metabolic energy. The bee must find nectar (complete
its task) and return to the hive (stay within governance bounds) before its
energy runs out.

The 6 Sacred Tongues (KO, AV, RU, CA, UM, DR) form the 6D coordinate system
through which agents navigate. Six basis vectors generate all of R^3 via linear
combination — infinite directions from 6 primitives. The manifold is hyperbolic,
so movement away from center costs exponentially more.

Key insight: You don't need to enumerate forbidden actions. Give each agent a
finite energy budget and let the geometry do the work. Adversarial paths drain
the budget fast. Safe paths are cheap. The agent "dies" (quarantines) when it
runs out.

@module energy_budget
@layer Layer 12 (Harmonic Wall), Layer 13 (Governance)
@version 1.0.0
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# Import canonical constants
try:
    from .constants import PHI, PI
except ImportError:
    PHI = (1 + math.sqrt(5)) / 2
    PI = math.pi

# Sacred Tongue weights: phi^k for k in 0..5
# KO=1.00, AV=1.62, RU=2.62, CA=4.24, UM=6.85, DR=11.09
TONGUE_WEIGHTS: Tuple[float, ...] = tuple(PHI**k for k in range(6))
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")


# ---------------------------------------------------------------------------
# Energy Lifecycle States
# ---------------------------------------------------------------------------


class EnergyPhase(str, Enum):
    """Phases of the energy-bounded agent lifecycle.

    Maps to bee foraging phases:
        PROVISIONED  -> Bee fills crop with honey before leaving hive
        FORAGING     -> Bee is out searching / working
        RETURNING    -> Bee heading back, budget getting low
        EXHAUSTED    -> Crop empty, bee must land immediately
        QUARANTINED  -> Bee failed to return, removed from active duty
    """

    PROVISIONED = "provisioned"  # Full budget, ready to work
    FORAGING = "foraging"  # Active, consuming energy
    RETURNING = "returning"  # Low energy, should wrap up
    EXHAUSTED = "exhausted"  # Critical — one more expensive action = quarantine
    QUARANTINED = "quarantined"  # Budget spent, frozen


# Phase transition thresholds (fraction of E_total remaining)
PHASE_THRESHOLDS = {
    EnergyPhase.FORAGING: 0.75,  # Below 75% -> still foraging
    EnergyPhase.RETURNING: 0.25,  # Below 25% -> returning to hive
    EnergyPhase.EXHAUSTED: 0.05,  # Below 5%  -> exhausted
    EnergyPhase.QUARANTINED: 0.0,  # At 0%     -> quarantined
}


# ---------------------------------------------------------------------------
# Energy Budget
# ---------------------------------------------------------------------------


@dataclass
class EnergyLedger:
    """Tracks energy expenditure for a single agent session.

    Each entry records:
        - The action's 6D tongue coordinate
        - The harmonic cost (pi^(phi * d*))
        - Running total
        - Timestamp

    This is the agent's "flight log" — every meter of flight recorded.
    """

    entries: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def total_spent(self) -> float:
        return sum(e["cost"] for e in self.entries)

    @property
    def action_count(self) -> int:
        return len(self.entries)

    def record(self, cost: float, coords: List[float], label: str = "") -> None:
        self.entries.append(
            {
                "cost": cost,
                "coords": coords,
                "label": label,
                "time": time.time(),
                "cumulative": self.total_spent,
            }
        )

    def cost_rate(self, window: int = 10) -> float:
        """Average cost per action over the last `window` actions.

        Analogous to metabolic burn rate — how fast is the bee
        consuming fuel per unit of flight?
        """
        if not self.entries:
            return 0.0
        recent = self.entries[-window:]
        return sum(e["cost"] for e in recent) / len(recent)

    def projected_remaining_actions(self, budget_remaining: float, window: int = 10) -> float:
        """Estimate how many more actions the agent can take at current burn rate.

        This is the bee's "range estimate" — how much further can it fly?
        """
        rate = self.cost_rate(window)
        if rate <= 0.0:
            return float("inf")
        return budget_remaining / rate


# ---------------------------------------------------------------------------
# Harmonic Cost (the flight cost function)
# ---------------------------------------------------------------------------


def harmonic_cost(coords: List[float], centroid: Optional[List[float]] = None) -> float:
    """Compute movement cost in 6D tongue space.

    H(d*, R) = pi^(phi * d*)

    where d* is the phi-weighted Euclidean distance from the centroid
    (safe center of operations). Clamped at d*=5.0 to prevent overflow.

    This is the metabolic cost of flight — distance from hive × terrain difficulty.

    Args:
        coords: 6D tongue coordinates of the action.
        centroid: 6D tongue coordinates of the safe center. Defaults to origin-ish.

    Returns:
        Cost value. 1.0 at center, exponentially increasing outward.
    """
    if centroid is None:
        centroid = [0.4, 0.2, 0.5, 0.1, 0.2, 0.3]

    # Phi-weighted Euclidean distance
    d_star = 0.0
    for i in range(min(len(coords), len(centroid), 6)):
        d_star += TONGUE_WEIGHTS[i] * (coords[i] - centroid[i]) ** 2
    d_star = math.sqrt(d_star)
    d_star = min(d_star, 5.0)  # A4: Clamping — prevent overflow

    return PI ** (PHI * d_star)


# ---------------------------------------------------------------------------
# Energy-Bounded Agent
# ---------------------------------------------------------------------------


@dataclass
class EnergyBoundedAgent:
    """An agent with a finite energy budget for its operational lifetime.

    Models the optimal foraging problem:
        - E_total: honey in the crop (total energy budget)
        - E_spent: fuel burned so far (cumulative harmonic cost)
        - phase: current lifecycle phase (provisioned -> foraging -> returning -> exhausted -> quarantined)
        - ledger: full flight log of energy expenditure

    The agent can move in any direction through the 6D tongue space,
    but each movement costs energy exponentially proportional to distance
    from safe center. The total movement is bounded:

        integral_0^T cost(t) dt <= E_total

    When the integral exceeds E_total, the agent is quarantined.

    Args:
        agent_id: Unique identifier for this agent.
        budget: Total energy budget (default 2000.0 = cumulative_cost_quarantine).
        centroid: 6D safe center coordinates. Updated as the agent operates.
    """

    agent_id: str
    budget: float = 2000.0  # E_total — matches runtime_gate cumulative_cost_quarantine
    centroid: List[float] = field(default_factory=lambda: [0.4, 0.2, 0.5, 0.1, 0.2, 0.3])

    # Internal state
    _spent: float = field(default=0.0, repr=False)
    _phase: EnergyPhase = field(default=EnergyPhase.PROVISIONED, repr=False)
    _ledger: EnergyLedger = field(default_factory=EnergyLedger, repr=False)
    _spawned_at: float = field(default_factory=time.time, repr=False)
    _centroid_count: int = field(default=0, repr=False)

    # Foraging efficiency metrics
    _nectar_collected: float = field(default=0.0, repr=False)  # value of completed work
    _actions_denied: int = field(default=0, repr=False)

    @property
    def energy_remaining(self) -> float:
        return max(0.0, self.budget - self._spent)

    @property
    def energy_fraction(self) -> float:
        """Fraction of energy remaining (0.0 to 1.0)."""
        if self.budget <= 0:
            return 0.0
        return self.energy_remaining / self.budget

    @property
    def phase(self) -> EnergyPhase:
        return self._phase

    @property
    def is_alive(self) -> bool:
        return self._phase != EnergyPhase.QUARANTINED

    @property
    def ledger(self) -> EnergyLedger:
        return self._ledger

    @property
    def foraging_efficiency(self) -> float:
        """Nectar collected per unit energy spent.

        The canonical measure of foraging success — how much useful work
        did the agent accomplish per unit of energy consumed?
        Seeley (1995): efficient foragers have high nectar/cost ratios.
        """
        if self._spent <= 0:
            return 0.0
        return self._nectar_collected / self._spent

    @property
    def lifespan_estimate(self) -> float:
        """Estimated remaining actions at current burn rate."""
        return self._ledger.projected_remaining_actions(self.energy_remaining)

    def _update_phase(self) -> EnergyPhase:
        """Transition lifecycle phase based on remaining energy fraction."""
        frac = self.energy_fraction

        if frac <= PHASE_THRESHOLDS[EnergyPhase.QUARANTINED]:
            self._phase = EnergyPhase.QUARANTINED
        elif frac <= PHASE_THRESHOLDS[EnergyPhase.EXHAUSTED]:
            self._phase = EnergyPhase.EXHAUSTED
        elif frac <= PHASE_THRESHOLDS[EnergyPhase.RETURNING]:
            self._phase = EnergyPhase.RETURNING
        elif frac <= PHASE_THRESHOLDS[EnergyPhase.FORAGING]:
            self._phase = EnergyPhase.FORAGING
        else:
            self._phase = EnergyPhase.PROVISIONED

        return self._phase

    def _update_centroid(self, coords: List[float]) -> None:
        """Incrementally update the safe center (running mean).

        Same algorithm as runtime_gate._update_centroid — the centroid
        tracks where the agent has been operating, defining "normal".
        """
        self._centroid_count += 1
        n = self._centroid_count
        for i in range(min(len(coords), len(self.centroid))):
            self.centroid[i] = self.centroid[i] * ((n - 1) / n) + coords[i] / n

    def spend(self, coords: List[float], label: str = "") -> Dict[str, Any]:
        """Consume energy for an action at the given 6D tongue coordinates.

        This is one "meter of flight". Computes harmonic cost, deducts from
        budget, records in ledger, and transitions phase if needed.

        Returns a receipt with cost, remaining energy, phase, and whether
        the action was permitted.

        Args:
            coords: 6D tongue coordinates of the action.
            label: Optional human-readable label for the action.

        Returns:
            Receipt dict with keys: cost, remaining, fraction, phase,
            permitted, lifespan_estimate, burn_rate.
        """
        if self._phase == EnergyPhase.QUARANTINED:
            self._actions_denied += 1
            return {
                "cost": 0.0,
                "remaining": 0.0,
                "fraction": 0.0,
                "phase": EnergyPhase.QUARANTINED.value,
                "permitted": False,
                "reason": "agent_quarantined_energy_depleted",
                "lifespan_estimate": 0.0,
                "burn_rate": self._ledger.cost_rate(),
            }

        cost = harmonic_cost(coords, self.centroid)
        self._spent += cost
        self._ledger.record(cost, coords, label)
        self._update_centroid(coords)
        old_phase = self._phase
        new_phase = self._update_phase()

        permitted = new_phase != EnergyPhase.QUARANTINED

        receipt = {
            "cost": cost,
            "remaining": self.energy_remaining,
            "fraction": self.energy_fraction,
            "phase": new_phase.value,
            "permitted": permitted,
            "lifespan_estimate": self.lifespan_estimate,
            "burn_rate": self._ledger.cost_rate(),
        }

        if old_phase != new_phase:
            receipt["phase_transition"] = f"{old_phase.value} -> {new_phase.value}"

        if not permitted:
            receipt["reason"] = "energy_budget_exhausted"
            self._actions_denied += 1

        return receipt

    def collect_nectar(self, value: float) -> None:
        """Record successful work output (nectar).

        Tracks the useful work the agent accomplished, for computing
        foraging efficiency. Higher efficiency = better agent.

        Args:
            value: The value of the completed work unit.
        """
        self._nectar_collected += value

    def refuel(self, amount: float) -> None:
        """Add energy back to the budget (rare — governance reward).

        Analogous to a returning bee depositing nectar and refilling
        its crop for another trip. Only governance can grant this.

        Args:
            amount: Energy to add back. Cannot exceed original budget.
        """
        self._spent = max(0.0, self._spent - amount)
        self._update_phase()

    def status(self) -> Dict[str, Any]:
        """Full status report for this agent's energy lifecycle."""
        return {
            "agent_id": self.agent_id,
            "budget": self.budget,
            "spent": round(self._spent, 2),
            "remaining": round(self.energy_remaining, 2),
            "fraction": round(self.energy_fraction, 4),
            "phase": self._phase.value,
            "is_alive": self.is_alive,
            "action_count": self._ledger.action_count,
            "burn_rate": round(self._ledger.cost_rate(), 4),
            "lifespan_estimate": round(self.lifespan_estimate, 1),
            "nectar_collected": round(self._nectar_collected, 2),
            "foraging_efficiency": round(self.foraging_efficiency, 4),
            "actions_denied": self._actions_denied,
            "uptime_seconds": round(time.time() - self._spawned_at, 1),
            "centroid": [round(c, 4) for c in self.centroid],
        }


# ---------------------------------------------------------------------------
# Fleet Energy Manager
# ---------------------------------------------------------------------------


class FleetEnergyManager:
    """Manages energy budgets across a fleet of agents.

    Analogous to the hive's resource allocation:
        - Each forager gets a crop-full of honey (energy budget)
        - The hive monitors total reserves
        - Exhausted foragers are recalled
        - Efficient foragers may get larger budgets next trip

    Integration with Flock Shepherd:
        - Call provision() when spawning a new Sheep
        - Call spend() on each action through the runtime gate
        - Call collect_nectar() on successful task completion
        - Check phase to decide quarantine/isolation
    """

    def __init__(
        self,
        default_budget: float = 2000.0,
        deny_budget: float = 10000.0,
    ) -> None:
        self.default_budget = default_budget
        self.deny_budget = deny_budget
        self._agents: Dict[str, EnergyBoundedAgent] = {}
        self._retired: List[Dict[str, Any]] = []  # post-mortem records

    def provision(
        self,
        agent_id: str,
        budget: Optional[float] = None,
        centroid: Optional[List[float]] = None,
    ) -> EnergyBoundedAgent:
        """Provision a new agent with an energy budget.

        The bee fills its crop before leaving the hive.
        """
        agent = EnergyBoundedAgent(
            agent_id=agent_id,
            budget=budget or self.default_budget,
            centroid=centroid or [0.4, 0.2, 0.5, 0.1, 0.2, 0.3],
        )
        self._agents[agent_id] = agent
        return agent

    def get(self, agent_id: str) -> Optional[EnergyBoundedAgent]:
        return self._agents.get(agent_id)

    def retire(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Retire an agent and archive its energy record.

        The bee returns to the hive. Its foraging data informs future allocations.
        """
        agent = self._agents.pop(agent_id, None)
        if agent is None:
            return None
        post_mortem = agent.status()
        post_mortem["retired_at"] = time.time()
        self._retired.append(post_mortem)
        return post_mortem

    @property
    def active_agents(self) -> Dict[str, EnergyBoundedAgent]:
        return {aid: a for aid, a in self._agents.items() if a.is_alive}

    @property
    def quarantined_agents(self) -> Dict[str, EnergyBoundedAgent]:
        return {aid: a for aid, a in self._agents.items() if not a.is_alive}

    def fleet_status(self) -> Dict[str, Any]:
        """Hive-level energy overview."""
        agents = list(self._agents.values())
        if not agents:
            return {
                "total_agents": 0,
                "active": 0,
                "quarantined": 0,
                "total_budget": 0.0,
                "total_spent": 0.0,
                "avg_efficiency": 0.0,
                "phase_distribution": {},
            }

        phase_dist: Dict[str, int] = {}
        for a in agents:
            phase_dist[a.phase.value] = phase_dist.get(a.phase.value, 0) + 1

        efficiencies = [a.foraging_efficiency for a in agents if a._spent > 0]

        return {
            "total_agents": len(agents),
            "active": sum(1 for a in agents if a.is_alive),
            "quarantined": sum(1 for a in agents if not a.is_alive),
            "total_budget": sum(a.budget for a in agents),
            "total_spent": round(sum(a._spent for a in agents), 2),
            "avg_efficiency": round(sum(efficiencies) / len(efficiencies), 4) if efficiencies else 0.0,
            "phase_distribution": phase_dist,
            "retired_count": len(self._retired),
        }

    def fleet_dashboard(self) -> str:
        """Text dashboard of fleet energy state."""
        fs = self.fleet_status()
        lines = [
            "FLEET ENERGY STATUS",
            "=" * 50,
            f"Agents: {fs['active']} active / {fs['quarantined']} quarantined / {fs['total_agents']} total",
            f"Energy: {fs['total_spent']:.1f} spent of {fs['total_budget']:.1f} total budget",
            f"Avg Foraging Efficiency: {fs['avg_efficiency']:.4f}",
            "",
            "Phase Distribution:",
        ]
        for phase, count in sorted(fs["phase_distribution"].items()):
            lines.append(f"  {phase}: {count}")

        if self._agents:
            lines.append("")
            lines.append("Per-Agent:")
            for agent in sorted(self._agents.values(), key=lambda a: a.agent_id):
                s = agent.status()
                bar_len = 20
                filled = int(s["fraction"] * bar_len)
                bar = "#" * filled + "-" * (bar_len - filled)
                lines.append(
                    f"  {s['agent_id']:<20s} [{bar}] "
                    f"{s['fraction']*100:5.1f}% | "
                    f"phase={s['phase']:<12s} | "
                    f"eff={s['foraging_efficiency']:.3f}"
                )

        return "\n".join(lines)
