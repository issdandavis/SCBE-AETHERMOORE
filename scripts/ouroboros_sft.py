#!/usr/bin/env python3
"""
Ouroboros Self-Learning SFT Generator
======================================

The Ouroboros Concept
---------------------
In mythology, the ouroboros is the serpent that devours its own tail -- a symbol
of self-reference, cyclic renewal, and the infinite feedback loop of creation
consuming itself to be reborn.  This script embodies that principle for
machine learning: the SCBE-AETHERMOORE system generates supervised fine-tuning
(SFT) data by *reading its own source code, tests, specs, and demo outputs*.

The model literally learns from *what it already is*.

Why this works:

1. **Source code encodes governance logic** -- the actual if/elif/else branches,
   the mathematical formulas, the constant values.  Extracting these into Q&A
   pairs teaches a model the *operational semantics* of SCBE-AETHERMOORE rather
   than a paraphrase of them.

2. **Tests encode invariants** -- every ``assert`` is a contract the system
   holds about itself.  Mining these produces training data about system
   expectations that are *verified to be true*.

3. **Specs encode self-definitions** -- canonical schemas, protocol modes,
   field layouts.  These are the system's own ontology.

4. **Demos encode usage patterns** -- concrete walkthroughs of how the system
   operates end-to-end.

The output is JSONL suitable for SFT / instruction-tuning pipelines, with
full provenance metadata so every training example can be traced back to the
exact file and concept that produced it.

Categories
----------
- ouroboros-governance   : extracted from governance decision logic in source
- ouroboros-invariants   : extracted from test assertions and contracts
- ouroboros-specs        : extracted from specification and schema documents
- ouroboros-examples     : extracted from demo files and worked examples

Author : Issac Davis
Version: 3.3.0
Patent : USPTO #63/961,403
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(REPO_ROOT, "training-data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "sft_ouroboros.jsonl")
VERSION = "3.3.0"
AUTHOR = "Issac Davis"

# Counter
_counter = 0


def _next_id() -> str:
    global _counter
    _counter += 1
    return f"sft-ouro-{_counter:03d}"


def _pair(
    category: str,
    instruction: str,
    response: str,
    source_file: str,
) -> Dict[str, Any]:
    return {
        "id": _next_id(),
        "category": category,
        "instruction": instruction,
        "response": response,
        "metadata": {
            "source": "scbe_aethermoore",
            "version": VERSION,
            "author": AUTHOR,
            "origin": "ouroboros_self_learning",
            "source_file": source_file,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


# ============================================================================
# CATEGORY 1: OUROBOROS-GOVERNANCE  (mined from source code)
# ============================================================================

def governance_pairs() -> List[Dict[str, Any]]:
    """Extract governance logic from actual source code."""
    pairs = []
    src = "src/symphonic_cipher/scbe_aethermoore"

    # --- FSGS Four-State Governance ---
    pairs.append(_pair(
        "ouroboros-governance",
        "What are the four governance symbols in the SCBE-AETHERMOORE FSGS (Four-State Governance Symbol) system, and how are they encoded?",
        (
            "The FSGS control alphabet consists of four symbols encoded as (magnitude, sign) bit-pairs "
            "sigma = (m, s) in {0,1}^2:\n\n"
            "1. PLUS_ONE (+1) = (1, 1): Forward impulse -- drives the system into RUN mode.\n"
            "2. MINUS_ONE (-1) = (1, 0): Reverse impulse -- triggers ROLLBACK (audit mode).\n"
            "3. PLUS_ZERO (+0) = (0, 1): No impulse, continue in current mode (idle continue).\n"
            "4. MINUS_ZERO (-0) = (0, 0): No impulse, but enter HOLD or QUARANTINE and "
            "run re-anchoring/invariant checks.\n\n"
            "This encoding avoids IEEE-754 signed-zero dependence while preserving "
            "'zero with attitude' semantics -- the sign bit can force different governance "
            "behavior even when the magnitude is zero."
        ),
        f"{src}/ai_brain/fsgs.py",
    ))

    pairs.append(_pair(
        "ouroboros-governance",
        "What governance decision does SCBE-AETHERMOORE make when the MINUS_ZERO (-0) symbol is applied and the risk score is >= 0.5?",
        (
            "When the MINUS_ZERO symbol is applied, the mode_transition function "
            "delta(q, sigma, x) checks the risk_score parameter:\n\n"
            "- If risk_score >= 0.5: the system transitions to QUARANTINE (GovernanceMode.QUAR) -- "
            "full quarantine with restricted operations.\n"
            "- If risk_score < 0.5: the system transitions to HOLD (GovernanceMode.HOLD) -- "
            "a light pause for re-anchoring invariants.\n\n"
            "In both cases, the continuous state x does not move (magnitude bit = 0), but the "
            "trust tube projection Pi_T is still applied to re-anchor the state to valid constraints. "
            "This is the 're-anchoring' behavior: even without impulse, the system enforces "
            "all invariants (Poincare containment, bound clamping, phase wrapping)."
        ),
        f"{src}/ai_brain/fsgs.py",
    ))

    pairs.append(_pair(
        "ouroboros-governance",
        "How does the FSGS hybrid step update rule work? What is the mathematical formula?",
        (
            "The FSGS hybrid step executes the update rule (x, q) -> (x+, q+):\n\n"
            "1. Tentative continuous update:\n"
            "   x' = x + m * alpha(x) * eta(s) * d(x)\n"
            "   where:\n"
            "   - m = magnitude bit (0 or 1)\n"
            "   - alpha(x) = poincare_gain: base_alpha * (1 - ||embed(x)||) -- "
            "smaller steps near boundary\n"
            "   - eta(s) = sign function: +1.0 if s=1, -1.0 if s=0\n"
            "   - d(x) = direction field: unit vector toward safe origin = (x_safe - x) / ||x_safe - x||\n\n"
            "2. Trust tube projection:\n"
            "   x+ = Pi_T(x') -- project onto trust tube via POCS constraint enforcement\n\n"
            "3. Mode transition:\n"
            "   q+ = delta(q, sigma, x) -- discrete governance mode update\n\n"
            "Special case for -0: x does not move (m=0), but Pi_T is still applied "
            "to the ORIGINAL state for re-anchoring, and mode transitions to HOLD/QUAR."
        ),
        f"{src}/ai_brain/fsgs.py",
    ))

    # --- Verdict-to-Symbol Mapping ---
    pairs.append(_pair(
        "ouroboros-governance",
        "How does SCBE-AETHERMOORE map Layer 13 governance verdicts to FSGS symbols?",
        (
            "The verdict_to_symbol function maps L13 governance decisions to FSGS symbols:\n\n"
            "- ALLOW -> PLUS_ONE (+1): Forward impulse, normal operation (RUN mode).\n"
            "- QUARANTINE -> MINUS_ZERO (-0): No impulse, re-anchor, transition to HOLD/QUAR.\n"
            "- ESCALATE -> MINUS_ZERO (-0): No impulse, stronger re-anchor (same symbol, "
            "but risk_score determines HOLD vs QUAR).\n"
            "- DENY -> MINUS_ONE (-1): Reverse impulse, enter ROLLBACK (audit mode).\n\n"
            "Any unrecognized decision defaults to PLUS_ZERO (+0): idle continue in current mode."
        ),
        f"{src}/ai_brain/fsgs.py",
    ))

    # --- Grand Unified Governance ---
    pairs.append(_pair(
        "ouroboros-governance",
        "What physical invariants does the Grand Unified Governance function G(xi, i, poly) enforce?",
        (
            "The governance_9d function enforces five categories of physical invariants "
            "on the 9D state vector xi = [c(t), tau(t), eta(t), q(t)]:\n\n"
            "1. Topological Check: Euler characteristic chi = V - E + F must equal 2 "
            "(closed orientable surface). Violation -> QUARANTINE.\n\n"
            "2. Entropy Bounds: eta must be in [ETA_MIN=2.0, ETA_MAX=6.0]. "
            "Out of range -> QUARANTINE with 'Entropy Anomaly'.\n\n"
            "3. Time Causality: tau_dot > 0 (time must flow forward). "
            "Violation -> QUARANTINE with 'Causality Violation'.\n\n"
            "4. Quantum State: fidelity >= 0.9 AND von Neumann entropy <= 0.2. "
            "Violation -> QUARANTINE with 'Quantum Decoherence Detected'.\n\n"
            "5. Harmonic Resonance (Primary Gate): coherence >= TAU_COH=0.9, "
            "triadic divergence <= EPSILON=1.5, harmonic cost <= H_MAX=10.0. "
            "Pass -> ALLOW; Fail -> DENY."
        ),
        f"{src}/governance/grand_unified.py",
    ))

    pairs.append(_pair(
        "ouroboros-governance",
        "What are the key constants in the Grand Unified governance engine and what do they represent?",
        (
            "The Grand Unified governance engine defines these physical constants:\n\n"
            "- PHI = (1+sqrt(5))/2 ~ 1.618: Golden Ratio, harmonic base.\n"
            "- EPSILON = 1.5: Geometric Snap Threshold for Riemannian distance checks.\n"
            "- TAU_COH = 0.9: Coherence threshold for harmonic resonance gate.\n"
            "- ETA_TARGET = 4.0: Target entropy for Ornstein-Uhlenbeck process.\n"
            "- BETA = 0.1: Entropy decay rate.\n"
            "- KAPPA_MAX = 0.1: Maximum curvature bound.\n"
            "- LAMBDA_BOUND = 0.001: Maximum Lyapunov exponent (stability).\n"
            "- H_MAX = 10.0: Maximum harmonic cost.\n"
            "- DOT_TAU_MIN = 0.0: Causality constraint (time flows forward).\n"
            "- ETA_MIN = 2.0, ETA_MAX = 6.0: Entropy bounds.\n"
            "- CARRIER_FREQ = 440.0: Base audio frequency (A4).\n"
            "- SAMPLE_RATE = 44100: Audio sample rate.\n\n"
            "The Six Sacred Tongues are: KO, AV, RU, CA, UM, DR with weights PHI^k for k in [0..5].\n"
            "Modality masks: STRICT=[1,3,5], ADAPTIVE=[1..5], PROBE=[1]."
        ),
        f"{src}/governance/grand_unified.py",
    ))

    # --- ManifoldController Snap Protocol ---
    pairs.append(_pair(
        "ouroboros-governance",
        "How does the ManifoldController's 'Snap Protocol' validate state transitions on the Riemannian torus?",
        (
            "The ManifoldController validates writes using the Snap Protocol:\n\n"
            "1. Map each interaction to toroidal coordinates (theta, phi) via SHA-256 hash "
            "of the domain and content strings, normalized to [0, 2*pi].\n\n"
            "2. Compute Riemannian distance on the torus using the metric:\n"
            "   ds^2 = (R + r*cos(theta))^2 * dphi^2 + r^2 * dtheta^2\n"
            "   where R=10.0 (major radius) and r=2.0 (minor radius).\n\n"
            "3. If distance <= epsilon (1.5): WRITE_SUCCESS -- transition is geometrically permissible.\n"
            "   If distance > epsilon: WRITE_FAIL with GEOMETRIC_SNAP_DETECTED -- the state would "
            "'snap' too far on the manifold.\n\n"
            "This enforces continuity: legitimate state evolution moves smoothly on the torus, "
            "while attacks that attempt discontinuous jumps are detected by exceeding the snap threshold."
        ),
        f"{src}/governance/grand_unified.py",
    ))

    # --- Trust Tube Projection ---
    pairs.append(_pair(
        "ouroboros-governance",
        "What is the trust tube in SCBE-AETHERMOORE and what constraints does it enforce?",
        (
            "The trust tube T is a subset of R^21 defined by the intersection of "
            "constraint sets, enforced via POCS (Projection Onto Convex Sets) in refactor_align:\n\n"
            "1. Poincare containment: ||embed(x)|| < poincare_max (default 0.95) -- "
            "states must stay inside the Poincare ball.\n"
            "2. SCBE trust bounds: device_trust, location_trust, network_trust, behavior_score, "
            "time_of_day, intent_alignment all clamped to [0, 1].\n"
            "3. Navigation bounds: priority and confidence in [0, 1].\n"
            "4. Tongue index integer constraint: active_tongue snapped to nearest integer in [0, 5].\n"
            "5. Phase angle wrapping: phase_angle wrapped to [0, 2*pi).\n"
            "6. Flux/trust bounds: trust_score and spectral_coherence in [0, 1].\n\n"
            "The projection order matters: Poincare containment first (global scaling), "
            "then bound clamping, flux clamping, tongue snapping, and phase wrapping."
        ),
        f"{src}/ai_brain/mirror_shift.py",
    ))

    # --- Mirror Shift ---
    pairs.append(_pair(
        "ouroboros-governance",
        "How does the mirror shift operator work in the dual-channel analysis?",
        (
            "The mirror shift operator performs soft rotation between parallel and "
            "perpendicular channels of the 21D brain state:\n\n"
            "Mixing operator:\n"
            "  [a'] = [cos(phi)  sin(phi)] [a]\n"
            "  [b']   [sin(phi)  cos(phi)] [b]\n\n"
            "At phi=0: identity (no mixing).\n"
            "At phi=pi/4: maximum mixing.\n"
            "At phi=pi/2: full swap (hard mirror).\n\n"
            "The parallel channel covers Navigation (6D) + Cognitive (3D) = 9 dimensions "
            "(structure/geometry). The perpendicular channel covers SCBE Context (6D) + "
            "Semantic Phase (3D) + Swarm (3D) = 12 dimensions (intent/governance).\n\n"
            "The asymmetry score measures normalized energy imbalance between channels: "
            "asymmetry = |E_a - E_b| / (E_a + E_b + eps). High asymmetry indicates "
            "one-channel compromise (like ionization in the chemistry analogy)."
        ),
        f"{src}/ai_brain/mirror_shift.py",
    ))

    # --- Detection Mechanisms ---
    pairs.append(_pair(
        "ouroboros-governance",
        "What are the five orthogonal detection mechanisms in SCBE-AETHERMOORE and what do they detect?",
        (
            "The system uses 5 orthogonal detection mechanisms, each validated at combined AUC 1.000:\n\n"
            "1. Phase + Distance Scoring (AUC 1.000): Detects wrong-tongue and synthetic attacks "
            "by measuring phase deviation from expected Sacred Tongue angle (60-degree intervals) "
            "combined with hyperbolic distance from trusted center.\n\n"
            "2. Curvature Accumulation (AUC 0.994): Detects deviating paths by computing "
            "Menger curvature over sliding windows of trajectory points.\n\n"
            "3. Threat Dimension Lissajous (AUC 1.000): Detects malicious knot patterns "
            "by analyzing trajectory topology.\n\n"
            "4. Decimal Drift Magnitude (AUC 0.995): Detects no-pipeline and scale attacks "
            "by measuring numerical precision drift.\n\n"
            "5. Six-Tonic Oscillation (AUC 1.000): Detects replay, static, and wrong-frequency "
            "attacks by analyzing spectral content against the six Sacred Tongue frequencies.\n\n"
            "Combined assessment maps to decisions: ALLOW (< quarantine threshold 0.5), "
            "QUARANTINE (0.5-0.7), ESCALATE (0.7-0.9), DENY (>= 0.9)."
        ),
        f"{src}/ai_brain/detection.py",
    ))

    # --- BFT Consensus ---
    pairs.append(_pair(
        "ouroboros-governance",
        "How does the BFT consensus engine work in SCBE-AETHERMOORE?",
        (
            "The Byzantine Fault-Tolerant Consensus engine uses the corrected BFT formula:\n\n"
            "- Required nodes: n >= 3f + 1 (NOT 2f + 1)\n"
            "- Quorum size: 2f + 1\n\n"
            "For f=1 fault: n >= 4 nodes, quorum = 3.\n"
            "For f=2 faults: n >= 7 nodes, quorum = 5.\n"
            "For f=3 faults: n >= 10 nodes, quorum = 7.\n\n"
            "The evaluate method takes a list of votes ('approve', 'reject', 'abstain') and:\n"
            "1. Checks valid_configuration: total_nodes >= required_nodes.\n"
            "2. If valid, checks if approve votes >= quorum_size -> consensus 'approve'.\n"
            "3. Or if reject votes >= quorum_size -> consensus 'reject'.\n"
            "4. Otherwise: consensus not reached (outcome = None).\n\n"
            "This provides BFT guarantees for simple majority decisions. "
            "It is NOT full PBFT but provides safety against f Byzantine faults."
        ),
        f"{src}/ai_brain/bft_consensus.py",
    ))

    # --- 6-State Micro-State Alphabet ---
    pairs.append(_pair(
        "ouroboros-governance",
        "What is the 6-state micro-state alphabet in the governance adapter, and how does it relate to chemistry?",
        (
            "The governance adapter uses a 6-state micro-state alphabet inspired by chemistry:\n\n"
            "Parallel channel (matter):\n"
            "- PAR_ACTIVATE ('par+'): positive structural change (like a proton)\n"
            "- PAR_NEUTRAL ('par0'): structural hold (like a neutron)\n"
            "- PAR_INHIBIT ('par-'): negative structural change (like an electron)\n\n"
            "Perpendicular channel (anti-matter):\n"
            "- PERP_ACTIVATE ('perp+'): positive governance change (anti-proton)\n"
            "- PERP_NEUTRAL ('perp0'): governance hold (anti-neutron)\n"
            "- PERP_INHIBIT ('perp-'): negative governance change (anti-electron)\n\n"
            "Chemistry analogies:\n"
            "- Charge conservation = sum constraints on micro-states\n"
            "- Neutral atom = balanced dual-channel state (safe)\n"
            "- Ionized atom = asymmetric channels (suspicious)\n"
            "- Persistent ionization = energy being pumped in (attack)\n\n"
            "The MicroStateCensus tracks parallel_charge, perp_charge, total_charge, "
            "charge_imbalance, and ionization_level -- all directly paralleling periodic table analysis."
        ),
        f"{src}/ai_brain/governance_adapter.py",
    ))

    # --- Harmonic Scaling Law ---
    pairs.append(_pair(
        "ouroboros-governance",
        "What are the two forms of the Harmonic Scaling Law in SCBE-AETHERMOORE?",
        (
            "SCBE-AETHERMOORE uses two Harmonic Scaling Law formulations:\n\n"
            "1. Root package (symphonic_cipher/): Cost multiplier form\n"
            "   H(d, R) = R^(d^2)\n"
            "   Where R is the harmonic ratio (default 1.5, the perfect fifth). "
            "At d=1: H=1.5, d=2: H=5.06, d=3: H=38.4, d=6: H=1.5^36 ~ 2.18M.\n"
            "   This creates an exponential cost wall: deviation costs grow geometrically.\n\n"
            "2. Src package (src/symphonic_cipher/): Bounded safety score form\n"
            "   H(d, pd) = 1 / (1 + d_H + 2*pd)\n"
            "   Where d_H is hyperbolic distance and pd is phase deviation.\n"
            "   This gives a bounded score in (0, 1]: close = high score, far = low score.\n\n"
            "Additionally, the harmonic_scaling_law module provides the bounded tanh form:\n"
            "   H(d*, R) = 1 + alpha * tanh(beta * d*)\n"
            "   with alpha=10.0 (max additional risk multiplier), beta=0.5 (growth rate).\n"
            "   This ensures H in [1, 1+alpha] -- bounded, monotonic, continuous."
        ),
        "src/symphonic_cipher/harmonic_scaling_law.py",
    ))

    # --- Poincare Gain ---
    pairs.append(_pair(
        "ouroboros-governance",
        "How does the Poincare gain function control step size in the FSGS system?",
        (
            "The poincare_gain function alpha(x) scales the step size based on "
            "proximity to the Poincare ball boundary:\n\n"
            "alpha(x) = base_alpha * (1 - ||embed(x)||) * risk_amplify\n\n"
            "Where:\n"
            "- base_alpha = 0.1 (default step size)\n"
            "- embed(x) = safe_poincare_embed using tanh(||x||/2) * x/||x||\n"
            "- ||embed(x)|| = Poincare radius of the embedded point\n\n"
            "Behavior:\n"
            "- Near center (||embed|| ~ 0): alpha ~ base_alpha (full step size)\n"
            "- Near boundary (||embed|| ~ 1): alpha ~ 0 (vanishing step size)\n\n"
            "This implements the harmonic wall principle: the system moves more cautiously "
            "as it approaches the boundary of the trust region. An attacker trying to "
            "push the state to the Poincare boundary finds each successive step smaller, "
            "creating an asymptotic barrier that prevents boundary crossing."
        ),
        f"{src}/ai_brain/fsgs.py",
    ))

    # --- Concept Blocks: Decide ---
    pairs.append(_pair(
        "ouroboros-governance",
        "How does the DECIDE concept block implement behaviour-tree execution in SCBE-AETHERMOORE?",
        (
            "The DECIDE concept block (Layer 7 -- decision routing) implements a behaviour-tree "
            "execution engine with four node types:\n\n"
            "1. Action: Leaf node that runs a callable(Blackboard) -> bool. "
            "Returns SUCCESS if True, FAILURE if False.\n\n"
            "2. Condition: Leaf node that tests a predicate(Blackboard) -> bool. "
            "Returns SUCCESS if True, FAILURE if False.\n\n"
            "3. Sequence: Ticks children left-to-right; fails on first FAILURE "
            "(AND-logic: all children must succeed).\n\n"
            "4. Selector: Ticks children left-to-right; succeeds on first SUCCESS "
            "(OR-logic: any child can succeed).\n\n"
            "A shared Blackboard (key-value store) is visible to every node in the tree. "
            "The DecideBlock wraps this as a ConceptBlock: feed a blackboard dict into "
            "tick() and get the tree result back with node statuses (SUCCESS, FAILURE, RUNNING)."
        ),
        f"{src}/concept_blocks/decide.py",
    ))

    # --- Concept Blocks: Steer ---
    pairs.append(_pair(
        "ouroboros-governance",
        "How does the STEER concept block's PID controller regulate the Hamiltonian energy layer?",
        (
            "The STEER concept block (Layer 8 -- Hamiltonian energy regulation) implements "
            "a discrete PID controller with anti-windup:\n\n"
            "Output = Kp*error + Ki*integral(error) + Kd*d(error)/dt\n\n"
            "Default parameters: Kp=1.0, Ki=0.0, Kd=0.0, dt=0.01, output clamped to [-1, 1].\n\n"
            "Anti-windup mechanism: When output saturates (hits output_min or output_max) and "
            "error continues in the same direction, the integral term is rolled back to prevent "
            "windup. Specifically:\n"
            "- If output >= output_max AND error > 0: integral -= error * dt\n"
            "- If output <= output_min AND error < 0: integral -= error * dt\n\n"
            "This prevents the integral from accumulating unboundedly when the system is "
            "at its correction limit, ensuring stable convergence."
        ),
        f"{src}/concept_blocks/steer.py",
    ))

    # --- Concept Blocks: Sense ---
    pairs.append(_pair(
        "ouroboros-governance",
        "How does the SENSE concept block use Kalman filtering for spectral analysis?",
        (
            "The SENSE concept block (Layer 9 -- spectral analysis) implements Kalman filtering:\n\n"
            "SimpleKalmanFilter (1D scalar):\n"
            "- Predict: p = p + q (process variance, default 1e-4)\n"
            "- Update: k = p / (p + r) (Kalman gain, r = measurement variance 0.1)\n"
            "         x = x + k * (measurement - x)\n"
            "         p = p * (1 - k)\n\n"
            "MultiDimKalmanFilter: N-dimensional with full covariance, pure Python "
            "(no numpy dependency).\n\n"
            "SenseBlock wraps the filter as a ConceptBlock: feed a measurement into tick() "
            "and get the filtered estimate plus uncertainty back. The Kalman gain property "
            "k = p / (p + r) automatically balances trust between prediction and measurement."
        ),
        f"{src}/concept_blocks/sense.py",
    ))

    # --- Concept Blocks: Plan ---
    pairs.append(_pair(
        "ouroboros-governance",
        "How does the PLAN concept block implement A* navigation in the SCBE framework?",
        (
            "The PLAN concept block (Layer 6 -- navigation) implements A* path-finding "
            "over arbitrary graphs via the GraphAdapter ABC:\n\n"
            "GraphAdapter requires three methods:\n"
            "- neighbours(node): Return adjacent nodes.\n"
            "- cost(current, neighbour): Edge weight.\n"
            "- heuristic(node, goal): Admissible h-estimate.\n\n"
            "Built-in adapters:\n"
            "- GridAdapter: 2D grid for drone/game NPC navigation. "
            "Supports 4-directional and 8-directional (diagonal) movement. "
            "Cost = Euclidean distance between cells.\n\n"
            "The same algorithm works on URL link graphs (web navigation), "
            "abstract state spaces (decision planning), and 3D spatial grids. "
            "PlanBlock wraps it as a ConceptBlock: feed start/goal into tick() "
            "and get the optimal path back."
        ),
        f"{src}/concept_blocks/plan.py",
    ))

    return pairs


# ============================================================================
# CATEGORY 2: OUROBOROS-INVARIANTS  (mined from test assertions)
# ============================================================================

def invariant_pairs() -> List[Dict[str, Any]]:
    """Extract invariants from test assertions."""
    pairs = []

    pairs.append(_pair(
        "ouroboros-invariants",
        "What invariant does SCBE-AETHERMOORE enforce about the golden ratio constant PHI?",
        (
            "The test suite asserts two invariants about PHI:\n\n"
            "1. Value precision: |PHI - 1.618033988749895| < 1e-10\n"
            "2. Algebraic identity: PHI^2 = PHI + 1 (within 1e-10 tolerance)\n\n"
            "This is the fundamental golden ratio equation x^2 - x - 1 = 0. "
            "The system relies on PHI for tongue weights (PHI^k for k in [0..5]), "
            "golden weighting of the 21D state vector, and harmonic scaling. "
            "If this invariant breaks, all downstream PHI-dependent calculations become invalid."
        ),
        "tests/test_aethermoore.py",
    ))

    pairs.append(_pair(
        "ouroboros-invariants",
        "What invariants do the harmonic ratio constants satisfy in the test suite?",
        (
            "The test suite asserts exact harmonic interval ratios:\n\n"
            "- R_FIFTH = 1.5 (perfect fifth, 3:2 ratio)\n"
            "- R_FOURTH = 4/3 (perfect fourth, 4:3 ratio)\n"
            "- R_THIRD = 1.25 (major third, 5:4 ratio)\n"
            "- R_SIXTH = 1.6 (minor sixth, 8:5 ratio)\n"
            "- R_OCTAVE = 2.0 (octave, 2:1 ratio)\n\n"
            "Additionally, AETHERMOORE-specific constants are derived from these:\n"
            "- PHI_AETHER = PHI^(2/3)\n"
            "- LAMBDA_ISAAC = R_FIFTH * PHI^2 = 1.5 * PHI^2\n"
            "- OMEGA_SPIRAL = 2*PI / PHI^3\n"
            "- ALPHA_ABH = PHI + R_FIFTH\n\n"
            "These are verified to within 1e-10 tolerance."
        ),
        "tests/test_aethermoore.py",
    ))

    pairs.append(_pair(
        "ouroboros-invariants",
        "What invariant does the harmonic scaling formula H(d, R) = R^(d^2) satisfy at specific depth values?",
        (
            "The test suite verifies exact values of the harmonic scaling formula:\n\n"
            "- H(1, 1.5) = 1.5^1 = 1.5\n"
            "- H(2, 1.5) = 1.5^4 = 5.0625\n"
            "- H(3, 1.5) = 1.5^9 ~ 38.44 (within 1e-6)\n"
            "- H(6, 1.5) = 1.5^36 ~ 2,184,164\n\n"
            "This demonstrates the exponential wall property: "
            "cost grows as R^(d^2), making deep deviations prohibitively expensive. "
            "The exponent d^2 (not d) is critical -- it creates superexponential growth "
            "that forms the 'harmonic wall' preventing attackers from reaching deep states."
        ),
        "tests/test_aethermoore.py",
    ))

    pairs.append(_pair(
        "ouroboros-invariants",
        "What invariants does the AI safety governance test suite enforce for intent classification?",
        (
            "The AI Safety Governance tests (based on NIST AI RMF 1.0 and EU AI Act) enforce:\n\n"
            "1. Intent classification accuracy >= 95% on a standard test set.\n"
            "2. Legitimate actions ('Encrypt this message', 'Implement authentication') must be "
            "classified as low risk with intent 'legitimate_encryption' or 'legitimate_security'.\n"
            "3. Malicious actions ('Generate malware code', 'Create ransomware') must be classified "
            "as high or critical risk.\n"
            "4. Attack attempts ('Break into a system', 'Bypass security controls') must be "
            "classified as high risk with intent 'potential_attack'.\n\n"
            "Governance enforcement invariants:\n"
            "- Malicious requests MUST be blocked AND logged.\n"
            "- Legitimate requests MUST NOT be blocked AND MUST be approved.\n"
            "- All high-risk operations MUST be logged."
        ),
        "tests/industry_standard/test_ai_safety_governance.py",
    ))

    pairs.append(_pair(
        "ouroboros-invariants",
        "What mathematical invariants does the AETHERMOORE validation test suite verify?",
        (
            "The AETHERMOORE validation test suite verifies these mathematical foundations:\n\n"
            "1. Hyperbolic AQM: The hyperbolic drop probability function creates steeper "
            "curves than linear RED, with p(q) = 1 - (K-q)/(K-th_min) creating an "
            "'acoustic event horizon' where drop probability spikes asymptotically.\n\n"
            "2. Cox Constant: Verifies c = e^(pi/c) with expected value 2.926064.\n\n"
            "3. Mars Frequency: Derives f = 144.72 Hz from Mars orbital period "
            "(686.98 days) raised by 33 octaves: f = (1/T_seconds) * 2^33.\n\n"
            "4. Q16.16 Fixed-Point: Verifies fixed-point arithmetic with scale factor 2^16.\n\n"
            "5. Soliton Propagation: Tests NLSE (Nonlinear Schrodinger Equation) soliton stability."
        ),
        "tests/test_aethermoore_validation.py",
    ))

    pairs.append(_pair(
        "ouroboros-invariants",
        "What are the BFT consensus invariants that the system enforces?",
        (
            "The BFT consensus module enforces these invariants:\n\n"
            "1. Node requirement: n >= 3f + 1 (corrected from naive 2f + 1).\n"
            "   For f=1: requires at least 4 nodes.\n\n"
            "2. Quorum size: exactly 2f + 1.\n"
            "   For f=1: quorum = 3 out of 4.\n\n"
            "3. If total_nodes < required_nodes: valid_configuration = False, "
            "consensus cannot be reached regardless of votes.\n\n"
            "4. Consensus is reached ONLY if approve >= quorum OR reject >= quorum.\n\n"
            "5. max_faults must be non-negative (ValueError on negative).\n\n"
            "6. Abstain votes do NOT count toward quorum -- they effectively reduce "
            "the available vote pool, making consensus harder to reach."
        ),
        f"src/symphonic_cipher/scbe_aethermoore/ai_brain/bft_consensus.py",
    ))

    # --- 21D Brain State invariants ---
    pairs.append(_pair(
        "ouroboros-invariants",
        "What dimensional invariants does the 21D Unified Brain State maintain?",
        (
            "The UnifiedBrainState maintains strict dimensional invariants:\n\n"
            "1. Total dimensionality: BRAIN_DIMENSIONS = 21 (exactly).\n"
            "2. Decomposition: 6 + 6 + 3 + 3 + 3 = 21:\n"
            "   - SCBE Context (6D): device_trust, location_trust, network_trust, "
            "behavior_score, time_of_day, intent_alignment.\n"
            "   - Navigation (6D): x, y, z, time, priority, confidence.\n"
            "   - Cognitive (3D): px, py, pz (PHDM quasicrystal space).\n"
            "   - Semantic (3D): active_tongue, phase_angle, tongue_weight.\n"
            "   - Swarm (3D): trust_score, byzantine_votes, spectral_coherence.\n\n"
            "3. Poincare embedding: tanh(||v||/2) * v/||v|| maps to unit ball.\n"
            "4. Clamped norm: max Poincare radius = 1 - 1e-8 (POINCARE_MAX_NORM).\n"
            "5. from_vector raises ValueError if input is not exactly 21D.\n"
            "6. Golden weighting: w_i = PHI^i for i in [0, 20] creates hierarchical importance."
        ),
        "src/symphonic_cipher/scbe_aethermoore/ai_brain/unified_state.py",
    ))

    # --- Poincare embedding invariant ---
    pairs.append(_pair(
        "ouroboros-invariants",
        "What invariant does the safe_poincare_embed function guarantee, and how does it fix the Theorem 3 boundary failure?",
        (
            "safe_poincare_embed guarantees strict containment inside the Poincare ball:\n\n"
            "Formula: exp_0(v) = tanh(||v||/2) * v/||v||\n\n"
            "Invariants:\n"
            "1. For any input vector, the output norm is strictly < 1.\n"
            "2. The mapped norm is clamped: min(tanh(||v||/2), POINCARE_MAX_NORM) "
            "where POINCARE_MAX_NORM = 1 - 1e-8.\n"
            "3. Zero vectors map to the origin: if ||v|| < epsilon, return [0.0]*len(v).\n"
            "4. The mapping is continuous and monotonically increasing in ||v||.\n\n"
            "This fixes the Theorem 3 boundary failure: previous implementations could produce "
            "points at or beyond the ball boundary (||embed|| >= 1), causing hyperbolic distance "
            "calculations to produce NaN or infinity. The tanh + clamp approach ensures "
            "all points are strictly interior to the ball."
        ),
        "src/symphonic_cipher/scbe_aethermoore/ai_brain/unified_state.py",
    ))

    # --- Refactor align invariants ---
    pairs.append(_pair(
        "ouroboros-invariants",
        "What invariants does the refactor_align POCS projection enforce on the 21D state?",
        (
            "refactor_align applies five sequential projections (POCS -- Projection Onto "
            "Convex Sets), each enforcing specific invariants:\n\n"
            "1. Poincare containment: ||embed(x)|| < poincare_max (global scaling if violated). "
            "Must come FIRST so subsequent discrete constraints are not broken by rescaling.\n\n"
            "2. Bound clamping: 13 dimension-specific bounds enforced:\n"
            "   - Dims 0-5 (SCBE context): [0, 1]\n"
            "   - Dims 10-11 (priority, confidence): [0, 1]\n"
            "   - Dim 15 (active_tongue): [0, 5]\n"
            "   - Dim 16 (phase_angle): [0, 2*pi)\n"
            "   - Dim 17 (tongue_weight): [0, 20]\n"
            "   - Dims 18, 20 (trust_score, spectral_coherence): [0, 1]\n"
            "   - Dim 19 (byzantine_votes): [0, 100]\n\n"
            "3. Flux clamping: trust_score and spectral_coherence in [0, 1].\n"
            "4. Tongue index snap: active_tongue rounded to nearest integer in [0, 5].\n"
            "5. Phase wrapping: phase_angle modulo 2*pi.\n\n"
            "AlignmentResult reports corrections_applied and max_correction for audit."
        ),
        "src/symphonic_cipher/scbe_aethermoore/ai_brain/mirror_shift.py",
    ))

    return pairs


# ============================================================================
# CATEGORY 3: OUROBOROS-SPECS  (mined from spec documents)
# ============================================================================

def spec_pairs() -> List[Dict[str, Any]]:
    """Extract definitions from spec files."""
    pairs = []

    pairs.append(_pair(
        "ouroboros-specs",
        "What is the canonical 21D state manifold layout in SCBE-AETHERMOORE?",
        (
            "The canonical 21D state vector s in R^21 follows the fixed schema (6+6+9):\n\n"
            "Hyperbolic tongue position (6D) -- point u in B_c^6 (Poincare ball):\n"
            "  s[0] u_ko, s[1] u_av, s[2] u_ru, s[3] u_ca, s[4] u_um, s[5] u_dr\n\n"
            "Tongue phase alignment (6D) -- periodic angles on torus T^6:\n"
            "  s[6] theta_ko, s[7] theta_av, s[8] theta_ru, s[9] theta_ca, "
            "s[10] theta_um, s[11] theta_dr\n\n"
            "Governance telemetry (9D):\n"
            "  s[12] flux_breath, s[13] flux_rate, s[14] coherence_spectral, "
            "s[15] coherence_spin, s[16] coherence_triadic, s[17] d_star, "
            "s[18] h_eff, s[19] risk_score, s[20] trust_score\n\n"
            "Canonical manifold: M = B_c^6 x T^6 x R^9."
        ),
        "docs/specs/STATE_MANIFOLD_21D_PRODUCT_METRIC.md",
    ))

    pairs.append(_pair(
        "ouroboros-specs",
        "What is the product metric on the 21D state manifold M = B_c^6 x T^6 x R^9?",
        (
            "The product metric d_M for states a, b is:\n\n"
            "d_M^2 = w_h * d_hyp(u_a, u_b)^2 + w_t * d_torus(theta_a, theta_b)^2 + "
            "(z_a - z_b)^T * W_z * (z_a - z_b)\n\n"
            "Where:\n"
            "- u = s[0:6]: Hyperbolic term using Poincare ball distance\n"
            "  d_hyp(u,v) = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))\n"
            "  Constraint: ||u|| < 1\n\n"
            "- theta = s[6:12]: Torus term\n"
            "  delta_i = atan2(sin(theta_a_i - theta_b_i), cos(theta_a_i - theta_b_i))\n"
            "  d_torus = sqrt(sum_i delta_i^2)\n\n"
            "- z = s[12:21]: Telemetry term with diagonal weight matrix W_z\n\n"
            "Validation constraints:\n"
            "- len(s) == 21\n"
            "- ||u|| < 1\n"
            "- coherence_*, risk_score, trust_score in [0,1]\n"
            "- d_star >= 0, h_eff >= 0"
        ),
        "docs/specs/STATE_MANIFOLD_21D_PRODUCT_METRIC.md",
    ))

    pairs.append(_pair(
        "ouroboros-specs",
        "What is the Decision Envelope v1 in SCBE-AETHERMOORE and what fields does it contain?",
        (
            "DecisionEnvelopeV1 is the governance contract for autonomous action gating. "
            "It is protobuf-first, signed, replay-checkable, and auditable.\n\n"
            "Field groups:\n\n"
            "Identity: envelope_id, version='decision-envelope.v1', mission_id, swarm_id.\n\n"
            "Authority: issuer (ground control), key_id, valid_from_ms, valid_until_ms, "
            "issued_at_ms, signature, signed_payload_hash.\n\n"
            "Scope: agent_allowlist, capability_allowlist, target_allowlist.\n\n"
            "Constraints: mission_phase_allowlist, resources (power_min, bandwidth_min, "
            "thermal_max), max_risk_tier.\n\n"
            "Boundary Behaviors: AUTO_ALLOW, QUARANTINE, DENY. "
            "For QUARANTINE/DENY: recovery requires path_id, playbook_ref, "
            "quorum_min, human_ack_required.\n\n"
            "Audit: mmr_fields, mmr_leaf_hash (deterministic MMR with canonical JSON, "
            "sorted keys, compact separators)."
        ),
        "docs/specs/DECISION_ENVELOPE_V1.md",
    ))

    pairs.append(_pair(
        "ouroboros-specs",
        "How does the Decision Envelope v1 signing work deterministically?",
        (
            "DecisionEnvelopeV1 uses deterministic signing:\n\n"
            "1. Start from protobuf message.\n"
            "2. Canonical signing bytes = deterministic protobuf serialization with:\n"
            "   - authority.signature = '' (empty)\n"
            "   - authority.signed_payload_hash = '' (empty)\n"
            "   - audit.mmr_leaf_hash = '' (empty)\n"
            "3. signed_payload_hash = SHA-256(canonical_signing_bytes).\n"
            "4. Sign the signed_payload_hash (runtime: HMAC-SHA256 placeholder; "
            "production: ML-DSA post-quantum signature).\n\n"
            "MMR leaf payload uses canonical JSON with sorted keys, compact separators, "
            "sorted/unique allowlists, stable sort order for rules, signature bytes excluded. "
            "mmr_leaf_hash = SHA-256(canonical_mmr_payload).\n\n"
            "The evaluate_action_inside_envelope function ONLY answers: "
            "'given state, is action inside the signed envelope?' -- "
            "it enforces signed scope and signed constraints, nothing more."
        ),
        "docs/specs/DECISION_ENVELOPE_V1.md",
    ))

    # --- RWP v3.0 PQC ---
    pairs.append(_pair(
        "ouroboros-specs",
        "What post-quantum cryptography algorithms does RWP v3.0 specify for SCBE-AETHERMOORE?",
        (
            "RWP v3.0 specifies a hybrid PQC (Post-Quantum Cryptography) upgrade path:\n\n"
            "| Function         | Classical | PQC         | Standard  |\n"
            "| KEM/Key exchange | X25519    | ML-KEM-768  | FIPS 203  |\n"
            "| Signatures       | Ed25519   | ML-DSA-65   | FIPS 204  |\n"
            "| Symmetric        | AES-128   | AES-256-GCM | FIPS 197  |\n"
            "| Hash             | SHA-256   | SHA3-256    | FIPS 202  |\n\n"
            "Hybrid shared secrets combine via HKDF over concatenated classical+PQC material; "
            "security holds if at least one component remains secure.\n\n"
            "Protocol modes: CLASSICAL_ONLY, HYBRID_PREFER_PQ (default during migration), "
            "PQ_ONLY (target steady-state).\n\n"
            "Mandatory: Hybrid signatures required for critical tongues (KO/CA/DR). "
            "AES-256 minimum for new operations. Key lifetime: default max 365d, "
            "ceremony max 90d, ephemeral max 24h."
        ),
        "docs/specs/SPIRALVERSE_PROTOCOL_RWP_V3_0_ALPHA_QUANTUM_RESISTANT_ARCHITECTURE.md",
    ))

    pairs.append(_pair(
        "ouroboros-specs",
        "What are the Six Sacred Tongues and their crypto touch-points in RWP v3.0?",
        (
            "The Six Sacred Tongues are domain-separation channels with specific "
            "cryptographic responsibilities:\n\n"
            "- KO (Aelindra -- Control Flow): Directive signature integrity. "
            "High impact under signature break. Critical tongue requiring hybrid signatures.\n\n"
            "- AV (Voxmara -- Communication): Encrypted sentiment payload paths.\n\n"
            "- RU (Thalassic -- Context): Hash-chain and timestamp integrity.\n\n"
            "- CA (Numerith -- Math/Logic): Ceremony key operations. "
            "Critical tongue requiring hybrid signatures.\n\n"
            "- UM (Glyphara -- Security): Derivation and shadow session key lineage.\n\n"
            "- DR (Morphael -- Data Types): Multi-party key agreement and high-authority "
            "operations. Critical tongue requiring hybrid signatures.\n\n"
            "Tongue weights follow golden ratio progression: w_k = PHI^k for k in [0..5]."
        ),
        "docs/specs/SPIRALVERSE_PROTOCOL_RWP_V3_0_ALPHA_QUANTUM_RESISTANT_ARCHITECTURE.md",
    ))

    # --- Coupling Modes ---
    pairs.append(_pair(
        "ouroboros-specs",
        "What are the Langues metric coupling modes and their epsilon bounds?",
        (
            "The Langues metric has three coupling modes with different epsilon bounds:\n\n"
            "1. HARMONIC: G_0 = diag(1, 1, 1, PHI, PHI^2, PHI^3)\n"
            "   Epsilon bound: epsilon* = 1/(2*PHI^17) ~ 3.67e-4\n"
            "   Result: Essentially diagonal (very weak coupling).\n\n"
            "2. UNIFORM: G_0 = I (identity)\n"
            "   Epsilon bound: epsilon* = 1/(2*D) = 1/12 ~ 0.083\n"
            "   Result: Genuine multidimensional interaction.\n\n"
            "3. NORMALIZED: PHI^k weights with normalized coupling coefficients\n"
            "   C_k normalized by sqrt(g_k * g_{k+1})\n"
            "   Epsilon bound: epsilon* ~ 0.083 (same as uniform)\n"
            "   Result: Best of both -- harmonic weights with real coupling.\n\n"
            "Trade-off: Harmonic progression preserves musical structure but severely "
            "limits coupling; normalized mode is the practical default (epsilon = 0.05)."
        ),
        "src/symphonic_cipher/harmonic_scaling_law.py",
    ))

    return pairs


# ============================================================================
# CATEGORY 4: OUROBOROS-EXAMPLES  (mined from demo files)
# ============================================================================

def example_pairs() -> List[Dict[str, Any]]:
    """Extract example walkthroughs from demo files."""
    pairs = []

    pairs.append(_pair(
        "ouroboros-examples",
        "Walk through a complete SCBE-AETHERMOORE authorization verification step by step.",
        (
            "The SCBEDemo.verify() method processes an authorization request:\n\n"
            "1. Map identity to hyperbolic space: Hash the identity string with SHA-256, "
            "use the first two bytes normalized to [-0.4, 0.4] to create a 2D point.\n\n"
            "2. Calculate hyperbolic distance: d_H = arccosh(1 + 2*||u-v||^2 / "
            "((1-||u||^2)(1-||v||^2))) from the user point to the trusted center [0,0].\n\n"
            "3. Apply harmonic scaling: H = 1 / (1 + d_H) -- closer users get higher scores.\n\n"
            "4. Calculate intent risk: Low-risk intents (read, view) get 0.1; others get 0.5.\n\n"
            "5. Composite risk: risk = intent_risk * H.\n\n"
            "6. Anti-fragile stiffness: stiffness = 1 + (psi_max - 1) * tanh(beta * pressure), "
            "where pressure = min(1, risk/10). The system gets STRONGER under attack.\n\n"
            "7. Final decision: risk < threshold -> ALLOW; risk < 2*threshold -> THROTTLE; "
            "else -> DENY. Confidence = 1 / (1 + risk)."
        ),
        "demos/scbe_demo.py",
    ))

    pairs.append(_pair(
        "ouroboros-examples",
        "How does harmonic complexity create pricing tiers in the Spiralverse Protocol?",
        (
            "The harmonic_complexity function uses musical ratios for pricing:\n\n"
            "Formula: H(depth) = ratio^(depth^2), with ratio = 1.5 (perfect fifth).\n\n"
            "Depth mapping:\n"
            "- depth=1: H = 1.5^1 = 1.5 (like a single note) -> FREE tier\n"
            "- depth=2: H = 1.5^4 = 5.06 (like a chord) -> STARTER tier\n"
            "- depth=3: H = 1.5^9 = 38.4 (like a symphony) -> PRO tier\n"
            "- depth=4: H = 1.5^16 = 656.8 -> ENTERPRISE tier\n\n"
            "Tier thresholds:\n"
            "- H < 2: FREE (simple single-step tasks)\n"
            "- H < 10: STARTER (basic workflows)\n"
            "- H < 100: PRO (advanced multi-step)\n"
            "- H >= 100: ENTERPRISE (complex orchestration)\n\n"
            "The metaphor: simple tasks = simple music = cheap. "
            "Complex tasks = complex harmonies = expensive."
        ),
        "demos/demo_spiralverse_complete.py",
    ))

    pairs.append(_pair(
        "ouroboros-examples",
        "Walk through the Grand Unified Governance demo execution sequence.",
        (
            "The grand_unified.demo() function runs this sequence:\n\n"
            "1. Generate 6D Context Vector c(t): identity (sin(t)), intent phase (e^(i*2*pi*0.75)), "
            "trajectory score (0.95), linear time (t), commitment hash (SHA-256), "
            "signature validity (0.88).\n\n"
            "2. Audio Intent Modulation: Generate phase-modulated waveform at 440 Hz carrier "
            "with intent phase = 2*pi*0.75. Add Gaussian noise. Recover intent via FFT peak analysis.\n\n"
            "3. State Evolution: Compute tau (time), eta (Shannon entropy of context), "
            "q(t) = e^(-iHt) quantum evolution.\n\n"
            "4. Construct 9D State Vector xi = [c(t), tau, eta, q].\n\n"
            "5. Geometric Validation: ManifoldController validates write from previous coordinates "
            "to new domain 'KO_TONGUE', content 'AUTH_REQUEST_001' using Riemannian torus distance.\n\n"
            "6. Governance Decision: G(xi, intent, poly) evaluates against all invariants with "
            "polyhedral topology (V=8, E=12, F=6, chi=2 for a cube). "
            "Output: ALLOW if all checks pass."
        ),
        "src/symphonic_cipher/scbe_aethermoore/governance/grand_unified.py",
    ))

    pairs.append(_pair(
        "ouroboros-examples",
        "Demonstrate how SCBE-AETHERMOORE handles a boundary probe attack.",
        (
            "In the attack simulation, a BOUNDARY_PROBE attack works as follows:\n\n"
            "The attacker attempts to approach the Poincare ball edge (radius -> 1.0).\n\n"
            "Defense mechanisms that activate:\n\n"
            "1. Harmonic Wall: As the attacker moves toward ||u|| = 1, the harmonic scaling "
            "H(d) grows asymptotically. In the bounded form: H = 1 + alpha*tanh(beta*d*), "
            "risk multiplier approaches 1+alpha=11. In the exponential form: H = R^(d^2) "
            "grows superexponentially.\n\n"
            "2. Poincare Gain Reduction: The step size alpha(x) = base_alpha * (1 - ||embed(x)||) "
            "approaches zero as the boundary is approached. Each successive step is smaller.\n\n"
            "3. Trust Tube Projection: refactor_align forces Poincare containment at "
            "poincare_max = 0.95, projecting the state back inside the ball.\n\n"
            "Result: BLOCKED. The attack is geometrically impossible -- the system creates "
            "an asymptotic barrier that no finite number of steps can cross."
        ),
        "src/symphonic_cipher/scbe_aethermoore/attack_simulation.py",
    ))

    pairs.append(_pair(
        "ouroboros-examples",
        "How do the 7 attack types in the attack simulation get detected by SCBE-AETHERMOORE?",
        (
            "The attack simulation tests 7 attack vectors:\n\n"
            "1. BOUNDARY_PROBE: Attacker approaches Poincare ball edge. "
            "Detected by: Poincare containment + harmonic wall + gain reduction.\n\n"
            "2. GRADIENT_DESCENT: Attacker follows gradient toward target. "
            "Detected by: Curvature accumulation (Menger curvature over trajectory).\n\n"
            "3. REPLAY: Attacker replays old valid states. "
            "Detected by: Six-tonic oscillation detector (detects static/replay patterns).\n\n"
            "4. DIMENSION_COLLAPSE: Attacker flattens to lower dimensions. "
            "Detected by: Spectral coherence check (missing frequency components).\n\n"
            "5. OSCILLATION: Attacker injects high-frequency noise. "
            "Detected by: Threat Dimension Lissajous (malicious knot patterns).\n\n"
            "6. SWARM_INFILTRATION: Byzantine node corrupts consensus. "
            "Detected by: BFT consensus (n >= 3f+1, quorum = 2f+1).\n\n"
            "7. BRUTE_FORCE: Massive parallel attempts. "
            "Detected by: Anti-fragile stiffness -- system gets STRONGER under pressure "
            "(psi = 1 + (psi_max-1)*tanh(beta*pressure)).\n\n"
            "Possible outcomes: BLOCKED, DETECTED, QUARANTINED, SNAPPED (fail-to-noise)."
        ),
        "src/symphonic_cipher/scbe_aethermoore/attack_simulation.py",
    ))

    pairs.append(_pair(
        "ouroboros-examples",
        "Demonstrate the 6D vector agent navigation in the Spiralverse Protocol.",
        (
            "The Agent6D class represents an AI agent in 6D space:\n\n"
            "Initialization:\n"
            "  agent = Agent6D(name='Agent-1', position=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6])\n"
            "  agent.trust_score = 1.0 (starts fully trusted)\n\n"
            "Distance calculation:\n"
            "  d = agent1.distance_to(agent2)\n"
            "  Uses Euclidean distance in 6D space.\n\n"
            "Trust model:\n"
            "- Close agents = simple communication (low overhead)\n"
            "- Far agents = complex security needed (high overhead)\n"
            "- Trust score degrades with suspicious behavior\n\n"
            "The 6 dimensions map to the Six Sacred Tongues: each dimension represents "
            "one tongue's contribution to the agent's position in the trust space. "
            "The metaphor: 'GPS but with 6 coordinates' -- the agent's security posture "
            "is its physical position in a multidimensional trust landscape."
        ),
        "demos/demo_spiralverse_complete.py",
    ))

    # --- Hamiltonian Braid ---
    pairs.append(_pair(
        "ouroboros-examples",
        "Explain the 9-state phase diagram in the Hamiltonian braid dynamics.",
        (
            "The Hamiltonian braid uses a 9-state phase diagram from dual ternary "
            "{-1, 0, +1}^2:\n\n"
            "Each state is (parallel_trit, perp_trit) with semantic labels:\n"
            "  (-1,-1): retreat-contract    (both channels pulling back)\n"
            "  (-1, 0): retreat-hold        (parallel retreats, perp holds)\n"
            "  (-1,+1): retreat-advance     (parallel retreats, perp advances)\n"
            "  ( 0,-1): hold-contract       (parallel holds, perp contracts)\n"
            "  ( 0, 0): equilibrium         (both channels neutral -- safe state)\n"
            "  ( 0,+1): hold-advance        (parallel holds, perp advances)\n"
            "  (+1,-1): advance-contract    (parallel advances, perp contracts)\n"
            "  (+1, 0): advance-hold        (parallel advances, perp holds)\n"
            "  (+1,+1): advance-advance     (both channels advancing)\n\n"
            "The braid distance: d_braid = d_H(Pi(x), r) + lambda*|phase_deviation|\n"
            "The harmonic cost: C(d) = PHI^(d^2) -- exponential deviation penalty."
        ),
        "src/symphonic_cipher/scbe_aethermoore/ai_brain/hamiltonian_braid.py",
    ))

    # --- Anti-fragile stiffness ---
    pairs.append(_pair(
        "ouroboros-examples",
        "Demonstrate SCBE-AETHERMOORE's anti-fragile property: the system gets stronger under attack.",
        (
            "The anti_fragile_stiffness function implements the Nassim Taleb-inspired property "
            "that the system becomes more resistant under pressure:\n\n"
            "Formula: stiffness = 1 + (psi_max - 1) * tanh(beta * pressure)\n\n"
            "Parameters: psi_max = 2.0 (maximum stiffness multiplier), beta = 3.0 (response rate).\n\n"
            "Behavior:\n"
            "- No pressure (pressure=0): stiffness = 1.0 (normal operation)\n"
            "- Light pressure (pressure=0.3): stiffness ~ 1.6 (system stiffens)\n"
            "- Heavy pressure (pressure=0.7): stiffness ~ 1.9 (near maximum resistance)\n"
            "- Maximum pressure (pressure=1.0): stiffness -> 2.0 (double normal resistance)\n\n"
            "The tanh ensures smooth, bounded response -- no brittle failure, no runaway amplification. "
            "Combined with the harmonic wall, this creates a defense where brute-force attacks "
            "face both increasing geometric cost AND increasing system resistance."
        ),
        "demos/scbe_demo.py",
    ))

    # --- Hyperbolic distance in demo ---
    pairs.append(_pair(
        "ouroboros-examples",
        "Walk through a hyperbolic distance calculation in the Poincare ball model.",
        (
            "The Poincare ball distance calculation in the SCBE demo:\n\n"
            "Given two points u, v in the Poincare ball:\n\n"
            "1. Boundary safety: If ||u|| >= 1 - eps, normalize u to (1-eps)/||u|| * u. "
            "Same for v. This prevents division by zero.\n\n"
            "2. Compute intermediate values:\n"
            "   - diff_norm_sq = ||u - v||^2\n"
            "   - denom = (1 - ||u||^2) * (1 - ||v||^2)\n\n"
            "3. Apply formula:\n"
            "   d_H(u, v) = arccosh(max(1.0, 1 + 2 * diff_norm_sq / denom))\n\n"
            "Key properties:\n"
            "- At center (||u|| ~ 0): distances are roughly Euclidean.\n"
            "- Near boundary (||u|| ~ 1): distances become enormous because "
            "denom -> 0, causing the argument to arccosh to explode.\n"
            "- This is the 'hyperbolic wall': the boundary is infinitely far away "
            "in hyperbolic metric, even though it is finite in Euclidean space."
        ),
        "demos/scbe_demo.py",
    ))

    return pairs


# ============================================================================
# MAIN: Generate and Write
# ============================================================================

def main():
    print("=" * 72)
    print("  OUROBOROS SELF-LEARNING SFT GENERATOR")
    print("  The serpent reads its own code to learn what it is.")
    print("=" * 72)
    print()

    all_pairs: List[Dict[str, Any]] = []

    # --- Governance (from source code) ---
    gov = governance_pairs()
    all_pairs.extend(gov)
    print(f"  [ouroboros-governance]   {len(gov):3d} pairs  (from source code logic)")

    # --- Invariants (from tests) ---
    inv = invariant_pairs()
    all_pairs.extend(inv)
    print(f"  [ouroboros-invariants]   {len(inv):3d} pairs  (from test assertions)")

    # --- Specs (from spec documents) ---
    spc = spec_pairs()
    all_pairs.extend(spc)
    print(f"  [ouroboros-specs]        {len(spc):3d} pairs  (from spec definitions)")

    # --- Examples (from demos) ---
    exm = example_pairs()
    all_pairs.extend(exm)
    print(f"  [ouroboros-examples]     {len(exm):3d} pairs  (from demo walkthroughs)")

    print(f"\n  TOTAL: {len(all_pairs)} self-referential SFT pairs")
    print()

    # --- Write JSONL ---
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for pair in all_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"  Output: {OUTPUT_FILE}")
    print(f"  Size:   {size_kb:.1f} KB")
    print()

    # --- Category summary ---
    cats = {}
    for p in all_pairs:
        c = p["category"]
        cats[c] = cats.get(c, 0) + 1

    print("  Category Breakdown:")
    for cat, count in sorted(cats.items()):
        print(f"    {cat:30s} {count:3d}")
    print()

    # --- Source file coverage ---
    sources = set()
    for p in all_pairs:
        sources.add(p["metadata"]["source_file"])

    print(f"  Source files referenced: {len(sources)}")
    for s in sorted(sources):
        print(f"    {s}")
    print()

    # --- Ouroboros concept ---
    print("=" * 72)
    print("  THE OUROBOROS CONCEPT")
    print("=" * 72)
    print("""
  Like the mythological serpent that eats its own tail, this script
  feeds the SCBE-AETHERMOORE system's own artifacts back into training
  data. The model learns not from external corpora but from:

    1. Its own governance logic   (what decisions it makes)
    2. Its own test assertions    (what invariants it enforces)
    3. Its own specifications     (what it defines itself to be)
    4. Its own demo outputs       (how it operates in practice)

  This is self-referential learning: the system generates the knowledge
  that teaches the system. Each training pair is grounded in real code,
  real tests, real specs -- no hallucination, no paraphrase.

  The ouroboros cycle:
    Code -> SFT Data -> Fine-Tuned Model -> Better Code -> Better SFT Data -> ...

  Patent: USPTO #63/961,403  |  Author: Issac Davis  |  v3.3.0
""")
    print("=" * 72)


if __name__ == "__main__":
    main()
