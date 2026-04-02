#!/usr/bin/env python3
"""Clean and consolidate training data labels.

Fixes three problems:
1. 690K 'unknown' records drowning real signal
2. 254 labels with massive class imbalance (134 labels have <10 samples)
3. Duplicate/overlapping label names (e.g., 'harmonic-wall' vs 'harmonic_wall')

Outputs a cleaned JSONL file with consolidated labels and balanced sampling.
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

# ── Label Taxonomy ──────────────────────────────────────────────────────
# Map 254 raw labels → ~25 consolidated families

LABEL_MAP: dict[str, str] = {
    # ── Architecture & Infrastructure ──
    "architecture": "architecture",
    "architecture-reference": "architecture",
    "architecture_explanation": "architecture",
    "architecture_overview": "architecture",
    "architecture_sessions": "architecture",
    "pipeline": "architecture",
    "integration": "architecture",
    "framework": "architecture",

    # ── Code & Engineering ──
    "code": "code_engineering",
    "code_example": "code_engineering",
    "code_review": "code_engineering",
    "codebase_understanding": "code_engineering",
    "cross_file": "code_engineering",
    "ci_fix": "code_engineering",
    "git_workflow": "code_engineering",
    "sft_codebase": "code_engineering",
    "sft_codebase_new": "code_engineering",
    "sft_functions": "code_engineering",
    "testing": "code_engineering",

    # ── Cryptography & Security ──
    "crypto": "crypto_security",
    "post-quantum-crypto": "crypto_security",
    "ml-dsa": "crypto_security",
    "ml-kem": "crypto_security",
    "hmac-chain": "crypto_security",
    "security": "crypto_security",
    "safety": "crypto_security",
    "authentication": "crypto_security",
    "verification": "crypto_security",
    "tamper_evidence": "crypto_security",
    "provenance": "crypto_security",

    # ── Governance ──
    "governance": "governance",
    "governance-reference": "governance",
    "sft_governance": "governance",
    "ouroboros-governance": "governance",
    "ouroboros-invariants": "governance",
    "ouroboros-specs": "governance",
    "ouroboros-examples": "governance",
    "council_review": "governance",
    "runtime_decision": "governance",
    "principle": "governance",
    "regulatory": "governance",
    "evidence_capture": "governance",
    "calibration": "governance",

    # ── Math & Geometry ──
    "math": "math_geometry",
    "math_explanation": "math_geometry",
    "math_security": "math_geometry",
    "math_sessions": "math_geometry",
    "geometry": "math_geometry",
    "poincare-ball": "math_geometry",
    "poincare-embedding": "math_geometry",
    "polyhedra": "math_geometry",
    "golden-ratio": "math_geometry",
    "fibonacci_trust": "math_geometry",
    "phi_shells": "math_geometry",
    "msr-algebra": "math_geometry",
    "theorem_proof": "math_geometry",
    "formal_proof": "math_geometry",

    # ── Harmonic & Spectral ──
    "harmonic-scaling": "harmonic_spectral",
    "harmonic-wall": "harmonic_spectral",
    "harmonic_wall": "harmonic_spectral",
    "breathing": "harmonic_spectral",
    "phase-diagram": "harmonic_spectral",
    "phason": "harmonic_spectral",
    "phason-shift": "harmonic_spectral",
    "spectral": "harmonic_spectral",
    "energy": "harmonic_spectral",
    "energy-conservation": "harmonic_spectral",
    "cost_function": "harmonic_spectral",

    # ── Sacred Tongues & Tokenizer ──
    "sacred-tongues": "sacred_tongues",
    "sacred_tongues": "sacred_tongues",
    "tongues_explanation": "sacred_tongues",
    "tongues_lore": "sacred_tongues",
    "tongues_sessions": "sacred_tongues",
    "tongues_technical": "sacred_tongues",
    "tongue_coordinates": "sacred_tongues",
    "kor-aelin": "sacred_tongues",
    "tokenizer-alignment": "sacred_tongues",
    "encoding-systems": "sacred_tongues",
    "runic-alphabet": "sacred_tongues",

    # ── Topology & Manifold ──
    "topology": "topology_manifold",
    "quasicrystal": "topology_manifold",
    "quantum-lattice": "topology_manifold",
    "quantum": "topology_manifold",
    "21d-embedding": "topology_manifold",
    "axiom_mesh": "topology_manifold",
    "toroidal": "topology_manifold",
    "particle-grammar": "topology_manifold",
    "fractal": "topology_manifold",
    "null_space": "topology_manifold",

    # ── Layers & Pipeline ──
    "layers": "layers_pipeline",
    "layer_detail": "layers_pipeline",
    "constants": "layers_pipeline",

    # ── Trust & Zones ──
    "trust-rings": "trust_zones",
    "trust-tube": "trust_zones",
    "trust-tubes": "trust_zones",
    "trust_modulation": "trust_zones",
    "zones": "trust_zones",
    "geometric-cages": "trust_zones",

    # ── Spiral & Protocol ──
    "spiral-seal": "spiralverse",
    "spiralverse-lore": "spiralverse",
    "sft_spiralverse": "spiralverse",

    # ── Lore & Narrative ──
    "lore_reference": "lore_narrative",
    "lore_explanation": "lore_narrative",
    "lore_character": "lore_narrative",
    "lore_outline": "lore_narrative",
    "lore_sessions": "lore_narrative",
    "lore_strategy": "lore_narrative",
    "lore_worldbuilding": "lore_narrative",
    "story-lore": "lore_narrative",
    "story-protocol": "lore_narrative",
    "story-tech-mapping": "lore_narrative",
    "narrative_technical": "lore_narrative",
    "roleplay_narrative": "lore_narrative",
    "origin_story": "lore_narrative",

    # ── Game Design ──
    "game_design": "game_design",
    "game_design_sessions": "game_design",
    "game_sessions": "game_design",
    "gacha_sessions": "game_design",
    "mini_game_design": "game_design",
    "battle": "game_design",
    "tower_floor": "game_design",
    "dialogue": "game_design",
    "choice": "game_design",
    "close": "game_design",
    "start": "game_design",
    "step": "game_design",
    "stop": "game_design",
    "transition": "game_design",
    "sft_iseki": "game_design",

    # ── Vault Systems ──
    "vault_av": "vault_systems",
    "vault_ca": "vault_systems",
    "vault_dr": "vault_systems",
    "vault_graph": "vault_systems",
    "vault_ko": "vault_systems",
    "vault_ru": "vault_systems",
    "vault_um": "vault_systems",

    # ── Multi-Agent & Fleet ──
    "multi-agent": "multi_agent",
    "fleet-management": "multi_agent",
    "coordination": "multi_agent",
    "distributed": "multi_agent",
    "routing": "multi_agent",
    "reroute": "multi_agent",
    "navigation": "multi_agent",
    "bft_consensus": "multi_agent",
    "quorum_design": "multi_agent",
    "hamiltonian": "multi_agent",
    "hamiltonian-routing": "multi_agent",

    # ── ML & Training ──
    "machine-learning": "ml_training",
    "nlp": "ml_training",
    "instruction-tuning": "ml_training",
    "training": "ml_training",
    "training_data": "ml_training",
    "datasets": "ml_training",
    "knowledge_graph": "ml_training",
    "sft_ouroboros": "ml_training",
    "dpo_covenant": "ml_training",
    "dpo_genesis": "ml_training",
    "dpo_invitation": "ml_training",
    "dpo_sabbath": "ml_training",
    "dpo_sanctuary": "ml_training",
    "dpo_witness": "ml_training",
    "evolution": "ml_training",
    "confidence_trigger": "ml_training",
    "adaptive_defense": "ml_training",

    # ── Research & Academic ──
    "academic": "research",
    "research_bridge_arxiv": "research",
    "research_bridge_obsidian": "research",
    "research_ops": "research",
    "theory": "research",
    "science": "research",
    "biomedical": "research",
    "bone-density": "research",
    "sft_notion": "research",
    "notebook-reference": "research",

    # ── Documentation ──
    "doc_chunk": "documentation",
    "documentation": "documentation",
    "kernel-docs": "documentation",
    "knowledge-base": "documentation",
    "knowledge_ops": "documentation",
    "library": "documentation",

    # ── Web & Browser ──
    "browser.run_headless": "web_ops",
    "browser_readiness": "web_ops",
    "web_corpus": "web_ops",
    "web_research_chunk": "web_ops",
    "dark_web_legitimate": "web_ops",
    "field_trip_tor": "web_ops",

    # ── Ops & Infrastructure ──
    "telemetry": "ops_infra",
    "tracking": "ops_infra",
    "storage": "ops_infra",
    "compute": "ops_infra",
    "execution": "ops_infra",
    "publish": "ops_infra",
    "update": "ops_infra",
    "deploy": "ops_infra",
    "deployment": "ops_infra",
    "ops_crm": "ops_infra",

    # ── Business & Finance ──
    "ai_subscription_deduction": "business_finance",
    "business_loss": "business_finance",
    "business_loss_w2_offset": "business_finance",
    "capital_gains": "business_finance",
    "cash_app_tax_platform": "business_finance",
    "crypto_auto_buy": "business_finance",
    "crypto_tax": "business_finance",
    "design_tool_deduction": "business_finance",
    "economics": "business_finance",
    "expense_classification": "business_finance",
    "expense_exceeds_income": "business_finance",
    "game_research_deduction": "business_finance",
    "game_research_expense": "business_finance",
    "gumroad_error": "business_finance",
    "gumroad_local_verification": "business_finance",
    "hobby_loss_defense": "business_finance",
    "home_office": "business_finance",
    "home_office_family_home": "business_finance",
    "internet_family_home": "business_finance",
    "mixed_use_phone": "business_finance",
    "partial_deduction": "business_finance",
    "patent_expense": "business_finance",
    "payment": "business_finance",
    "qbi_deduction": "business_finance",
    "quarterly_estimated_payments": "business_finance",
    "research_expense": "business_finance",
    "saas_deduction_organization": "business_finance",
    "self_publishing_royalties": "business_finance",
    "small_revenue_reporting": "business_finance",
    "stock_trading_many_positions": "business_finance",
    "tax_basics": "business_finance",
    "washington_no_income_tax": "business_finance",
    "youtube_business_income": "business_finance",
    "youtube_ca": "business_finance",

    # ── Communication ──
    "email_triage": "communication",
    "form_fill": "communication",
    "file_upload": "communication",
    "app_command": "communication",
    "non_technical": "communication",

    # ── Creative & Media ──
    "music_composition": "creative_media",
    "music_lyrics": "creative_media",
    "music_production": "creative_media",
    "music_sessions": "creative_media",
    "magical-properties": "creative_media",

    # ── AI & Agents ──
    "ai": "ai_agents",
    "sidekick": "ai_agents",
    "sidekick_memory": "ai_agents",
    "curriculum": "ai_agents",
    "project_memory": "ai_agents",
    "diagnosis": "ai_agents",
    "incident": "ai_agents",
    "fail_to_noise": "ai_agents",
    "attack_example": "ai_agents",

    # ── Knowledge Systems ──
    "ip": "knowledge_systems",
    "legal_record": "knowledge_systems",
    "archive": "knowledge_systems",

    # ── Misc (explicit catch) ──
    "fsgs": "medical",
}


def map_label(raw: str) -> str | None:
    """Map raw label to consolidated family. Returns None if should be dropped."""
    if raw == "unknown":
        return None  # Drop unknown
    return LABEL_MAP.get(raw, raw)  # Pass through unmapped labels as-is


def text_from_record(row: dict) -> str:
    inst = row.get("instruction")
    resp = row.get("response")
    if isinstance(inst, str) and isinstance(resp, str):
        text = f"{inst.strip()} {resp.strip()}".strip()
        if text:
            return text
    msgs = row.get("messages")
    if isinstance(msgs, list):
        parts = []
        for m in msgs:
            if not isinstance(m, dict):
                continue
            content = str(m.get("content", "")).strip()
            if content:
                parts.append(content)
        joined = " ".join(parts).strip()
        if joined:
            return joined
    parts = []
    for key in ("dataset", "event_type", "message", "reason", "product", "status"):
        val = row.get(key)
        if val is not None:
            parts.append(str(val))
    payload = row.get("event_payload")
    if payload is not None:
        if isinstance(payload, dict):
            parts.append(json.dumps(payload, sort_keys=True))
        else:
            parts.append(str(payload))
    return " ".join(parts).strip()


def raw_label(row: dict) -> str:
    cat = str(row.get("category", "")).strip()
    if cat:
        return cat
    if isinstance(row.get("meta"), dict):
        source_type = str(row["meta"].get("source_type", "")).strip()
        if source_type:
            return source_type
    for key in ("event_type", "dataset", "status"):
        val = str(row.get(key, "")).strip()
        if val:
            return val
    return "unknown"


def main():
    random.seed(42)
    input_patterns = ["training/**/*.jsonl", "training-data/**/*.jsonl"]
    output_path = Path("training-data/cleaned/consolidated_labels.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Pass 1: collect all records with mapped labels
    records: list[dict] = []
    label_counter = Counter()
    dropped_unknown = 0
    dropped_empty = 0
    raw_to_mapped = Counter()

    for pattern in input_patterns:
        for path in sorted(Path(".").glob(pattern)):
            if not path.is_file() or "cleaned" in str(path):
                continue
            try:
                with path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            row = json.loads(line)
                        except Exception:
                            continue
                        if not isinstance(row, dict):
                            continue

                        text = text_from_record(row)
                        if not text or len(text) < 10:
                            dropped_empty += 1
                            continue

                        rl = raw_label(row)
                        mapped = map_label(rl)
                        if mapped is None:
                            dropped_unknown += 1
                            continue

                        raw_to_mapped[f"{rl} -> {mapped}"] += 1
                        label_counter[mapped] += 1
                        records.append({
                            "instruction": row.get("instruction", text[:200]),
                            "response": row.get("response", ""),
                            "category": mapped,
                            "original_category": rl,
                            "messages": row.get("messages"),
                        })
            except Exception:
                continue

    print(f"Pass 1 complete:")
    print(f"  Total records with labels: {len(records)}")
    print(f"  Dropped 'unknown': {dropped_unknown}")
    print(f"  Dropped empty/short: {dropped_empty}")
    print(f"  Consolidated labels: {len(label_counter)}")
    print()

    # Pass 2: balanced sampling
    # Cap each label at max 5000 samples, floor at minimum 10
    MAX_PER_LABEL = 5000
    MIN_PER_LABEL = 10

    by_label: dict[str, list[dict]] = {}
    for rec in records:
        by_label.setdefault(rec["category"], []).append(rec)

    final_records: list[dict] = []
    label_stats: list[tuple[str, int, int]] = []

    for label in sorted(by_label.keys()):
        pool = by_label[label]
        original_count = len(pool)

        if original_count < MIN_PER_LABEL:
            # Drop labels with too few samples
            label_stats.append((label, original_count, 0))
            continue

        random.shuffle(pool)
        sampled = pool[:MAX_PER_LABEL]
        final_records.append(None)  # placeholder
        final_records.pop()
        final_records.extend(sampled)
        label_stats.append((label, original_count, len(sampled)))

    random.shuffle(final_records)

    # Write output
    with output_path.open("w", encoding="utf-8") as f:
        for rec in final_records:
            # Clean the record for output
            out = {
                "instruction": rec.get("instruction", ""),
                "response": rec.get("response", ""),
                "category": rec["category"],
            }
            if rec.get("messages"):
                out["messages"] = rec["messages"]
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    print(f"Pass 2 complete:")
    print(f"  Output: {output_path}")
    print(f"  Final records: {len(final_records)}")
    print()

    # Summary table
    final_counter = Counter(r["category"] for r in final_records)
    print(f"{'Label':<25} {'Raw':>8} {'Final':>8} {'Action':<12}")
    print("-" * 60)
    for label, raw_count, final_count in sorted(label_stats, key=lambda x: -x[2]):
        action = "kept" if final_count == raw_count else ("capped" if final_count > 0 else "DROPPED")
        print(f"{label:<25} {raw_count:>8} {final_count:>8} {action:<12}")

    print()
    print(f"Final label count: {len(final_counter)}")
    print(f"Final record count: {len(final_records)}")
    print(f"Min samples/label: {min(final_counter.values())}")
    print(f"Max samples/label: {max(final_counter.values())}")
    print(f"Median samples/label: {sorted(final_counter.values())[len(final_counter)//2]}")


if __name__ == "__main__":
    main()
