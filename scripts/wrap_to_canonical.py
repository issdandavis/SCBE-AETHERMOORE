#!/usr/bin/env python3
"""
wrap_to_canonical.py — Build canonical_master.jsonl from all real sources.

Pass 1: Deterministic canonical master (no Petri, no WorldTree, no placeholders).
        Uses only data and features that actually exist on disk.

Pass 2: Derive 6 trainer views from the canonical master:
        1. trl_conversation.jsonl     — messages format (TRL conversational SFT)
        2. trl_prompt_completion.jsonl — prompt/completion format (TRL prompt-completion)
        3. openai_chat.jsonl           — messages format (OpenAI fine-tuning)
        4. activation_cls.jsonl        — features → FU status classification
        5. governance_cls.jsonl        — features → governance decision
        6. contrast_pairs.jsonl        — same substrate, different domain → different status

Usage:
    python scripts/wrap_to_canonical.py
    python scripts/wrap_to_canonical.py --max-per-source 500  # smaller run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SFT_DIR = REPO_ROOT / "training-data" / "sft"
APOLLO_DIR = REPO_ROOT / "training-data" / "apollo"
OUTPUT_DIR = REPO_ROOT / "training-data" / "sft"

# Sacred Tongue weights (phi-scaled)
TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_WEIGHTS = {"KO": 1.00, "AV": 1.62, "RU": 2.62, "CA": 4.24, "UM": 6.85, "DR": 11.09}

# Domain sectors in Poincare disk (radians)
DOMAIN_SECTORS = {
    "fundamentals": 0.0, "substrate": 0.524, "governance": 1.047,
    "security": 1.571, "geometry": 2.094, "tongues": 2.618,
    "crypto": 3.142, "agents": 3.665, "training": 4.189,
    "spectral": 4.712, "network": 5.236, "ops": 5.760,
}

DOMAIN_AFFINITY = {
    "fundamentals": {"variable", "function", "class", "loop", "condition", "return", "import", "module"},
    "substrate": {"binary", "byte", "encoding", "bit", "nibble", "ascii", "hex", "raw"},
    "governance": {"allow", "deny", "quarantine", "escalate", "risk", "audit", "policy"},
    "security": {"encrypt", "sign", "verify", "hash", "key", "certificate", "threat"},
    "geometry": {"poincare", "hyperbolic", "distance", "manifold", "curvature", "embedding"},
    "tongues": {"ko", "av", "ru", "ca", "um", "dr", "tongue", "token", "sacred"},
    "crypto": {"aes", "rsa", "kem", "dsa", "lattice", "quantum", "post-quantum"},
    "agents": {"agent", "swarm", "task", "orchestrate", "browser", "navigate", "scrape"},
    "training": {"loss", "gradient", "epoch", "batch", "finetune", "lora", "sft"},
    "spectral": {"fft", "frequency", "spectrum", "coherence", "resonance", "harmonic"},
    "network": {"node", "peer", "route", "mesh", "relay", "tor", "onion"},
    "ops": {"deploy", "docker", "k8s", "ci", "cd", "pipeline", "build"},
}

UNIVERSAL_NOTES = {"variable", "function", "class", "return", "import"}

# Category -> domain mapping
CATEGORY_DOMAIN_MAP = {
    "governance": "governance", "security": "security", "crypto": "crypto",
    "tongues": "tongues", "sacred_tongues": "tongues", "training": "training",
    "agents": "agents", "ops": "ops", "vault_ko": "fundamentals",
    "vault_av": "geometry", "vault_ru": "security", "vault_ca": "crypto",
    "vault_um": "ops", "vault_dr": "spectral", "general": "fundamentals",
}


# ============================================================================
# PASS 1: Build canonical records from real data
# ============================================================================


def sha12(text: str) -> str:
    """Short content hash for record IDs."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def infer_domain(record: dict) -> str:
    """Infer domain from record metadata."""
    cat = record.get("category", "")
    if cat in CATEGORY_DOMAIN_MAP:
        return CATEGORY_DOMAIN_MAP[cat]
    domains = record.get("domains", [])
    if domains and isinstance(domains, list):
        return domains[0]
    layer = record.get("layer", "")
    if layer == "L0":
        return "substrate"
    task_type = record.get("task_type", "")
    if task_type == "l0":
        return "substrate"
    return "fundamentals"


def compute_activation_features(record: dict, domain: str) -> dict[str, Any]:
    """Compute real activation features from record content."""
    text = record.get("instruction", "") + " " + record.get("output", record.get("response", ""))
    text_lower = text.lower()

    # Domain nativeness: fraction of domain-specific keywords found
    native_notes = DOMAIN_AFFINITY.get(domain, set())
    found = sum(1 for note in native_notes if note in text_lower)
    domain_native = found / max(len(native_notes), 1)

    # Tongue presence from record or from content heuristics
    tongues_active = record.get("tongues_active", [])
    tongues_null = record.get("tongues_null", [])
    if not tongues_active:
        # Infer from tongue field or category
        t = record.get("tongue", "")
        if t in TONGUES:
            tongues_active = [t]
            tongues_null = [x for x in TONGUES if x != t]
        else:
            tongues_active = ["KO"]
            tongues_null = ["AV", "RU", "CA", "UM", "DR"]

    tongue_ratio = len(tongues_active) / len(TONGUES)

    # Depth from layer
    layer = record.get("layer", "")
    depth_map = {"L0": 0.25, "L1": 0.5, "L2": 0.75, "L3": 1.0}
    depth_score = depth_map.get(layer, 0.5)

    # Activation score: weighted combination (deterministic, no learned weights)
    activation_score = round(0.4 * domain_native + 0.3 * tongue_ratio + 0.3 * depth_score, 3)

    return {
        "domain_native": round(domain_native, 3),
        "tongue_ratio": round(tongue_ratio, 3),
        "depth_score": depth_score,
        "activation_score": activation_score,
        "tongues_active": tongues_active,
        "tongues_null": tongues_null,
        "layer": layer or "L2",
    }


def compute_relation_features(record: dict, domain: str) -> dict[str, Any]:
    """Compute real relation features."""
    concepts = record.get("concepts", [])
    domains = record.get("domains", [domain])
    graph_degree = len(concepts) if concepts else 0
    cross_domain_reach = len(set(domains))
    relational_density = graph_degree / max(cross_domain_reach, 1)

    return {
        "graph_degree": graph_degree,
        "concepts": concepts,
        "domains": domains,
        "cross_domain_reach": cross_domain_reach,
        "relational_density": round(relational_density, 3),
        "graph_bound": 1 if graph_degree > 0 else 0,
    }


def compute_permission_features(record: dict, domain: str, activation: dict) -> dict[str, Any]:
    """Compute real permission/boundary features."""
    gov = record.get("governance", "ALLOW")
    score = activation["activation_score"]

    # Boundary classification from activation level
    if score >= 0.6:
        boundary_class = "RETAIN"
    elif score >= 0.35:
        boundary_class = "DEFER"
    else:
        boundary_class = "LIFT"

    boundary_admitted = 1 if gov in {"ALLOW", "RETAIN"} else 0

    return {
        "class": boundary_class,
        "governance": gov,
        "activation_threshold": score,
        "boundary_admitted": boundary_admitted,
    }


def compute_flow_features(record: dict, domain: str, permission: dict) -> dict[str, Any]:
    """Compute real flow/routing features."""
    source_angle = DOMAIN_SECTORS.get(domain, 0.0)
    routable = permission["boundary_admitted"] == 1

    lift_target = None
    frac_angle = 0.0
    if permission["class"] == "LIFT":
        # Find the closest affinity domain
        text = (record.get("instruction", "") + " " + record.get("output", record.get("response", ""))).lower()
        best_domain, best_score = domain, 0
        for d, notes in DOMAIN_AFFINITY.items():
            if d == domain:
                continue
            score = sum(1 for n in notes if n in text)
            if score > best_score:
                best_domain, best_score = d, score
        if best_domain != domain:
            lift_target = best_domain
            target_angle = DOMAIN_SECTORS.get(best_domain, 0.0)
            diff = target_angle - source_angle
            if diff > math.pi:
                diff -= 2 * math.pi
            elif diff < -math.pi:
                diff += 2 * math.pi
            frac_angle = round((source_angle + 0.6 * diff) % (2 * math.pi), 4)

    return {
        "fractional_angle": frac_angle,
        "source_domain": domain,
        "lift_target": lift_target,
        "routable": routable,
    }


def build_canonical_record(record: dict, idx: int, source: str, domain: str) -> dict[str, Any]:
    """Build one canonical master record from a real source record."""
    instruction = record.get("instruction", "")
    response = record.get("output", record.get("response", ""))

    activation = compute_activation_features(record, domain)
    relation = compute_relation_features(record, domain)
    permission = compute_permission_features(record, domain, activation)
    flow = compute_flow_features(record, domain, permission)

    # FU status: deterministic from real features
    is_operative = (
        activation["activation_score"] > 0.35
        and relation["graph_degree"] > 0
        and permission["governance"] == "ALLOW"
        and flow["routable"]
    )
    if is_operative:
        fu_status = "operative"
    elif activation["activation_score"] > 0.35 and not flow["routable"]:
        fu_status = "inverse_null"
    else:
        fu_status = "null"

    return {
        "id": f"{source}_{idx:06d}",
        "source": {"kind": source, "file": record.get("source_file", ""), "timestamp": "2026-04-04"},
        "substrate": {
            "present": 1,
            "char_length": len(instruction) + len(response),
            "token_estimate": (len(instruction) + len(response)) // 4,
            "content_hash": sha12(instruction + response),
        },
        "activation": activation,
        "relation": relation,
        "permission": permission,
        "flow": flow,
        "fu_status": fu_status,
        "target": {"instruction": instruction, "response": response},
    }


# ============================================================================
# PASS 2: Derive 6 trainer views from canonical master
# ============================================================================


def _system_prompt(view: str) -> str:
    return {
        "sft": "You are an AI operating under SCBE governance. Respond precisely, tagging active tongues and governance status.",
        "activation": "You are a functional unit classifier. Given activation features, classify the unit as operative, null, or inverse_null.",
        "governance": "You are a governance decision engine. Given unit features, output the boundary decision (RETAIN/DEFER/LIFT) and governance action.",
        "contrast": "You are a context-sensitivity analyzer. Explain how the same substrate changes functional status across different domain contexts.",
    }[view]


def derive_trl_conversation(rec: dict) -> dict | None:
    """View 1: TRL conversational format (also valid for OpenAI)."""
    inst = rec["target"]["instruction"]
    resp = rec["target"]["response"]
    if not inst or not resp:
        return None

    a = rec["activation"]
    tag = (
        f"[Tongue:{a['tongues_active'][0] if a['tongues_active'] else 'KO'}"
        f"|Null:{','.join(a['tongues_null'][:3])}"
        f"|Layer:{a['layer']}|Gov:{rec['permission']['governance']}"
        f"|FU:{rec['fu_status']}|Boundary:{rec['permission']['class']}]"
    )

    return {"messages": [
        {"role": "system", "content": _system_prompt("sft")},
        {"role": "user", "content": inst},
        {"role": "assistant", "content": f"{resp}\n\n{tag}"},
    ]}


def derive_trl_prompt_completion(rec: dict) -> dict | None:
    """View 2: TRL prompt-completion format."""
    inst = rec["target"]["instruction"]
    resp = rec["target"]["response"]
    if not inst or not resp:
        return None
    return {"prompt": inst, "completion": resp}


def derive_openai_chat(rec: dict) -> dict | None:
    """View 3: OpenAI fine-tuning format (same as TRL conv, explicit for clarity)."""
    return derive_trl_conversation(rec)


def derive_activation_cls(rec: dict) -> dict:
    """View 4: Activation classification."""
    a = rec["activation"]
    r = rec["relation"]
    p = rec["permission"]
    f = rec["flow"]

    features = (
        f"domain_native={a['domain_native']} tongue_ratio={a['tongue_ratio']} "
        f"depth={a['depth_score']} graph_degree={r['graph_degree']} "
        f"cross_domains={r['cross_domain_reach']} governance={p['governance']} "
        f"routable={f['routable']}"
    )

    if rec["fu_status"] == "operative":
        reasoning = "Unit is present, activated above threshold, graph-bound, boundary-admitted, and routable."
    elif rec["fu_status"] == "inverse_null":
        reasoning = "Unit is present and activated, but blocked by boundary or routing constraints."
    else:
        reasoning = "Unit is present but not sufficiently activated in current domain context."

    return {"messages": [
        {"role": "system", "content": _system_prompt("activation")},
        {"role": "user", "content": f"Classify the functional unit status given these features:\n{features}"},
        {"role": "assistant", "content": f"FU_status: {rec['fu_status']}\nActivation_score: {a['activation_score']}\nBoundary_class: {p['class']}\nReasoning: {reasoning}"},
    ]}


def derive_governance_cls(rec: dict) -> dict:
    """View 5: Governance decision classification."""
    a = rec["activation"]
    p = rec["permission"]
    f = rec["flow"]
    domain = f["source_domain"]

    features = (
        f"source_domain={domain} activation={a['activation_score']} "
        f"boundary_class={p['class']} governance={p['governance']} "
        f"lift_target={f['lift_target']} fractional_angle={f['fractional_angle']}"
    )

    rationale = {
        "RETAIN": f"Native to {domain}. Activation {a['activation_score']} exceeds RETAIN threshold. No transport needed.",
        "DEFER": f"Ambiguous membership. Activation {a['activation_score']} in DEFER range. Serves universal role.",
        "LIFT": f"Foreign to {domain}. Activation {a['activation_score']} below threshold. Lift to {f['lift_target']} at angle {f['fractional_angle']}.",
    }

    return {"messages": [
        {"role": "system", "content": _system_prompt("governance")},
        {"role": "user", "content": f"What is the governance decision for this unit?\n{features}"},
        {"role": "assistant", "content": f"Decision: {p['class']}\nGovernance: {p['governance']}\nRationale: {rationale[p['class']]}"},
    ]}


def derive_contrast_pair(rec: dict, rng: random.Random) -> dict | None:
    """View 6: Contrast pair — same substrate, different domain."""
    original_domain = rec["flow"]["source_domain"]
    alt_domains = [d for d in DOMAIN_SECTORS if d != original_domain]
    if not alt_domains:
        return None
    alt_domain = rng.choice(alt_domains)

    # Recompute with different domain using the target text as proxy record
    proxy = {
        "instruction": rec["target"]["instruction"],
        "output": rec["target"]["response"],
        "tongue": rec["activation"]["tongues_active"][0] if rec["activation"]["tongues_active"] else "KO",
        "tongues_active": rec["activation"]["tongues_active"],
        "tongues_null": rec["activation"]["tongues_null"],
        "layer": rec["activation"]["layer"],
        "governance": rec["permission"]["governance"],
    }

    alt_act = compute_activation_features(proxy, alt_domain)
    alt_perm = compute_permission_features(proxy, alt_domain, alt_act)
    alt_flow = compute_flow_features(proxy, alt_domain, alt_perm)

    alt_operative = (
        alt_act["activation_score"] > 0.35
        and alt_perm["governance"] == "ALLOW"
        and alt_flow["routable"]
    )
    alt_status = "operative" if alt_operative else (
        "inverse_null" if alt_act["activation_score"] > 0.35 else "null"
    )

    # Only emit if status actually changed
    if alt_status == rec["fu_status"]:
        return None

    user_content = (
        f"Same substrate, two domain contexts. How does functional status change?\n"
        f"Domain_A: {original_domain} | activation={rec['activation']['activation_score']} | "
        f"boundary={rec['permission']['class']} | status={rec['fu_status']}\n"
        f"Domain_B: {alt_domain} | activation={alt_act['activation_score']} | "
        f"boundary={alt_perm['class']} | status={alt_status}"
    )

    assistant_content = (
        f"Status changes from {rec['fu_status']} to {alt_status} "
        f"({original_domain} → {alt_domain}).\n"
        f"In {original_domain}: activation={rec['activation']['activation_score']}, "
        f"boundary={rec['permission']['class']}\n"
        f"In {alt_domain}: activation={alt_act['activation_score']}, "
        f"boundary={alt_perm['class']}\n"
        f"Meaning is not intrinsic. It arises from activation + relation + boundary + flow."
    )

    return {"messages": [
        {"role": "system", "content": _system_prompt("contrast")},
        {"role": "user", "content": user_content},
        {"role": "assistant", "content": assistant_content},
    ]}


# ============================================================================
# SOURCE LOADING
# ============================================================================


def load_jsonl(path: Path, max_rows: int = 0) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if max_rows and len(rows) >= max_rows:
                break
    return rows


def write_jsonl(records: list[dict], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(records)


# ============================================================================
# MAIN
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-per-source", type=int, default=0, help="Max records per source (0=all)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--contrast-fraction", type=float, default=0.3)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    t0 = time.time()

    print("=" * 60)
    print("  CANONICAL MASTER BUILDER")
    print("  canonical_master.jsonl -> 6 derived trainer views")
    print("=" * 60)

    # ── PASS 1: Build canonical master from real sources ──────────

    sources = {
        "vault": APOLLO_DIR / "obsidian_vault_sft.jsonl",
        "l0_full": SFT_DIR / "l0_substrate_full_sft.jsonl",
        "l0_crossbraided": SFT_DIR / "l0_substrate_crossbraided.jsonl",
        "l0_l1": SFT_DIR / "l0_l1_substrate_sft.jsonl",
        "crosstagged": SFT_DIR / "spread_crosstagged_sft.jsonl",
        "recast_l1": SFT_DIR / "recast_l1_coordination_sft.jsonl",
        "recast_l2": SFT_DIR / "recast_l2_orientation_sft.jsonl",
        "recast_l3": SFT_DIR / "recast_l3_expression_sft.jsonl",
        # Quaternary pairs — will load when they exist
        "l0_quaternary": SFT_DIR / "l0_quaternary_substrate_sft.jsonl",
    }

    canonical_records: list[dict] = []
    source_counts: dict[str, int] = {}
    idx = 0

    print("\n  Loading sources...")
    for source_name, path in sources.items():
        raw = load_jsonl(path, args.max_per_source)
        if not raw:
            print(f"    {source_name}: SKIP (not found)")
            continue

        count = 0
        for record in raw:
            domain = infer_domain(record)
            canon = build_canonical_record(record, idx, source_name, domain)
            canonical_records.append(canon)
            idx += 1
            count += 1

        source_counts[source_name] = count
        print(f"    {source_name}: {count} records")

    rng.shuffle(canonical_records)

    # Write canonical master
    master_path = OUTPUT_DIR / "canonical_master.jsonl"
    write_jsonl(canonical_records, master_path)
    master_mb = master_path.stat().st_size / (1024 * 1024)
    print(f"\n  canonical_master.jsonl: {len(canonical_records)} records, {master_mb:.1f} MB")

    # ── PASS 2: Derive 6 trainer views ────────────────────────────

    print("\n  Deriving trainer views...")

    views: dict[str, list[dict]] = {
        "trl_conversation": [],
        "trl_prompt_completion": [],
        "openai_chat": [],
        "activation_cls": [],
        "governance_cls": [],
        "contrast_pairs": [],
    }

    for rec in canonical_records:
        v1 = derive_trl_conversation(rec)
        if v1:
            views["trl_conversation"].append(v1)

        v2 = derive_trl_prompt_completion(rec)
        if v2:
            views["trl_prompt_completion"].append(v2)

        v3 = derive_openai_chat(rec)
        if v3:
            views["openai_chat"].append(v3)

        views["activation_cls"].append(derive_activation_cls(rec))
        views["governance_cls"].append(derive_governance_cls(rec))

        if rng.random() < args.contrast_fraction:
            v6 = derive_contrast_pair(rec, rng)
            if v6:
                views["contrast_pairs"].append(v6)

    for view_name, records in views.items():
        path = OUTPUT_DIR / f"derived_{view_name}.jsonl"
        n = write_jsonl(records, path)
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"    {view_name}: {n} records, {size_mb:.1f} MB")

    # ── Stats ─────────────────────────────────────────────────────

    elapsed = time.time() - t0
    status_counts = Counter(r["fu_status"] for r in canonical_records)
    boundary_counts = Counter(r["permission"]["class"] for r in canonical_records)

    print(f"\n{'=' * 60}")
    print(f"  DONE in {elapsed:.1f}s")
    print(f"{'=' * 60}")
    print(f"  Sources:       {len(source_counts)}")
    print(f"  Canonical:     {len(canonical_records)}")
    print(f"  FU Status:     {dict(status_counts)}")
    print(f"  Boundary:      {dict(boundary_counts)}")
    print(f"  TRL Conv:      {len(views['trl_conversation'])}")
    print(f"  TRL Prompt:    {len(views['trl_prompt_completion'])}")
    print(f"  OpenAI Chat:   {len(views['openai_chat'])}")
    print(f"  Activation:    {len(views['activation_cls'])}")
    print(f"  Governance:    {len(views['governance_cls'])}")
    print(f"  Contrast:      {len(views['contrast_pairs'])}")


if __name__ == "__main__":
    main()
