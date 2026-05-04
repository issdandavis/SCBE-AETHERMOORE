#!/usr/bin/env python3
"""Evaluate GeoShell pair-agent SFT rows for tokenizer alignment and shape."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED_CODES = {"KO", "AV", "RU", "CA", "UM", "DR"}
EXPECTED_NAMES = {
    "Kor'aelin",
    "Avali",
    "Runethic",
    "Cassisivadan",
    "Umbroth",
    "Draumric",
}
FORBIDDEN_STRINGS = {
    "HF_TOKEN",
    "GEMINI_API_KEY",
    "PROTONMAIL_BRIDGE_PASSWORD",
    "config/connector_oauth/.env.connector.oauth",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def _assistant(row: dict[str, Any]) -> dict[str, Any]:
    messages = row.get("messages") or []
    if len(messages) < 3:
        return {}
    return json.loads(messages[-1].get("content") or "{}")


def evaluate_dataset(train_path: Path, holdout_path: Path) -> dict[str, Any]:
    rows = [(train_path, row) for row in _read_jsonl(train_path)] + [
        (holdout_path, row) for row in _read_jsonl(holdout_path)
    ]
    errors: list[dict[str, Any]] = []
    primary_counts: dict[str, int] = {}
    population_contexts: set[str] = set()
    base_tasks: set[str] = set()

    for path, row in rows:
        meta = row.get("meta") or {}
        body = json.dumps(row, sort_keys=True)
        for forbidden in FORBIDDEN_STRINGS:
            if forbidden in body:
                errors.append(
                    {
                        "path": str(path),
                        "line": row["_line_no"],
                        "error": f"forbidden_string:{forbidden}",
                    }
                )

        assistant = _assistant(row)
        alignment = (
            assistant.get("tokenizer_alignment")
            if isinstance(assistant, dict)
            else None
        )
        if not isinstance(alignment, dict):
            errors.append(
                {
                    "path": str(path),
                    "line": row["_line_no"],
                    "error": "missing_tokenizer_alignment",
                }
            )
            continue

        codes = {
            str(item.get("code"))
            for item in alignment.get("sacred_tongues") or []
            if isinstance(item, dict)
        }
        names = {
            str(item.get("name"))
            for item in alignment.get("sacred_tongues") or []
            if isinstance(item, dict)
        }
        if codes != EXPECTED_CODES:
            errors.append(
                {
                    "path": str(path),
                    "line": row["_line_no"],
                    "error": f"bad_codes:{sorted(codes)}",
                }
            )
        if names != EXPECTED_NAMES:
            errors.append(
                {
                    "path": str(path),
                    "line": row["_line_no"],
                    "error": f"bad_names:{sorted(names)}",
                }
            )
        if set(alignment.get("risk_tiers") or []) != {
            "ALLOW",
            "QUARANTINE",
            "ESCALATE",
            "DENY",
        }:
            errors.append(
                {"path": str(path), "line": row["_line_no"], "error": "bad_risk_tiers"}
            )

        primary = str(alignment.get("primary_tongue") or "")
        primary_counts[primary] = primary_counts.get(primary, 0) + 1
        if meta.get("population_context"):
            population_contexts.add(str(meta["population_context"]))
        if meta.get("base_task_id"):
            base_tasks.add(str(meta["base_task_id"]))

    return {
        "schema_version": "geoshell_pair_agent_dataset_eval_v1",
        "train_path": str(train_path),
        "holdout_path": str(holdout_path),
        "row_count": len(rows),
        "primary_tongue_counts": primary_counts,
        "population_context_count": len(population_contexts),
        "base_task_count": len(base_tasks),
        "errors": errors,
        "ok": not errors and len(rows) > 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--train",
        type=Path,
        default=Path("training-data/sft/geoshell_pair_agent_v1_train.sft.jsonl"),
    )
    parser.add_argument(
        "--holdout",
        type=Path,
        default=Path("training-data/sft/geoshell_pair_agent_v1_holdout.sft.jsonl"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/training_hub/geoshell_pair_agent_dataset_eval.json"),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = evaluate_dataset(args.train, args.holdout)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
