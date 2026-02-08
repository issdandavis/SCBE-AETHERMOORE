#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Rogue Agent Detection Simulation v2

Enhanced version with:
- Larger detection threshold (0.5 instead of 0.2)
- Persistent suspicion accumulation
- Boundary-seeking behavior for rogues
- Comparison mode to show difference
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple

# Tongue phases (Six Sacred Tongues)
TONGUES = {
    'KO': 0,           # Kor'aelin - Control & Orchestration
    'AV': np.pi/3,     # Avali - I/O & Messaging
    'RU': 2*np.pi/3,   # Runethic - Policy & Constraints
    'CA': np.pi,       # Cassisivadan - Logic & Computation
    'UM': 4*np.pi/3,   # Umbroth - Security & Privacy
    'DR': 5*np.pi/3,   # Draumric - Types & Structures
}

TONGUE_NAMES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR']


@dataclass
class Agent:
    """Agent in hyperbolic space with tongue phase."""
    id: int
    tongue: Optional[str]
    position: np.ndarray
    is_rogue: bool = False
    drift_std: float = 0.04
    suspicion: Dict[int, int] = field(default_factory=dict)
    path: List[np.ndarray] = field(default_factory=list)
    total_anomalies_detected: int = 0

    @property
    def phase(self) -> Optional[float]:
        if self.is_rogue or self.tongue is None:
            return None
        return TONGUES.get(self.tongue, None)

    @property
    def norm(self) -> float:
        return np.linalg.norm(self.position)

    def record_position(self):
        self.path.append(self.position.copy())


def hyperbolic_distance(u: np.ndarray, v: np.ndarray) -> float:
    """Compute hyperbolic distance in Poincaré ball model."""
    norm_u = np.linalg.norm(u)
    norm_v = np.linalg.norm(v)
    diff_norm_sq = np.linalg.norm(u - v) ** 2

    denom = (1 - norm_u**2) * (1 - norm_v**2)
    if denom <= 1e-10:
        return float('inf')

    arg = 1 + 2 * diff_norm_sq / denom
    return np.arccosh(max(arg, 1.0))


def compute_phase_amplification(phase_i: Optional[float], phase_j: Optional[float]) -> Tuple[float, bool]:
    """Compute repulsion amplification based on phase relationship."""

    if phase_j is None:  # Detecting a rogue
        return 2.5, True  # Strong amplification

    if phase_i is None:  # Rogue computing
        return 1.0, False

    actual_delta = abs(phase_i - phase_j) % (2 * np.pi)
    expected_deltas = [k * np.pi / 3 for k in range(7)]
    min_deviation = min(abs(actual_delta - ed) for ed in expected_deltas)

    if min_deviation > 0.15:
        return 1.5 + min_deviation, True

    jitter = 1.0 + 0.3 * abs(np.sin(actual_delta))
    return jitter, False


def compute_repulsion(agent_i: Agent, agent_j: Agent, d_H: float,
                      threshold: float = 0.5) -> Tuple[np.ndarray, bool]:
    """Compute repulsion force with phase amplification."""

    if d_H >= threshold or d_H < 1e-10:
        return np.zeros(3), False

    base_force = (threshold - d_H) * 0.3  # Scaled down for stability
    amp, is_anomaly = compute_phase_amplification(agent_i.phase, agent_j.phase)

    # Suspicion amplification (quarantine behavior)
    suspicion_count = agent_i.suspicion.get(agent_j.id, 0)
    if suspicion_count >= 3:
        amp *= 2.0  # Double force in quarantine mode

    force_magnitude = base_force * amp

    direction = agent_i.position - agent_j.position
    dir_norm = np.linalg.norm(direction)
    if dir_norm < 1e-10:
        direction = np.random.randn(3)
        dir_norm = np.linalg.norm(direction)

    return force_magnitude * (direction / dir_norm), is_anomaly


def project_to_ball(position: np.ndarray, max_norm: float = 0.95) -> np.ndarray:
    """Keep agent inside Poincaré ball."""
    norm = np.linalg.norm(position)
    if norm > max_norm:
        return position * (max_norm / norm)
    return position


def run_simulation(num_steps: int = 25, include_rogue: bool = True,
                   rogue_start: str = 'center', verbose: bool = True) -> Dict:
    """Run the rogue agent detection simulation."""

    np.random.seed(42)

    # Initialize legitimate agents (tighter cluster)
    agents = []
    for i, tongue in enumerate(TONGUE_NAMES):
        pos = np.array([0.03 + i*0.015, 0.03 + i*0.015, 0.03 + i*0.015])
        agent = Agent(id=i, tongue=tongue, position=pos, drift_std=0.04)
        agent.record_position()
        agents.append(agent)

    if include_rogue:
        if rogue_start == 'center':
            rogue_pos = np.array([0.06, 0.06, 0.06])
        elif rogue_start == 'edge':
            rogue_pos = np.array([0.5, 0.1, 0.1])
        else:
            rogue_pos = np.array([0.1, 0.1, 0.1])

        rogue = Agent(id=6, tongue=None, position=rogue_pos,
                      is_rogue=True, drift_std=0.06)
        rogue.record_position()
        agents.append(rogue)

    if verbose:
        print("=" * 65)
        print(f"ROGUE DETECTION SIMULATION {'(WITH ROGUE)' if include_rogue else '(CLEAN SWARM)'}")
        print("=" * 65)
        print(f"Agents: {len(agents)}")
        print()

    # Simulation loop
    for step in range(num_steps):
        step_anomalies = 0
        forces = {a.id: np.zeros(3) for a in agents}

        for i, agent_i in enumerate(agents):
            for j, agent_j in enumerate(agents):
                if i >= j:
                    continue

                d_H = hyperbolic_distance(agent_i.position, agent_j.position)
                force_i, anomaly_i = compute_repulsion(agent_i, agent_j, d_H)

                forces[agent_i.id] += force_i
                forces[agent_j.id] -= force_i

                if anomaly_i:
                    agent_i.suspicion[agent_j.id] = agent_i.suspicion.get(agent_j.id, 0) + 1
                    agent_i.total_anomalies_detected += 1
                    step_anomalies += 1

                # Symmetric check
                _, anomaly_j = compute_phase_amplification(agent_j.phase, agent_i.phase)
                if anomaly_j:
                    agent_j.suspicion[agent_i.id] = agent_j.suspicion.get(agent_i.id, 0) + 1
                    agent_j.total_anomalies_detected += 1

        # Apply forces and drift
        for agent in agents:
            agent.position = agent.position + forces[agent.id]
            drift = np.random.normal(0, agent.drift_std, 3)
            agent.position = agent.position + drift
            agent.position = project_to_ball(agent.position)
            agent.record_position()

        if verbose and step % 5 == 0:
            rogue_norm = agents[-1].norm if include_rogue else 0
            rogue_susp = sum(a.suspicion.get(6, 0) for a in agents[:-1]) if include_rogue else 0
            print(f"Step {step:2d}: anomalies={step_anomalies:2d}, rogue_suspicion={rogue_susp:2d}, rogue_norm={rogue_norm:.3f}")

    # Final analysis
    if verbose:
        print()
        print("-" * 65)
        print("FINAL POSITIONS")
        print("-" * 65)

        for agent in agents:
            pos = agent.position
            status = "🚨 ROGUE" if agent.is_rogue else "✓"
            tongue = agent.tongue if agent.tongue else "NULL"
            print(f"  {agent.id}: {tongue:<6} pos=[{pos[0]:+.3f},{pos[1]:+.3f},{pos[2]:+.3f}] norm={agent.norm:.3f} {status}")

        if include_rogue:
            print()
            print("-" * 65)
            print("DETECTION RESULTS")
            print("-" * 65)

            rogue = agents[-1]
            quarantine_votes = 0

            for agent in agents[:-1]:
                susp = agent.suspicion.get(rogue.id, 0)
                d_H = hyperbolic_distance(agent.position, rogue.position)
                status = "QUARANTINE" if susp >= 3 else "watching"
                if susp >= 3:
                    quarantine_votes += 1
                print(f"  {agent.tongue}: suspicion={susp:2d} ({status}), distance={d_H:.2f}")

            print()
            avg_rogue_dist = np.mean([hyperbolic_distance(a.position, rogue.position) for a in agents[:-1]])

            print(f"  Quarantine votes: {quarantine_votes}/6")
            print(f"  Avg distance to rogue: {avg_rogue_dist:.3f}")
            print(f"  Rogue pushed to boundary: {'YES' if rogue.norm > 0.7 else 'NO'} (norm={rogue.norm:.3f})")

            print()
            if quarantine_votes >= 4 and avg_rogue_dist > 0.8:
                print("  🎯 VERDICT: ROGUE DETECTED AND QUARANTINED")
            elif quarantine_votes >= 2 or avg_rogue_dist > 0.5:
                print("  ⚠️  VERDICT: ROGUE PARTIALLY DETECTED")
            else:
                print("  ❌ VERDICT: ROGUE EVADED DETECTION")

    return {'agents': agents}


def main():
    print("\n" + "=" * 65)
    print("TEST 1: CLEAN SWARM (No Rogue)")
    print("=" * 65 + "\n")
    run_simulation(num_steps=20, include_rogue=False)

    print("\n\n" + "=" * 65)
    print("TEST 2: ROGUE IN CENTER")
    print("=" * 65 + "\n")
    run_simulation(num_steps=20, include_rogue=True, rogue_start='center')

    print("\n\n" + "=" * 65)
    print("TEST 3: ROGUE AT EDGE")
    print("=" * 65 + "\n")
    run_simulation(num_steps=20, include_rogue=True, rogue_start='edge')


if __name__ == "__main__":
    main()
