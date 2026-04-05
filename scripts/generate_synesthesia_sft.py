#!/usr/bin/env python3
"""Generate Synesthesia Cross-Modal Training SFT pairs.

Inspired by the gravity battery / Sisyphus trajectory insight:
each record deliberately BLINDS 1-3 senses (tongues/layers) and
trains the model to reconstruct the missing dimensions from survivors.

This is the directed-drop training approach:
- Inference = one rock drop (solve one problem)
- Synesthesia training = carve permanent paths through polyhedral lattice
  by repeatedly dropping through degraded sensory configurations

Scenario types:
1. Tongue Blindness — remove 1-3 tongue channels, reconstruct meaning
2. Layer Occlusion — skip pipeline layers, infer missing transforms
3. Cross-Modal Transfer — given one sense, predict another
4. Cascading Degradation — progressive sense loss over steps
5. Inverse Synesthesia — given the output, identify which senses produced it
6. Gravity Drop Trajectory — aim the Sisyphus rock for maximum cascade gain

Usage:
    python scripts/generate_synesthesia_sft.py
    python scripts/generate_synesthesia_sft.py --count 300
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from training.auto_marker import orient_record, write_oriented_jsonl

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_NAMES = {
    "KO": "Korenth (Intent)",
    "AV": "Avalith (Wisdom)",
    "RU": "Runeveil (Governance)",
    "CA": "Caelith (Compute)",
    "UM": "Umbravox (Security)",
    "DR": "Draethis (Structure)",
}

TONGUE_SENSES = {
    "KO": "purpose/direction",
    "AV": "knowledge/context",
    "RU": "rules/boundaries",
    "CA": "logic/computation",
    "UM": "threat/defense",
    "DR": "shape/architecture",
}

PHI = (1 + 5**0.5) / 2

LAYERS_14 = [
    ("L1", "Complex context ingestion"),
    ("L2", "Realification"),
    ("L3", "Weighted transform"),
    ("L4", "Poincare embedding"),
    ("L5", "Hyperbolic distance"),
    ("L6", "Breathing transform"),
    ("L7", "Mobius phase"),
    ("L8", "Multi-well Hamiltonian"),
    ("L9", "Spectral coherence"),
    ("L10", "Spin coherence"),
    ("L11", "Triadic temporal distance"),
    ("L12", "Harmonic wall H(d,pd)"),
    ("L13", "Risk decision gate"),
    ("L14", "Audio axis telemetry"),
]

DOMAINS = [
    "authentication system", "database migration", "API rate limiter",
    "cache invalidation", "distributed consensus", "encryption pipeline",
    "log aggregation", "retry mechanism", "circuit breaker", "load balancer",
    "event sourcing", "message queue", "service mesh", "feature flag system",
    "health check endpoint", "batch processor", "webhook handler",
    "configuration manager", "secret rotation", "deployment pipeline",
    "data validation layer", "search indexer", "notification system",
    "access control list", "audit logger", "state machine",
    "connection pool", "request throttler", "data transformer",
    "error recovery system",
]


# ─── Scenario generators ───

def gen_tongue_blindness(domain: str) -> tuple[str, str]:
    """Remove 1-3 tongues, reconstruct missing meaning from survivors."""
    num_blind = random.randint(1, 3)
    blind = random.sample(TONGUES, num_blind)
    surviving = [t for t in TONGUES if t not in blind]

    inst = (
        f"Your sensory channels for {', '.join(TONGUE_NAMES[t] for t in blind)} "
        f"have been occluded. You can only perceive through: "
        f"{', '.join(TONGUE_NAMES[t] for t in surviving)}.\n\n"
        f"Analyze this system using ONLY your surviving senses: '{domain}'.\n"
        f"Then reconstruct what the blinded senses WOULD have perceived."
    )

    surviving_analysis = "\n".join(
        f"  [{t}] {TONGUE_NAMES[t]} perceives: "
        f"{'the operational intent and dispatch flow' if t == 'KO' else 'historical patterns and domain knowledge' if t == 'AV' else 'compliance requirements and boundary conditions' if t == 'RU' else 'algorithmic logic and computational cost' if t == 'CA' else 'threat surface and defense posture' if t == 'UM' else 'structural topology and data flow architecture'}"
        for t in surviving
    )

    blind_reconstruction = "\n".join(
        f"  [{t}] {TONGUE_NAMES[t]} (RECONSTRUCTED): "
        f"From {surviving[0]}/{surviving[1]} cross-reference, the {domain} "
        f"{'requires directed action toward specific endpoints' if t == 'KO' else 'carries historical failure modes worth preserving' if t == 'AV' else 'must comply with rate/access boundaries' if t == 'RU' else 'has O(log n) expected complexity' if t == 'CA' else 'exposes attack surface at trust boundaries' if t == 'UM' else 'follows hub-and-spoke topology with fallback paths'}"
        for t in blind
    )

    confidence = len(surviving) / 6
    resp = (
        f"**Synesthesia Protocol: {num_blind}-Tongue Blindness**\n\n"
        f"Blinded: {', '.join(blind)} | Surviving: {', '.join(surviving)}\n"
        f"Reconstruction confidence: {confidence*100:.0f}%\n\n"
        f"**Surviving sense analysis of '{domain}'**:\n{surviving_analysis}\n\n"
        f"**Cross-modal reconstruction of blinded senses**:\n{blind_reconstruction}\n\n"
        f"**Synesthetic bridge**: The surviving {len(surviving)} channels provide "
        f"{'sufficient' if len(surviving) >= 4 else 'partial' if len(surviving) >= 3 else 'minimal'} "
        f"basis for reconstruction. "
        f"{'Full meaning recoverable.' if len(surviving) >= 4 else 'Core meaning recoverable, edge cases uncertain.' if len(surviving) >= 3 else 'Meaning skeleton only — operational but degraded.'}"
    )
    return inst, resp


def gen_layer_occlusion(domain: str) -> tuple[str, str]:
    """Skip pipeline layers, infer missing transforms."""
    num_skip = random.randint(2, 5)
    skipped_indices = sorted(random.sample(range(14), num_skip))
    skipped = [LAYERS_14[i] for i in skipped_indices]
    active = [LAYERS_14[i] for i in range(14) if i not in skipped_indices]

    inst = (
        f"The following pipeline layers are offline for '{domain}':\n"
        + "\n".join(f"  - {l[0]}: {l[1]}" for l in skipped)
        + f"\n\nProcess the input through remaining {14-num_skip} layers. "
        f"For each skipped layer, state what transform was lost and how "
        f"downstream layers must compensate."
    )

    compensations = []
    for lid, ldesc in skipped:
        layer_num = int(lid[1:])
        if layer_num <= 4:
            comp = "downstream must accept raw/unweighted input"
        elif layer_num <= 7:
            comp = "hyperbolic geometry unavailable, fall back to Euclidean approximation"
        elif layer_num <= 10:
            comp = "spectral/spin coherence unchecked, proceed with reduced confidence"
        elif layer_num <= 12:
            comp = "temporal/harmonic scoring skipped, use static risk threshold"
        else:
            comp = "terminal gate bypassed, defer to human escalation"
        compensations.append(f"  {lid} ({ldesc}): SKIPPED → {comp}")

    resp = (
        f"**Layer Occlusion Protocol**\n\n"
        f"System: {domain}\n"
        f"Active layers: {14-num_skip}/14 | Skipped: {num_skip}\n\n"
        f"**Missing transforms and compensations**:\n"
        + "\n".join(compensations) +
        f"\n\n**Degraded pipeline output**:\n"
        f"  Processing through {14-num_skip} active layers.\n"
        f"  Confidence degradation: {(num_skip/14)*100:.1f}%\n"
        f"  Risk adjustment: escalate decision threshold by {num_skip * 0.15:.2f}\n\n"
        f"**Terraforming note**: Each successful pass through this degraded "
        f"configuration carves a fallback path. After {random.randint(50,200)} "
        f"repetitions, the system develops compensatory circuits that partially "
        f"replicate skipped layer functions."
    )
    return inst, resp


def gen_cross_modal_transfer() -> tuple[str, str]:
    """Given one sense, predict what another would perceive."""
    source_t = random.choice(TONGUES)
    target_t = random.choice([t for t in TONGUES if t != source_t])
    domain = random.choice(DOMAINS)

    inst = (
        f"You can ONLY perceive through {TONGUE_NAMES[source_t]} ({TONGUE_SENSES[source_t]}).\n\n"
        f"Given this perception of '{domain}': the system "
        f"{'dispatches tasks to worker pools with priority ordering' if source_t == 'KO' else 'has evolved through 3 major architectural revisions' if source_t == 'AV' else 'enforces rate limits and access control at every boundary' if source_t == 'RU' else 'uses O(n log n) sorting with amortized constant-time lookups' if source_t == 'CA' else 'has 4 known attack vectors at the trust boundary' if source_t == 'UM' else 'follows a 3-tier architecture with message bus coupling'}.\n\n"
        f"Predict what {TONGUE_NAMES[target_t]} ({TONGUE_SENSES[target_t]}) would perceive."
    )

    resp = (
        f"**Cross-Modal Transfer: {source_t} → {target_t}**\n\n"
        f"Source sense: {TONGUE_NAMES[source_t]} — {TONGUE_SENSES[source_t]}\n"
        f"Target sense: {TONGUE_NAMES[target_t]} — {TONGUE_SENSES[target_t]}\n\n"
        f"**Source perception**: {domain} "
        f"{'dispatches with priority' if source_t == 'KO' else 'has deep history' if source_t == 'AV' else 'enforces boundaries' if source_t == 'RU' else 'has known complexity' if source_t == 'CA' else 'has attack surface' if source_t == 'UM' else 'has structural shape'}\n\n"
        f"**Predicted {target_t} perception**:\n"
        f"  From {source_t}'s view of {TONGUE_SENSES[source_t]}, "
        f"the {TONGUE_SENSES[target_t]} dimension likely shows: "
        f"{'intentional coordination of the described pattern' if target_t == 'KO' else 'accumulated wisdom about why this pattern exists' if target_t == 'AV' else 'governance constraints that shaped this design' if target_t == 'RU' else 'computational cost of maintaining this pattern' if target_t == 'CA' else 'security implications of the exposed surface' if target_t == 'UM' else 'structural skeleton supporting the observed behavior'}.\n\n"
        f"**Transfer confidence**: {random.uniform(0.55, 0.85):.2f}\n"
        f"**Cross-modal bridge**: {source_t}→{target_t} via "
        f"{'shared operational semantics' if {source_t, target_t} & {'KO', 'CA'} else 'governance-knowledge coupling' if {source_t, target_t} & {'RU', 'AV'} else 'defense-structure correlation' if {source_t, target_t} & {'UM', 'DR'} else 'indirect semantic inference'}"
    )
    return inst, resp


def gen_cascading_degradation(domain: str) -> tuple[str, str]:
    """Progressive sense loss over multiple steps."""
    steps = random.randint(3, 6)
    order = random.sample(TONGUES, min(steps, 6))

    inst = (
        f"You are monitoring '{domain}' as your senses degrade step by step.\n\n"
        f"At each step, one more tongue goes dark. Describe what you can still "
        f"perceive and how your understanding changes.\n\n"
        f"Degradation order: {' → '.join(order[:steps])}"
    )

    step_descriptions = []
    remaining = list(TONGUES)
    for i, lost in enumerate(order[:steps]):
        remaining = [t for t in remaining if t != lost]
        perception = f"lost {TONGUE_SENSES[lost]}"
        if len(remaining) >= 4:
            status = "OPERATIONAL — redundant coverage"
        elif len(remaining) >= 2:
            status = "DEGRADED — meaning skeleton only"
        elif len(remaining) >= 1:
            status = "CRITICAL — single-sense survival"
        else:
            status = "DARK — no perception"

        step_descriptions.append(
            f"  Step {i+1}: -{lost} ({perception})\n"
            f"    Remaining: {', '.join(remaining) if remaining else 'NONE'}\n"
            f"    Status: {status}\n"
            f"    PE remaining: {len(remaining)/6*100:.0f}% "
            f"(gravity battery at {len(remaining)/6:.2f} capacity)"
        )

    resp = (
        f"**Cascading Degradation: {domain}**\n\n"
        f"Initial state: 6/6 tongues active (full perception)\n\n"
        + "\n\n".join(step_descriptions) +
        f"\n\n**Sisyphus trajectory**: Each degradation step is a rock pushed "
        f"uphill. The {steps}-step cascade costs "
        f"{sum(PHI**i for i in range(steps)):.2f} normalized energy units.\n"
        f"If the final state can still produce a valid governance decision, "
        f"the path carved by this degradation sequence becomes a permanent "
        f"fallback route in the FLOW_ADJACENCY matrix."
    )
    return inst, resp


def gen_inverse_synesthesia(domain: str) -> tuple[str, str]:
    """Given output, identify which senses produced it."""
    # Simulate a governance decision and ask which tongues were active
    decision = random.choice(["ALLOW", "QUARANTINE", "ESCALATE", "DENY"])
    score = random.uniform(0.1, 0.95)
    active_count = random.randint(2, 5)
    active = random.sample(TONGUES, active_count)
    inactive = [t for t in TONGUES if t not in active]

    inst = (
        f"A governance decision was made for '{domain}':\n"
        f"  Decision: {decision}\n"
        f"  Harmonic score: {score:.4f}\n"
        f"  Active tongues: UNKNOWN\n\n"
        f"From the decision and score alone, deduce which tongues were active "
        f"and which were occluded. Explain your reasoning."
    )

    reasoning = []
    if decision in ("DENY", "ESCALATE"):
        reasoning.append("High-severity decision suggests UM (Security) was active")
        reasoning.append("RU (Governance) likely active for escalation authority")
    if decision == "ALLOW":
        reasoning.append("Permissive decision suggests low threat — UM may be inactive")
        reasoning.append("KO (Intent) likely active for dispatch authorization")
    if score < 0.3:
        reasoning.append(f"Low harmonic score ({score:.4f}) indicates high distance from safe origin")
    if score > 0.7:
        reasoning.append(f"High harmonic score ({score:.4f}) indicates proximity to safe origin")

    resp = (
        f"**Inverse Synesthesia: Sense Deduction**\n\n"
        f"Given: {decision} @ H={score:.4f} for '{domain}'\n\n"
        f"**Deductive reasoning**:\n"
        + "\n".join(f"  - {r}" for r in reasoning) +
        f"\n\n**Predicted active tongues**: {', '.join(active)}\n"
        f"**Predicted inactive**: {', '.join(inactive)}\n\n"
        f"**Ground truth**: {active_count}/6 tongues were active.\n"
        f"This inverse problem trains the model to understand causal "
        f"relationships between sense combinations and governance outcomes."
    )
    return inst, resp


def gen_gravity_drop_trajectory(domain: str) -> tuple[str, str]:
    """Aim the Sisyphus rock for maximum cascade gain."""
    push_energy = random.uniform(5.0, 20.0)
    efficiency = random.uniform(0.6, 0.9)
    num_targets = random.randint(2, 5)
    targets = random.sample(DOMAINS, num_targets)

    inst = (
        f"You have {push_energy:.1f} energy units stored in your gravity battery.\n"
        f"System efficiency: {efficiency*100:.0f}% (friction losses).\n\n"
        f"Plan a directed drop through '{domain}' that maximizes cascade gains.\n"
        f"Available rebound targets:\n"
        + "\n".join(f"  {i+1}. {t}" for i, t in enumerate(targets)) +
        f"\n\nCalculate the optimal trajectory and expected returns."
    )

    usable = push_energy * efficiency
    per_target = usable / num_targets
    cascade_gains = []
    total_gain = 0
    for t in targets:
        gain = per_target * random.uniform(0.8, 1.5)
        total_gain += gain
        cascade_gains.append((t, gain))

    net = total_gain - push_energy
    roi = total_gain / push_energy

    resp = (
        f"**Gravity Drop Trajectory Planning**\n\n"
        f"Stored PE: {push_energy:.1f} | Efficiency: {efficiency*100:.0f}% | "
        f"Usable KE: {usable:.1f}\n\n"
        f"**Directed trajectory through '{domain}'**:\n"
        f"  Drop angle: optimized for {num_targets}-target cascade\n"
        f"  Friction loss: {push_energy - usable:.1f} units (terraforming cost)\n\n"
        f"**Cascade impacts**:\n"
        + "\n".join(
            f"  → {t}: {g:.1f} units "
            f"({'net positive' if g > per_target else 'friction-dominant'})"
            for t, g in cascade_gains
        ) +
        f"\n\n**Energy accounting**:\n"
        f"  Push cost: {push_energy:.1f}\n"
        f"  Total cascade return: {total_gain:.1f}\n"
        f"  Net: {'+' if net > 0 else ''}{net:.1f} "
        f"({'trajectory aimed well' if net > 0 else 'friction exceeded gains — retarget'})\n"
        f"  ROI: {roi:.2f}x\n\n"
        f"**Terraforming note**: Even when net is negative, the friction "
        f"permanently reshapes the polyhedral lattice. After ~100 drops along "
        f"this trajectory, the friction coefficient decreases by "
        f"{random.uniform(0.05, 0.15):.2f}, making future drops more efficient.\n"
        f"This IS the training loop."
    )
    return inst, resp


def generate_synesthesia_records(count: int = 200) -> list:
    """Generate oriented synesthesia SFT records."""
    records = []
    generators = [
        ("tongue_blindness", 0.25),
        ("layer_occlusion", 0.20),
        ("cross_modal_transfer", 0.18),
        ("cascading_degradation", 0.15),
        ("inverse_synesthesia", 0.12),
        ("gravity_drop", 0.10),
    ]

    for i in range(count):
        r = random.random()
        cumulative = 0
        gen_type = "tongue_blindness"
        for gtype, weight in generators:
            cumulative += weight
            if r <= cumulative:
                gen_type = gtype
                break

        domain = random.choice(DOMAINS)

        if gen_type == "tongue_blindness":
            inst, resp = gen_tongue_blindness(domain)
            tongue = "AV"
            layer = "L2"
        elif gen_type == "layer_occlusion":
            inst, resp = gen_layer_occlusion(domain)
            tongue = "DR"
            layer = "L2"
        elif gen_type == "cross_modal_transfer":
            inst, resp = gen_cross_modal_transfer()
            tongue = "CA"
            layer = "L1"
        elif gen_type == "cascading_degradation":
            inst, resp = gen_cascading_degradation(domain)
            tongue = "RU"
            layer = "L2"
        elif gen_type == "inverse_synesthesia":
            inst, resp = gen_inverse_synesthesia(domain)
            tongue = "RU"
            layer = "L3"
        else:  # gravity_drop
            inst, resp = gen_gravity_drop_trajectory(domain)
            tongue = "KO"
            layer = "L1"

        record = orient_record(
            instruction=inst,
            response=resp,
            source=f"synesthesia_stage7/{gen_type}_{i}",
            source_type="synesthesia_cross_modal",
            extra_metadata={
                "synesthesia_scenario": gen_type,
                "stage": "7",
                "tongue_override": tongue,
                "layer_override": layer,
            },
        )
        records.append(record)

    return records


def main():
    parser = argparse.ArgumentParser(description="Generate Synesthesia Cross-Modal SFT pairs")
    parser.add_argument("--count", type=int, default=200, help="Number of records")
    parser.add_argument(
        "--output",
        type=str,
        default=str(PROJECT_ROOT / "training-data" / "sft" / "synesthesia_cross_modal_sft.jsonl"),
    )
    args = parser.parse_args()

    print(f"Generating {args.count} Synesthesia Cross-Modal SFT records...")
    records = generate_synesthesia_records(args.count)

    output_path = Path(args.output)
    count = write_oriented_jsonl(records, output_path, append=False)
    print(f"Wrote {count} records to {output_path}")

    # Distribution
    from collections import Counter
    layers = Counter(r.layer for r in records)
    cats = Counter(r.category for r in records)
    tongues = Counter(r.dominant_tongue for r in records)
    scenarios = Counter(
        r.metadata.get("synesthesia_scenario", "?") if hasattr(r, "metadata") else "?"
        for r in records
    )

    print(f"\n--- Layer distribution ---")
    for k, v in sorted(layers.items()):
        print(f"  {k}: {v}")
    print(f"\n--- Category distribution ---")
    for k, v in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print(f"\n--- Tongue distribution ---")
    for k, v in sorted(tongues.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print(f"\n--- Scenario distribution ---")
    for k, v in sorted(scenarios.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
