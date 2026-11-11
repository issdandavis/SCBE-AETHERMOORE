from __future__ import annotations

import json
from pathlib import Path

import pytest

from python.scbe.prime_token_input_access_evidence import REQUIRED_ARMS, aggregate_evidence
from python.scbe.prime_token_training import canonical_sha256, sha256_file

SEEDS = (11, 29, 47)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _grid(tmp_path: Path, *, candidate_wins: int = 20) -> tuple[Path, dict[tuple[str, int], tuple[Path, Path]]]:
    entries = []
    paths: dict[tuple[str, int], tuple[Path, Path]] = {}
    for arm in REQUIRED_ARMS:
        for seed in SEEDS:
            values = [
                1.0 if arm == "canonical_six_view_reader" and index < candidate_wins else 0.0 for index in range(20)
            ]
            outcomes = [
                {
                    "id": f"held-{index}:3",
                    "record_id": f"held-{index}",
                    "split": "final_test",
                    "source_family": "held-family",
                    "accuracy": value,
                    "relationship": value,
                    "function": value,
                }
                for index, value in enumerate(values)
            ]
            identity = {
                "arm": arm,
                "seed": str(seed),
                "parent_sha256": "a" * 64,
                "source_manifest_sha256": "b" * 64,
                "split_manifest_sha256": "c" * 64,
            }
            aggregate = sum(values) / len(values)
            run = {
                "schema": "scbe.prime-token-reader-run.v1",
                "status": "COMPLETE_NO_PROMOTION",
                "identity": identity,
                "final_step": 0 if arm == "no_intervention" else 10,
                "evaluation": {
                    "evaluator_receipt_sha256": "e" * 64,
                    "metrics": {
                        "accuracy": aggregate,
                        "relationship": aggregate,
                        "function": aggregate,
                        "ordinary_false_activation": 0.0,
                        "frozen_parent_retention": 1.0,
                        "throughput": 100.0,
                        "peak_memory": 1024.0,
                        "checkpoint_bytes": 0.0 if arm == "no_intervention" else 4096.0,
                    },
                    "per_example": outcomes,
                },
                "tool_dispatch": False,
                "promotion_authorized": False,
                "partial_unfreeze_authorized": False,
            }
            replay_outcomes = [
                {
                    "id": row["id"],
                    "record_id": row["record_id"],
                    "split": row["split"],
                    "source_family": row["source_family"],
                    "correct": bool(row["accuracy"]),
                }
                for row in outcomes
            ]
            checkpoint = {
                "checkpoint": None if arm == "no_intervention" else f"{arm}-{seed}.pt",
                "checkpoint_sha256": None if arm == "no_intervention" else "d" * 64,
                "step": 0 if arm == "no_intervention" else 10,
                "identity_sha256": canonical_sha256(identity),
                "producer_metrics_ignored": True,
            }
            if arm == "no_intervention":
                checkpoint["checkpoint_free_baseline"] = True
            replay = {
                "schema": "scbe.prime-token-independent-replay-run.v1",
                "status": "VERIFIED_REPLAY_NO_PROMOTION",
                "checkpoint": checkpoint,
                "case_count": 1,
                "example_count": len(replay_outcomes),
                "correct_count": sum(int(row["correct"]) for row in replay_outcomes),
                "accuracy": aggregate,
                "cases": [
                    {
                        "case": 0,
                        "exact_evaluator_receipt_sha256": "e" * 64,
                        "prime_packet_used": arm != "no_intervention",
                        "outcomes": replay_outcomes,
                    }
                ],
                "tool_dispatch": False,
                "promotion_authorized": False,
                "partial_unfreeze_authorized": False,
            }
            run_path = tmp_path / arm / str(seed) / "RUN_RESULT.json"
            replay_path = tmp_path / arm / str(seed) / "REPLAY_RESULT.json"
            _write(run_path, run)
            _write(replay_path, replay)
            paths[(arm, seed)] = (run_path, replay_path)
            entries.append(
                {
                    "arm": arm,
                    "seed": seed,
                    "run_result_path": str(run_path),
                    "run_result_sha256": sha256_file(run_path),
                    "replay_result_path": str(replay_path),
                    "replay_result_sha256": sha256_file(replay_path),
                }
            )
    manifest = tmp_path / "EVIDENCE_MANIFEST.json"
    _write(
        manifest,
        {
            "schema": "scbe.prime-token-input-access-evidence-manifest.v1",
            "seeds": list(SEEDS),
            "entries": entries,
        },
    )
    return manifest, paths


def test_aggregate_requires_candidate_to_beat_baseline_and_strongest_control(tmp_path: Path) -> None:
    manifest, _ = _grid(tmp_path)
    result = aggregate_evidence(manifest)
    assert result["status"] == "SUPPORTED_NO_PROMOTION"
    assert result["all_primary_metrics_pass"] is True
    assert result["independent_bounded_output_replay_complete"] is True
    assert result["promotion_authorized"] is False
    for metric in ("accuracy", "relationship", "function"):
        gate = result["comparisons"][metric]
        assert gate["passes_gate"] is True
        assert set(gate["comparisons"]) == {"no_intervention", gate["strongest_matched_control"]}


def test_aggregate_marks_finite_sample_failure_underpowered(tmp_path: Path) -> None:
    manifest, _ = _grid(tmp_path, candidate_wins=1)
    result = aggregate_evidence(manifest)
    assert result["status"] == "UNDERPOWERED_NO_PROMOTION"
    assert result["comparisons"]["accuracy"]["passes_gate"] is False
    assert (
        result["comparisons"]["accuracy"]["comparisons"]["no_intervention"]["passes_finite_sample_uncertainty"] is False
    )


def test_aggregate_rejects_producer_replay_disagreement(tmp_path: Path) -> None:
    manifest_path, paths = _grid(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    replay_path = paths[("canonical_six_view_reader", SEEDS[0])][1]
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    replay["cases"][0]["outcomes"][0]["correct"] = False
    replay["correct_count"] -= 1
    replay["accuracy"] = replay["correct_count"] / replay["example_count"]
    _write(replay_path, replay)
    for entry in manifest["entries"]:
        if entry["arm"] == "canonical_six_view_reader" and entry["seed"] == SEEDS[0]:
            entry["replay_result_sha256"] = sha256_file(replay_path)
    _write(manifest_path, manifest)
    with pytest.raises(RuntimeError, match="accuracy differ"):
        aggregate_evidence(manifest_path)
