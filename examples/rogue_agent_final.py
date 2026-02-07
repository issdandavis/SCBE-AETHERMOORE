#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Rogue Agent Detection - Final Version

Key insight: Detection works immediately, quarantine needs PERSISTENT MEMORY.
This version adds:
- Broadcast suspicion (agents share who they've flagged)
- Immune response clustering (legitimate agents attract slightly when threatened)
- Longer detection range
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set

TONGUES = {
    'KO': 0, 'AV': np.pi/3, 'RU': 2*np.pi/3,
    'CA': np.pi, 'UM': 4*np.pi/3, 'DR': 5*np.pi/3,
}
TONGUE_NAMES = list(TONGUES.keys())


@dataclass
class Agent:
    id: int
    tongue: Optional[str]
    position: np.ndarray
    is_rogue: bool = False
    drift_std: float = 0.03
    suspicion: Dict[int, int] = field(default_factory=dict)
    flagged_by: Set[int] = field(default_factory=set)  # Who flagged me

    @property
    def phase(self) -> Optional[float]:
        return None if self.is_rogue else TONGUES.get(self.tongue)

    @property
    def norm(self) -> float:
        return float(np.linalg.norm(self.position))

    @property
    def is_quarantined(self) -> bool:
        return len(self.flagged_by) >= 4  # Consensus threshold


def hyperbolic_distance(u: np.ndarray, v: np.ndarray) -> float:
    norm_u, norm_v = np.linalg.norm(u), np.linalg.norm(v)
    diff_sq = np.linalg.norm(u - v) ** 2
    denom = (1 - norm_u**2) * (1 - norm_v**2)
    if denom <= 1e-10:
        return float('inf')
    return float(np.arccosh(max(1 + 2 * diff_sq / denom, 1.0)))


def is_phase_anomaly(phase_i: Optional[float], phase_j: Optional[float]) -> bool:
    """Check if phase relationship is anomalous."""
    if phase_j is None:
        return True  # Null phase = always anomaly

    if phase_i is None:
        return False  # Rogue doesn't detect

    delta = abs(phase_i - phase_j) % (2 * np.pi)
    valid_deltas = [k * np.pi / 3 for k in range(7)]
    return min(abs(delta - vd) for vd in valid_deltas) > 0.15


def project_to_ball(pos: np.ndarray, max_norm: float = 0.95) -> np.ndarray:
    norm = np.linalg.norm(pos)
    return pos * (max_norm / norm) if norm > max_norm else pos


def run_simulation(num_steps: int = 40):
    """Run with broadcast suspicion and immune clustering."""

    np.random.seed(123)

    # Create agents - tight cluster
    agents = []
    for i, tongue in enumerate(TONGUE_NAMES):
        pos = np.array([0.02 + i*0.01, 0.02 + i*0.01, 0.02 + i*0.01])
        agents.append(Agent(id=i, tongue=tongue, position=pos))

    # Rogue - starts in the cluster
    rogue = Agent(id=6, tongue=None, position=np.array([0.04, 0.04, 0.04]),
                  is_rogue=True, drift_std=0.05)
    agents.append(rogue)

    print("=" * 70)
    print("SCBE-AETHERMOORE: ROGUE DETECTION WITH IMMUNE RESPONSE")
    print("=" * 70)
    print("7 agents (6 legitimate + 1 rogue in center)")
    print("Detection: phase-null = anomaly, broadcast suspicion, immune clustering")
    print()

    quarantine_step = None

    for step in range(num_steps):
        # Phase 1: Detection & Suspicion Broadcast
        for i, ai in enumerate(agents):
            for j, aj in enumerate(agents):
                if i == j:
                    continue

                d_H = hyperbolic_distance(ai.position, aj.position)

                # Detection range: 1.5 hyperbolic distance
                if d_H < 1.5 and is_phase_anomaly(ai.phase, aj.phase):
                    ai.suspicion[aj.id] = ai.suspicion.get(aj.id, 0) + 1
                    aj.flagged_by.add(ai.id)

        # Phase 2: Compute forces
        forces = {a.id: np.zeros(3) for a in agents}

        for i, ai in enumerate(agents):
            for j, aj in enumerate(agents):
                if i >= j:
                    continue

                d_H = hyperbolic_distance(ai.position, aj.position)
                if d_H < 0.01 or d_H > 2.0:
                    continue

                direction = ai.position - aj.position
                direction = direction / (np.linalg.norm(direction) + 1e-10)

                # Repulsion (always)
                repel = max(0, 0.4 - d_H) * 0.5

                # QUARANTINE AMPLIFICATION
                if aj.is_quarantined or len(aj.flagged_by) >= 2:
                    repel *= 3.0  # 3x repulsion against suspected rogues

                # IMMUNE CLUSTERING (legitimate agents attract slightly when threatened)
                attract = 0
                if not ai.is_rogue and not aj.is_rogue:
                    if any(a.is_quarantined or len(a.flagged_by) >= 2 for a in agents):
                        # Threat present - cluster together
                        attract = max(0, d_H - 0.3) * 0.1

                force = (repel - attract) * direction
                forces[ai.id] += force
                forces[aj.id] -= force

        # Phase 3: Apply forces + drift
        for agent in agents:
            agent.position = agent.position + forces[agent.id]
            agent.position = agent.position + np.random.normal(0, agent.drift_std, 3)
            agent.position = project_to_ball(agent.position)

        # Check quarantine
        if rogue.is_quarantined and quarantine_step is None:
            quarantine_step = step

        # Progress
        if step % 5 == 0 or rogue.is_quarantined:
            flags = len(rogue.flagged_by)
            status = "🚨 QUARANTINED" if rogue.is_quarantined else f"flagged by {flags}/6"
            print(f"Step {step:2d}: rogue {status}, norm={rogue.norm:.3f}")

            if rogue.is_quarantined and step == quarantine_step:
                print(f"         ^^^ QUARANTINE ACHIEVED AT STEP {step} ^^^")

    # Final report
    print()
    print("=" * 70)
    print("FINAL STATE")
    print("=" * 70)

    print("\nAgent Positions:")
    for a in agents:
        status = "🚨 ROGUE" if a.is_rogue else "✓"
        q = " [QUARANTINED]" if a.is_quarantined else ""
        t = a.tongue or "NULL"
        print(f"  {a.id} {t:<4}: norm={a.norm:.3f} flagged_by={len(a.flagged_by)}{q} {status}")

    print("\nSuspicion Matrix (who suspects whom):")
    print("       ", end="")
    for a in agents:
        print(f"{a.tongue or 'X':>4}", end=" ")
    print()

    for ai in agents:
        t = ai.tongue or "X"
        print(f"  {t:<4}:", end=" ")
        for aj in agents:
            s = ai.suspicion.get(aj.id, 0)
            print(f"{s:>4}", end=" ")
        print()

    print()
    print("=" * 70)
    print("VERDICT")
    print("=" * 70)

    rogue_dist = np.mean([hyperbolic_distance(a.position, rogue.position)
                          for a in agents if not a.is_rogue])

    if rogue.is_quarantined:
        print(f"✅ ROGUE DETECTED AND QUARANTINED at step {quarantine_step}")
        print(f"   Consensus: {len(rogue.flagged_by)}/6 agents flagged the intruder")
        print(f"   Average distance from swarm: {rogue_dist:.2f}")
        print(f"   Rogue pushed to norm: {rogue.norm:.3f}")
        print()
        print("   The swarm 'smelled' the phase-null intruder through pure math.")
        print("   No explicit messaging required - just hyperbolic geometry + tongue phases.")
    else:
        print(f"⚠️  Rogue only flagged by {len(rogue.flagged_by)}/6 (need 4 for quarantine)")

    # False positive check
    print()
    print("False Positive Check:")
    false_positives = [a for a in agents if not a.is_rogue and len(a.flagged_by) > 0]
    if false_positives:
        for a in false_positives:
            print(f"  ⚠️  {a.tongue} was flagged {len(a.flagged_by)} times (false positive)")
    else:
        print("  ✅ Zero false positives - only the rogue was flagged")


if __name__ == "__main__":
    run_simulation(num_steps=35)
