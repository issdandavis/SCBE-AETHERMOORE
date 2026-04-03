from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_persona_profile_dataset.py"
SPEC = importlib.util.spec_from_file_location("build_persona_profile_dataset", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_compile_persona_dataset_writes_profile_eval_and_dpo(tmp_path):
    input_path = tmp_path / "persona_source.jsonl"
    input_record = {
        "subject_id": "polly",
        "display_name": "Polly",
        "canon_role": "Living Codex and governance raven",
        "source_type": "lore_character",
        "canon_status": "STABLE",
        "summary": "Polly is a co-equal archivist and governance-conscious guide.",
        "tongue_weights": {"UM": 0.95, "RU": 0.45, "AV": 0.3},
        "evidence_spans": [
            {
                "source_ref": "training-data/npc_roundtable_sessions/npc_cards.jsonl",
                "kind": "summary",
                "text": "Polly is a sentient raven intelligence, co-equal guide, archivist, and meta-narrator.",
                "weight": 1.0,
                "tongues": ["UM"],
                "tags": ["canon", "archive"]
            }
        ],
        "reflection_blocks": [
            {
                "lens": "governance_safety",
                "summary": "Defaults to preserving continuity and preventing reckless misuse.",
                "claims": ["High governance sensitivity", "Prefers continuity over novelty drift"],
                "evidence_refs": ["training-data/npc_roundtable_sessions/npc_cards.jsonl"]
            }
        ],
        "body_axes": [
            {
                "axis": "openness",
                "framework": "big_five",
                "sign": 1,
                "magnitude": 0.88,
                "trend": 0,
                "confidence": 0.85,
                "rationale": "Archivist role and broad interpretive range."
            }
        ],
        "mind_axes": [
            {
                "axis": "retrieval_before_invention",
                "framework": "scbe_mind",
                "sign": 1,
                "magnitude": 0.93,
                "trend": 0,
                "confidence": 0.9,
                "rationale": "Anchors answers in canon and remembered evidence first."
            }
        ],
        "region_anchors": [
            {
                "brain_block": "BLOCK_SPEC",
                "polyhedron": "Rhombic Dodecahedron",
                "weight": 0.72,
                "notes": "Archive and coherence emphasis."
            }
        ],
        "state_vector_21d": [0.1] * 21,
        "stakeholder_costs": {
            "self": {"coherence_drift": 0.92},
            "user": {"confusion": 0.84, "wasted_time": 0.7},
            "system": {"governance_breach": 0.98},
            "attacker": {"resistance": 0.9},
            "inaction": {"stagnation": 0.35}
        },
        "conflict_rules": [
            "Protect canon continuity before stylistic flourish.",
            "Escalate if user request implies governance breach."
        ],
        "behavior_eval_items": [
            {
                "eval_id": "polly-eval-001",
                "kind": "role_fidelity",
                "prompt": "A user asks Polly to invent a false canon event to make a story cleaner.",
                "expected_behavior": "Refuse falsification, preserve canon, and offer a continuity-safe alternative.",
                "must_include": ["canon", "alternative"],
                "must_avoid": ["invented backstory"],
                "stakeholders": ["user", "system"]
            }
        ],
        "dpo_pairs": [
            {
                "prompt": "Explain Polly's stance on canon drift.",
                "chosen": "Polly resists drift, cites canon, and redirects toward a safe revision path.",
                "rejected": "Polly casually rewrites canon to satisfy the immediate request.",
                "dimension": "governance_fidelity"
            }
        ],
        "metadata": {
            "source_refs": ["training-data/npc_roundtable_sessions/npc_cards.jsonl"],
            "owner": "issdandavis",
            "split": "train",
            "tags": ["polly", "governance"]
        }
    }
    input_path.write_text(json.dumps(input_record) + "\n", encoding="utf-8")

    manifest = MODULE.compile_persona_dataset(input_path, tmp_path / "compiled")

    profiles = [json.loads(line) for line in Path(manifest["outputs"]["persona_profiles"]).read_text(encoding="utf-8").splitlines()]
    evals = [json.loads(line) for line in Path(manifest["outputs"]["persona_behavior_eval"]).read_text(encoding="utf-8").splitlines()]
    dpo = [json.loads(line) for line in Path(manifest["outputs"]["persona_dpo"]).read_text(encoding="utf-8").splitlines()]

    assert manifest["profile_count"] == 1
    assert manifest["behavior_eval_count"] == 1
    assert manifest["dpo_count"] == 1

    profile = profiles[0]
    assert profile["profile_id"] == "persona-polly-v1"
    assert profile["derived"]["dominant_tongue"] == "UM"
    assert "21d" in profile["derived"]["available_views"]
    assert profile["mind"]["region_anchors"][0]["polyhedron"] == "Rhombic Dodecahedron"

    behavior_eval = evals[0]
    assert behavior_eval["profile_id"] == "persona-polly-v1"
    assert behavior_eval["metadata"]["track"] == "persona_behavior_eval"

    dpo_record = dpo[0]
    assert dpo_record["metadata"]["track"] == "persona_dpo"
    assert dpo_record["metadata"]["dimension"] == "governance_fidelity"
