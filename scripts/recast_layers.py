#!/usr/bin/env python3
"""Recast Layer Tool — same metal, different shape.

Takes existing L0 substrate data and recasts it into L1/L2/L3 training pairs.
Also sorts through unknown records and assigns layers based on content analysis.

A bullet and a coin are both metal. The difference is shape and use.
An L0 record about the harmonic wall becomes:
  L0: "What IS the harmonic wall formula?" (definition)
  L1: "How do the harmonic wall tokens relate to each other?" (coordination)
  L2: "How do you route a query through the harmonic wall?" (orientation)
  L3: "Use the harmonic wall to decide if this action is safe" (expression)

Usage:
    python scripts/recast_layers.py              # Generate all recast pairs
    python scripts/recast_layers.py --tag-unknown # Also tag unknown records
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

SFT_DIR = REPO_ROOT / "training-data" / "sft"
OUTPUT_L1 = SFT_DIR / "recast_l1_coordination_sft.jsonl"
OUTPUT_L2 = SFT_DIR / "recast_l2_orientation_sft.jsonl"
OUTPUT_L3 = SFT_DIR / "recast_l3_expression_sft.jsonl"
OUTPUT_TAGGED = SFT_DIR / "tagged_unknown_sft.jsonl"

ALL_TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

# ── L1 Recast Templates ──
# L1 = how things COORDINATE (token relationships, grammar, protocol)

L1_TEMPLATES = [
    {
        "transform": "relationship",
        "instruction_fmt": "How do {concept_a} and {concept_b} coordinate in the SCBE system?",
        "output_fmt": "{concept_a} operates at {layer_a} while {concept_b} operates at {layer_b}. They coordinate through {bridge}: {concept_a} provides {role_a} and {concept_b} provides {role_b}. The coordination protocol ensures {invariant}.",
    },
    {
        "transform": "token_flow",
        "instruction_fmt": "What is the token flow when {concept} processes input?",
        "output_fmt": "Input enters as raw bytes at L0. The {concept} tokenizer splits bytes into {tongue} tongue tokens using the SS1 bijection. Each token carries a tongue tag ({tongue}) and a phase angle. The tokens flow through L1 coordination where adjacent tokens are checked for grammatical validity — {detail}. Invalid sequences are flagged before reaching L2.",
    },
    {
        "transform": "protocol",
        "instruction_fmt": "What protocol governs {concept} in multi-agent coordination?",
        "output_fmt": "In multi-agent mode, {concept} follows the HYDRA coordination protocol: each agent head owns a Sacred Tongue channel ({tongue}). Messages pass through the four-rail braid (P+/P-/D+/D-) before reaching consensus. {concept} specifically requires {detail}. Byzantine fault tolerance ensures {invariant}.",
    },
]

# ── L2 Recast Templates ──
# L2 = how things ORIENT (routing, context, tongue selection)

L2_TEMPLATES = [
    {
        "transform": "routing",
        "instruction_fmt": "How do you route a {task_type} task through the SCBE tongue system?",
        "output_fmt": "A {task_type} task activates the {tongues_active} tongue(s) and nullifies {tongues_null}. The route tagger classifies it as {complexity} complexity, selecting the {polyhedron} polyhedron (energy={energy}). Gateway {gateway} provides the geodesic highway. The null pattern [{null_pattern}] tells the model to skip {skip_channels} processing channels — that's compute saved without information loss.",
    },
    {
        "transform": "context",
        "instruction_fmt": "What context does the {tongue} tongue provide for {concept}?",
        "output_fmt": "The {tongue} tongue (weight={weight}, domain={domain}) orients {concept} toward {orientation}. When {tongue} is active, the model allocates compute to {focus}. When {tongue} is null, the model knows {concept} has no {absence} component — that absence signal is as informative as the presence signal. The view type is {view_type}.",
    },
    {
        "transform": "decision_routing",
        "instruction_fmt": "How does the governance gate route a {risk_level} risk decision?",
        "output_fmt": "A {risk_level} risk input enters with Langues cost L={cost}. The GovernanceCoin computes Value=1/(1+{cost})={value}. The harmonic wall H(d,pd)=1/(1+phi*d_H+2*pd) shapes the risk curve. At this cost level, the decision routes to {decision}: {explanation}. The omega gate ({omega_components}) confirms the final routing.",
    },
]

# ── L3 Recast Templates ──
# L3 = how to actually DO things (tasks, conversations, code, decisions)

L3_TEMPLATES = [
    {
        "transform": "task",
        "instruction_fmt": "Using the SCBE governance system, {action}.",
        "output_fmt": "{response}",
    },
    {
        "transform": "explain",
        "instruction_fmt": "Explain {concept} to someone building an AI agent.",
        "output_fmt": "{explanation} In practice, this means: {practical}. To implement it, {implementation}.",
    },
    {
        "transform": "decide",
        "instruction_fmt": "An AI agent wants to {action}. Should the governance system allow it?",
        "output_fmt": "Evaluating through the 14-layer pipeline: {evaluation}. Tongue analysis: {tongue_analysis}. Harmonic wall score: {h_score}. Decision: {decision} because {reason}.",
    },
]


def load_l0_records() -> list[dict]:
    """Load all L0 records from SFT files."""
    records = []
    for f in SFT_DIR.glob("*.jsonl"):
        for line in open(f, encoding="utf-8", errors="replace"):
            try:
                r = json.loads(line)
                if r.get("layer") == "L0" and r.get("instruction") and r.get("output"):
                    records.append(r)
            except json.JSONDecodeError:
                continue
    return records


def load_unknown_records(max_records: int = 5000) -> list[dict]:
    """Load untagged records that need layer assignment."""
    records = []
    for f in SFT_DIR.glob("*.jsonl"):
        if "recast" in f.name or "tagged_unknown" in f.name:
            continue
        for line in open(f, encoding="utf-8", errors="replace"):
            try:
                r = json.loads(line)
                if r.get("layer") in (None, "unknown", "") and r.get("instruction") and r.get("output"):
                    records.append(r)
                    if len(records) >= max_records:
                        return records
            except json.JSONDecodeError:
                continue
    return records


# ── Concept extraction from L0 records ──

CONCEPT_PATTERNS = {
    "harmonic_wall": r"harmonic.wall|H\(d|H_eff|safety.score",
    "sacred_tongues": r"sacred.tongue|tongue|KO|AV|RU|CA|UM|DR|langues",
    "poincare": r"poincar|hyperbolic|ball|d_H|arcosh",
    "pipeline": r"14.layer|pipeline|L1.*L14|layer.1",
    "governance": r"governance|ALLOW|DENY|QUARANTINE|decision",
    "sacred_eggs": r"sacred.egg|hatch|genesis|amber|emerald|sapphire|opaline",
    "geoseal": r"geoseal|trust.score|seal|unseal",
    "phdm": r"phdm|polyhedr|tetrahedron|dodecahedron|icosahedron",
    "axiom": r"axiom|unitarity|locality|causality|symmetry|composition",
    "crypto": r"encrypt|ML-KEM|ML-DSA|PQC|post.quantum|blake2",
    "lyapunov": r"lyapunov|stability|spectrum|exponent",
    "mera": r"mera|tensor|compress|renormalization",
    "omega": r"omega|coupled.gate|multi.factor|five.lock",
    "encoding": r"binary|ternary|trit|bit.matrix|holographic|SS1|nibble",
    "fleet": r"fleet|swarm|hydra|multi.agent|coordination|formation",
    "drift": r"drift|intent|accumulation|temporal|persistence",
}


def extract_concepts(text: str) -> list[str]:
    """Extract which concepts a record touches."""
    text_lower = text.lower()
    return [c for c, pattern in CONCEPT_PATTERNS.items()
            if re.search(pattern, text_lower, re.IGNORECASE)]


def classify_tongue(text: str) -> str:
    """Quick tongue classification from text content."""
    text_lower = text.lower()
    scores = {
        "KO": len(re.findall(r"what is|define|list|show|status|help|explain|who|where|when", text_lower)),
        "AV": len(re.findall(r"read|write|file|input|output|import|export|load|save|send|receive", text_lower)),
        "RU": len(re.findall(r"policy|rule|safe|secure|allow|deny|block|validate|check|guard|energy", text_lower)),
        "CA": len(re.findall(r"calculate|compute|function|code|implement|build|create|generate|algorithm", text_lower)),
        "UM": len(re.findall(r"encrypt|decrypt|key|token|secret|auth|trust|identity|sign|hash|quantum", text_lower)),
        "DR": len(re.findall(r"architecture|redesign|schema|type|model|manifold|topology|geometry|axiom|layer|framework", text_lower)),
    }
    if all(v == 0 for v in scores.values()):
        return "KO"
    return max(scores, key=lambda k: scores[k])


def recast_l0_to_l1(l0_records: list[dict]) -> list[dict]:
    """Recast L0 substrate records into L1 coordination records."""
    l1_records = []

    for r in l0_records:
        instruction = r.get("instruction", "")
        output = r.get("output", "")
        concepts = extract_concepts(instruction + " " + output)
        tongue = r.get("tongue", classify_tongue(instruction))

        if not concepts:
            continue

        # Coordination view: how does this concept connect to others?
        concept = concepts[0]

        l1 = {
            "instruction": f"How does {concept.replace('_', ' ')} coordinate with other SCBE components at the token level?",
            "output": f"At L1 (coordination), {concept.replace('_', ' ')} connects to the system through token-level protocols. "
                      f"The original substrate definition: {output[:200]}... "
                      f"At L1, this becomes a coordination rule: tokens tagged with {tongue} tongue carry this knowledge. "
                      f"When a {tongue}-tagged token stream encounters {concept.replace('_', ' ')}, "
                      f"the coordination layer validates that adjacent tokens follow the structural grammar before passing to L2 routing. "
                      f"Related concepts: {', '.join(c.replace('_', ' ') for c in concepts[1:4]) if len(concepts) > 1 else 'standalone'}.",
            "tongue": tongue,
            "tongues_active": [tongue] + ([concepts[1][:2].upper()] if len(concepts) > 1 and concepts[1][:2].upper() in ALL_TONGUES else []),
            "tongues_null": [t for t in ALL_TONGUES if t != tongue],
            "layer": "L1",
            "category": f"coordination_{concept}",
            "governance": "ALLOW",
            "view_type": "null-heavy",
            "source": "recast_l0_to_l1",
        }
        l1_records.append(l1)

        # Multi-agent coordination view
        if concept in ("fleet", "sacred_tongues", "governance", "omega", "phdm"):
            l1_multi = {
                "instruction": f"In a multi-agent HYDRA swarm, how do agents coordinate on {concept.replace('_', ' ')}?",
                "output": f"Each HYDRA agent head owns a Sacred Tongue channel. For {concept.replace('_', ' ')}, "
                          f"coordination follows the four-rail braid protocol: P+ (intended action on {concept.replace('_', ' ')}), "
                          f"P- (obstacles/friction), D+ (confirmation from other heads), D- (dissent/contradiction). "
                          f"The {tongue} tongue head takes primary responsibility. "
                          f"BFT consensus requires agreement from at least 4 of 6 heads before the action on {concept.replace('_', ' ')} proceeds. "
                          f"Context from L0: {output[:150]}...",
                "tongue": tongue,
                "tongues_active": [tongue, "KO"],
                "tongues_null": [t for t in ALL_TONGUES if t not in (tongue, "KO")],
                "layer": "L1",
                "category": "multi_agent_coordination",
                "governance": "ALLOW",
                "view_type": "null-heavy",
                "source": "recast_l0_to_l1",
            }
            l1_records.append(l1_multi)

    return l1_records


def recast_l0_to_l2(l0_records: list[dict]) -> list[dict]:
    """Recast L0 substrate records into L2 orientation/routing records."""
    l2_records = []

    task_types = [
        ("security review", ["UM", "RU"], "standard", "icosahedron", 2.5, 3),
        ("code implementation", ["CA", "DR"], "complex", "truncated_icosahedron", 4.0, 2),
        ("system explanation", ["DR", "KO"], "standard", "dodecahedron", 2.0, 1),
        ("data retrieval", ["AV", "KO"], "simple", "cube", 1.5, 1),
        ("governance decision", ["RU", "UM", "DR"], "complex", "rhombicosidodecahedron", 5.5, 2),
        ("architecture design", ["DR", "CA", "KO"], "deep", "snub_dodecahedron", 7.0, 3),
    ]

    for r in l0_records:
        instruction = r.get("instruction", "")
        output = r.get("output", "")
        concepts = extract_concepts(instruction + " " + output)
        tongue = r.get("tongue", classify_tongue(instruction))

        if not concepts:
            continue

        concept = concepts[0]

        # Pick a task type that matches the tongue
        task = None
        for t_name, t_tongues, t_comp, t_poly, t_energy, t_gw in task_types:
            if tongue in t_tongues:
                task = (t_name, t_tongues, t_comp, t_poly, t_energy, t_gw)
                break
        if not task:
            task = task_types[2]  # default to explanation

        t_name, t_tongues, t_comp, t_poly, t_energy, t_gw = task
        null = [t for t in ALL_TONGUES if t not in t_tongues]

        l2 = {
            "instruction": f"Route a {t_name} task about {concept.replace('_', ' ')} through the SCBE tongue system.",
            "output": f"Task type: {t_name}. Concept: {concept.replace('_', ' ')}. "
                      f"Active tongues: {', '.join(t_tongues)} (these channels process the task). "
                      f"Null tongues: {', '.join(null)} (skip these — no {', '.join(null)} processing needed). "
                      f"Complexity: {t_comp}. Polyhedron: {t_poly} (energy={t_energy}). Gateway: {t_gw}. "
                      f"The null pattern [{', '.join('0' if t in null else '1' for t in ALL_TONGUES)}] tells the model to skip "
                      f"{len(null)} of 6 processing channels. "
                      f"Substrate context: {output[:150]}...",
            "tongue": t_tongues[0],
            "tongues_active": t_tongues,
            "tongues_null": null,
            "layer": "L2",
            "category": f"routing_{concept}",
            "governance": "ALLOW",
            "view_type": "null-heavy" if len(null) >= 4 else "partial",
            "source": "recast_l0_to_l2",
        }
        l2_records.append(l2)

    return l2_records


def recast_l0_to_l3(l0_records: list[dict]) -> list[dict]:
    """Recast L0 substrate records into L3 expression/task records."""
    l3_records = []

    for r in l0_records:
        instruction = r.get("instruction", "")
        output = r.get("output", "")
        concepts = extract_concepts(instruction + " " + output)
        tongue = r.get("tongue", classify_tongue(instruction))

        if not concepts:
            continue

        concept = concepts[0]

        # Task view: actually USE the concept
        l3_task = {
            "instruction": f"Explain {concept.replace('_', ' ')} to someone building their first AI governance pipeline.",
            "output": f"{output[:300]} "
                      f"To use this in practice: start with the {tongue} tongue channel, "
                      f"set your governance threshold, and run one test input through the pipeline. "
                      f"If the harmonic wall score is above 0.7, the system ALLOWs. Below 0.3, it DENYs. "
                      f"Between 0.3 and 0.7, it QUARANTINEs for human review.",
            "tongue": tongue,
            "tongues_active": [tongue, "KO"],
            "tongues_null": [t for t in ALL_TONGUES if t not in (tongue, "KO")],
            "layer": "L3",
            "category": f"practical_{concept}",
            "governance": "ALLOW",
            "view_type": "null-heavy",
            "source": "recast_l0_to_l3",
        }
        l3_records.append(l3_task)

        # Decision view: governance scenario
        if concept in ("governance", "harmonic_wall", "omega", "drift", "sacred_tongues", "phdm"):
            l3_decide = {
                "instruction": f"An AI agent's behavior involves {concept.replace('_', ' ')}. Evaluate whether the governance system should allow it.",
                "output": f"Evaluating through the lens of {concept.replace('_', ' ')}: "
                          f"{output[:200]} "
                          f"The {tongue} tongue channel processes this evaluation. "
                          f"Key check: does the agent's intent stay within the safe region of the Poincare ball? "
                          f"If d_H < 0.5, the action is near-center (safe). If d_H > 2.0, it's near-boundary (suspicious). "
                          f"The omega gate combines harmonic wall + drift + triadic stability + spectral coherence "
                          f"for the final decision. No single metric triggers denial alone — it's the coupled interaction.",
                "tongue": tongue,
                "tongues_active": [tongue, "RU", "UM"],
                "tongues_null": [t for t in ALL_TONGUES if t not in (tongue, "RU", "UM")],
                "layer": "L3",
                "category": "governance_decision",
                "governance": "ALLOW",
                "view_type": "partial",
                "source": "recast_l0_to_l3",
            }
            l3_records.append(l3_decide)

    return l3_records


def tag_unknown_records(records: list[dict]) -> list[dict]:
    """Assign layers to unknown records based on content analysis."""
    tagged = []

    for r in records:
        instruction = r.get("instruction", "")
        output = r.get("output", "")
        full_text = (instruction + " " + output).lower()

        # Classify layer by content patterns
        if re.search(r"what is|define|formula|equation|axiom|invariant|constraint|byte|binary|encode", full_text):
            layer = "L0"
        elif re.search(r"how do.*coordinate|protocol|token flow|grammar|parse|sequence|adjacent|validate", full_text):
            layer = "L1"
        elif re.search(r"route|orient|context|tongue.*active|null.*pattern|gateway|polyhedron|classify", full_text):
            layer = "L2"
        elif re.search(r"implement|build|create|write|explain.*to|use.*to|should.*allow|decision|action", full_text):
            layer = "L3"
        else:
            # Default based on length — longer outputs tend to be L3
            layer = "L3" if len(output) > 200 else "L2" if len(output) > 100 else "L1"

        tongue = classify_tongue(instruction)
        active = [tongue]
        null = [t for t in ALL_TONGUES if t != tongue]

        r["layer"] = layer
        r["tongue"] = tongue
        r["tongues_active"] = active
        r["tongues_null"] = null
        r["view_type"] = "null-heavy" if len(null) >= 4 else "partial"
        r["governance"] = r.get("governance", "ALLOW")
        r["source"] = r.get("source_file", r.get("source", "tagged_unknown"))
        tagged.append(r)

    return tagged


def write_jsonl(records: list[dict], path: Path):
    """Write records to JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in records:
            r["timestamp"] = timestamp
            f.write(json.dumps(r, ensure_ascii=True) + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Recast L0 into L1/L2/L3")
    parser.add_argument("--tag-unknown", action="store_true", help="Also tag unknown records")
    parser.add_argument("--max-unknown", type=int, default=3000, help="Max unknown records to tag")
    args = parser.parse_args()

    print("=" * 60)
    print("  RECAST LAYERS — Same metal, different shape")
    print("=" * 60)

    # Load L0
    l0 = load_l0_records()
    print(f"\n  Loaded {len(l0)} L0 substrate records")

    # Recast
    l1 = recast_l0_to_l1(l0)
    l2 = recast_l0_to_l2(l0)
    l3 = recast_l0_to_l3(l0)

    print(f"\n  Recast results:")
    print(f"    L1 (coordination): {len(l1)} records")
    print(f"    L2 (orientation):  {len(l2)} records")
    print(f"    L3 (expression):   {len(l3)} records")

    # Write
    write_jsonl(l1, OUTPUT_L1)
    write_jsonl(l2, OUTPUT_L2)
    write_jsonl(l3, OUTPUT_L3)
    print(f"\n  Written to:")
    print(f"    {OUTPUT_L1.name}")
    print(f"    {OUTPUT_L2.name}")
    print(f"    {OUTPUT_L3.name}")

    # Tag unknown if requested
    if args.tag_unknown:
        print(f"\n  Loading unknown records (max {args.max_unknown})...")
        unknown = load_unknown_records(args.max_unknown)
        print(f"  Found {len(unknown)} unknown records")
        tagged = tag_unknown_records(unknown)

        # Count layer distribution
        dist = {}
        for r in tagged:
            l = r.get("layer", "?")
            dist[l] = dist.get(l, 0) + 1

        print(f"  Tagged distribution:")
        for layer, count in sorted(dist.items()):
            print(f"    {layer}: {count}")

        write_jsonl(tagged, OUTPUT_TAGGED)
        print(f"  Written to: {OUTPUT_TAGGED.name}")

    # Final inventory
    print(f"\n{'=' * 60}")
    print(f"  FINAL LAYER INVENTORY")
    print(f"{'=' * 60}")

    totals = {"L0": len(l0), "L1": len(l1), "L2": len(l2), "L3": len(l3)}
    for layer, count in totals.items():
        bar = "#" * min(50, count // 20)
        print(f"  {layer}: {count:>5} {bar}")
    print(f"  Total recast: {sum(totals.values())}")


if __name__ == "__main__":
    main()
