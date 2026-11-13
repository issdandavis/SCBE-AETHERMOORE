"""Independently verify one completed Clay hash-spread specificity campaign.

This file deliberately imports neither the campaign producer nor its gate.  It
reimplements JSON/tensor/state receipts, checkpoint effects, aggregate market
math, and the held-sector gate from the frozen preregistration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

import torch
from torch import Tensor

CAMPAIGN_SCHEMA = "clay.multiview-hash-spread-campaign.v1"
GATE_SCHEMA = "clay.multiview-hash-spread-gate.v1"
VERIFY_SCHEMA = "clay.multiview-hash-spread-independent-verification.v1"
COMPLETE_STATE = "COMPLETE_MECHANICS_NO_PROMOTION"
ARMS = (
    "static_unique",
    "multiview_random",
    "multiview_factor_shuffled",
    "multiview_hash_spread",
)
PRIMARY = "multiview_factor_shuffled"
CONTROLS = (
    "multiview_hash_spread",
    "multiview_random",
    "static_unique",
)
SEEDS = (419, 431, 443, 457, 461)
HELD_SECTORS = (1, 4, 7)
SOURCE_FILES = {
    "policy": "trit_compiled_action_policy.py",
    "topology": "topology_sector_action_ab.py",
    "sandbox": "developmental_game_sandbox.py",
    "regional": "regional_breathing_field.py",
}


class IndependentVerificationError(RuntimeError):
    """Raised when independent reconstruction finds receipt or result drift."""


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tensor_sha256(value: Tensor) -> str:
    cpu = value.detach().cpu().contiguous()
    header = f"{cpu.dtype}|{tuple(cpu.shape)}|".encode("ascii")
    return hashlib.sha256(header + cpu.numpy().tobytes()).hexdigest()


def state_dict_sha256(state: Mapping[str, Tensor]) -> str:
    digest = hashlib.sha256()
    for name in sorted(state):
        value = state[name].detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(str(value.dtype).encode("ascii"))
        digest.update(str(tuple(value.shape)).encode("ascii"))
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise IndependentVerificationError(f"missing JSON receipt: {path}") from exc
    if not isinstance(value, dict):
        raise IndependentVerificationError(f"JSON receipt is not an object: {path}")
    return value


def _verify_json(path: Path, field: str) -> tuple[dict[str, Any], str]:
    value = _load_json(path)
    claimed = str(value.get(field, ""))
    body = dict(value)
    body.pop(field, None)
    if len(claimed) != 64 or sha256_json(body) != claimed:
        raise IndependentVerificationError(f"invalid {field}: {path}")
    return value, claimed


def _load_bank(path: Path, name: str) -> tuple[dict[str, Tensor], str]:
    try:
        value = torch.load(path, map_location="cpu", weights_only=True)
    except Exception as exc:
        raise IndependentVerificationError(f"could not load bank: {path}") from exc
    if not isinstance(value, dict):
        raise IndependentVerificationError(f"bank is not a mapping: {path}")
    required = ("features", "labels", "sectors", "groups", "views")
    if any(not isinstance(value.get(key), Tensor) for key in required):
        raise IndependentVerificationError(f"bank tensors are incomplete: {path}")
    features = value["features"]
    count = int(features.shape[0])
    if features.ndim != 2 or features.shape[1] != 37:
        raise IndependentVerificationError(f"bank feature shape differs: {path}")
    if not bool(torch.isfinite(features).all()):
        raise IndependentVerificationError(f"bank has non-finite features: {path}")
    if any(value[key].shape != (count,) for key in required[1:]):
        raise IndependentVerificationError(f"bank vector shape differs: {path}")
    body = {
        "name": name,
        "records": count,
        "feature_sha256": tensor_sha256(features),
        "label_sha256": tensor_sha256(value["labels"]),
        "sector_sha256": tensor_sha256(value["sectors"]),
        "group_sha256": tensor_sha256(value["groups"]),
        "view_sha256": tensor_sha256(value["views"]),
        "complete_groups": bool(value["complete_groups"]),
    }
    manifest = sha256_json(body)
    if manifest != value.get("manifest_sha256"):
        raise IndependentVerificationError(f"bank manifest drift: {path}")
    return value, manifest


def _load_state(path: Path) -> tuple[dict[str, Tensor], str]:
    try:
        value = torch.load(path, map_location="cpu", weights_only=True)
    except Exception as exc:
        raise IndependentVerificationError(f"could not load checkpoint: {path}") from exc
    if not isinstance(value, dict) or not value:
        raise IndependentVerificationError(f"checkpoint is not a state dict: {path}")
    if any(not isinstance(tensor, Tensor) for tensor in value.values()):
        raise IndependentVerificationError(f"checkpoint contains non-tensors: {path}")
    return value, state_dict_sha256(value)


def _weight_effect(initial: Mapping[str, Tensor], final: Mapping[str, Tensor]) -> dict[str, Any]:
    if set(initial) != set(final):
        raise IndependentVerificationError("checkpoint parameter names differ")
    changed = 0
    total = 0
    squared = 0.0
    for name in initial:
        delta = final[name].to(torch.float64) - initial[name].to(torch.float64)
        changed += int(torch.count_nonzero(delta).item())
        total += delta.numel()
        squared += float(torch.sum(delta * delta).item())
    return {
        "changed_scalars": changed,
        "total_scalars": total,
        "changed_ratio": changed / total,
        "l2_drift": math.sqrt(squared),
    }


def _assert_effect(expected: Mapping[str, Any], actual: Mapping[str, Any]) -> None:
    for key in ("changed_scalars", "total_scalars"):
        if int(expected[key]) != int(actual[key]):
            raise IndependentVerificationError(f"weight effect differs: {key}")
    for key in ("changed_ratio", "l2_drift"):
        if not math.isclose(float(expected[key]), float(actual[key]), rel_tol=1e-13, abs_tol=1e-13):
            raise IndependentVerificationError(f"weight effect differs: {key}")


def _mean_sd(values: Sequence[float]) -> dict[str, float]:
    return {
        "mean": statistics.fmean(values),
        "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def _two_pooled_sd(left: Sequence[float], right: Sequence[float]) -> float:
    return 2.0 * math.sqrt((statistics.variance(left) + statistics.variance(right)) / 2.0)


def recompute_aggregate(horses: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for arm in ARMS:
        rows = [row for row in horses if row["arm"] == arm]
        if len(rows) != len(SEEDS) * len(HELD_SECTORS):
            raise IndependentVerificationError(f"aggregate arm is incomplete: {arm}")
        summary[arm] = {
            f"{split}_{metric}": _mean_sd([float(row[split][metric]) for row in rows])
            for split in ("holdout", "anchor")
            for metric in (
                "accuracy",
                "macro_f1",
                "stable_macro_f1",
                "worst_class_accuracy",
                "worst_stable_class_accuracy",
                "cross_entropy",
            )
        }
        summary[arm]["gradient_coherence"] = _mean_sd(
            [float(row["selected_gradient_coherence"]["mean_cosine"]) for row in rows]
        )
        summary[arm]["weight_l2_drift"] = _mean_sd([float(row["weight_effect"]["l2_drift"]) for row in rows])

    comparisons: dict[str, Any] = {}
    candidate_rows = [row for row in horses if row["arm"] == PRIMARY]
    for control in CONTROLS:
        control_rows = [row for row in horses if row["arm"] == control]
        metrics: dict[str, Any] = {}
        for metric in (
            "accuracy",
            "macro_f1",
            "stable_macro_f1",
            "worst_class_accuracy",
            "worst_stable_class_accuracy",
        ):
            candidate = [float(row["holdout"][metric]) for row in candidate_rows]
            baseline = [float(row["holdout"][metric]) for row in control_rows]
            threshold = _two_pooled_sd(candidate, baseline)
            delta = statistics.fmean(candidate) - statistics.fmean(baseline)
            metrics[metric] = {
                "delta": delta,
                "two_pooled_sd": threshold,
                "clears_noise_gate": delta > threshold,
            }
        candidate_anchor = statistics.fmean(float(row["anchor"]["accuracy"]) for row in candidate_rows)
        control_anchor = statistics.fmean(float(row["anchor"]["accuracy"]) for row in control_rows)
        comparisons[control] = {
            "holdout": metrics,
            "anchor_accuracy_delta": candidate_anchor - control_anchor,
            "retention_within_two_points": candidate_anchor >= control_anchor - 0.02,
        }
    fully_powered = all(
        comparison["holdout"][metric]["clears_noise_gate"]
        for comparison in comparisons.values()
        for metric in ("accuracy", "stable_macro_f1")
    )
    retained = all(comparison["retention_within_two_points"] for comparison in comparisons.values())
    return {
        "primary_arm": PRIMARY,
        "controls": list(CONTROLS),
        "arms": summary,
        "comparisons": comparisons,
        "verdict": ("MULTIVIEW_FACTOR_SHUFFLED_DATA_SIGNAL" if fully_powered and retained else "NO_SELECTION"),
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }


def recompute_gate(result: Mapping[str, Any], horses: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    config = result["configuration"]
    floor = 2.0 / math.sqrt(int(config["evaluation_records"]))
    comparisons: dict[str, Any] = {}
    for control in CONTROLS:
        sectors: dict[str, Any] = {}
        for held in HELD_SECTORS:
            candidate_rows = [row for row in horses if int(row["held_sector"]) == held and row["arm"] == PRIMARY]
            control_rows = [row for row in horses if int(row["held_sector"]) == held and row["arm"] == control]
            candidate = {int(row["seed"]): row for row in candidate_rows}
            baseline = {int(row["seed"]): row for row in control_rows}
            if set(candidate) != set(SEEDS) or set(baseline) != set(SEEDS):
                raise IndependentVerificationError("matched sector seeds differ")
            metrics: dict[str, Any] = {}
            for metric in ("accuracy", "stable_macro_f1"):
                left = [float(candidate[seed]["holdout"][metric]) for seed in SEEDS]
                right = [float(baseline[seed]["holdout"][metric]) for seed in SEEDS]
                delta = statistics.fmean(left) - statistics.fmean(right)
                required = max(_two_pooled_sd(left, right), floor)
                paired = [a - b for a, b in zip(left, right, strict=True)]
                metrics[metric] = {
                    "candidate_mean": statistics.fmean(left),
                    "control_mean": statistics.fmean(right),
                    "delta": delta,
                    "required_delta": required,
                    "positive": delta > 0.0,
                    "clears_gate": delta > required,
                    "matched_wins": sum(value > 0.0 for value in paired),
                    "matched_ties": sum(value == 0.0 for value in paired),
                    "matched_losses": sum(value < 0.0 for value in paired),
                }
            candidate_anchor = statistics.fmean(float(row["anchor"]["accuracy"]) for row in candidate_rows)
            control_anchor = statistics.fmean(float(row["anchor"]["accuracy"]) for row in control_rows)
            sectors[str(held)] = {
                "metrics": metrics,
                "anchor_delta": candidate_anchor - control_anchor,
                "retention_within_two_points": candidate_anchor >= control_anchor - 0.02,
            }
        metric_gate = {
            metric: {
                "positive_in_every_sector": all(row["metrics"][metric]["positive"] for row in sectors.values()),
                "clear_sector_count": sum(row["metrics"][metric]["clears_gate"] for row in sectors.values()),
            }
            for metric in ("accuracy", "stable_macro_f1")
        }
        passed = all(
            row["positive_in_every_sector"] and row["clear_sector_count"] >= 2 for row in metric_gate.values()
        ) and all(row["retention_within_two_points"] for row in sectors.values())
        comparisons[control] = {
            "sectors": sectors,
            "gate": metric_gate,
            "passes": passed,
        }
    passed = all(row["passes"] for row in comparisons.values())
    body: dict[str, Any] = {
        "schema": GATE_SCHEMA,
        "source_result_sha256": result["result_sha256"],
        "primary_arm": PRIMARY,
        "controls": list(CONTROLS),
        "held_sectors": list(HELD_SECTORS),
        "finite_evaluation_floor": floor,
        "comparisons": comparisons,
        "verdict": ("PASS_SHUFFLED_OVER_HASH_MECHANICS_NO_PROMOTION" if passed else "NO_SELECTION"),
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    return {**body, "gate_sha256": sha256_json(body)}


def verify_campaign(root: str | Path, *, clay_source_dir: str | Path) -> dict[str, Any]:
    campaign_root = Path(root).resolve()
    source_root = Path(clay_source_dir).resolve()
    campaign, campaign_sha = _verify_json(campaign_root / "CAMPAIGN.json", "campaign_sha256")
    result, result_sha = _verify_json(campaign_root / "RESULT.json", "result_sha256")
    gate, gate_sha = _verify_json(campaign_root / "STRATIFIED_GATE.json", "gate_sha256")
    if campaign.get("schema") != CAMPAIGN_SCHEMA or result.get("schema") != CAMPAIGN_SCHEMA:
        raise IndependentVerificationError("campaign schema differs")
    if result.get("state") != COMPLETE_STATE:
        raise IndependentVerificationError("campaign is not complete")
    if result.get("campaign_sha256") != campaign_sha:
        raise IndependentVerificationError("result/campaign lineage differs")
    config = campaign.get("configuration")
    if result.get("configuration") != config or not isinstance(config, dict):
        raise IndependentVerificationError("campaign/result configuration differs")
    expected_config = {
        "arms": list(ARMS),
        "primary_arm": PRIMARY,
        "controls": list(CONTROLS),
        "seeds": list(SEEDS),
        "held_sectors": list(HELD_SECTORS),
        "rows_per_view": 10_000,
        "records_per_arm": 30_000,
        "candidate_rows_per_view": 60_000,
        "evaluation_records": 10_000,
        "steps": 4_800,
        "batch_size": 192,
        "learning_rate": 0.001,
        "weight_decay": 0.0001,
        "log_every": 200,
        "hidden_width": 64,
        "device": "cuda",
        "data_seed_offset": 6_000_000,
        "evaluation_min_class_support": 32,
    }
    if config != expected_config:
        raise IndependentVerificationError("campaign differs from preregistration")
    if any(
        bool(campaign.get(field)) or bool(result.get(field)) or bool(gate.get(field))
        for field in ("promotion_authorized", "partial_unfreeze_authorized")
    ):
        raise IndependentVerificationError("authority flag was raised")

    implementation = Path(__file__).resolve().parents[2] / "python" / "scbe" / "clay_multiview_hash_spread.py"
    if file_sha256(implementation) != campaign.get("implementation_sha256"):
        raise IndependentVerificationError("campaign implementation hash drift")
    source_hashes = {name: file_sha256(source_root / relative) for name, relative in SOURCE_FILES.items()}
    if source_hashes != campaign.get("source_hashes"):
        raise IndependentVerificationError("Clay source hash drift")

    dataset_manifests = _load_json(campaign_root / "DATASET_MANIFESTS.json")
    selection_manifests = _load_json(campaign_root / "SELECTION_MANIFESTS.json")
    if dataset_manifests != result.get("dataset_manifests"):
        raise IndependentVerificationError("dataset manifest ledger differs")
    if selection_manifests != result.get("selection_manifests"):
        raise IndependentVerificationError("selection manifest ledger differs")

    verified_banks: dict[tuple[int, str], str] = {}
    selections: list[dict[str, Any]] = []
    for held in HELD_SECTORS:
        expected_manifests = dataset_manifests[str(held)]
        for name, expected_manifest in expected_manifests.items():
            _, manifest = _load_bank(
                campaign_root / "inputs" / f"held-{held}" / f"{name}.pt",
                name,
            )
            if manifest != expected_manifest:
                raise IndependentVerificationError("dataset manifest mapping drift")
            verified_banks[(held, name)] = manifest
        selection, selection_sha = _verify_json(
            campaign_root / "inputs" / f"held-{held}" / "SELECTION.json",
            "selection_sha256",
        )
        if selection_sha != selection_manifests[str(held)]:
            raise IndependentVerificationError("selection manifest mapping drift")
        if (
            selection.get("schema") != "clay.multiview-hash-spread-selection.v1"
            or not selection.get("intervention_verified")
            or selection.get("holdout_used_for_selection") is not False
            or selection.get("reward_or_post_outcome_used_for_selection") is not False
            or any(int(value) for value in selection["selected_index_overlap"].values())
            or any(int(value) for value in selection["exact_feature_overlap"].values())
        ):
            raise IndependentVerificationError("selection safety contract failed")
        for arm, manifest in selection["bank_manifest_sha256"].items():
            if verified_banks[(held, arm)] != manifest:
                raise IndependentVerificationError("selection/bank lineage differs")
        selections.append(
            {
                "held_sector": held,
                "selection_sha256": selection_sha,
                "hash_entropy": selection["hash_space_coverage"]["multiview_hash_spread"]["mean_entropy_evenness"],
                "shuffled_entropy": selection["hash_space_coverage"]["multiview_factor_shuffled"][
                    "mean_entropy_evenness"
                ],
                "random_entropy": selection["hash_space_coverage"]["multiview_random"]["mean_entropy_evenness"],
            }
        )

    horses = result.get("horses")
    if not isinstance(horses, list):
        raise IndependentVerificationError("result horse ledger is absent")
    aggregate_rows: dict[tuple[int, str, int], Mapping[str, Any]] = {}
    for row in horses:
        key = (int(row["held_sector"]), str(row["arm"]), int(row["seed"]))
        if key in aggregate_rows:
            raise IndependentVerificationError("duplicate aggregate horse")
        aggregate_rows[key] = row
    expected_horses = {(held, arm, seed) for held in HELD_SECTORS for arm in ARMS for seed in SEEDS}
    if set(aggregate_rows) != expected_horses:
        raise IndependentVerificationError("aggregate horse set is incomplete")

    checkpoint_count = 0
    changed_horses = 0
    initial_hashes_by_seed: dict[int, set[str]] = {seed: set() for seed in SEEDS}
    horse_receipts: list[str] = []
    for held, arm, seed in sorted(expected_horses):
        folder = campaign_root / "horses" / f"held-{held}" / f"{arm}-seed-{seed}"
        horse, horse_sha = _verify_json(folder / "RESULT.json", "result_sha256")
        if horse != aggregate_rows[(held, arm, seed)]:
            raise IndependentVerificationError("horse/aggregate ledger differs")
        if horse.get("data_manifest_sha256") != verified_banks[(held, arm)]:
            raise IndependentVerificationError("horse/bank lineage differs")
        initial, initial_sha = _load_state(folder / "INITIAL.pt")
        best, best_sha = _load_state(folder / "BEST.pt")
        final, final_sha = _load_state(folder / "FINAL.pt")
        checkpoint_count += 3
        if (
            initial_sha != horse.get("initial_weight_sha256")
            or best_sha != horse.get("best_weight_sha256")
            or final_sha != horse.get("final_weight_sha256")
        ):
            raise IndependentVerificationError("checkpoint hash differs")
        best_effect = _weight_effect(initial, best)
        final_effect = _weight_effect(initial, final)
        _assert_effect(best_effect, horse["weight_effect"])
        _assert_effect(final_effect, horse["final_weight_effect"])
        if final_effect["changed_scalars"] > 0:
            changed_horses += 1
        initial_hashes_by_seed[seed].add(initial_sha)
        horse_receipts.append(horse_sha)
    if changed_horses != len(expected_horses):
        raise IndependentVerificationError("not every horse changed weights")
    if any(len(values) != 1 for values in initial_hashes_by_seed.values()):
        raise IndependentVerificationError("matched initialization hashes differ")

    aggregate = recompute_aggregate(horses)
    if aggregate != result.get("aggregate"):
        raise IndependentVerificationError("independent aggregate differs")
    rebuilt_gate = recompute_gate(result, horses)
    if rebuilt_gate != gate:
        raise IndependentVerificationError("independent gate differs")

    body: dict[str, Any] = {
        "schema": VERIFY_SCHEMA,
        "campaign_root": str(campaign_root),
        "campaign_sha256": campaign_sha,
        "result_sha256": result_sha,
        "gate_sha256": gate_sha,
        "implementation_sha256": campaign["implementation_sha256"],
        "source_hashes": source_hashes,
        "selection_receipts": selections,
        "verified_banks": len(verified_banks),
        "verified_horses": len(horse_receipts),
        "verified_checkpoints": checkpoint_count,
        "matched_initialization_groups": len(initial_hashes_by_seed),
        "all_horses_changed_weights": True,
        "aggregate_recomputed_exactly": True,
        "gate_recomputed_exactly": True,
        "verdict": rebuilt_gate["verdict"],
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
        "verifier_file_sha256": file_sha256(Path(__file__).resolve()),
    }
    return {**body, "verification_sha256": sha256_json(body)}


def _write_once(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists():
        raise IndependentVerificationError(f"refusing to overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--clay-source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = verify_campaign(args.campaign, clay_source_dir=args.clay_source_dir)
    output = args.output or Path(args.campaign).resolve() / "INDEPENDENT_RESULT_AUDIT.json"
    _write_once(output.resolve(), result)
    print(
        json.dumps(
            {
                "status": "PASS_INDEPENDENT_RESULT_AUDIT_NO_PROMOTION",
                "output": str(output.resolve()),
                "verification_sha256": result["verification_sha256"],
                "horses": result["verified_horses"],
                "checkpoints": result["verified_checkpoints"],
                "verdict": result["verdict"],
                "promotion_authorized": False,
                "partial_unfreeze_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
