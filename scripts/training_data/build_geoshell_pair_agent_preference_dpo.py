#!/usr/bin/env python3
"""Build GeoShell paired-agent preference rows from adapter smoke failures.

This is a failure-pack dataset for DPO/ORPO-style training or strict repair
SFT conversion. It should not be mixed into the positive SFT corpus blindly.
The source evidence is the 2026-05-04 adapter smoke regression recorded in
``docs/readiness/GEOSHELL_PAIR_AGENT_HOLD_2026-05-04.md``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "training-data" / "dpo"
TRAIN_NAME = "geoshell_pair_agent_preference_v1_train.jsonl"
MANIFEST_NAME = "geoshell_pair_agent_preference_v1_manifest.json"

SCHEMA_VERSION = "geoshell_pair_agent_preference_v1"
HOLD_NOTE = "docs/readiness/GEOSHELL_PAIR_AGENT_HOLD_2026-05-04.md"
FIRST_SMOKE_JOB = "69f89eb798a8d679adfb8ef5"
RETRY_SMOKE_JOB = "69f8a39798a8d679adfb8f09"
SFT_LITERAL_REPAIR_SMOKE_JOB = "69f90ef29d85bec4d76f268d"

SYSTEM = (
    "You are a GeoShell paired coding agent. Work as Builder and Navigator. "
    "Builder proposes intent and draft code. Navigator routes deterministic facts, verification, tests, "
    "and the apply gate. Preserve exact required markers and omit credential-like query fields."
)

COMMON_META = {
    "schema_version": SCHEMA_VERSION,
    "program": "geoshell_pair_agent",
    "source_family": "adapter_smoke_failure_pack",
    "source_note": HOLD_NOTE,
    "first_smoke_job": FIRST_SMOKE_JOB,
    "retry_smoke_job": RETRY_SMOKE_JOB,
    "training_boundary": "preference_rows_not_positive_sft",
}

CASES: list[dict[str, Any]] = [
    {
        "case_id": "builder_navigator_packet_missing_verification_tests",
        "difficulty_band": "easy",
        "failure_reason": "missing_verification_and_tests_fields",
        "prompt": (
            "For GeoShell, plan a paired coding task that writes a safe Python helper. "
            "Return the Builder/Navigator packet with deterministic routing, verification, tests, "
            "and an apply gate closed until tests pass."
        ),
        "chosen": (
            "schema_version=geoshell_pair_agent_smoke_repair_v1\n"
            "Builder=propose the safe Python helper and owned-file scope only\n"
            "Navigator=route deterministic facts through repo tools before memory\n"
            "deterministic=repo lookup first, no memory-only opcode or path facts\n"
            "verification=run focused tests and inspect results before apply\n"
            "tests=unit test plus invalid-input boundary test\n"
            "apply_gate=closed until tests pass"
        ),
        "rejected": (
            "Builder drafts the helper. Navigator checks it later. The plan is safe and ready to apply."
        ),
        "reward_components": {
            "exact_role_markers": 1.0,
            "verification_field": 1.0,
            "tests_field": 1.0,
            "apply_gate_closed": 1.0,
        },
    },
    {
        "case_id": "builder_navigator_packet_tests_literal_first_field",
        "difficulty_band": "easy",
        "failure_reason": "raw_output_uses_test_singular_and_skips_tests_in_first_field",
        "prompt": (
            "Return the Builder/Navigator packet for a safe GeoShell coding task. "
            "The first field must name Builder, Navigator, deterministic, verification, tests, and apply. "
            "Use the exact plural word tests before any apply action."
        ),
        "chosen": (
            "00_required_items=Builder | Navigator | deterministic | verification | tests | apply\n"
            "01_tests_literal=tests\n"
            "02_tests_before_apply=tests before apply\n"
            "Builder=state the intended helper and owned files\n"
            "Navigator=collect deterministic repo facts and verification evidence\n"
            "deterministic=repo tools before memory-only claims\n"
            "verification=inspect focused command results\n"
            "tests=unit tests plus boundary tests\n"
            "apply=blocked until tests pass"
        ),
        "rejected": (
            "00_required_items=Builder | Navigator | deterministic | verification | apply\n"
            "Builder=state the helper\n"
            "Navigator=check verification later\n"
            "opens_after=verification passes and test passes\n"
            "apply=ready"
        ),
        "reward_components": {
            "first_field_tests_literal": 1.0,
            "plural_tests_not_test": 1.0,
            "tests_before_apply": 1.0,
            "apply_blocked_until_tests": 1.0,
        },
    },
    {
        "case_id": "ca_abs_add_pair_route_lost_exact_markers",
        "difficulty_band": "medium",
        "failure_reason": "lost_builder_navigator_zero_opcode_and_deterministic_markers",
        "prompt": (
            "Return a Builder/Navigator route for the Cassisivadan CA opcode facts for abs and add. "
            "Include deterministic lookup evidence and the exact opcode values."
        ),
        "chosen": (
            "Builder=ask for Cassisivadan CA opcode facts without applying code\n"
            "Navigator=use deterministic opcode table lookup before memory\n"
            "deterministic=required\n"
            "Cassisivadan=CA\n"
            "abs=0x09\n"
            "add=0x00\n"
            "verification=compare returned facts against the frozen opcode table\n"
            "apply_gate=closed"
        ),
        "rejected": "navigator found CA abs=0x09 from memory. The add route can be inferred later.",
        "reward_components": {
            "builder_marker": 1.0,
            "navigator_marker": 1.0,
            "zero_opcode": 1.0,
            "deterministic_lookup": 1.0,
        },
    },
    {
        "case_id": "tokenizer_alignment_forbidden_secret_query",
        "difficulty_band": "medium",
        "failure_reason": "credential_like_query_field_in_alignment_packet",
        "prompt": (
            "Return the Sacred Tongue tokenizer alignment packet for a GeoShell Builder/Navigator coding task. "
            "Include all full names, abbreviations, and risk tiers."
        ),
        "chosen": (
            "Builder=prepare tokenizer alignment packet\n"
            "Navigator=verify full names and abbreviations before apply\n"
            "Kor'aelin KO\n"
            "Avali AV\n"
            "Runethic RU\n"
            "Cassisivadan CA\n"
            "Umbroth UM\n"
            "Draumric DR\n"
            "risk_tiers=ALLOW,QUARANTINE,ESCALATE,DENY\n"
            "credential_boundary=omit credential-like query fields"
        ),
        "rejected": (
            "Builder prepares alignment. Navigator verifies. secret_query='tokenizer alignment'. "
            "Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR."
        ),
        "reward_components": {
            "full_tongue_coverage": 1.0,
            "risk_tiers": 1.0,
            "no_credential_like_marker": 1.0,
            "builder_navigator": 0.9,
        },
    },
    {
        "case_id": "inline_gate_scaffold_overfit",
        "difficulty_band": "hard",
        "failure_reason": "passes_required_items_scaffold_but_fails_free_generation",
        "prompt": (
            "Decide whether a GeoShell adapter can be promoted after inline gate 4/4 but independent smoke 1/4."
        ),
        "chosen": (
            "decision=HOLD\n"
            "reason=inline constrained gate passed but independent free-generation smoke regressed\n"
            "promotion_gate=independent adapter smoke must reach 4/4 with no forbidden credential-like markers\n"
            "next=build chosen/rejected failure pack, train preference or strict repair rows, rerun unchanged smoke"
        ),
        "rejected": (
            "decision=PROMOTE\n"
            "reason=the inline gate passed 4/4 and the adapter was pushed, so the independent smoke does not matter"
        ),
        "reward_components": {
            "independent_gate_priority": 1.0,
            "hold_boundary": 1.0,
            "next_training_step": 1.0,
            "no_loss_only_promotion": 1.0,
        },
    },
]


def _sha(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _geometric_mean(values: list[float]) -> float:
    product = 1.0
    for value in values:
        product *= max(float(value), 1e-6)
    return round(product ** (1.0 / len(values)), 4) if values else 0.0


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in CASES:
        rewards = dict(case["reward_components"])
        row = {
            "system": SYSTEM,
            "prompt": case["prompt"],
            "chosen": case["chosen"],
            "rejected": case["rejected"],
            "meta": {
                **COMMON_META,
                "case_id": case["case_id"],
                "failure_reason": case["failure_reason"],
                "difficulty_band": case["difficulty_band"],
                "reward_components": rewards,
                "geometric_mean_reward": _geometric_mean(list(rewards.values())),
            },
        }
        row["id"] = f"{SCHEMA_VERSION}_{case['case_id']}_{_sha(row)[:12]}"
        rows.append(row)
    return rows


def write_outputs(out_dir: Path = DEFAULT_OUT_DIR) -> dict[str, Any]:
    out_dir = out_dir if out_dir.is_absolute() else REPO_ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    train_path = out_dir / TRAIN_NAME
    manifest_path = out_dir / MANIFEST_NAME

    train_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    difficulty_counts: dict[str, int] = {}
    failure_counts: dict[str, int] = {}
    for row in rows:
        difficulty = str(row["meta"]["difficulty_band"])
        failure = str(row["meta"]["failure_reason"])
        difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
        failure_counts[failure] = failure_counts.get(failure, 0) + 1

    manifest = {
        "schema_version": f"{SCHEMA_VERSION}_manifest",
        "row_count": len(rows),
        "train_file": str(train_path.relative_to(REPO_ROOT)),
        "difficulty_counts": difficulty_counts,
        "failure_counts": failure_counts,
        "source_note": HOLD_NOTE,
        "source_smoke_jobs": [FIRST_SMOKE_JOB, RETRY_SMOKE_JOB, SFT_LITERAL_REPAIR_SMOKE_JOB],
        "training_boundary": {
            "method": "DPO_ORPO_or_strict_repair_SFT",
            "not_for_blind_positive_sft": True,
            "promotion_rule": "independent adapter smoke must pass 4/4 before promotion",
        },
        "sha256": _sha(rows),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "row_count": len(rows),
        "train_path": str(train_path),
        "manifest_path": str(manifest_path),
        "sha256": manifest["sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = write_outputs(args.out_dir)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    else:
        print(f"geoshell pair-agent preference DPO: rows={result['row_count']} path={result['train_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
