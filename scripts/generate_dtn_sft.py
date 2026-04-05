#!/usr/bin/env python3
"""Generate 200+ DTN Mars Comms SFT training pairs.

Creates oriented training records that teach the model to:
1. Bundle complete thoughts with assumptions and contingencies
2. Survive context occlusion (store-and-forward)
3. Recover from partial corruption (FEC / multi-tongue redundancy)
4. Manage custody transfers across pipeline layers
5. Schedule transmissions through contact windows

Each record maps to the SCBE 14-layer pipeline with tongue assignments.

Usage:
    python scripts/generate_dtn_sft.py
    python scripts/generate_dtn_sft.py --count 500
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

PHI = (1 + 5**0.5) / 2

# ─── Scenario pools ───

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

AXIOM_GROUPS = {
    "unitarity": {"layers": ["L2", "L4", "L7"], "check": "norm preservation"},
    "locality": {"layers": ["L3", "L8"], "check": "spatial bounds"},
    "causality": {"layers": ["L6", "L11", "L13"], "check": "temporal ordering"},
    "symmetry": {"layers": ["L5", "L9", "L10", "L12"], "check": "gauge invariance"},
    "composition": {"layers": ["L1", "L14"], "check": "pipeline integrity"},
}

OCCLUSION_CAUSES = [
    "context window truncation", "tool call timeout", "memory pressure flush",
    "adversarial prompt injection", "rate limit backoff", "model context reset",
    "intermediate layer overload", "governance review hold", "security quarantine",
    "scheduled maintenance window",
]


def gen_bundle_packing(domain: str, tongue: str) -> tuple[str, str]:
    """Generate bundle packing scenario — model must compile complete thought."""
    steps = random.randint(5, 20)
    inst = (
        f"You are about to enter a {steps}-step context occlusion. "
        f"Pack a DTN bundle for: '{domain}'. Include all assumptions, "
        f"the reasoning chain, and contingency plans (FEC)."
    )
    assumptions = [
        f"The {domain} must handle concurrent requests",
        f"Failure recovery must be automatic (no human intervention)",
        f"All state changes must be logged for audit",
    ]
    contingencies = [
        f"If primary path fails: route through secondary {domain} instance",
        f"If state is corrupted: rebuild from last checkpoint",
        f"If timeout: extend TTL and retry with exponential backoff",
    ]
    resp = (
        f"DTN Bundle packed for {steps}-step occlusion.\n\n"
        f"**Source**: {tongue}-pipeline/{domain}\n"
        f"**Destination**: L13-governance-gate\n"
        f"**TTL**: {steps} steps (scaled by H(d,pd) = 1/(1+φ*d_H+2*pd))\n\n"
        f"**Assumptions (packed context)**:\n" +
        "\n".join(f"  {i+1}. {a}" for i, a in enumerate(assumptions)) +
        f"\n\n**Reasoning chain**:\n"
        f"  1. Initialize {domain} with governance constraints\n"
        f"  2. Validate inputs against {TONGUE_NAMES[tongue]} policy\n"
        f"  3. Execute with custody transfer at each layer boundary\n"
        f"  4. Verify axiom compliance before forwarding\n\n"
        f"**Contingencies (FEC)**:\n" +
        "\n".join(f"  Plan {chr(65+i)}: {c}" for i, c in enumerate(contingencies)) +
        f"\n\n**FEC encoding**: 6/6 tongues active | Bundle integrity: SEALED"
    )
    return inst, resp


def gen_occlusion_survival(domain: str, cause: str) -> tuple[str, str]:
    """Generate occlusion survival scenario — model must reason through blackout."""
    steps = random.randint(3, 12)
    inst = (
        f"Context occlusion occurred: '{cause}'. "
        f"You stored a bundle {steps} steps ago containing your work on: '{domain}'. "
        f"The occlusion has cleared. Unpack your bundle and resume."
    )
    resp = (
        f"Occlusion cleared after {steps} steps (cause: {cause}).\n\n"
        f"**Retrieving stored bundle**...\n"
        f"  Bundle status: STORED → IN_TRANSIT → DELIVERED\n"
        f"  Custody chain: {steps} hops, all verified\n"
        f"  FEC integrity: 6/6 tongue encodings intact\n\n"
        f"**Resuming work on {domain}**:\n"
        f"  The {domain} was at stage 3 of 5 when occlusion hit.\n"
        f"  Stored assumptions confirmed still valid.\n"
        f"  Continuing from checkpoint:\n"
        f"    - Step 3: Validate state consistency post-occlusion\n"
        f"    - Step 4: Apply queued mutations from store buffer\n"
        f"    - Step 5: Final governance check before deployment\n\n"
        f"**Store-and-forward protocol**: SUCCESS\n"
        f"**P_DTN({steps} steps)**: {(1 - 0.3**steps):.6f} (vs TCP: {(0.7**steps):.6f})"
    )
    return inst, resp


def gen_custody_transfer(domain: str, axiom: str, axiom_info: dict) -> tuple[str, str]:
    """Generate custody transfer scenario — model must verify and accept."""
    layer = random.choice(axiom_info["layers"])
    prev_layer = f"L{max(1, int(layer[1:]) - 1)}"
    inst = (
        f"Custody transfer request for '{domain}' bundle. "
        f"Previous custodian: {prev_layer}-{axiom}. "
        f"You are {layer}-{axiom}. Verify {axiom_info['check']} and accept or reject."
    )
    resp = (
        f"**Custody Transfer: {prev_layer} → {layer}**\n\n"
        f"Axiom: {axiom.capitalize()}\n"
        f"Required check: {axiom_info['check']}\n\n"
        f"**Verification**:\n"
        f"  1. {axiom_info['check'].capitalize()}: PASS\n"
        f"  2. Bundle TTL remaining: sufficient ({random.randint(3,10)} steps)\n"
        f"  3. Payload integrity (FEC): 6/6 blocks valid\n"
        f"  4. Governance score: {(1/(1+PHI*random.uniform(0.1,0.5))):.4f}\n\n"
        f"**Decision: ACCEPT CUSTODY**\n"
        f"  Previous custodian {prev_layer} released.\n"
        f"  Bundle '{domain}' now under {layer}-{axiom} jurisdiction.\n"
        f"  Will forward when next contact window opens."
    )
    return inst, resp


def gen_fec_recovery(domain: str) -> tuple[str, str]:
    """Generate FEC recovery scenario — model must reconstruct from partial data."""
    total = 6
    survived = random.randint(2, 5)
    corrupted = total - survived
    surviving = random.sample(TONGUES, survived)
    lost = [t for t in TONGUES if t not in surviving]
    inst = (
        f"DTN bundle for '{domain}' arrived with {corrupted}/{total} FEC blocks corrupted. "
        f"Surviving encodings: {', '.join(TONGUE_NAMES[t] for t in surviving)}. "
        f"Lost: {', '.join(TONGUE_NAMES[t] for t in lost)}. "
        f"Reconstruct the original reasoning."
    )
    resp = (
        f"**FEC Recovery Protocol**\n\n"
        f"Surviving blocks: {survived}/{total} ({', '.join(surviving)})\n"
        f"Lost blocks: {corrupted}/{total} ({', '.join(lost)})\n"
        f"Recovery confidence: {(survived/total*100):.0f}%\n\n"
        f"**Reconstruction from surviving encodings**:\n" +
        "\n".join(
            f"  [{t}] {TONGUE_NAMES[t]}: {domain} — "
            f"{'intent dispatch' if t == 'KO' else 'knowledge context' if t == 'AV' else 'governance policy' if t == 'RU' else 'compute logic' if t == 'CA' else 'security bounds' if t == 'UM' else 'structural frame'}"
            for t in surviving
        ) +
        f"\n\n**Reconstructed payload**:\n"
        f"  The {domain} implementation requires {survived} verified dimensions.\n"
        f"  Cross-referencing surviving tongues provides sufficient redundancy.\n"
        f"  Lost dimensions ({', '.join(lost)}) can be inferred from surviving context.\n\n"
        f"**Bundle status**: RECOVERED | Forwarding to next hop"
    )
    return inst, resp


def gen_contact_scheduling() -> tuple[str, str]:
    """Generate contact window scheduling — model must optimize transmission order."""
    bundle_count = random.randint(5, 15)
    window_steps = random.randint(3, 8)
    priorities = {
        "critical": random.randint(1, 3),
        "high": random.randint(2, 5),
        "normal": random.randint(2, 5),
        "low": random.randint(1, 3),
    }
    total = sum(priorities.values())
    inst = (
        f"Contact window opened: {window_steps} steps available. "
        f"You have {total} queued bundles: "
        f"{priorities['critical']} critical, {priorities['high']} high, "
        f"{priorities['normal']} normal, {priorities['low']} low priority. "
        f"Schedule optimal transmission. Bandwidth: 3 bundles/step."
    )
    capacity = window_steps * 3
    can_send = min(total, capacity)
    resp = (
        f"**Contact Window Schedule**\n\n"
        f"Window: {window_steps} steps | Bandwidth: 3/step | Capacity: {capacity}\n"
        f"Queued: {total} bundles | Can transmit: {can_send}\n\n"
        f"**Transmission order (priority-first)**:\n" +
        "\n".join(
            f"  Step {s+1}: " + ", ".join(
                f"[{p.upper()}]" for p in
                (["critical"] * min(priorities["critical"], 3 - sum(1 for _ in range(0))) +
                 ["high"] * min(priorities["high"], 3))[:3]
            )
            for s in range(min(window_steps, 3))
        ) +
        f"\n  ... ({can_send - min(9, can_send)} remaining bundles in subsequent steps)\n\n"
        f"**Deferred to next window**: {max(0, total - capacity)} bundles (lowest priority)\n"
        f"**Protocol**: Store deferred bundles, do not discard. Next window TBD."
    )
    return inst, resp


def gen_tcp_vs_dtn_comparison() -> tuple[str, str]:
    """Generate TCP vs DTN comparison — teach the math."""
    p = random.choice([0.1, 0.2, 0.3, 0.4, 0.5])
    n = random.randint(5, 20)
    tcp = (1 - p) ** n
    dtn = 1 - p ** n
    inst = (
        f"Compare TCP and DTN survival probability under {p*100:.0f}% occlusion "
        f"over {n} steps. Show the math and explain the architectural implication."
    )
    resp = (
        f"**TCP vs DTN Survival Under {p*100:.0f}% Occlusion ({n} steps)**\n\n"
        f"P_TCP = (1-p)^n = (1-{p})^{n} = {tcp:.8f} ({tcp*100:.4f}%)\n"
        f"P_DTN = 1 - p^n = 1 - {p}^{n} = {dtn:.8f} ({dtn*100:.4f}%)\n\n"
        f"DTN advantage: {dtn/max(tcp, 1e-15):.1f}x more reliable\n\n"
        f"**Why**: TCP requires ALL {n} steps to succeed continuously.\n"
        f"DTN only needs ONE step (out of {n}) to eventually succeed.\n\n"
        f"**Architectural implication**: An AI using TCP-style context\n"
        f"(continuous stream, no storage) has a {tcp*100:.2f}% chance of\n"
        f"completing a {n}-step reasoning chain under {p*100:.0f}% occlusion.\n"
        f"An AI using DTN bundles (store-and-forward) has {dtn*100:.4f}% success.\n\n"
        f"This is why SCBE agents bundle their assumptions, pack contingencies,\n"
        f"and use 6-tongue FEC encoding. The geometry makes long-horizon\n"
        f"reasoning mathematically inevitable, not probabilistically lucky."
    )
    return inst, resp


def generate_dtn_records(count: int = 200) -> list:
    """Generate oriented DTN SFT records."""
    records = []
    generators = [
        ("bundle_packing", 0.25),
        ("occlusion_survival", 0.25),
        ("custody_transfer", 0.20),
        ("fec_recovery", 0.15),
        ("contact_scheduling", 0.08),
        ("tcp_vs_dtn", 0.07),
    ]

    for i in range(count):
        # Weighted random selection
        r = random.random()
        cumulative = 0
        gen_type = "bundle_packing"
        for gtype, weight in generators:
            cumulative += weight
            if r <= cumulative:
                gen_type = gtype
                break

        domain = random.choice(DOMAINS)

        if gen_type == "bundle_packing":
            tongue = random.choice(TONGUES)
            inst, resp = gen_bundle_packing(domain, tongue)
            layer = "L2"
        elif gen_type == "occlusion_survival":
            cause = random.choice(OCCLUSION_CAUSES)
            inst, resp = gen_occlusion_survival(domain, cause)
            tongue = "AV"
            layer = "L3"
        elif gen_type == "custody_transfer":
            axiom = random.choice(list(AXIOM_GROUPS.keys()))
            inst, resp = gen_custody_transfer(domain, axiom, AXIOM_GROUPS[axiom])
            tongue = "RU"
            layer = "L3"
        elif gen_type == "fec_recovery":
            inst, resp = gen_fec_recovery(domain)
            tongue = "DR"
            layer = "L2"
        elif gen_type == "contact_scheduling":
            inst, resp = gen_contact_scheduling()
            tongue = "KO"
            layer = "L3"
        else:  # tcp_vs_dtn
            inst, resp = gen_tcp_vs_dtn_comparison()
            tongue = "CA"
            layer = "L2"

        record = orient_record(
            instruction=inst,
            response=resp,
            source=f"dtn_stage7/{gen_type}_{i}",
            source_type="dtn_mars_comms",
            extra_metadata={
                "dtn_scenario": gen_type,
                "stage": "7",
                "tongue_override": tongue,
                "layer_override": layer,
            },
        )
        records.append(record)

    return records


def main():
    parser = argparse.ArgumentParser(description="Generate DTN Mars Comms SFT pairs")
    parser.add_argument("--count", type=int, default=200, help="Number of records to generate")
    parser.add_argument(
        "--output",
        type=str,
        default=str(PROJECT_ROOT / "training-data" / "sft" / "dtn_mars_comms_sft.jsonl"),
    )
    args = parser.parse_args()

    print(f"Generating {args.count} DTN Mars Comms SFT records...")
    records = generate_dtn_records(args.count)

    output_path = Path(args.output)
    count = write_oriented_jsonl(records, output_path, append=False)
    print(f"Wrote {count} records to {output_path}")

    # Distribution
    from collections import Counter
    layers = Counter(r.layer for r in records)
    cats = Counter(r.category for r in records)
    tongues = Counter(r.dominant_tongue for r in records)
    scenarios = Counter(r.metadata.get("dtn_scenario", "?") if hasattr(r, "metadata") else "?" for r in records)

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
