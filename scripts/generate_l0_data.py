#!/usr/bin/env python3
"""Generate L0 (substrate/foundation) training data — the gap Grok identified.

L0 = structural constraints, axioms, geometric invariants, fundamental definitions.
These are the "bones" the model needs to reason about structure itself, not just
surface patterns.

Generates records tagged at L0 with full tongue/null/view metadata for multi-view training.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "training-data" / "sft" / "l0_substrate_sft.jsonl"

# L0 substrate records — structural constraints, axioms, geometry definitions
L0_RECORDS = [
    # ── Harmonic Wall Foundations ──
    {
        "instruction": "What is the structural constraint of the harmonic wall?",
        "output": "H(d,R) = R^(d^2). This is super-exponential: doubling distance squares the exponent. At d=1, H=R. At d=2, H=R^4. At d=3, H=R^9. The wall makes adversarial drift computationally infeasible because cost grows faster than any polynomial.",
        "tongues_active": ["DR"],
        "category": "axiom",
    },
    {
        "instruction": "Why must the harmonic wall use super-exponential scaling?",
        "output": "Polynomial walls (H=R*d^n) can be overcome with polynomial compute. Exponential walls (H=R^d) can be overcome with exponential compute. Super-exponential (H=R^(d^2)) requires super-exponential compute to breach — matching the hardness of the PQC primitives (ML-KEM-768, ML-DSA-65) that protect the pipeline.",
        "tongues_active": ["DR", "UM"],
        "category": "axiom",
    },
    {
        "instruction": "What happens if the harmonic wall exponent is changed from d^2 to d?",
        "output": "The wall becomes merely exponential. An attacker with access to quantum compute (Grover's algorithm) can reduce effective distance by sqrt, making d^1 attacks feasible. The d^2 exponent provides a quadratic safety margin above known quantum speedups.",
        "tongues_active": ["DR", "UM"],
        "category": "constraint",
    },
    # ── Poincare Ball Constraints ──
    {
        "instruction": "What is the structural constraint of the Poincare ball embedding?",
        "output": "All points must satisfy ||u|| < 1. The boundary ||u|| = 1 is at infinity in hyperbolic distance. Points near the center are in safe territory. Points near the boundary represent extreme drift. The tanh mapping u = tanh(a||x||) * x/||x|| guarantees ||u|| < 1 for all finite inputs.",
        "tongues_active": ["DR"],
        "category": "invariant",
    },
    {
        "instruction": "Why does SCBE use hyperbolic geometry instead of Euclidean?",
        "output": "Hyperbolic space has exponential volume growth: the area of a circle of radius r grows as exp(r), not r^2. This means adversarial regions are exponentially larger than safe regions — but reaching them costs exponentially more. Euclidean space gives linear cost growth, which is insufficient for safety guarantees.",
        "tongues_active": ["DR", "RU"],
        "category": "axiom",
    },
    {
        "instruction": "What invariant does the hyperbolic distance formula preserve?",
        "output": "d_H = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2))). This is Mobius-invariant: applying any Mobius transformation to both u and v preserves d_H. This means the safety distance cannot be manipulated by coordinate tricks — it is a geometric invariant, not a metric artifact.",
        "tongues_active": ["DR"],
        "category": "invariant",
    },
    # ── Sacred Tongue Constraints ──
    {
        "instruction": "Why must Sacred Tongue weights follow phi-scaling?",
        "output": "Weights w_l = phi^(l-1) ensure: (1) each tongue is exactly phi times more expensive than the previous — no two tongues have the same cost, preventing confusion; (2) the sum converges to a known constant (phi^6 - 1)/(phi - 1) = 19.416; (3) the ratio between any two tongues is a power of phi, making all ratios structurally determined, not arbitrary.",
        "tongues_active": ["DR", "KO"],
        "category": "constraint",
    },
    {
        "instruction": "What happens if you remove one Sacred Tongue from the metric?",
        "output": "The 6-tongue metric becomes 5-dimensional. The missing dimension creates a blind spot: inputs that differ only in the removed tongue's domain become indistinguishable. The 21D state manifold loses 3.5 dimensions (1 hyperbolic + 1 phase + 1.5 telemetry), collapsing the product metric and breaking the Lyapunov stability guarantee.",
        "tongues_active": ["DR"],
        "category": "constraint",
    },
    {
        "instruction": "What is the structural role of tongue phase angles?",
        "output": "Each tongue has both a position u_l in the Poincare ball (where it is) and a phase angle theta_l on the torus (how it oscillates). Position encodes static state. Phase encodes dynamic behavior. The product metric d_M^2 = w_h*d_hyp^2 + w_t*d_torus^2 + z^T*W*z combines both. Without phases, the metric cannot detect temporal drift — an attacker who slowly rotates their position escapes detection.",
        "tongues_active": ["DR", "AV"],
        "category": "axiom",
    },
    # ── PHDM Structural Constraints ──
    {
        "instruction": "Why exactly 16 polyhedra in the PHDM?",
        "output": "5 Platonic (the only regular convex polyhedra — complete coverage of simple reasoning). 3 Archimedean (vertex-transitive semi-regular — complex multi-agent operations). 2 Kepler-Poinsot (non-convex regular — adversarial paths that SHOULD be expensive). 2 Toroidal (cyclic topology — feedback/recursive reasoning). 2 Rhombic (space-filling — lattice operations). 2 Johnson (irregular but face-regular — edge cases). Together they tile the full reasoning space with no gaps.",
        "tongues_active": ["DR"],
        "category": "axiom",
    },
    {
        "instruction": "What is the anti-loop constraint in PHDM routing?",
        "output": "Each polyhedron is visited at most once per reasoning path. This is the Hamiltonian path constraint: H(q,p) = sum(E_i * path_i) + sum(w_ij * jump_ij). Revisiting a polyhedron would mean circular reasoning. The energy budget enforces this — returning to a visited node incurs a doubled transition penalty, exhausting the budget before a cycle completes.",
        "tongues_active": ["DR", "CA"],
        "category": "invariant",
    },
    {
        "instruction": "What structural guarantee does the flux state provide?",
        "output": "POLLY mode: all 16 polyhedra active (full capability). QUASI mode: Platonic + Archimedean only (8, defensive). DEMI mode: Platonic only (5, lockdown). The guarantee: reducing the active set can only REDUCE capability, never introduce new paths. DEMI is strictly a subset of QUASI which is strictly a subset of POLLY. Degradation is monotonic — no surprise behaviors emerge from restriction.",
        "tongues_active": ["DR", "RU"],
        "category": "invariant",
    },
    # ── Geodesic Gateway Constraints ──
    {
        "instruction": "Why must the three geodesic gateways be at exactly 120 degrees?",
        "output": "Three vectors v1, v2, v3 at 120-degree separation satisfy <v_i, v_j> = -1/2 for i != j. This is the maximum-spread configuration in 3D — no gateway is closer to another than necessary. The equal spacing ensures: (1) no routing bias toward any gateway, (2) the cost reduction alpha*exp(-d^2/sigma^2) covers the full angular range uniformly, (3) the fractal recursion at each gateway produces identical sub-structure, maintaining symmetry at all scales.",
        "tongues_active": ["DR"],
        "category": "constraint",
    },
    {
        "instruction": "What is the structural role of fractal recursion in geodesic routing?",
        "output": "At each depth level m, the gateway cost reduction contracts by lambda = 1/phi (golden ratio contraction). Depth 0: -0.387, Depth 1: -0.239, Depth 2: -0.148. This creates scale-invariant routing: the same gateway pattern repeats at every zoom level, but with diminishing influence. The sum converges to a finite total discount — the gateway cannot reduce cost to zero, only asymptotically approach a floor.",
        "tongues_active": ["DR"],
        "category": "constraint",
    },
    # ── Lyapunov and Stability ──
    {
        "instruction": "What does the Lyapunov spectrum tell you about system stability?",
        "output": "The reference spectrum has lambda_1 = 0 (neutral, required for time-translation symmetry) and lambda_2 through lambda_7 approximately -0.10025 (stable). The trace sum = -0.601505 < 0, guaranteeing global asymptotic stability. If any exponent becomes positive, the system has a chaotic attractor — indicating adversarial manipulation of the phase space. The Lyapunov monitor detects this before the harmonic wall needs to fire.",
        "tongues_active": ["DR", "RU"],
        "category": "axiom",
    },
    {
        "instruction": "What is the structural constraint on the Lyapunov trace sum?",
        "output": "The trace must be strictly negative: sum(lambda_i) < 0 for i = 2..7 (excluding the neutral mode). This is the necessary and sufficient condition for the 21D state manifold to be a globally stable attractor. If the trace crosses zero, the system transitions from stable to chaotic. The harmonic wall H(d,R) acts as a Lyapunov function candidate: V = H is always positive and dV/dt < 0 along all trajectories — the wall is the stability proof.",
        "tongues_active": ["DR"],
        "category": "invariant",
    },
    # ── 21D State Manifold ──
    {
        "instruction": "What are the three structural components of the 21D state manifold?",
        "output": "6D hyperbolic positions (u_l in B^6, one per tongue — WHERE the state is), 6D phase angles (theta_l in T^6, one per tongue — HOW it oscillates), 9D telemetry (z vector — risk, trust, coherence, d_star, spectral ratio, spin alignment, temporal drift, energy budget, flux state). The product metric d_M^2 = w_h*d_hyp^2 + w_t*d_torus^2 + z^T*W_z*z combines all three with independent weights. No component can be removed without breaking the metric.",
        "tongues_active": ["DR"],
        "category": "axiom",
    },
    {
        "instruction": "Why is the 21D manifold a product space and not a single 21D Euclidean space?",
        "output": "Hyperbolic space (B^6) has negative curvature. The torus (T^6) has zero curvature with periodic topology. Telemetry (R^9) is flat. Mixing these into a single Euclidean R^21 would destroy the geometric properties: hyperbolic distance would become Euclidean (losing exponential volume growth), torus periodicity would be lost (phases would not wrap), and telemetry would interfere with spatial distances. The product metric preserves each component's geometry while coupling them through the weight matrices.",
        "tongues_active": ["DR"],
        "category": "constraint",
    },
    # ── GeoSeal and Trust ──
    {
        "instruction": "What is the structural trust scoring formula in GeoSeal v2?",
        "output": "trust = 0.4 * s_H + 0.35 * s_S + 0.25 * s_G. s_H = hyperbolic distance score (spatial), s_S = spectral coherence score (frequency), s_G = governance compliance score (policy). The weights (0.4, 0.35, 0.25) sum to 1.0 and are ordered by information content: spatial position carries the most signal, spectral coherence is second, governance compliance is third. The threshold: >= 0.7 ALLOW, >= 0.3 QUARANTINE, < 0.3 DENY.",
        "tongues_active": ["UM", "RU"],
        "category": "axiom",
    },
    # ── Quantum Axiom Mesh ──
    {
        "instruction": "What are the five quantum axioms and which layers enforce them?",
        "output": "1. Unitarity (L2, L4, L7): norm preservation — no information is created or destroyed. 2. Locality (L3, L8): spatial bounds — effects cannot propagate faster than the metric allows. 3. Causality (L6, L11, L13): time-ordering — causes precede effects in the temporal metric. 4. Symmetry (L5, L9, L10, L12): gauge invariance — the physics is the same regardless of coordinate choice. 5. Composition (L1, L14): pipeline integrity — the whole pipeline produces the same result as composing individual layers.",
        "tongues_active": ["DR"],
        "category": "axiom",
    },
    {
        "instruction": "What breaks if the Unitarity axiom is violated?",
        "output": "If ||output|| != ||input|| at L2/L4/L7, then either information was created (hallucination) or destroyed (information loss). Created information has no grounding — the model invented something. Destroyed information means the model forgot something it should remember. The unitarity check detects both: if the norm changes by more than epsilon, the layer output is rejected and the pipeline falls back to the previous valid state.",
        "tongues_active": ["DR", "RU"],
        "category": "constraint",
    },
    # ── Absence / Null Patterns ──
    {
        "instruction": "What does it mean when a tongue is null (inactive) in a record?",
        "output": "A null tongue means that domain was NOT relevant to the task. This is structural information: knowing that Security (UM) is null for a simple lookup tells the model not to allocate security-checking compute. The null pattern encodes constraint awareness — the model learns which processing channels to skip, reducing wasted computation. Average: 3.9 inactive tongues per note = most tasks use only 2-3 channels.",
        "tongues_active": ["DR", "KO"],
        "category": "constraint",
    },
    {
        "instruction": "Why is absence more informative than presence for training?",
        "output": "Presence says 'this is relevant' — any dataset can teach that. Absence says 'this is NOT relevant and here is why' — this requires structural understanding. A model trained only on presence will over-activate all channels (wasteful). A model trained on absence learns constraint gating: only activate the channels the geometry says are needed. This is why the vault dataset (avg 3.9 null tongues) produced 14% improvement — the model learned to NOT think about irrelevant dimensions.",
        "tongues_active": ["DR"],
        "category": "axiom",
    },
    # ── MERA / Tensor Network Foundations ──
    {
        "instruction": "What is the structural role of MERA in thought compression?",
        "output": "MERA (Multi-scale Entanglement Renormalization Ansatz) is a hierarchical tensor network that compresses quantum states at each scale. In SCBE, the 6 Sacred Tongues form a natural MERA tree: Level 0 = [KO,AV,RU,CA,UM,DR] (6 channels). Level 1 = [KO+AV, RU+CA, UM+DR] (3 paired). Level 2 = [Control, Logic, Security] (3 abstract). Level 3 = [Decision] (1 output). Most thoughts only need Level 2 — 66% compression with no information loss for standard tasks.",
        "tongues_active": ["DR", "CA"],
        "category": "axiom",
    },
    {
        "instruction": "What determines the minimum sufficient MERA level for a thought?",
        "output": "Complexity classification: Trivial/Simple = Level 3 (1 channel, just the decision). Standard = Level 2 (3 abstract channels — Control/Logic/Security). Complex = Level 1 (3 paired channels — full tongue pairs but compressed). Deep/Adversarial = Level 0 (all 6 individual channels, no compression). Using a lower level than needed produces incorrect outputs. Using a higher level than needed wastes compute. The route tagger determines the minimum sufficient level before processing begins.",
        "tongues_active": ["DR", "CA"],
        "category": "constraint",
    },
    # ── Governance Coin ──
    {
        "instruction": "What is the structural invariant of the Governance Coin?",
        "output": "Value = 1/(1+L) where L is the total Langues cost. Value is always in (0, 1]. Value = 1 when L = 0 (zero cost, perfect efficiency). Value approaches 0 as L approaches infinity (infinite cost, total inefficiency). The coin is monotonically decreasing in L — more cost always means less value. This is a structural guarantee: there is no way to increase value by increasing cost. The blake2s hash binds the coin to its inputs, preventing retroactive manipulation.",
        "tongues_active": ["DR", "RU"],
        "category": "invariant",
    },
    # ── Quasicrystal Lattice ──
    {
        "instruction": "Why is the quasicrystal lattice aperiodic?",
        "output": "The icosahedral lattice is projected from 6D (one dimension per Sacred Tongue) into 3D. Because icosahedral symmetry has 5-fold rotation (incompatible with periodic tiling in 3D by the crystallographic restriction theorem), the resulting lattice is aperiodic. Aperiodicity means: no repeating pattern that an attacker can predict and exploit. Combined with phason shifts (6D projection matrix rotation), the lattice acts as a one-time pad for spatial routing — each shift produces a completely new 3D arrangement.",
        "tongues_active": ["DR", "UM"],
        "category": "axiom",
    },
    # ── Cross-Domain Bridges ──
    {
        "instruction": "How does the neurotransmitter analogy map to computational efficiency?",
        "output": "KO=dopamine (reward for correct routing — reinforces efficient paths). AV=acetylcholine (attention to relevant I/O — prevents scattered reads). RU=GABA (inhibition of wrong paths — stops wasteful exploration). CA=glutamate (excitation of compute paths — activates necessary calculations). UM=serotonin (trust calibration — neither paranoid nor naive). DR=noradrenaline (structural alertness — flags when architecture needs change). Balance = efficiency. Imbalance = waste (CA dominance = over-thinking, RU dominance = over-caution).",
        "tongues_active": ["DR", "KO"],
        "category": "axiom",
    },
    {
        "instruction": "What is the Perpendicular Torsion Attack and why does it bypass centroid detection?",
        "output": "Two coordinated agents push inverse directions on perpendicular axes. Agent A shifts +x on KO. Agent B shifts -x on CA. The centroid (average) stays at origin — looks normal to any centroid-based detector. But the Lyapunov V function sees the variance: V = sum(lambda_i * ||x_i - mean||^2) which is 100x baseline for torsion vs 1x for benign. GTET catches this because Lyapunov stability monitoring is part of the efficiency score — high V means the system is unstable regardless of where the centroid is.",
        "tongues_active": ["UM", "DR"],
        "category": "constraint",
    },
    {
        "instruction": "What is the trichromatic clustering signature?",
        "output": "Attacks cluster tightly in trichromatic color space (std=12.3). Benign inputs are diverse (std=20.1). This is an emergent signature — not predicted by the math or designed into the system. It appears because adversarial inputs optimize for a specific target (low variance = all aiming at same goal) while benign inputs have natural diversity. The trichromatic encoding (mapping 6-tongue vectors to RGB via spectral bands) makes this visible as color clustering.",
        "tongues_active": ["UM", "RU"],
        "category": "axiom",
    },
]


def generate():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    all_tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
    timestamp = datetime.now(timezone.utc).isoformat()

    records = []
    for item in L0_RECORDS:
        active = item["tongues_active"]
        null = [t for t in all_tongues if t not in active]

        record = {
            "instruction": item["instruction"],
            "output": item["output"],
            "tongue": active[0],
            "tongues_active": active,
            "tongues_null": null,
            "layer": "L0",
            "category": item["category"],
            "view_type": "null-heavy" if len(null) >= 4 else "partial" if len(null) >= 2 else "full",
            "governance": "ALLOW",
            "source": "l0_substrate_generator",
            "timestamp": timestamp,
        }
        records.append(record)

    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=True) + "\n")

    print(f"Generated {len(records)} L0 substrate records")
    print(f"Output: {OUTPUT}")

    # Stats
    categories = {}
    for r in records:
        cat = r["category"]
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\nBy category:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    view_types = {}
    for r in records:
        vt = r["view_type"]
        view_types[vt] = view_types.get(vt, 0) + 1

    print(f"\nBy view type:")
    for vt, count in sorted(view_types.items()):
        print(f"  {vt}: {count}")

    avg_null = sum(len(r["tongues_null"]) for r in records) / len(records)
    print(f"\nAvg null tongues per record: {avg_null:.1f}")


if __name__ == "__main__":
    generate()
