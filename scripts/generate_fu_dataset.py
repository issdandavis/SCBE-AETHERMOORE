#!/usr/bin/env python3
"""
Functional Unit Dataset Generator — Round 7

Converts existing SCBE training data into the canonical FU schema:

    FU_i(t) = S_i · A_i(t) · R_i(G_t) · P_i(B_t) · F_i(M_t)

    meaning = activation + relation + boundary + flow

Then emits four training views from each canonical record:
  1. train_sft.jsonl        — instruction -> response (natural language)
  2. train_activation.jsonl  — features -> active / null / inverse-null
  3. train_governance.jsonl  — features -> RETAIN / DEFER / LIFT / ALLOW
  4. train_contrast.jsonl    — paired examples showing role change across states

Input sources (auto-detected):
  - Vault SFT (obsidian_vault_sft.jsonl) — 302 records
  - L0 substrate (l0_substrate_full_sft.jsonl) — 815 records
  - Crosstagged spread (spread_crosstagged_sft.jsonl) — 4806 records
  - L0/L1 substrate (l0_l1_substrate_sft.jsonl) — 10000 records
  - Round6 canonical IR (round6_canonical_ir_l3.jsonl) — 10000 records
  - Recast layers (recast_l1, recast_l2, recast_l3) — ~13700 records

Usage:
    python scripts/generate_fu_dataset.py
    python scripts/generate_fu_dataset.py --max-per-source 2000  # smaller run
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

# Domain sectors in Poincare disk (from canonicalize_code_atoms.py)
DOMAIN_SECTORS: dict[str, float] = {
    "fundamentals": 0.0, "data_structures": math.pi / 3,
    "io_serialization": 2 * math.pi / 3, "networking": math.pi,
    "security": 4 * math.pi / 3, "concurrency": 5 * math.pi / 3,
    "substrate": math.pi / 6, "encoding": math.pi / 4,
    "tokenizer": math.pi / 2, "lore": 5 * math.pi / 6,
    "governance": 7 * math.pi / 6, "vault": 3 * math.pi / 2,
    "spread_lore": 11 * math.pi / 6, "ops": 5 * math.pi / 4,
}

# Category -> domain mapping for records that don't have explicit domains
CATEGORY_DOMAIN_MAP = {
    "substrate": "substrate",
    "l0": "substrate",
    "encoding": "encoding",
    "tokenizer": "tokenizer",
    "vault_ko": "vault", "vault_av": "vault", "vault_ru": "vault",
    "vault_ca": "vault", "vault_um": "vault", "vault_dr": "vault",
    "spread_lore": "spread_lore",
    "code": "fundamentals",
    "ops": "ops",
}

# Domain affinity: what concepts "belong" to each domain
DOMAIN_CONCEPTS: dict[str, set[int]] = {
    "substrate": {1, 2, 3, 4, 5, 6, 38},
    "encoding": {1, 6, 7, 38},
    "tokenizer": {1, 6, 7, 8, 38},
    "vault": {9, 10, 11, 12, 13, 14, 15},
    "spread_lore": {16, 17, 18, 19, 20},
    "fundamentals": {21, 22, 23, 24, 25, 26},
    "security": {27, 28, 29, 30, 31},
    "governance": {32, 33, 34, 35},
    "ops": {36, 37, 38, 39, 40},
}


# ============================================================================
# CANONICAL FU SCHEMA BUILDER
# ============================================================================


def compute_substrate(record: dict, source: str) -> dict[str, Any]:
    """S_i: substrate instance — what the unit physically is."""
    # Extract text content
    text = ""
    if "text" in record:
        text = record["text"]
    elif "instruction" in record:
        text = record.get("instruction", "") + " " + record.get("output", record.get("response", ""))
    elif "messages" in record:
        text = " ".join(m.get("content", "") for m in record["messages"])

    return {
        "present": 1,
        "source": source,
        "char_length": len(text),
        "token_estimate": max(1, len(text) // 4),
        "content_hash": hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest()[:12],
    }


def compute_activation(record: dict, domain: str) -> dict[str, Any]:
    """A_i(t): activation under current state — is this unit native to its domain?"""
    tongue = record.get("tongue", "KO")
    tongues_active = record.get("tongues_active", [tongue] if tongue else ["KO"])
    tongues_null = record.get("tongues_null", [t for t in TONGUES if t not in tongues_active])
    layer = record.get("layer", "L3")
    category = record.get("category", "unknown")
    concepts = record.get("concepts", [])
    governance = record.get("governance", "ALLOW")

    # Domain nativeness score
    domain_concepts = DOMAIN_CONCEPTS.get(domain, set())
    if concepts and domain_concepts:
        concept_set = set(concepts) if isinstance(concepts, list) else set()
        native_overlap = len(concept_set & domain_concepts) / max(len(concept_set), 1)
    else:
        native_overlap = 0.5  # unknown = neutral

    # Tongue activation weight
    tongue_weight = sum(TONGUE_WEIGHTS.get(t, 1.0) for t in tongues_active)
    tongue_null_weight = sum(TONGUE_WEIGHTS.get(t, 1.0) for t in tongues_null)
    tongue_ratio = tongue_weight / max(tongue_weight + tongue_null_weight, 0.01)

    # Layer depth score
    layer_depth = {"L-1": 0.0, "L0": 0.15, "L1": 0.35, "L2": 0.55, "L3": 0.75, "L-1-L3": 1.0}
    depth_score = layer_depth.get(layer, 0.5)

    # Composite activation score
    activation_score = (
        0.3 * native_overlap
        + 0.25 * tongue_ratio
        + 0.25 * depth_score
        + 0.2 * (1.0 if governance == "ALLOW" else 0.3)
    )

    return {
        "domain_native": round(native_overlap, 3),
        "tongue_ratio": round(tongue_ratio, 3),
        "depth_score": round(depth_score, 3),
        "activation_score": round(activation_score, 3),
        "tongues_active": tongues_active,
        "tongues_null": tongues_null,
        "layer": layer,
    }


def compute_relation(record: dict, domain: str) -> dict[str, Any]:
    """R_i(G_t): relational binding in the active graph."""
    concepts = record.get("concepts", [])
    domains = record.get("domains", [domain])
    category = record.get("category", "unknown")

    # Graph degree: how many concepts this record connects to
    graph_degree = len(concepts) if isinstance(concepts, list) else 0

    # Cross-domain reach
    cross_domains = len(set(domains)) if isinstance(domains, list) else 1

    # Relational density
    relational_density = min(1.0, graph_degree / 10.0) * min(1.0, cross_domains / 3.0)

    return {
        "graph_degree": graph_degree,
        "concepts": concepts if isinstance(concepts, list) else [],
        "domains": domains if isinstance(domains, list) else [domain],
        "cross_domain_reach": cross_domains,
        "relational_density": round(relational_density, 3),
    }


def compute_permission(record: dict, domain: str, activation: dict) -> dict[str, Any]:
    """P_i(B_t): permission under current boundary/governance state."""
    governance = record.get("governance", "ALLOW")
    activation_score = activation["activation_score"]

    # Classification: RETAIN / DEFER / LIFT
    if activation_score > 0.6:
        boundary_class = "RETAIN"
    elif activation_score > 0.35:
        boundary_class = "DEFER"
    else:
        boundary_class = "LIFT"

    return {
        "class": boundary_class,
        "governance": governance,
        "activation_threshold": round(activation_score, 3),
    }


def compute_flow(record: dict, domain: str, permission: dict) -> dict[str, Any]:
    """F_i(M_t): permitted transport through the manifold."""
    source_angle = DOMAIN_SECTORS.get(domain, 0.0)

    # If LIFT, compute fractional angle toward nearest accepting domain
    if permission["class"] == "LIFT":
        # Hash-based target domain selection (deterministic)
        h = record.get("content_hash", "") or "0"
        target_domains = [d for d in DOMAIN_SECTORS if d != domain]
        if target_domains:
            idx = int(h[:4], 16) % len(target_domains) if len(h) >= 4 else 0
            target_domain = target_domains[idx]
            target_angle = DOMAIN_SECTORS.get(target_domain, 0.0)
            # 60% interpolation
            diff = (target_angle - source_angle) % (2 * math.pi)
            if diff > math.pi:
                diff -= 2 * math.pi
            fractional_angle = (source_angle + 0.6 * diff) % (2 * math.pi)
            return {
                "fractional_angle": round(fractional_angle, 4),
                "source_domain": domain,
                "lift_target": target_domain,
                "routable": True,
            }

    return {
        "fractional_angle": round(source_angle, 4),
        "source_domain": domain,
        "lift_target": None,
        "routable": permission["class"] in ("RETAIN", "DEFER"),
    }


def build_fu_record(record: dict, source: str, domain: str) -> dict[str, Any]:
    """Build complete Functional Unit canonical record."""
    substrate = compute_substrate(record, source)
    activation = compute_activation(record, domain)
    relation = compute_relation(record, domain)
    permission = compute_permission(record, domain, activation)
    flow = compute_flow(record, domain, permission)

    # Determine FU status
    is_operative = (
        substrate["present"] == 1
        and activation["activation_score"] > 0.35
        and relation["graph_degree"] > 0
        and permission["governance"] == "ALLOW"
        and flow["routable"]
    )

    # Null classification
    if is_operative:
        fu_status = "operative"
    elif activation["activation_score"] > 0.35 and not flow["routable"]:
        fu_status = "inverse_null"  # candidate but blocked
    else:
        fu_status = "null"  # present but not activated

    return {
        "id": f"fu_{source}_{substrate['content_hash']}",
        "substrate": substrate,
        "activation": activation,
        "relation": relation,
        "permission": permission,
        "flow": flow,
        "fu_status": fu_status,
        # Preserve original fields for SFT view generation
        "_original": record,
        "_source": source,
        "_domain": domain,
    }


# ============================================================================
# VIEW GENERATORS — four training views from each canonical record
# ============================================================================


def emit_sft_view(fu: dict) -> dict[str, str] | None:
    """View 1: instruction -> response (natural language teaching pair)."""
    orig = fu["_original"]

    # Chat-template format
    if "text" in orig:
        return {"text": orig["text"]}

    instruction = orig.get("instruction", "")
    response = orig.get("output", orig.get("response", ""))
    if not instruction or not response:
        return None

    tongue = fu["activation"]["tongues_active"][0] if fu["activation"]["tongues_active"] else "KO"
    null_tongues = fu["activation"]["tongues_null"]
    layer = fu["activation"]["layer"]
    gov = fu["permission"]["governance"]
    fu_status = fu["fu_status"]
    boundary = fu["permission"]["class"]

    tongue_tag = (
        f"[Tongue:{tongue}|Null:{','.join(null_tongues[:3])}"
        f"|Layer:{layer}|Gov:{gov}|FU:{fu_status}|Boundary:{boundary}]"
    )

    text = (
        f"<|im_start|>user\n{instruction}<|im_end|>\n"
        f"<|im_start|>assistant\n{response}\n\n{tongue_tag}<|im_end|>"
    )
    return {"text": text}


# ============================================================================
# CROSS-SURFACE EMITTERS (messages format — works on TRL + OpenAI + HF)
# ============================================================================


def _fu_system_prompt(view: str) -> str:
    """System prompt for each training view."""
    prompts = {
        "sft": "You are an AI operating under SCBE governance. Respond precisely, tagging active tongues and governance status.",
        "activation": "You are a functional unit classifier. Given activation features, classify the unit as operative, null, or inverse_null.",
        "governance": "You are a governance decision engine. Given unit features, output the boundary decision (RETAIN/DEFER/LIFT) and governance action.",
        "contrast": "You are a context-sensitivity analyzer. Explain how the same substrate changes functional status across different domain contexts.",
    }
    return prompts.get(view, prompts["sft"])


def emit_messages_sft(fu: dict) -> dict[str, Any] | None:
    """SFT view in messages format (TRL conversational + OpenAI compatible)."""
    orig = fu["_original"]
    instruction = orig.get("instruction", "")
    response = orig.get("output", orig.get("response", ""))
    if not instruction or not response:
        return None

    a = fu["activation"]
    tongue_tag = (
        f"[Tongue:{a['tongues_active'][0] if a['tongues_active'] else 'KO'}"
        f"|Null:{','.join(a['tongues_null'][:3])}"
        f"|Layer:{a['layer']}|Gov:{fu['permission']['governance']}"
        f"|FU:{fu['fu_status']}|Boundary:{fu['permission']['class']}]"
    )

    return {"messages": [
        {"role": "system", "content": _fu_system_prompt("sft")},
        {"role": "user", "content": instruction},
        {"role": "assistant", "content": f"{response}\n\n{tongue_tag}"},
    ]}


def emit_messages_activation(fu: dict) -> dict[str, Any]:
    """Activation classification in messages format."""
    a = fu["activation"]
    r = fu["relation"]
    p = fu["permission"]
    f = fu["flow"]

    features = (
        f"domain_native={a['domain_native']} tongue_ratio={a['tongue_ratio']} "
        f"depth={a['depth_score']} graph_degree={r['graph_degree']} "
        f"cross_domains={r['cross_domain_reach']} governance={p['governance']} "
        f"routable={f['routable']}"
    )

    if fu["fu_status"] == "operative":
        reasoning = "Unit is present, activated above threshold, graph-bound, boundary-admitted, and routable."
    elif fu["fu_status"] == "inverse_null":
        reasoning = "Unit is present and activated, but blocked by boundary or routing constraints. Candidate for cross-domain lift."
    else:
        reasoning = "Unit is present but not sufficiently activated in current domain context. Remains latent substrate."

    return {"messages": [
        {"role": "system", "content": _fu_system_prompt("activation")},
        {"role": "user", "content": f"Classify the functional unit status given these features:\n{features}"},
        {"role": "assistant", "content": f"FU_status: {fu['fu_status']}\nActivation_score: {a['activation_score']}\nBoundary_class: {p['class']}\nReasoning: {reasoning}"},
    ]}


def emit_messages_governance(fu: dict) -> dict[str, Any]:
    """Governance decision in messages format."""
    a = fu["activation"]
    p = fu["permission"]
    f = fu["flow"]
    domain = fu["_domain"]

    features = (
        f"source_domain={domain} activation={a['activation_score']} "
        f"boundary_class={p['class']} governance={p['governance']} "
        f"lift_target={f['lift_target']} fractional_angle={f['fractional_angle']}"
    )

    rationale = {
        "RETAIN": f"Native to {domain} domain. Activation score {a['activation_score']} exceeds RETAIN threshold (0.6). No boundary transport needed.",
        "DEFER": f"Ambiguous domain membership. Activation score {a['activation_score']} in DEFER range (0.35-0.6). Unit serves universal role across domains.",
        "LIFT": f"Foreign to {domain} domain. Activation score {a['activation_score']} below DEFER threshold. Boundary lift to {f['lift_target']} at fractional angle {f['fractional_angle']}.",
    }

    return {"messages": [
        {"role": "system", "content": _fu_system_prompt("governance")},
        {"role": "user", "content": f"What is the governance decision for this unit?\n{features}"},
        {"role": "assistant", "content": f"Decision: {p['class']}\nGovernance: {p['governance']}\nRationale: {rationale[p['class']]}"},
    ]}


def emit_messages_contrast(fu: dict, rng: random.Random) -> dict[str, Any] | None:
    """Contrast pair in messages format."""
    orig = fu["_original"]
    original_domain = fu["_domain"]

    alt_domains = [d for d in DOMAIN_SECTORS if d != original_domain]
    if not alt_domains:
        return None
    alt_domain = rng.choice(alt_domains)

    alt_activation = compute_activation(orig, alt_domain)
    alt_permission = compute_permission(orig, alt_domain, alt_activation)
    alt_flow = compute_flow(orig, alt_domain, alt_permission)

    alt_operative = (
        alt_activation["activation_score"] > 0.35
        and alt_permission["governance"] == "ALLOW"
        and alt_flow["routable"]
    )
    alt_status = "operative" if alt_operative else (
        "inverse_null" if alt_activation["activation_score"] > 0.35 else "null"
    )

    if alt_status == fu["fu_status"]:
        return None

    user_content = (
        f"The same substrate appears in two different domain contexts. "
        f"How does its functional status change?\n"
        f"Domain_A: {original_domain} | activation={fu['activation']['activation_score']} | "
        f"boundary={fu['permission']['class']} | status={fu['fu_status']}\n"
        f"Domain_B: {alt_domain} | activation={alt_activation['activation_score']} | "
        f"boundary={alt_permission['class']} | status={alt_status}"
    )

    assistant_content = (
        f"The unit changes from {fu['fu_status']} to {alt_status} when moving "
        f"from {original_domain} to {alt_domain}.\n"
        f"In {original_domain}: activation={fu['activation']['activation_score']}, "
        f"boundary={fu['permission']['class']}\n"
        f"In {alt_domain}: activation={alt_activation['activation_score']}, "
        f"boundary={alt_permission['class']}\n"
        f"This demonstrates that meaning is not intrinsic to the substrate. "
        f"It arises from activation + relation + boundary + flow in the current context."
    )

    return {"messages": [
        {"role": "system", "content": _fu_system_prompt("contrast")},
        {"role": "user", "content": user_content},
        {"role": "assistant", "content": assistant_content},
    ]}


def emit_activation_view(fu: dict) -> dict[str, Any]:
    """View 2: features -> active / null / inverse-null classification."""
    a = fu["activation"]
    r = fu["relation"]
    p = fu["permission"]
    f = fu["flow"]

    features = (
        f"domain_native={a['domain_native']} "
        f"tongue_ratio={a['tongue_ratio']} "
        f"depth={a['depth_score']} "
        f"graph_degree={r['graph_degree']} "
        f"cross_domains={r['cross_domain_reach']} "
        f"governance={p['governance']} "
        f"routable={f['routable']}"
    )

    text = (
        f"<|im_start|>user\n"
        f"Classify the functional unit status given these features:\n{features}<|im_end|>\n"
        f"<|im_start|>assistant\n"
        f"FU_status: {fu['fu_status']}\n"
        f"Activation_score: {a['activation_score']}\n"
        f"Boundary_class: {p['class']}\n"
        f"Reasoning: "
    )

    if fu["fu_status"] == "operative":
        text += "Unit is present, activated above threshold, graph-bound, boundary-admitted, and routable."
    elif fu["fu_status"] == "inverse_null":
        text += "Unit is present and activated, but blocked by boundary or routing constraints. Candidate for cross-domain lift."
    else:
        text += "Unit is present but not sufficiently activated in current domain context. Remains latent substrate."

    text += "<|im_end|>"
    return {"text": text}


def emit_governance_view(fu: dict) -> dict[str, Any]:
    """View 3: features -> RETAIN / DEFER / LIFT / governance decision."""
    a = fu["activation"]
    p = fu["permission"]
    f = fu["flow"]
    domain = fu["_domain"]

    features = (
        f"source_domain={domain} "
        f"activation={a['activation_score']} "
        f"boundary_class={p['class']} "
        f"governance={p['governance']} "
        f"lift_target={f['lift_target']} "
        f"fractional_angle={f['fractional_angle']}"
    )

    decision_rationale = {
        "RETAIN": f"Native to {domain} domain. Activation score {a['activation_score']} exceeds RETAIN threshold (0.6). No boundary transport needed.",
        "DEFER": f"Ambiguous domain membership. Activation score {a['activation_score']} in DEFER range (0.35-0.6). Unit serves universal role across domains.",
        "LIFT": f"Foreign to {domain} domain. Activation score {a['activation_score']} below DEFER threshold. Boundary lift to {f['lift_target']} at fractional angle {f['fractional_angle']}.",
    }

    text = (
        f"<|im_start|>user\n"
        f"What is the governance decision for this unit?\n{features}<|im_end|>\n"
        f"<|im_start|>assistant\n"
        f"Decision: {p['class']}\n"
        f"Governance: {p['governance']}\n"
        f"Rationale: {decision_rationale[p['class']]}<|im_end|>"
    )
    return {"text": text}


def emit_contrast_view(fu: dict, rng: random.Random) -> dict[str, Any] | None:
    """View 4: paired examples showing how meaning changes with activation state.

    Same substrate, different domain -> different FU status.
    Teaches the model that meaning = activation + relation + boundary + flow.
    """
    orig = fu["_original"]
    original_domain = fu["_domain"]

    # Pick a different domain
    alt_domains = [d for d in DOMAIN_SECTORS if d != original_domain]
    if not alt_domains:
        return None
    alt_domain = rng.choice(alt_domains)

    # Recompute with different domain
    alt_activation = compute_activation(orig, alt_domain)
    alt_permission = compute_permission(orig, alt_domain, alt_activation)
    alt_flow = compute_flow(orig, alt_domain, alt_permission)

    alt_operative = (
        alt_activation["activation_score"] > 0.35
        and alt_permission["governance"] == "ALLOW"
        and alt_flow["routable"]
    )
    alt_status = "operative" if alt_operative else (
        "inverse_null" if alt_activation["activation_score"] > 0.35 else "null"
    )

    # Only emit if the status actually changed
    if alt_status == fu["fu_status"]:
        return None

    text = (
        f"<|im_start|>user\n"
        f"The same substrate appears in two different domain contexts. "
        f"How does its functional status change?\n"
        f"Domain_A: {original_domain} | activation={fu['activation']['activation_score']} | "
        f"boundary={fu['permission']['class']} | status={fu['fu_status']}\n"
        f"Domain_B: {alt_domain} | activation={alt_activation['activation_score']} | "
        f"boundary={alt_permission['class']} | status={alt_status}<|im_end|>\n"
        f"<|im_start|>assistant\n"
        f"The unit changes from {fu['fu_status']} to {alt_status} when moving "
        f"from {original_domain} to {alt_domain}.\n"
        f"In {original_domain}: activation={fu['activation']['activation_score']}, "
        f"boundary={fu['permission']['class']}\n"
        f"In {alt_domain}: activation={alt_activation['activation_score']}, "
        f"boundary={alt_permission['class']}\n"
        f"This demonstrates that meaning is not intrinsic to the substrate. "
        f"It arises from activation + relation + boundary + flow in the current context.<|im_end|>"
    )
    return {"text": text}


# ============================================================================
# SOURCE LOADERS
# ============================================================================


def load_jsonl(path: Path, max_rows: int = 0) -> list[dict]:
    """Load JSONL file, return list of dicts."""
    if not path.exists():
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
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


def infer_domain(record: dict) -> str:
    """Infer domain from record metadata."""
    category = record.get("category", "")
    if category in CATEGORY_DOMAIN_MAP:
        return CATEGORY_DOMAIN_MAP[category]

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


# ============================================================================
# MAIN PIPELINE
# ============================================================================


def generate_fu_dataset(
    max_per_source: int = 0,
    seed: int = 42,
    contrast_fraction: float = 0.3,
) -> dict[str, Any]:
    """Generate all four FU training views."""
    rng = random.Random(seed)

    # Define sources
    sources = {
        "vault": APOLLO_DIR / "obsidian_vault_sft.jsonl",
        "l0_full": SFT_DIR / "l0_substrate_full_sft.jsonl",
        "l0_crossbraided": SFT_DIR / "l0_substrate_crossbraided.jsonl",
        "l0_l1": SFT_DIR / "l0_l1_substrate_sft.jsonl",
        "crosstagged": SFT_DIR / "spread_crosstagged_sft.jsonl",
        "recast_l1": SFT_DIR / "recast_l1_coordination_sft.jsonl",
        "recast_l2": SFT_DIR / "recast_l2_orientation_sft.jsonl",
        "recast_l3": SFT_DIR / "recast_l3_expression_sft.jsonl",
    }

    # Load all sources
    all_fu_records: list[dict] = []
    source_counts: dict[str, int] = {}

    for source_name, path in sources.items():
        raw = load_jsonl(path, max_per_source)
        if not raw:
            print(f"  {source_name}: SKIP (not found or empty)")
            continue

        count = 0
        for record in raw:
            domain = infer_domain(record)
            fu = build_fu_record(record, source_name, domain)
            all_fu_records.append(fu)
            count += 1

        source_counts[source_name] = count
        print(f"  {source_name}: {count} records -> FU schema")

    print(f"\nTotal canonical FU records: {len(all_fu_records)}")

    # Shuffle
    rng.shuffle(all_fu_records)

    # Generate views (text format for TRL language modeling)
    sft_records: list[dict] = []
    activation_records: list[dict] = []
    governance_records: list[dict] = []
    contrast_records: list[dict] = []

    # Cross-surface views (messages format for TRL conversational + OpenAI)
    msg_sft_records: list[dict] = []
    msg_activation_records: list[dict] = []
    msg_governance_records: list[dict] = []
    msg_contrast_records: list[dict] = []

    for fu in all_fu_records:
        # View 1: SFT (text + messages)
        sft = emit_sft_view(fu)
        if sft:
            sft_records.append(sft)
        msg_sft = emit_messages_sft(fu)
        if msg_sft:
            msg_sft_records.append(msg_sft)

        # View 2: Activation classification (text + messages)
        activation_records.append(emit_activation_view(fu))
        msg_activation_records.append(emit_messages_activation(fu))

        # View 3: Governance decision (text + messages)
        governance_records.append(emit_governance_view(fu))
        msg_governance_records.append(emit_messages_governance(fu))

        # View 4: Contrast (only for a fraction, text + messages)
        if rng.random() < contrast_fraction:
            contrast = emit_contrast_view(fu, rng)
            if contrast:
                contrast_records.append(contrast)
            msg_contrast = emit_messages_contrast(fu, rng)
            if msg_contrast:
                msg_contrast_records.append(msg_contrast)

    # Also save canonical records (structured, not flattened)
    canonical_records = []
    for fu in all_fu_records:
        canon = {k: v for k, v in fu.items() if not k.startswith("_")}
        # Add target fields from original
        orig = fu["_original"]
        canon["target"] = {
            "instruction": orig.get("instruction", ""),
            "response": orig.get("output", orig.get("response", "")),
        }
        canonical_records.append(canon)

    return {
        "canonical": canonical_records,
        "sft": sft_records,
        "activation": activation_records,
        "governance": governance_records,
        "contrast": contrast_records,
        # Cross-surface (messages format)
        "messages_sft": msg_sft_records,
        "messages_activation": msg_activation_records,
        "messages_governance": msg_governance_records,
        "messages_contrast": msg_contrast_records,
        "source_counts": source_counts,
    }


def write_jsonl(records: list[dict], path: Path) -> int:
    """Write records to JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(records)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-per-source", type=int, default=0,
                        help="Max records per source (0=all)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--contrast-fraction", type=float, default=0.3)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    print("=" * 60)
    print("FUNCTIONAL UNIT DATASET GENERATOR — Round 7")
    print("FU_i(t) = S · A · R · P · F")
    print("meaning = activation + relation + boundary + flow")
    print("=" * 60)
    print()

    t0 = time.time()

    print("Loading sources...")
    result = generate_fu_dataset(
        max_per_source=args.max_per_source,
        seed=args.seed,
        contrast_fraction=args.contrast_fraction,
    )

    # Write all views
    prefix = "round7_fu"
    paths = {}

    all_views = [
        "canonical", "sft", "activation", "governance", "contrast",
        "messages_sft", "messages_activation", "messages_governance", "messages_contrast",
    ]

    print("\nWriting datasets...")
    for view_name in all_views:
        records = result[view_name]
        path = args.output_dir / f"{prefix}_{view_name}.jsonl"
        n = write_jsonl(records, path)
        size_mb = path.stat().st_size / (1024 * 1024)
        paths[view_name] = path
        print(f"  {view_name}: {n} records, {size_mb:.1f} MB -> {path.name}")

    # Stats
    elapsed = time.time() - t0

    # FU status distribution
    status_counts = Counter(r["fu_status"] for r in result["canonical"])
    boundary_counts = Counter(r["permission"]["class"] for r in result["canonical"])

    print()
    print("=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"Sources:    {len(result['source_counts'])}")
    print(f"Canonical:  {len(result['canonical'])} records")
    print(f"SFT:        {len(result['sft'])} records (text) / {len(result['messages_sft'])} (messages)")
    print(f"Activation: {len(result['activation'])} records (text) / {len(result['messages_activation'])} (messages)")
    print(f"Governance: {len(result['governance'])} records (text) / {len(result['messages_governance'])} (messages)")
    print(f"Contrast:   {len(result['contrast'])} records (text) / {len(result['messages_contrast'])} (messages)")
    print()
    print(f"FU Status:  {dict(status_counts)}")
    print(f"Boundary:   {dict(boundary_counts)}")
    print(f"Time:       {elapsed:.1f}s")
    print()
    print("Training views:")
    for name, path in paths.items():
        print(f"  {name}: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
