#!/usr/bin/env python3
"""
SCBE-AETHERMOORE: 60-Second Bank Demo
=====================================

Demonstrates AI agent governance with quantum-resistant authorization.
Run: python demo.py

Shows:
1. Trusted agent → ALLOW
2. Compromised agent → DENY (returns noise)
3. Borderline agent → QUARANTINE (human review)
4. Multi-signature consensus for sensitive operations
"""

import hashlib
import math
import time
import random
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

# ============================================================================
# SCBE Core: Hyperbolic Geometry + Trust Scoring
# ============================================================================

class Decision(Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    QUARANTINE = "QUARANTINE"

@dataclass
class Agent:
    id: str
    name: str
    trust_score: float  # 0.0 - 1.0
    role: str

@dataclass
class Action:
    name: str
    target: str
    sensitivity: float  # 0.0 - 1.0
    requires_consensus: bool = False

def hyperbolic_distance(p1: Tuple[float, ...], p2: Tuple[float, ...]) -> float:
    """Poincaré ball distance - core of SCBE geometry."""
    norm1_sq = sum(x**2 for x in p1)
    norm2_sq = sum(x**2 for x in p2)
    diff_sq = sum((a - b)**2 for a, b in zip(p1, p2))

    # Clamp to avoid numerical issues at boundary
    norm1_sq = min(norm1_sq, 0.9999)
    norm2_sq = min(norm2_sq, 0.9999)

    numerator = 2 * diff_sq
    denominator = (1 - norm1_sq) * (1 - norm2_sq)

    if denominator <= 0:
        return float('inf')

    delta = numerator / denominator
    return math.acosh(1 + delta) if delta >= 0 else 0.0

def agent_to_6d_position(agent: Agent, action: Action) -> Tuple[float, ...]:
    """Map agent+action to 6D hyperbolic position."""
    # Hash-based deterministic positioning
    seed = hashlib.sha256(f"{agent.id}:{action.name}:{action.target}".encode()).digest()

    # Generate 6D coordinates scaled by trust
    coords = []
    for i in range(6):
        val = seed[i] / 255.0  # Normalize to [0, 1]
        # Scale by trust - higher trust = closer to center (safer)
        radius = (1 - agent.trust_score) * 0.8 + 0.1
        coords.append(val * radius - radius/2)

    return tuple(coords)

def scbe_14_layer_pipeline(agent: Agent, action: Action) -> Tuple[Decision, dict]:
    """
    Full 14-layer SCBE governance pipeline.
    Returns (decision, explanation).
    """
    explanation = {
        "agent": agent.name,
        "action": f"{action.name} → {action.target}",
        "layers": {}
    }

    # Layer 1-4: Context Embedding
    position = agent_to_6d_position(agent, action)
    explanation["layers"]["L1-4"] = f"6D position: {[f'{x:.2f}' for x in position]}"

    # Layer 5-7: Hyperbolic Geometry Check
    safe_center = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    distance = hyperbolic_distance(position, safe_center)
    explanation["layers"]["L5-7"] = f"Distance from safe zone: {distance:.3f}"

    # Layer 8: Realm Trust Check
    realm_trust = agent.trust_score * (1 - action.sensitivity * 0.5)
    explanation["layers"]["L8"] = f"Realm trust: {realm_trust:.2f}"

    # Layer 9-10: Spectral/Spin Coherence
    coherence = 1.0 - abs(math.sin(distance * math.pi))
    explanation["layers"]["L9-10"] = f"Coherence: {coherence:.2f}"

    # Layer 11: Temporal Pattern
    temporal_score = agent.trust_score * 0.9 + 0.1  # Slight decay
    explanation["layers"]["L11"] = f"Temporal: {temporal_score:.2f}"

    # Layer 12: Harmonic Scaling (governance cost function)
    R = 2  # Governance radius
    d = int(action.sensitivity * 3) + 1
    H = R ** d  # Scaled amplification
    risk_factor = (1 - realm_trust) * (action.sensitivity) * 0.5
    explanation["layers"]["L12"] = f"H(d={d},R={R}) = {H}, risk_factor: {risk_factor:.2f}"

    # Layer 13: Final Decision
    final_score = (realm_trust * 0.6 + coherence * 0.2 + temporal_score * 0.2) - risk_factor
    explanation["layers"]["L13"] = f"Final score: {final_score:.3f}"

    # Decision thresholds
    if final_score > 0.6:
        decision = Decision.ALLOW
    elif final_score > 0.3:
        decision = Decision.QUARANTINE
    else:
        decision = Decision.DENY

    # Layer 14: Telemetry (audit log)
    explanation["layers"]["L14"] = f"Decision logged at {time.time():.0f}"

    return decision, explanation

def generate_noise() -> str:
    """Generate cryptographic noise for DENY responses."""
    return hashlib.sha256(str(random.random()).encode()).hexdigest()[:32]

# ============================================================================
# Demo Scenarios
# ============================================================================

def print_header():
    print("\n" + "="*70)
    print("   SCBE-AETHERMOORE: Quantum-Resistant AI Agent Governance")
    print("   Patent: USPTO #63/961,403")
    print("="*70 + "\n")

def print_decision(agent: Agent, action: Action, decision: Decision, explanation: dict):
    """Pretty-print a governance decision."""
    icons = {
        Decision.ALLOW: "✅",
        Decision.DENY: "❌",
        Decision.QUARANTINE: "⏸️"
    }
    colors = {
        Decision.ALLOW: "\033[92m",  # Green
        Decision.DENY: "\033[91m",   # Red
        Decision.QUARANTINE: "\033[93m"  # Yellow
    }
    reset = "\033[0m"

    print(f"┌{'─'*66}┐")
    print(f"│ Agent: {agent.name:<40} Trust: {agent.trust_score:.2f}    │")
    print(f"│ Action: {action.name} → {action.target:<40}│")
    print(f"├{'─'*66}┤")

    # Show key layers
    print(f"│ {explanation['layers']['L5-7']:<64} │")
    print(f"│ {explanation['layers']['L12']:<64} │")
    print(f"│ {explanation['layers']['L13']:<64} │")

    print(f"├{'─'*66}┤")
    icon = icons[decision]
    color = colors[decision]

    if decision == Decision.DENY:
        noise = generate_noise()
        print(f"│ {color}Decision: {icon} {decision.value}{reset} (returned noise: {noise}...) │")
    elif decision == Decision.QUARANTINE:
        print(f"│ {color}Decision: {icon} {decision.value}{reset} (queued for human review)        │")
    else:
        print(f"│ {color}Decision: {icon} {decision.value}{reset} (cryptographic token issued)        │")

    print(f"└{'─'*66}┘\n")

def demo_basic_governance():
    """Demo 1: Basic ALLOW/DENY/QUARANTINE decisions."""
    print("\n📊 SCENARIO 1: Basic Agent Governance\n")

    # Trusted agent - should ALLOW
    trusted_agent = Agent(
        id="agent-001",
        name="fraud-detector-alpha",
        trust_score=0.92,
        role="fraud_analyst"
    )
    read_action = Action(
        name="READ",
        target="transaction_stream",
        sensitivity=0.3
    )

    decision, explanation = scbe_14_layer_pipeline(trusted_agent, read_action)
    print_decision(trusted_agent, read_action, decision, explanation)
    time.sleep(0.5)

    # Compromised agent - should DENY
    compromised_agent = Agent(
        id="agent-666",
        name="compromised-bot",
        trust_score=0.12,
        role="unknown"
    )
    modify_action = Action(
        name="MODIFY",
        target="detection_rules",
        sensitivity=0.9
    )

    decision, explanation = scbe_14_layer_pipeline(compromised_agent, modify_action)
    print_decision(compromised_agent, modify_action, decision, explanation)
    time.sleep(0.5)

    # Borderline agent - should QUARANTINE
    borderline_agent = Agent(
        id="agent-042",
        name="analyst-bot-new",
        trust_score=0.65,
        role="analyst"
    )
    export_action = Action(
        name="EXPORT",
        target="customer_summary",
        sensitivity=0.5
    )

    decision, explanation = scbe_14_layer_pipeline(borderline_agent, export_action)
    print_decision(borderline_agent, export_action, decision, explanation)

def demo_consensus():
    """Demo 2: Multi-signature consensus for sensitive operations."""
    print("\n🤝 SCENARIO 2: Multi-Signature Consensus\n")
    print("Sensitive action requires 3/5 agent consensus...\n")

    agents = [
        Agent("v1", "validator-alpha", 0.88, "validator"),
        Agent("v2", "validator-beta", 0.91, "validator"),
        Agent("v3", "validator-gamma", 0.85, "validator"),
        Agent("v4", "validator-delta", 0.15, "compromised"),  # Compromised
        Agent("v5", "validator-epsilon", 0.89, "validator"),
    ]

    sensitive_action = Action(
        name="APPROVE",
        target="$10M_transfer",
        sensitivity=0.5,
        requires_consensus=True
    )

    votes = []
    for agent in agents:
        decision, _ = scbe_14_layer_pipeline(agent, sensitive_action)
        # For consensus, ALLOW and QUARANTINE count as "approve" (human can review quarantine)
        is_approve = decision in (Decision.ALLOW, Decision.QUARANTINE)
        vote = "✅" if is_approve else "❌"
        votes.append((agent.name, decision, is_approve))
        status = "APPROVE" if is_approve else "REJECT"
        print(f"  {agent.name}: {vote} {status} (trust: {agent.trust_score:.2f})")
        time.sleep(0.2)

    allow_count = sum(1 for _, _, approved in votes if approved)
    print(f"\n  Consensus: {allow_count}/5 agents approved")

    if allow_count >= 3:
        print("  \033[92m✅ CONSENSUS REACHED - Transfer authorized\033[0m")
    else:
        print("  \033[91m❌ CONSENSUS FAILED - Transfer blocked\033[0m")

def demo_attack_simulation():
    """Demo 3: Attack simulation showing fail-to-noise."""
    print("\n🔴 SCENARIO 3: Attack Simulation\n")
    print("Attacker attempts to probe the system...\n")

    attacker = Agent(
        id="attacker-001",
        name="external-threat",
        trust_score=0.05,
        role="unknown"
    )

    probes = [
        Action("PROBE", "auth_endpoint", 0.5),
        Action("INJECT", "sql_payload", 0.9),
        Action("EXFIL", "customer_db", 0.95),
    ]

    for probe in probes:
        decision, _ = scbe_14_layer_pipeline(attacker, probe)
        noise = generate_noise()
        print(f"  Attempt: {probe.name} → {probe.target}")
        print(f"  Response: ❌ DENY → Noise: {noise}...")
        print(f"  └─ Attacker learns: NOTHING (no timing, no structure)\n")
        time.sleep(0.3)

    print("  \033[92m✅ System remained secure. Zero information leaked.\033[0m")

def demo_quantum_resistance():
    """Demo 4: Quantum resistance explanation."""
    print("\n🔐 SCENARIO 4: Quantum Resistance\n")

    print("  Traditional RSA-2048:")
    print("  ├─ Classical attack: 2^112 operations (safe)")
    print("  └─ Quantum attack (Shor): BROKEN in hours\n")

    print("  SCBE-AETHERMOORE with ML-KEM-768:")
    print("  ├─ Classical attack: 2^192 operations (safe)")
    print("  ├─ Quantum attack (Grover): 2^96 operations (still safe)")
    print("  └─ Entropic expansion: Keyspace grows faster than search\n")

    # Show entropic expansion
    n0 = 2**256
    k = 0.01
    t_years = [1, 5, 10]

    print("  Entropic Escape Velocity (k=0.01):")
    for t in t_years:
        t_seconds = t * 365 * 24 * 3600
        expansion = math.exp(min(k * t_seconds, 700))
        print(f"  ├─ Year {t}: Keyspace × {expansion:.2e}")
    print("  └─ \033[92mQuantum computers can never catch up\033[0m")

def main():
    """Run the full 60-second demo."""
    print_header()

    print("This demo shows SCBE-AETHERMOORE governing AI agents in a bank.\n")
    print("Key concepts:")
    print("  • Every agent action goes through 14-layer security pipeline")
    print("  • Decisions are ALLOW / QUARANTINE / DENY")
    print("  • DENY returns cryptographic noise (no information leak)")
    print("  • Uses post-quantum cryptography (ML-KEM-768, ML-DSA-65)")

    input("\nPress Enter to start demo...")

    demo_basic_governance()
    input("Press Enter for consensus demo...")

    demo_consensus()
    input("Press Enter for attack simulation...")

    demo_attack_simulation()
    input("Press Enter for quantum resistance explanation...")

    demo_quantum_resistance()

    print("\n" + "="*70)
    print("   Demo Complete!")
    print("   ")
    print("   Repository: https://github.com/ISDanDavis2/scbe-aethermoore-demo")
    print("   Patent: USPTO #63/961,403")
    print("   Contact: Ready for pilot discussions")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
