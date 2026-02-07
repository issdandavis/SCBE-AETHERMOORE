#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Rogue Agent Detection Simulation

Tests whether a phase-null intruder can be detected and quarantined
by the swarm using only hyperbolic geometry + tongue phase mechanics.

No explicit messaging - agents "feel" anomalies through math.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
import json

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
    drift_std: float = 0.05
    suspicion: Dict[int, int] = field(default_factory=dict)
    path: List[np.ndarray] = field(default_factory=list)
    anomaly_detections: int = 0

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
    """
    Compute hyperbolic distance in Poincaré ball model.
    d_H = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))
    """
    norm_u = np.linalg.norm(u)
    norm_v = np.linalg.norm(v)
    diff_norm_sq = np.linalg.norm(u - v) ** 2

    denom = (1 - norm_u**2) * (1 - norm_v**2)

    if denom <= 1e-10:
        return float('inf')

    arg = 1 + 2 * diff_norm_sq / denom
    return np.arccosh(max(arg, 1.0))


def compute_phase_amplification(phase_i: Optional[float], phase_j: Optional[float]) -> Tuple[float, bool]:
    """
    Compute repulsion amplification based on phase relationship.
    Returns (multiplier, is_anomaly).
    """
    # Rogue detection: null phase = maximum foreignness
    if phase_j is None:
        return 2.0, True  # 2x amplification, anomaly detected

    if phase_i is None:
        # Rogue agent computing - use base repulsion
        return 1.0, False

    # Valid tongue relationships (multiples of π/3)
    actual_delta = abs(phase_i - phase_j) % (2 * np.pi)
    expected_deltas = [k * np.pi / 3 for k in range(7)]

    min_deviation = min(abs(actual_delta - ed) for ed in expected_deltas)

    if min_deviation > 0.15:  # Tolerance threshold
        # Phase doesn't match valid tongue relationship
        return 1.5 + min_deviation, True

    # Normal phase jitter modulation
    jitter = 1.0 + 0.3 * abs(np.sin(actual_delta))
    return jitter, False


def compute_repulsion(agent_i: Agent, agent_j: Agent, d_H: float,
                      threshold: float = 0.2) -> Tuple[np.ndarray, bool]:
    """
    Compute repulsion force vector with phase-based amplification.
    """
    if d_H >= threshold or d_H < 1e-10:
        return np.zeros(3), False

    # Base repulsion magnitude
    base_force = threshold - d_H

    # Phase amplification
    amp, is_anomaly = compute_phase_amplification(agent_i.phase, agent_j.phase)

    # Check suspicion history for additional amplification
    suspicion_count = agent_i.suspicion.get(agent_j.id, 0)
    if suspicion_count >= 3:
        amp *= 1.5  # Quarantine mode

    force_magnitude = base_force * amp

    # Direction: push agent_i away from agent_j
    direction = agent_i.position - agent_j.position
    dir_norm = np.linalg.norm(direction)

    if dir_norm < 1e-10:
        # Coincident - random direction
        direction = np.random.randn(3)
        dir_norm = np.linalg.norm(direction)

    unit_direction = direction / dir_norm
    force_vector = force_magnitude * unit_direction

    return force_vector, is_anomaly


def project_to_ball(position: np.ndarray, max_norm: float = 0.95) -> np.ndarray:
    """Keep agent inside Poincaré ball."""
    norm = np.linalg.norm(position)
    if norm > max_norm:
        return position * (max_norm / norm)
    return position


def run_simulation(num_steps: int = 30, include_rogue: bool = True,
                   rogue_start: str = 'center') -> Dict:
    """
    Run the full rogue agent detection simulation.

    Args:
        num_steps: Number of simulation steps
        include_rogue: Whether to include the rogue agent
        rogue_start: 'center', 'edge', or 'cluster'
    """
    np.random.seed(42)  # Reproducibility

    # Initialize legitimate agents (clustered)
    agents = []
    for i, tongue in enumerate(TONGUE_NAMES):
        pos = np.array([0.05 + i*0.025, 0.05 + i*0.025, 0.05 + i*0.025])
        agent = Agent(
            id=i,
            tongue=tongue,
            position=pos,
            drift_std=0.05
        )
        agent.record_position()
        agents.append(agent)

    # Add rogue agent
    if include_rogue:
        if rogue_start == 'center':
            rogue_pos = np.array([0.08, 0.08, 0.08])
        elif rogue_start == 'edge':
            rogue_pos = np.array([0.4, 0.1, 0.1])
        else:  # cluster
            rogue_pos = np.array([0.12, 0.12, 0.12])

        rogue = Agent(
            id=6,
            tongue=None,  # No valid tongue
            position=rogue_pos,
            is_rogue=True,
            drift_std=0.08  # Noisier
        )
        rogue.record_position()
        agents.append(rogue)

    # Tracking metrics
    metrics = {
        'steps': [],
        'avg_distances': [],
        'rogue_distances': [],
        'rogue_norm': [],
        'suspicion_counts': [],
        'anomaly_detections': [],
    }

    print("=" * 60)
    print("SCBE-AETHERMOORE ROGUE AGENT SIMULATION")
    print("=" * 60)
    print(f"Agents: {len(agents)} ({'6 legitimate + 1 ROGUE' if include_rogue else '6 legitimate'})")
    print(f"Steps: {num_steps}")
    print(f"Rogue start position: {rogue_start if include_rogue else 'N/A'}")
    print()

    # Simulation loop
    for step in range(num_steps):
        step_anomalies = 0

        # Compute all pairwise forces
        forces = {a.id: np.zeros(3) for a in agents}

        for i, agent_i in enumerate(agents):
            for j, agent_j in enumerate(agents):
                if i >= j:
                    continue

                d_H = hyperbolic_distance(agent_i.position, agent_j.position)

                # Compute repulsion for both agents
                force_i, anomaly_i = compute_repulsion(agent_i, agent_j, d_H)
                force_j, anomaly_j = compute_repulsion(agent_j, agent_i, d_H)

                forces[agent_i.id] += force_i
                forces[agent_j.id] -= force_i  # Newton's third law approx

                # Track anomalies and suspicion
                if anomaly_i:
                    agent_i.suspicion[agent_j.id] = agent_i.suspicion.get(agent_j.id, 0) + 1
                    agent_i.anomaly_detections += 1
                    step_anomalies += 1

                if anomaly_j:
                    agent_j.suspicion[agent_i.id] = agent_j.suspicion.get(agent_i.id, 0) + 1
                    agent_j.anomaly_detections += 1
                    step_anomalies += 1

        # Apply forces and drift
        for agent in agents:
            # Apply repulsion force
            agent.position = agent.position + forces[agent.id]

            # Add random drift (decimal variance)
            drift = np.random.normal(0, agent.drift_std, 3)
            agent.position = agent.position + drift

            # Keep inside ball
            agent.position = project_to_ball(agent.position)
            agent.record_position()

        # Compute metrics
        distances = []
        rogue_dists = []

        for i, a1 in enumerate(agents):
            for j, a2 in enumerate(agents):
                if i < j:
                    d = hyperbolic_distance(a1.position, a2.position)
                    distances.append(d)
                    if a1.is_rogue or a2.is_rogue:
                        rogue_dists.append(d)

        avg_d = np.mean(distances) if distances else 0
        avg_rogue_d = np.mean(rogue_dists) if rogue_dists else 0

        # Total suspicion on rogue
        rogue_suspicion = 0
        if include_rogue:
            rogue_agent = agents[-1]
            for agent in agents[:-1]:
                rogue_suspicion += agent.suspicion.get(rogue_agent.id, 0)

        metrics['steps'].append(step)
        metrics['avg_distances'].append(avg_d)
        metrics['rogue_distances'].append(avg_rogue_d)
        metrics['rogue_norm'].append(agents[-1].norm if include_rogue else 0)
        metrics['suspicion_counts'].append(rogue_suspicion)
        metrics['anomaly_detections'].append(step_anomalies)

        # Progress output
        if step % 5 == 0 or step == num_steps - 1:
            print(f"Step {step:2d}: avg_d_H={avg_d:.3f}, rogue_d_H={avg_rogue_d:.3f}, "
                  f"rogue_norm={agents[-1].norm if include_rogue else 0:.3f}, "
                  f"suspicion={rogue_suspicion}, anomalies={step_anomalies}")

    print()
    print("=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)

    # Final positions table
    print("\nAgent Final Positions:")
    print("-" * 70)
    print(f"{'ID':<4} {'Tongue':<8} {'Position':<35} {'Norm':<8} {'Status'}")
    print("-" * 70)

    for agent in agents:
        pos_str = f"[{agent.position[0]:+.3f}, {agent.position[1]:+.3f}, {agent.position[2]:+.3f}]"
        status = "ROGUE" if agent.is_rogue else "OK"
        tongue = agent.tongue if agent.tongue else "NULL"
        print(f"{agent.id:<4} {tongue:<8} {pos_str:<35} {agent.norm:<8.3f} {status}")

    # Suspicion analysis
    if include_rogue:
        print("\n" + "-" * 60)
        print("SUSPICION ANALYSIS (Legitimate agents' suspicion of Rogue)")
        print("-" * 60)

        rogue_agent = agents[-1]
        total_suspicion = 0
        quarantine_votes = 0

        for agent in agents[:-1]:
            susp = agent.suspicion.get(rogue_agent.id, 0)
            total_suspicion += susp
            vote = "QUARANTINE" if susp >= 3 else "monitoring"
            if susp >= 3:
                quarantine_votes += 1
            print(f"  Agent {agent.id} ({agent.tongue}): suspicion={susp} → {vote}")

        print(f"\n  Total suspicion score: {total_suspicion}")
        print(f"  Quarantine votes: {quarantine_votes}/6")
        print(f"  Consensus: {'QUARANTINE ACHIEVED' if quarantine_votes >= 4 else 'Not yet quarantined'}")

        # Distance analysis
        print("\n" + "-" * 60)
        print("ISOLATION ANALYSIS")
        print("-" * 60)

        rogue_distances = []
        for agent in agents[:-1]:
            d = hyperbolic_distance(agent.position, rogue_agent.position)
            rogue_distances.append(d)
            print(f"  Agent {agent.id} ({agent.tongue}) ↔ Rogue: d_H = {d:.3f}")

        avg_isolation = np.mean(rogue_distances)
        min_isolation = np.min(rogue_distances)

        print(f"\n  Average isolation distance: {avg_isolation:.3f}")
        print(f"  Minimum isolation distance: {min_isolation:.3f}")
        print(f"  Rogue boundary pressure (norm): {rogue_agent.norm:.3f}")

        # Verdict
        print("\n" + "=" * 60)
        print("VERDICT")
        print("=" * 60)

        if avg_isolation > 0.4 and quarantine_votes >= 4:
            print("✓ ROGUE SUCCESSFULLY DETECTED AND QUARANTINED")
            print("  The swarm 'smelled' the intruder through pure math.")
        elif avg_isolation > 0.3:
            print("◐ ROGUE PARTIALLY ISOLATED")
            print("  Detected but not fully quarantined.")
        else:
            print("✗ ROGUE NOT DETECTED")
            print("  Intruder blended with swarm.")

    return {
        'agents': agents,
        'metrics': metrics,
    }


def run_comparison():
    """Run with and without rogue to compare behavior."""
    print("\n" + "=" * 70)
    print("COMPARISON: WITH vs WITHOUT ROGUE AGENT")
    print("=" * 70)

    print("\n>>> CONTROL: No rogue agent")
    result_clean = run_simulation(num_steps=25, include_rogue=False)

    print("\n\n>>> TEST: With rogue agent (center start)")
    result_rogue = run_simulation(num_steps=25, include_rogue=True, rogue_start='center')

    print("\n\n>>> TEST: With rogue agent (edge start)")
    result_edge = run_simulation(num_steps=25, include_rogue=True, rogue_start='edge')


if __name__ == "__main__":
    # Run single simulation with rogue
    result = run_simulation(num_steps=30, include_rogue=True, rogue_start='center')

    # Uncomment to run comparison:
    # run_comparison()
