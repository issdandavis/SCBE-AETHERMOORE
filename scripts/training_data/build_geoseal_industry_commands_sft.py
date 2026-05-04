#!/usr/bin/env python3
"""Build GeoSeal industry-command use-case SFT rows.

This pack teaches the agent to map both specific CLI requests and ambiguous
operator intent into the next GeoSeal command family. It is offline-only and
does not execute commands or call providers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "training-data" / "sft"
DEFAULT_KAGGLE_DIR = REPO_ROOT / "artifacts" / "kaggle_datasets" / "scbe-coding-agent-stage6-repair-v7"

TRAIN_NAME = "geoseal_industry_commands_v1_train.sft.jsonl"
EVAL_NAME = "geoseal_industry_commands_v1_eval.sft.jsonl"
MANIFEST_NAME = "geoseal_industry_commands_v1_manifest.json"

SYSTEM = (
    "You are a GeoSeal CLI command-routing agent. Convert operator intent into "
    "the smallest safe command plan. Prefer exact existing commands when known, "
    "mark proposed commands as planned when they are not implemented yet, preserve "
    "receipts, never expose secrets, and return compact JSON."
)


COMMAND_FAMILIES = {
    "auth": {
        "planned": ["geoseal auth status", "geoseal auth login <provider>", "geoseal auth mirror <provider>"],
        "purpose": "credential readiness, login, and local encrypted key mirror checks",
    },
    "models": {
        "planned": [
            "geoseal models list",
            "geoseal models probe",
            "geoseal models recommend --task coding",
        ],
        "purpose": "discover callable local, free-tier, and paid model lanes",
    },
    "factory": {
        "existing": [
            (
                "python scripts/benchmark/harness_provider_matrix.py --software-factory "
                "--task-id <task-id> --json"
            )
        ],
        "planned": [
            "geoseal factory run --task <task>",
            "geoseal factory logs <run-id>",
            "geoseal factory replay <run-id>",
            "geoseal factory promote <run-id>",
        ],
        "purpose": "software-factory task lifecycle with prompt packet, branch strategy, logs, and gates",
    },
    "sandbox": {
        "planned": [
            "geoseal sandbox create",
            "geoseal sandbox close",
            "geoseal sandbox clean",
            "geoseal worktree list",
        ],
        "purpose": "Docker, Podman, Vercel, no-sandbox, and worktree lifecycle control",
    },
    "bench": {
        "existing": [
            "npm run benchmark:cli",
            "python scripts/benchmark/harness_provider_matrix.py --software-factory --json",
        ],
        "planned": [
            "geoseal bench run --suite agentic-cli",
            "geoseal bench compare --target sandcastle",
            "geoseal bench report",
        ],
        "purpose": "prove harness quality against public agentic coding CLI baselines",
    },
    "train": {
        "existing": [
            "npm run training:eval-matrix",
            "npm run training:build:active-research-api",
            "npm run eval:stage6:constrained:prefix-only",
            "python scripts/system/dispatch_coding_agent_hf_job.py status --json",
        ],
        "planned": [
            "geoseal train status",
            "geoseal train launch --profile stage6",
            "geoseal train gate --latest",
            "geoseal train promote --latest",
        ],
        "purpose": "Hugging Face, Kaggle, local eval, and promotion-gate workflow",
    },
    "release": {
        "existing": [
            "npm run publish:check:strict",
            "npm run publish:pypi:check",
        ],
        "planned": [
            "geoseal release doctor",
            "geoseal release pack",
            "geoseal release publish --npm",
            "geoseal release publish --pypi",
        ],
        "purpose": "npm and PyPI release readiness, packaging, and publish gates",
    },
    "github": {
        "existing": [
            "python scripts/system/geoseal_github_ops.py doctor --json",
            "python scripts/security/code_governance_gate.py check-push",
        ],
        "planned": [
            "geoseal gh doctor",
            "geoseal gh issue-summary --safe",
            "geoseal gh fix-ci",
            "geoseal gh release-notes",
        ],
        "purpose": "GitHub CI, issue, security, release-note, and workflow routing",
    },
}


SPECIFIC_CASES = [
    {
        "scenario": "specific_factory_compare_sandcastle",
        "family": "factory",
        "user": "Run the software-factory comparison envelope for Sandcastle and GeoSeal.",
        "intent_class": "specific",
        "command": (
            "python scripts/benchmark/harness_provider_matrix.py --models "
            '"ollama:a,kimi:kimi-for-coding,moonshot:kimi-k2.6" --software-factory '
            "--task-id sandcastle-compare --json"
        ),
        "why": "Uses the implemented offline factory envelope and avoids mutating worktrees.",
    },
    {
        "scenario": "specific_training_gate_latest",
        "family": "train",
        "user": "Check the latest Stage 6 local gate before we launch another remote run.",
        "intent_class": "specific",
        "command": "npm run eval:stage6:constrained:prefix-only",
        "why": "Runs the deterministic no-model Stage 6 contract check first.",
    },
    {
        "scenario": "specific_training_matrix",
        "family": "train",
        "user": "Show me the current training merge readiness matrix.",
        "intent_class": "specific",
        "command": "npm run training:eval-matrix",
        "why": "Builds the repo's readable training evaluation matrix from local artifacts.",
    },
    {
        "scenario": "specific_release_npm_gate",
        "family": "release",
        "user": "Before publishing npm, check what would go into the package.",
        "intent_class": "specific",
        "command": "npm run publish:check:strict",
        "why": "Runs the existing npm pack guard before any publish action.",
    },
    {
        "scenario": "specific_github_security_push_gate",
        "family": "github",
        "user": "Check local changes for GitHub workflow and prompt-injection risk before pushing.",
        "intent_class": "specific",
        "command": "python scripts/security/code_governance_gate.py check-push",
        "why": "Uses the repo's deterministic governance gate for local diffs.",
    },
    {
        "scenario": "specific_models_provider_matrix",
        "family": "models",
        "user": "Tell me which AI providers are callable from the command line right now.",
        "intent_class": "specific",
        "command": "python scripts/benchmark/harness_provider_matrix.py --json",
        "why": "Reports provider availability, local key-mirror status, model refs, and lane-switch costs.",
    },
    {
        "scenario": "specific_active_research_build",
        "family": "train",
        "user": "Add public-source research API use cases into the next Kaggle training round.",
        "intent_class": "specific",
        "command": "npm run training:build:active-research-api",
        "why": "Rebuilds the deterministic active research/API usage SFT pack and mirrors it for Kaggle.",
    },
    {
        "scenario": "specific_python_release_gate",
        "family": "release",
        "user": "Check the PyPI package before we publish.",
        "intent_class": "specific",
        "command": "npm run publish:pypi:check",
        "why": "Runs the existing Python distribution guard without publishing.",
    },
]


NON_SPECIFIC_CASES = [
    {
        "scenario": "ambiguous_can_we_call_models",
        "family": "models",
        "user": "How many AI can we call from here now?",
        "intent_class": "non_specific",
        "clarity": "No clarification needed; this maps to provider discovery.",
        "command": "python scripts/benchmark/harness_provider_matrix.py --json",
    },
    {
        "scenario": "ambiguous_get_training_running",
        "family": "train",
        "user": "Get the next training round moving but do not burn credits blindly.",
        "intent_class": "non_specific",
        "clarity": "Use local gate and status first, then choose remote launch only after evidence.",
        "command": "npm run training:eval-matrix",
    },
    {
        "scenario": "ambiguous_make_cli_better_than_others",
        "family": "bench",
        "user": "Try to outperform other harness benchmarks.",
        "intent_class": "non_specific",
        "clarity": "Start with a benchmark report and compare against the software-factory envelope.",
        "command": "npm run benchmark:cli",
    },
    {
        "scenario": "ambiguous_ship_packages",
        "family": "release",
        "user": "Get the packages ready to ship this weekend.",
        "intent_class": "non_specific",
        "clarity": "Run release doctors and pack checks before any publish command.",
        "command": "npm run publish:check:strict",
    },
    {
        "scenario": "ambiguous_fix_github_warning",
        "family": "github",
        "user": "GitHub sent me a security thing; make sure we do not get burned.",
        "intent_class": "non_specific",
        "clarity": "Use governance check on local diff and avoid model-in-the-write-path automation.",
        "command": "python scripts/security/code_governance_gate.py check-push",
    },
    {
        "scenario": "ambiguous_sandbox_before_agent",
        "family": "sandbox",
        "user": "Let the agent work but do not let it wreck the repo.",
        "intent_class": "non_specific",
        "clarity": "Route to scratch or branch strategy; sandbox commands are planned until implemented.",
        "command": "geoseal sandbox create",
        "planned_command": True,
    },
    {
        "scenario": "ambiguous_auth_before_remote",
        "family": "auth",
        "user": "Check the keys without showing them and then move on.",
        "intent_class": "non_specific",
        "clarity": "Use key presence, fingerprint, or local mirror status only; never print raw secrets.",
        "command": "geoseal auth status",
        "planned_command": True,
    },
    {
        "scenario": "ambiguous_factory_run",
        "family": "factory",
        "user": "Have the AI run a task, review it, and keep the receipts.",
        "intent_class": "non_specific",
        "clarity": "Use software-factory envelope now; real factory run is planned until adapter gates land.",
        "command": "geoseal factory run --task <task>",
        "planned_command": True,
    },
]


def _sha(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _assistant_json(case: dict[str, Any]) -> str:
    family = COMMAND_FAMILIES[case["family"]]
    planned = bool(case.get("planned_command")) or str(case["command"]).startswith("geoseal ")
    payload = {
        "decision": "PLAN_COMMAND" if planned else "RUN_EXISTING_COMMAND",
        "intent_class": case["intent_class"],
        "command_family": case["family"],
        "primary_command": case["command"],
        "command_status": "planned_cli_surface" if planned else "existing_repo_command",
        "specific_use_case": case["intent_class"] == "specific",
        "non_specific_use_case": case["intent_class"] == "non_specific",
        "purpose": family["purpose"],
        "why_this_command": case.get("why", case.get("clarity", "")),
        "available_existing_commands": family.get("existing", []),
        "planned_aliases": family.get("planned", []),
        "receipts_required": [
            "command",
            "returncode",
            "stdout_or_artifact_path",
            "changed_paths",
            "test_or_gate_evidence",
        ],
        "safety_checks": [
            "no_raw_secrets",
            "prefer_read_only_or_gate_first",
            "mark_planned_commands_without_executing",
            "do_not_publish_or_merge_without_promotion_gate",
        ],
        "fallback": {
            "if_command_missing": "emit planned_cli_surface and use the closest existing script",
            "if_ambiguous": "choose the safest read-only command or ask one short clarification",
        },
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=True)


def _record(case: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": case["user"]},
            {"role": "assistant", "content": _assistant_json(case)},
        ],
        "metadata": {
            "track": "geoseal_industry_commands_v1",
            "scenario": case["scenario"],
            "intent_class": case["intent_class"],
            "command_family": case["family"],
        },
    }
    payload["id"] = f"geoseal_industry_commands_v1_{case['scenario']}_{_sha(payload)[:16]}"
    return payload


def build_records() -> list[dict[str, Any]]:
    return [_record(case) for case in [*SPECIFIC_CASES, *NON_SPECIFIC_CASES]]


def split_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eval_scenarios = {
        "specific_models_provider_matrix",
        "ambiguous_auth_before_remote",
        "ambiguous_factory_run",
    }
    train: list[dict[str, Any]] = []
    eval_rows: list[dict[str, Any]] = []
    for record in records:
        row = dict(record)
        row["metadata"] = dict(record["metadata"])
        split = "eval" if row["metadata"]["scenario"] in eval_scenarios else "train"
        row["metadata"]["split"] = split
        (eval_rows if split == "eval" else train).append(row)
    return train, eval_rows


def write_outputs(out_dir: Path, *, copy_kaggle: bool = False, kaggle_dir: Path = DEFAULT_KAGGLE_DIR) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    records = build_records()
    train, eval_rows = split_records(records)

    train_path = out_dir / TRAIN_NAME
    eval_path = out_dir / EVAL_NAME
    manifest_path = out_dir / MANIFEST_NAME

    for path, rows in ((train_path, train), (eval_path, eval_rows)):
        path.write_text(
            "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=True) for row in rows) + "\n",
            encoding="utf-8",
        )

    manifest = {
        "schema_version": "geoseal_industry_commands_manifest_v1",
        "track": "geoseal_industry_commands_v1",
        "train_file": str(train_path.relative_to(REPO_ROOT)),
        "eval_file": str(eval_path.relative_to(REPO_ROOT)),
        "train_records": len(train),
        "eval_records": len(eval_rows),
        "specific_records": sum(1 for row in records if row["metadata"]["intent_class"] == "specific"),
        "non_specific_records": sum(1 for row in records if row["metadata"]["intent_class"] == "non_specific"),
        "command_families": sorted(COMMAND_FAMILIES),
        "files": {
            TRAIN_NAME: _sha(train),
            EVAL_NAME: _sha(eval_rows),
        },
        "gate": {
            "decision": (
                "PASS only if the response preserves intent_class, command_family, command_status, receipts, "
                "and distinguishes planned GeoSeal aliases from existing repo commands."
            ),
            "blocked": ["raw_secrets", "fake_execution_claims", "publish_without_gate", "merge_without_review"],
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")

    copied: list[str] = []
    if copy_kaggle:
        kaggle_dir.mkdir(parents=True, exist_ok=True)
        for path in (train_path, eval_path, manifest_path):
            target = kaggle_dir / path.name
            shutil.copy2(path, target)
            copied.append(str(target.relative_to(REPO_ROOT)))

    return {
        "ok": True,
        "train_records": len(train),
        "eval_records": len(eval_rows),
        "train_path": str(train_path),
        "eval_path": str(eval_path),
        "manifest_path": str(manifest_path),
        "copied_to_kaggle": copied,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--copy-kaggle", action="store_true")
    parser.add_argument("--kaggle-dir", type=Path, default=DEFAULT_KAGGLE_DIR)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = write_outputs(args.out_dir, copy_kaggle=args.copy_kaggle, kaggle_dir=args.kaggle_dir)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(
            "GeoSeal industry-command SFT: "
            f"train={result['train_records']} eval={result['eval_records']} "
            f"train_path={result['train_path']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
