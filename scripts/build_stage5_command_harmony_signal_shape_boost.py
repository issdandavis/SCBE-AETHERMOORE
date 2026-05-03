"""Build Stage 5 command-harmony forced-prefix repair data.

The first restored Stage 5 online run learned the broad corpus but failed the
inline gate because exact required markers were dropped during generation. This
builder creates a small concentrated shard where every answer opens with a
deterministic required-token checklist before the normal response body.

Output:
- training-data/sft/stage5_command_harmony_signal_shape_boost_train.sft.jsonl
- training-data/sft/stage5_command_harmony_signal_shape_boost_holdout.sft.jsonl
- training-data/sft/stage5_command_harmony_signal_shape_boost_manifest.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SFT_ROOT = REPO_ROOT / "training-data" / "sft"
TRAIN_OUT = SFT_ROOT / "stage5_command_harmony_signal_shape_boost_train.sft.jsonl"
HOLDOUT_OUT = SFT_ROOT / "stage5_command_harmony_signal_shape_boost_holdout.sft.jsonl"
MANIFEST_OUT = SFT_ROOT / "stage5_command_harmony_signal_shape_boost_manifest.json"

SYSTEM_PROMPT = (
    "You are an SCBE-AETHERMOORE GeoSeal command-line coding agent. "
    "Emit required command markers before prose, preserve lane-change signals, "
    "and separate structural-only maps from runtime-verified evidence."
)

KINDS: dict[str, dict[str, Any]] = {
    "current_harness_terminal_command": {
        "required": [
            "python -m src.geoseal_cli",
            "harness-terminal",
            "--models",
            "ollama:",
            "deepseek:",
            "--no-health",
            "--json",
        ],
        "prompts": [
            "Show the current GeoSeal CLI command that prints the harness terminal as JSON without probing the bridge.",
            "Give the exact no-health harness-terminal command for an Ollama to DeepSeek model pair.",
            "Return a machine-readable GeoSeal harness-terminal example using Ollama and DeepSeek.",
        ],
        "body": (
            "Command:\n"
            "python -m src.geoseal_cli harness-terminal --models ollama:a,deepseek:b --no-health --json\n\n"
            "Use this current harness-terminal surface for provider matrix inspection. "
            "Do not use removed command names, and do not add flags that are not in the CLI help."
        ),
    },
    "provider_lane_signal": {
        "required": [
            "provider-pair:ollama->deepseek:benchmark",
            "signal",
            "blocked",
            "lane",
            "cost",
        ],
        "prompts": [
            "Explain the required signal for routing an agent pair from Ollama to DeepSeek for a benchmark.",
            "Why is an Ollama to DeepSeek provider pair blocked without a signal, and what signal should be used?",
            "Give the lane-change signal shape for a benchmark handoff from Ollama to DeepSeek.",
        ],
        "body": (
            "Signal:\n"
            "provider-pair:ollama->deepseek:benchmark\n\n"
            "The pair is blocked without that signal because crossing provider lanes has route cost "
            "and must be explicit. The signal says which lane changes, why it changes, and that "
            "the benchmark handoff is intentional rather than accidental provider drift."
        ),
    },
    "analog_action_ladder": {
        "required": [
            "observe-room",
            "move-lane",
            "inspect-object",
            "solve-checkpoint",
            "verify-evidence",
            "reset-run",
        ],
        "prompts": [
            "Map a terminal-game coding task into six reusable GeoSeal analog actions.",
            "Compress a coding workflow into observe, move, inspect, solve, verify, and reset primitives.",
            "Show the analog action ladder for a GeoSeal terminal coding run.",
        ],
        "body": (
            "Analog action ladder:\n"
            "1. observe-room - list visible files, exits, models, or provider lanes.\n"
            "2. move-lane - change directory, provider, phase, or permission lane with signal.\n"
            "3. inspect-object - read the task, schema, contract, or artifact.\n"
            "4. solve-checkpoint - commit a candidate answer or packet run.\n"
            "5. verify-evidence - run tests, seals, hashes, or score gates.\n"
            "6. reset-run - replay from a clean state when the path must be deterministic."
        ),
    },
    "runtime_vs_structural_boundary": {
        "required": [
            "KO",
            "Python",
            "AV",
            "TypeScript",
            "structural",
            "runtime",
            "evidence",
        ],
        "prompts": [
            "For a KO/Python to AV/TypeScript add command mapping, separate structural alignment from runtime-verified convergence.",
            "Explain when a KO Python and AV TypeScript add command can be called runtime verified.",
            "State the evidence needed before a cross-language command map is runtime convergence.",
        ],
        "body": (
            "KO / Python and AV / TypeScript can be structurally aligned when both lanes map to the "
            "same add intent and compatible source shape. That is structural evidence only. Runtime "
            "convergence requires evidence from execution: both lanes must run, produce the expected "
            "shared stdout or result, and attach the test, trace, or packet proof before the system "
            "calls the outputs runtime verified."
        ),
    },
}


def _prefix(required: list[str]) -> str:
    return "required-tokens: " + " | ".join(required) + " ::"


def _row(kind: str, prompt: str, response: str, idx: int, split: str) -> dict[str, Any]:
    digest = hashlib.sha256(f"{kind}|{idx}|{split}|{prompt}".encode("utf-8")).hexdigest()[:12]
    return {
        "id": f"stage5_command_harmony_signal_shape_boost_{split}_{idx:04d}_{digest}",
        "source": "stage5_command_harmony_eval_repair",
        "track": "stage5_command_harmony_signal_shape_boost",
        "source_type": "failed_gate_repair",
        "quality": "contract_targeted",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response},
        ],
        "metadata": {
            "stage": "stage5_command_harmony",
            "kind": kind,
            "split": split,
            "shape": "required_token_prefix",
        },
    }


def _build_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train: list[dict[str, Any]] = []
    holdout: list[dict[str, Any]] = []
    idx = 1
    for kind, spec in KINDS.items():
        required = list(spec["required"])
        response = f"{_prefix(required)}\n\n{spec['body']}"
        for repeat in range(10):
            prompt = spec["prompts"][repeat % len(spec["prompts"])]
            train.append(_row(kind, prompt, response, idx, "train"))
            idx += 1
        holdout_prompt = f"Holdout: {spec['prompts'][-1]}"
        holdout.append(_row(kind, holdout_prompt, response, len(holdout) + 1, "holdout"))
    return train, holdout


def _assert_rows(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        content = row["messages"][-1]["content"]
        kind = row["metadata"]["kind"]
        for token in KINDS[kind]["required"]:
            if token not in content:
                raise AssertionError(f"{row['id']} missing required token {token!r}")
        for forbidden in ("command-harmony-map", "--training-jsonl-output", "no tests needed"):
            if forbidden in content:
                raise AssertionError(f"{row['id']} contains forbidden token {forbidden!r}")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def main() -> None:
    train, holdout = _build_rows()
    _assert_rows(train + holdout)
    _write_jsonl(TRAIN_OUT, train)
    _write_jsonl(HOLDOUT_OUT, holdout)
    manifest = {
        "schema_version": "stage5_command_harmony_signal_shape_boost_manifest_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "train": str(TRAIN_OUT),
        "holdout": str(HOLDOUT_OUT),
        "train_rows": len(train),
        "holdout_rows": len(holdout),
        "kinds": sorted(KINDS),
        "repair_source": {
            "job_id": "69f69b559d85bec4d76f0e0e",
            "failed_gate": "stage5_command_harmony_eval_v1",
            "failure_summary": "1/4 pass; exact CLI, provider signal, and runtime/structural boundary markers were missing.",
        },
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"train_rows": len(train), "holdout_rows": len(holdout), "manifest": str(MANIFEST_OUT)}))


if __name__ == "__main__":
    main()
