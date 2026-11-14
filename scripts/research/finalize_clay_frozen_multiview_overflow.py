#!/usr/bin/env python3
"""Finalize the pinned Clay campaign after its exact paired test overflowed.

The affected runner completed every parent and adapter artifact, then failed
while converting a very large exact binomial ratio to ``float``.  This repair
does not train, resume, load model tensors, or mutate weights.  It verifies all
terminal model hashes, rebuilds the original aggregate with the repaired exact
test, and labels the resulting campaign receipt with both evaluator identities.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.clay_frozen_multiview_adapter import (  # noqa: E402
    RunConfig,
    TRAINED_ARMS,
    aggregate_results,
    atomic_json,
    file_sha256,
    paired_exact_p,
    stable_hash,
    utc_now,
)

SCHEMA = "clay.frozen-multiview-adapter-overflow-finalizer.v1"
SUPPORTED_RUNNER_SHA256 = {"764809fc4ddff339d4480c2f2bf7287b56847db840f30c165923ad5e76ec08a6"}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def _verified_result(
    run_dir: Path,
    result_path: Path,
    model_path: Path,
    hash_field: str,
) -> tuple[dict[str, Any], tuple[str, str]]:
    result = _load_json(result_path)
    if result.get("status") != "COMPLETE":
        raise RuntimeError(f"terminal result is not complete: {result_path}")
    measured = file_sha256(model_path)
    if measured != result.get(hash_field):
        raise RuntimeError(f"terminal model hash differs: {model_path}")
    relative = result_path.relative_to(run_dir).as_posix()
    return result, (relative, file_sha256(result_path))


def finalize(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve(strict=True)
    result_path = run_dir / "RESULT.json"
    if result_path.exists():
        existing = _load_json(result_path)
        repair = existing.get("finalization_repair", {})
        if repair.get("schema") == SCHEMA:
            return existing
        raise RuntimeError("campaign RESULT.json already exists without this repair receipt")

    manifest_path = run_dir / "RUN_MANIFEST.json"
    manifest = _load_json(manifest_path)
    runner_sha = str(manifest.get("runner_sha256", ""))
    if runner_sha not in SUPPORTED_RUNNER_SHA256:
        raise RuntimeError("campaign runner is not the audited overflowed runner")
    config = RunConfig(**manifest["config"])
    if stable_hash(asdict(config)) != manifest.get("config_hash"):
        raise RuntimeError("campaign config hash differs")
    # This call used to overflow for the campaign's highly discordant control.
    if not 0.0 < paired_exact_p(5000, 0) <= 0.05:
        raise RuntimeError("current exact paired test is not the audited stable implementation")

    parents: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    terminal_hashes: dict[str, str] = {}
    for seed in config.seeds:
        parent, receipt = _verified_result(
            run_dir,
            run_dir / "parents" / f"seed-{seed}" / "RESULT.json",
            run_dir / "parents" / f"seed-{seed}" / "PARENT.pt",
            "parent_sha256",
        )
        terminal_hashes[receipt[0]] = receipt[1]
        parents.append(parent)
        rows.append(
            {
                "arm": "no_intervention_adapter",
                "seed": seed,
                "trainable_parameters": 0,
                "metrics": parent["metrics"],
                "predictions": parent["predictions"],
                "counting_accuracy": parent["counting_accuracy"],
                "parent_counting_accuracy": parent["counting_accuracy"],
            }
        )
        for arm in TRAINED_ARMS:
            horse, receipt = _verified_result(
                run_dir,
                run_dir / "horses" / f"{arm}-seed-{seed}" / "RESULT.json",
                run_dir / "horses" / f"{arm}-seed-{seed}" / "MODEL.pt",
                "model_sha256",
            )
            terminal_hashes[receipt[0]] = receipt[1]
            rows.append(horse)

    if len(terminal_hashes) != 12:
        raise RuntimeError(f"expected 12 terminal artifacts, got {len(terminal_hashes)}")
    aggregate = aggregate_results(rows, parents, config)
    evaluator_path = Path(sys.modules[aggregate_results.__module__].__file__).resolve()
    aggregate["finalization_repair"] = {
        "schema": SCHEMA,
        "reason": "exact paired binomial ratio overflowed during int-to-float conversion",
        "original_runner": str(manifest["runner"]),
        "original_runner_sha256": runner_sha,
        "repaired_evaluator": str(evaluator_path),
        "repaired_evaluator_sha256": file_sha256(evaluator_path),
        "finalizer": str(Path(__file__).resolve()),
        "finalizer_sha256": file_sha256(Path(__file__).resolve()),
        "run_manifest_sha256": file_sha256(manifest_path),
        "terminal_result_hashes": dict(sorted(terminal_hashes.items())),
        "terminal_result_count": len(terminal_hashes),
        "training_replayed": False,
        "model_tensors_loaded": False,
        "weights_mutated": False,
        "completed_at_utc": utc_now(),
    }
    atomic_json(result_path, aggregate)
    atomic_json(
        run_dir / "STATUS.json",
        {
            "schema": "clay.frozen-multiview-adapter-campaign.v1.status",
            "status": "COMPLETE_REPAIRED_AGGREGATION",
            "result": str(result_path),
            "repair_schema": SCHEMA,
            "updated_at_utc": utc_now(),
        },
    )
    return aggregate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    result = finalize(args.run_dir)
    print(
        json.dumps(
            {
                "status": result["status"],
                "producer_gate": result["producer_gate"],
                "promotion": result["promotion"],
                "repair": result["finalization_repair"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
