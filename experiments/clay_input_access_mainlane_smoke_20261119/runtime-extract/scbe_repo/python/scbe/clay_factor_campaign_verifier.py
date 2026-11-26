"""Independent inference replay for Clay multi-view factor campaigns.

This verifier deliberately does not import the campaign producer, its model,
its metric helper, or its gate.  It reloads the pinned Clay authority, rebuilds
held and anchor rows from their declared seeds, evaluates sealed checkpoints
through a separately written MLP forward path, and independently recomputes
the aggregate and stratified gate when a campaign is complete.

The running-campaign mode is an integrity snapshot, not a selection decision.
No result from this module grants promotion, execution authority, or unfreeze.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import importlib
import json
import math
from pathlib import Path
import random
import statistics
import sys
from typing import Any

import torch
from torch import Tensor

CAMPAIGN_SCHEMA = "clay.multiview-factor-coverage-campaign.v1"
SELECTION_SCHEMA = "clay.multiview-factor-selection.v1"
GATE_SCHEMA = "clay.multiview-factor-stratified-gate.v1"
HORSE_SCHEMA = "clay.paired-orbit-horse.v2"
VERIFY_SCHEMA = "clay.multiview-factor-independent-inference.v1"
COMPLETE_STATE = "COMPLETE_MECHANICS_NO_PROMOTION"
RUNNING_STATE = "RUNNING"
FEATURE_WIDTH = 37
ACTION_COUNT = 5
VIEW_COUNT = 3
KNOWN_ARMS = (
    "static_unique",
    "multiview_random",
    "multiview_factor",
    "multiview_factor_shuffled",
)
SOURCE_FILES = {
    "policy": "trit_compiled_action_policy.py",
    "topology": "topology_sector_action_ab.py",
    "sandbox": "developmental_game_sandbox.py",
    "regional": "regional_breathing_field.py",
}


class FactorCampaignVerificationError(RuntimeError):
    """Raised when an independently reconstructed campaign fact differs."""


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
        raise FactorCampaignVerificationError(f"missing JSON receipt: {path}") from exc
    if not isinstance(value, dict):
        raise FactorCampaignVerificationError(f"JSON receipt is not an object: {path}")
    return value


def _verify_json(path: Path, field: str) -> tuple[dict[str, Any], str]:
    value = _load_json(path)
    claimed = str(value.get(field, ""))
    body = dict(value)
    body.pop(field, None)
    if len(claimed) != 64 or sha256_json(body) != claimed:
        raise FactorCampaignVerificationError(f"invalid {field}: {path}")
    return value, claimed


def _load_bank(path: Path, name: str) -> tuple[dict[str, Any], str]:
    try:
        value = torch.load(path, map_location="cpu", weights_only=True)
    except Exception as exc:
        raise FactorCampaignVerificationError(f"could not load bank: {path}") from exc
    if not isinstance(value, dict):
        raise FactorCampaignVerificationError(f"bank is not a mapping: {path}")
    tensor_names = ("features", "labels", "sectors", "groups", "views")
    if any(not isinstance(value.get(key), Tensor) for key in tensor_names):
        raise FactorCampaignVerificationError(f"bank tensors are incomplete: {path}")
    features = value["features"]
    count = int(features.shape[0])
    if features.shape != (count, FEATURE_WIDTH) or features.dtype != torch.float32:
        raise FactorCampaignVerificationError(f"bank feature contract differs: {path}")
    if not bool(torch.isfinite(features).all()):
        raise FactorCampaignVerificationError(
            f"bank contains non-finite features: {path}"
        )
    for key in tensor_names[1:]:
        if value[key].shape != (count,) or value[key].dtype != torch.int64:
            raise FactorCampaignVerificationError(
                f"bank vector contract differs: {path}"
            )
    if bool(torch.any((value["labels"] < 0) | (value["labels"] >= ACTION_COUNT))):
        raise FactorCampaignVerificationError(f"bank label range differs: {path}")
    body = _bank_body(
        name,
        features,
        value["labels"],
        value["sectors"],
        value["groups"],
        value["views"],
        bool(value.get("complete_groups")),
    )
    manifest = sha256_json(body)
    if manifest != value.get("manifest_sha256"):
        raise FactorCampaignVerificationError(f"bank manifest drift: {path}")
    return value, manifest


def _bank_body(
    name: str,
    features: Tensor,
    labels: Tensor,
    sectors: Tensor,
    groups: Tensor,
    views: Tensor,
    complete_groups: bool,
) -> dict[str, Any]:
    return {
        "name": name,
        "records": int(features.shape[0]),
        "feature_sha256": tensor_sha256(features),
        "label_sha256": tensor_sha256(labels),
        "sector_sha256": tensor_sha256(sectors),
        "group_sha256": tensor_sha256(groups),
        "view_sha256": tensor_sha256(views),
        "complete_groups": complete_groups,
    }


def _load_state(path: Path) -> tuple[dict[str, Tensor], str]:
    try:
        value = torch.load(path, map_location="cpu", weights_only=True)
    except Exception as exc:
        raise FactorCampaignVerificationError(
            f"could not load checkpoint: {path}"
        ) from exc
    if not isinstance(value, dict) or not value:
        raise FactorCampaignVerificationError(f"checkpoint is not a state dict: {path}")
    if any(not isinstance(tensor, Tensor) for tensor in value.values()):
        raise FactorCampaignVerificationError(
            f"checkpoint contains non-tensors: {path}"
        )
    return value, state_dict_sha256(value)


def _weight_effect(
    initial: Mapping[str, Tensor], final: Mapping[str, Tensor]
) -> dict[str, Any]:
    if set(initial) != set(final):
        raise FactorCampaignVerificationError("checkpoint parameter names differ")
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
            raise FactorCampaignVerificationError(f"weight effect differs: {key}")
    for key in ("changed_ratio", "l2_drift"):
        if not math.isclose(
            float(expected[key]),
            float(actual[key]),
            rel_tol=1e-13,
            abs_tol=1e-13,
        ):
            raise FactorCampaignVerificationError(f"weight effect differs: {key}")


class IndependentClayAuthority:
    """Reload only the pinned deterministic state/action authority."""

    def __init__(
        self, source_dir: str | Path, expected_hashes: Mapping[str, Any]
    ) -> None:
        self.source_dir = Path(source_dir).resolve(strict=True)
        source_hashes: dict[str, str] = {}
        for name, relative in SOURCE_FILES.items():
            path = self.source_dir / relative
            if not path.is_file():
                raise FactorCampaignVerificationError(
                    f"missing Clay authority source: {path}"
                )
            source_hashes[name] = file_sha256(path)
        if source_hashes != dict(expected_hashes):
            raise FactorCampaignVerificationError("Clay source authority hash drift")
        self.source_hashes = source_hashes

        source_text = str(self.source_dir)
        if source_text not in sys.path:
            sys.path.insert(0, source_text)
        for name in (
            "trit_compiled_action_policy",
            "topology_sector_action_ab",
        ):
            existing = sys.modules.get(name)
            if existing is not None:
                module_path = Path(str(getattr(existing, "__file__", ""))).resolve()
                if module_path.parent != self.source_dir:
                    raise FactorCampaignVerificationError(
                        f"authority module already loaded from another lane: {name}"
                    )
        self.policy = importlib.import_module("trit_compiled_action_policy")
        self.topology = importlib.import_module("topology_sector_action_ab")
        if len(self.policy.FEATURE_NAMES) != FEATURE_WIDTH:
            raise FactorCampaignVerificationError("Clay feature width changed")
        if len(self.policy.MOTOR_ACTIONS) != ACTION_COUNT:
            raise FactorCampaignVerificationError("Clay action width changed")

    def training_sandbox(self) -> Any:
        sandboxes = tuple(self.policy.training_curriculum_sandboxes())
        if len(sandboxes) != VIEW_COUNT:
            raise FactorCampaignVerificationError("Clay training view count changed")
        return sandboxes[0]

    def holdout_sandbox(self) -> Any:
        return self.policy.holdout_sandbox()

    def materialize(self, sandbox: Any, state: Any) -> tuple[Tensor, int, int]:
        feature = (
            self.policy.vectorize_state(sandbox, state).detach().cpu().to(torch.float32)
        )
        sector = int(self.topology.scope_sector(feature[None, :])[0].item())
        selected, _ = sandbox.sieve_actions(state)
        label = int(selected.token_id)
        if feature.shape != (FEATURE_WIDTH,) or label not in range(ACTION_COUNT):
            raise FactorCampaignVerificationError(
                "Clay authority emitted an invalid row"
            )
        return feature, label, sector


def _rebuild_split(
    authority: IndependentClayAuthority,
    sandbox: Any,
    *,
    name: str,
    count: int,
    held_sector: int,
    include_held: bool,
    seed: int,
) -> dict[str, Any]:
    rng = random.Random(seed)
    features: list[Tensor] = []
    labels: list[int] = []
    sectors: list[int] = []
    attempts = 0
    while len(features) < count and attempts < count * 96:
        attempts += 1
        state = authority.policy.sample_state(sandbox, rng)
        feature, label, sector = authority.materialize(sandbox, state)
        if (sector == held_sector) != include_held:
            continue
        features.append(feature)
        labels.append(label)
        sectors.append(sector)
    if len(features) != count:
        raise FactorCampaignVerificationError(
            f"could not rebuild declared {name} split"
        )
    feature_tensor = torch.stack(features).to(torch.float32)
    label_tensor = torch.tensor(labels, dtype=torch.int64)
    sector_tensor = torch.tensor(sectors, dtype=torch.int64)
    group_tensor = torch.arange(count, dtype=torch.int64)
    view_tensor = torch.zeros(count, dtype=torch.int64)
    body = _bank_body(
        name,
        feature_tensor,
        label_tensor,
        sector_tensor,
        group_tensor,
        view_tensor,
        False,
    )
    return {
        "features": feature_tensor,
        "labels": label_tensor,
        "sectors": sector_tensor,
        "groups": group_tensor,
        "views": view_tensor,
        "complete_groups": False,
        "manifest_sha256": sha256_json(body),
    }


def rebuild_evaluation_banks(
    authority: IndependentClayAuthority,
    *,
    held_sector: int,
    count: int,
    data_seed: int,
) -> dict[str, dict[str, Any]]:
    """Recreate the two evaluation banks without calling producer code."""

    return {
        "holdout": _rebuild_split(
            authority,
            authority.holdout_sandbox(),
            name="holdout",
            count=count,
            held_sector=held_sector,
            include_held=True,
            seed=data_seed + 2003,
        ),
        "anchor": _rebuild_split(
            authority,
            authority.training_sandbox(),
            name="anchor",
            count=count,
            held_sector=held_sector,
            include_held=False,
            seed=data_seed + 3001,
        ),
    }


def _assert_bank_equal(
    saved: Mapping[str, Any], rebuilt: Mapping[str, Any], *, split: str
) -> None:
    for name in ("features", "labels", "sectors", "groups", "views"):
        if not torch.equal(saved[name], rebuilt[name]):
            raise FactorCampaignVerificationError(
                f"authority-rebuilt {split} tensor differs: {name}"
            )
    if saved.get("manifest_sha256") != rebuilt.get("manifest_sha256"):
        raise FactorCampaignVerificationError(
            f"authority-rebuilt {split} manifest differs"
        )


def manual_mlp_logits(state: Mapping[str, Tensor], features: Tensor) -> Tensor:
    """Evaluate the ordinary 37-hidden-hidden-5 MLP without its model class."""

    expected = {
        "input_layer.weight",
        "input_layer.bias",
        "hidden_layer.weight",
        "hidden_layer.bias",
        "output_layer.weight",
        "output_layer.bias",
    }
    if set(state) != expected:
        raise FactorCampaignVerificationError("checkpoint architecture differs")
    width = int(state["input_layer.weight"].shape[0])
    shapes = {
        "input_layer.weight": (width, FEATURE_WIDTH),
        "input_layer.bias": (width,),
        "hidden_layer.weight": (width, width),
        "hidden_layer.bias": (width,),
        "output_layer.weight": (ACTION_COUNT, width),
        "output_layer.bias": (ACTION_COUNT,),
    }
    if any(tuple(state[name].shape) != shape for name, shape in shapes.items()):
        raise FactorCampaignVerificationError("checkpoint tensor shape differs")
    values = features.to(torch.float32)
    values = values @ state["input_layer.weight"].T + state["input_layer.bias"]
    values = 0.5 * values * (1.0 + torch.erf(values / math.sqrt(2.0)))
    values = values @ state["hidden_layer.weight"].T + state["hidden_layer.bias"]
    values = 0.5 * values * (1.0 + torch.erf(values / math.sqrt(2.0)))
    return values @ state["output_layer.weight"].T + state["output_layer.bias"]


def independent_metrics(
    logits: Tensor, labels: Tensor, *, min_stable_support: int
) -> tuple[dict[str, Any], Tensor]:
    """Recompute all producer metrics from raw logits and labels."""

    if min_stable_support < 1:
        raise FactorCampaignVerificationError(
            "stable support threshold must be positive"
        )
    predictions = logits.argmax(dim=-1)
    confusion = torch.zeros((ACTION_COUNT, ACTION_COUNT), dtype=torch.int64)
    for truth, predicted in zip(labels.cpu(), predictions.cpu(), strict=True):
        confusion[int(truth), int(predicted)] += 1
    per_class: list[float | None] = []
    supported_f1: list[float] = []
    stable_f1: list[float] = []
    stable_accuracy: list[float] = []
    all_f1: list[float] = []
    absent_classes: list[int] = []
    sparse_classes: list[int] = []
    class_support: list[int] = []
    for index in range(ACTION_COUNT):
        true_positive = int(confusion[index, index])
        support = int(confusion[index].sum())
        predicted = int(confusion[:, index].sum())
        class_support.append(support)
        if support:
            per_class.append(true_positive / support)
        else:
            per_class.append(None)
            absent_classes.append(index)
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / support if support else 0.0
        f1 = (
            2.0 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        all_f1.append(f1)
        if support:
            supported_f1.append(f1)
        if support >= min_stable_support:
            stable_f1.append(f1)
            stable_accuracy.append(true_positive / support)
        elif support:
            sparse_classes.append(index)
    supported_accuracy = [value for value in per_class if value is not None]
    if not stable_f1:
        raise FactorCampaignVerificationError("evaluation has no stable class")
    row_index = torch.arange(labels.shape[0], dtype=torch.int64)
    cross_entropy = torch.mean(
        torch.logsumexp(logits, dim=-1) - logits[row_index, labels]
    )
    metrics = {
        "accuracy": float((predictions == labels).to(torch.float64).mean().item()),
        "macro_f1": statistics.fmean(supported_f1),
        "full_action_macro_f1": statistics.fmean(all_f1),
        "stable_macro_f1": statistics.fmean(stable_f1),
        "worst_class_accuracy": min(supported_accuracy),
        "worst_stable_class_accuracy": min(stable_accuracy),
        "cross_entropy": float(cross_entropy.item()),
        "per_class_accuracy": per_class,
        "supported_class_count": len(supported_accuracy),
        "stable_class_count": len(stable_f1),
        "stable_class_support_threshold": min_stable_support,
        "class_support": class_support,
        "absent_true_classes": absent_classes,
        "sparse_true_classes": sparse_classes,
        "predictions_into_absent_classes": int(
            confusion[:, absent_classes].sum().item() if absent_classes else 0
        ),
        "confusion": confusion.tolist(),
    }
    return metrics, predictions


def _assert_metric_receipt(
    expected: Mapping[str, Any], actual: Mapping[str, Any]
) -> float:
    if set(expected) != set(actual):
        raise FactorCampaignVerificationError("metric receipt fields differ")
    maximum_float_delta = 0.0
    for key, expected_value in expected.items():
        actual_value = actual[key]
        if isinstance(expected_value, float):
            delta = abs(float(expected_value) - float(actual_value))
            maximum_float_delta = max(maximum_float_delta, delta)
            if not math.isclose(
                float(expected_value), float(actual_value), rel_tol=1e-6, abs_tol=1e-7
            ):
                raise FactorCampaignVerificationError(f"metric differs: {key}")
        elif isinstance(expected_value, list) and key == "per_class_accuracy":
            if len(expected_value) != len(actual_value):
                raise FactorCampaignVerificationError("per-class metric length differs")
            for left, right in zip(expected_value, actual_value, strict=True):
                if left is None or right is None:
                    if left is not right:
                        raise FactorCampaignVerificationError(
                            "per-class absence differs"
                        )
                else:
                    delta = abs(float(left) - float(right))
                    maximum_float_delta = max(maximum_float_delta, delta)
                    if not math.isclose(
                        float(left), float(right), rel_tol=1e-12, abs_tol=1e-12
                    ):
                        raise FactorCampaignVerificationError(
                            "per-class metric differs"
                        )
        elif expected_value != actual_value:
            raise FactorCampaignVerificationError(f"metric differs: {key}")
    return maximum_float_delta


def _prediction_receipt(
    *,
    held_sector: int,
    arm: str,
    seed: int,
    split: str,
    features: Tensor,
    labels: Tensor,
    predictions: Tensor,
    logits: Tensor,
) -> str:
    return sha256_json(
        {
            "held_sector": held_sector,
            "arm": arm,
            "seed": seed,
            "split": split,
            "feature_sha256": tensor_sha256(features),
            "label_sha256": tensor_sha256(labels),
            "prediction_sha256": tensor_sha256(predictions),
            "logit_sha256": tensor_sha256(logits),
        }
    )


def _mean_sd(values: Sequence[float]) -> dict[str, float]:
    return {
        "mean": statistics.fmean(values),
        "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def _two_pooled_sd(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) < 2 or len(right) < 2:
        return None
    return 2.0 * math.sqrt(
        (statistics.variance(left) + statistics.variance(right)) / 2.0
    )


def recompute_aggregate(
    horses: Sequence[Mapping[str, Any]], *, configuration: Mapping[str, Any]
) -> dict[str, Any]:
    arms = tuple(str(value) for value in configuration["arms"])
    primary = str(configuration["primary_arm"])
    controls = tuple(str(value) for value in configuration["controls"])
    summary: dict[str, Any] = {}
    for arm in arms:
        rows = [row for row in horses if row["arm"] == arm]
        if not rows:
            raise FactorCampaignVerificationError(f"aggregate arm is incomplete: {arm}")
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
        summary[arm]["weight_l2_drift"] = _mean_sd(
            [float(row["weight_effect"]["l2_drift"]) for row in rows]
        )

    candidate_rows = [row for row in horses if row["arm"] == primary]
    comparisons: dict[str, Any] = {}
    for control in controls:
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
                "clears_noise_gate": threshold is not None and delta > threshold,
            }
        candidate_anchor = statistics.fmean(
            float(row["anchor"]["accuracy"]) for row in candidate_rows
        )
        control_anchor = statistics.fmean(
            float(row["anchor"]["accuracy"]) for row in control_rows
        )
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
    retained = all(row["retention_within_two_points"] for row in comparisons.values())
    return {
        "primary_arm": primary,
        "controls": list(controls),
        "arms": summary,
        "comparisons": comparisons,
        "verdict": (
            f"{primary.upper()}_DATA_SIGNAL"
            if fully_powered and retained
            else "NO_SELECTION"
        ),
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }


def recompute_gate(
    result: Mapping[str, Any], *, configuration: Mapping[str, Any]
) -> dict[str, Any]:
    horses = result["horses"]
    primary = str(configuration["primary_arm"])
    controls = tuple(str(value) for value in configuration["controls"])
    held_sectors = tuple(int(value) for value in configuration["held_sectors"])
    floor = 2.0 / math.sqrt(int(configuration["evaluation_records"]))
    comparisons: dict[str, Any] = {}
    for control in controls:
        sectors: dict[str, Any] = {}
        for held in held_sectors:
            candidate_rows = [
                row
                for row in horses
                if int(row["held_sector"]) == held and row["arm"] == primary
            ]
            control_rows = [
                row
                for row in horses
                if int(row["held_sector"]) == held and row["arm"] == control
            ]
            candidate = {int(row["seed"]): row for row in candidate_rows}
            baseline = {int(row["seed"]): row for row in control_rows}
            if set(candidate) != set(baseline) or len(candidate) != len(candidate_rows):
                raise FactorCampaignVerificationError("matched sector seeds differ")
            metrics: dict[str, Any] = {}
            for metric in ("accuracy", "stable_macro_f1"):
                ordered = sorted(candidate)
                left = [float(candidate[seed]["holdout"][metric]) for seed in ordered]
                right = [float(baseline[seed]["holdout"][metric]) for seed in ordered]
                threshold = _two_pooled_sd(left, right)
                if threshold is None:
                    raise FactorCampaignVerificationError("gate has too few seeds")
                delta = statistics.fmean(left) - statistics.fmean(right)
                required = max(threshold, floor)
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
            candidate_anchor = statistics.fmean(
                float(row["anchor"]["accuracy"]) for row in candidate_rows
            )
            control_anchor = statistics.fmean(
                float(row["anchor"]["accuracy"]) for row in control_rows
            )
            sectors[str(held)] = {
                "metrics": metrics,
                "anchor_delta": candidate_anchor - control_anchor,
                "retention_within_two_points": candidate_anchor
                >= control_anchor - 0.02,
            }
        metric_gate = {
            metric: {
                "positive_in_every_sector": all(
                    row["metrics"][metric]["positive"] for row in sectors.values()
                ),
                "clear_sector_count": sum(
                    row["metrics"][metric]["clears_gate"] for row in sectors.values()
                ),
            }
            for metric in ("accuracy", "stable_macro_f1")
        }
        passed = all(
            row["positive_in_every_sector"] and row["clear_sector_count"] >= 2
            for row in metric_gate.values()
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
        "primary_arm": primary,
        "controls": list(controls),
        "held_sectors": list(held_sectors),
        "finite_evaluation_floor": floor,
        "comparisons": comparisons,
        "verdict": (
            (
                "PASS_SHUFFLED_DATA_MECHANICS_NO_PROMOTION"
                if primary == "multiview_factor_shuffled"
                else "PASS_FACTOR_DATA_MECHANICS_NO_PROMOTION"
            )
            if passed
            else "NO_SELECTION"
        ),
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    return {**body, "gate_sha256": sha256_json(body)}


def _validate_configuration(
    configuration: Mapping[str, Any],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[int, ...], tuple[int, ...]]:
    arms = tuple(str(value) for value in configuration.get("arms", ()))
    controls = tuple(str(value) for value in configuration.get("controls", ()))
    primary = str(configuration.get("primary_arm", ""))
    seeds = tuple(int(value) for value in configuration.get("seeds", ()))
    held_sectors = tuple(int(value) for value in configuration.get("held_sectors", ()))
    if (
        set(arms) != set(KNOWN_ARMS)
        or len(arms) != len(KNOWN_ARMS)
        or primary not in arms
        or set(controls) != set(arms) - {primary}
        or len(controls) != len(arms) - 1
        or len(seeds) < 2
        or len(set(seeds)) != len(seeds)
        or len(held_sectors) != 3
        or len(set(held_sectors)) != 3
    ):
        raise FactorCampaignVerificationError(
            "campaign comparison configuration differs"
        )
    positive_fields = (
        "rows_per_view",
        "records_per_arm",
        "candidate_rows_per_view",
        "evaluation_records",
        "steps",
        "batch_size",
        "log_every",
        "hidden_width",
        "evaluation_min_class_support",
    )
    if any(int(configuration.get(name, 0)) < 1 for name in positive_fields):
        raise FactorCampaignVerificationError("campaign has a non-positive dimension")
    if (
        int(configuration["records_per_arm"])
        != int(configuration["rows_per_view"]) * VIEW_COUNT
    ):
        raise FactorCampaignVerificationError("campaign row accounting differs")
    return arms, controls, seeds, held_sectors


def verify_factor_campaign(
    root: str | Path,
    *,
    clay_source_dir: str | Path,
    allow_running: bool = False,
) -> dict[str, Any]:
    """Independently replay a running or completed factor campaign."""

    campaign_root = Path(root).resolve(strict=True)
    campaign, campaign_sha = _verify_json(
        campaign_root / "CAMPAIGN.json", "campaign_sha256"
    )
    if campaign.get("schema") != CAMPAIGN_SCHEMA:
        raise FactorCampaignVerificationError("campaign schema differs")
    if campaign.get("promotion_authorized") or campaign.get(
        "partial_unfreeze_authorized"
    ):
        raise FactorCampaignVerificationError("campaign authority flag was raised")
    configuration = campaign.get("configuration")
    if not isinstance(configuration, Mapping):
        raise FactorCampaignVerificationError("campaign configuration is absent")
    arms, controls, seeds, held_sectors = _validate_configuration(configuration)
    primary = str(configuration["primary_arm"])

    implementation = (
        Path(__file__).resolve().parent / "clay_multiview_factor_coverage.py"
    )
    implementation_sha = file_sha256(implementation)
    if implementation_sha != campaign.get("implementation_sha256"):
        raise FactorCampaignVerificationError("campaign implementation hash drift")
    authority = IndependentClayAuthority(
        clay_source_dir, campaign.get("source_hashes", {})
    )

    dataset_manifests = _load_json(campaign_root / "DATASET_MANIFESTS.json")
    selection_manifests = _load_json(campaign_root / "SELECTION_MANIFESTS.json")
    if set(dataset_manifests) != {str(value) for value in held_sectors}:
        raise FactorCampaignVerificationError("dataset fold manifest set differs")
    if set(selection_manifests) != {str(value) for value in held_sectors}:
        raise FactorCampaignVerificationError("selection fold manifest set differs")

    verified_banks: dict[tuple[int, str], str] = {}
    rebuilt_eval: dict[int, dict[str, dict[str, Any]]] = {}
    selection_receipts: list[dict[str, Any]] = []
    expected_bank_names = set(arms) | {
        "candidate_pool",
        "paired_probe",
        "holdout",
        "anchor",
    }
    for held in held_sectors:
        fold_manifests = dataset_manifests[str(held)]
        if (
            not isinstance(fold_manifests, Mapping)
            or set(fold_manifests) != expected_bank_names
        ):
            raise FactorCampaignVerificationError("dataset bank manifest set differs")
        saved_banks: dict[str, dict[str, Any]] = {}
        for name, expected_manifest in fold_manifests.items():
            saved, manifest = _load_bank(
                campaign_root / "inputs" / f"held-{held}" / f"{name}.pt", str(name)
            )
            if manifest != expected_manifest:
                raise FactorCampaignVerificationError("dataset manifest mapping drift")
            saved_banks[str(name)] = saved
            verified_banks[(held, str(name))] = manifest

        data_seed = 2026111300 + held + int(configuration["data_seed_offset"])
        rebuilt = rebuild_evaluation_banks(
            authority,
            held_sector=held,
            count=int(configuration["evaluation_records"]),
            data_seed=data_seed,
        )
        for split in ("holdout", "anchor"):
            _assert_bank_equal(
                saved_banks[split], rebuilt[split], split=f"held-{held}/{split}"
            )
        rebuilt_eval[held] = rebuilt

        selection, selection_sha = _verify_json(
            campaign_root / "inputs" / f"held-{held}" / "SELECTION.json",
            "selection_sha256",
        )
        if selection_sha != selection_manifests[str(held)]:
            raise FactorCampaignVerificationError("selection manifest mapping drift")
        if (
            selection.get("schema") != SELECTION_SCHEMA
            or not selection.get("intervention_verified")
            or selection.get("holdout_used_for_selection") is not False
            or selection.get("reward_or_post_outcome_used_for_selection") is not False
            or any(
                int(value)
                for value in selection.get("selected_index_overlap", {}).values()
            )
            or any(
                int(value)
                for value in selection.get("exact_feature_overlap", {}).values()
            )
        ):
            raise FactorCampaignVerificationError("selection safety contract failed")
        if int(selection.get("held_sector", -1)) != held:
            raise FactorCampaignVerificationError("selection held sector differs")
        for arm, manifest in selection.get("bank_manifest_sha256", {}).items():
            if arm not in arms or verified_banks[(held, arm)] != manifest:
                raise FactorCampaignVerificationError("selection/bank lineage differs")
        selection_receipts.append(
            {"held_sector": held, "selection_sha256": selection_sha}
        )

    expected_horses = {
        (held, arm, seed) for held in held_sectors for arm in arms for seed in seeds
    }
    discovered: dict[tuple[int, str, int], Path] = {}
    for path in campaign_root.glob("horses/held-*/*-seed-*/RESULT.json"):
        horse = _load_json(path)
        key = (int(horse["held_sector"]), str(horse["arm"]), int(horse["seed"]))
        if key not in expected_horses or key in discovered:
            raise FactorCampaignVerificationError(
                "unexpected or duplicate horse receipt"
            )
        discovered[key] = path
    if not allow_running and set(discovered) != expected_horses:
        raise FactorCampaignVerificationError("campaign horse set is incomplete")
    if not discovered:
        raise FactorCampaignVerificationError(
            "campaign has no completed horse to audit"
        )

    horse_rows: list[dict[str, Any]] = []
    prediction_receipts: list[dict[str, Any]] = []
    initial_hashes_by_seed: dict[int, set[str]] = {seed: set() for seed in seeds}
    max_metric_delta = 0.0
    changed_horses = 0
    checkpoint_count = 0
    for held, arm, seed in sorted(discovered):
        result_path = discovered[(held, arm, seed)]
        horse, horse_sha = _verify_json(result_path, "result_sha256")
        if horse.get("schema") != HORSE_SCHEMA:
            raise FactorCampaignVerificationError("horse schema differs")
        if (
            horse.get("promotion_authorized")
            or horse.get("partial_unfreeze_authorized")
            or horse.get("data_manifest_sha256") != verified_banks[(held, arm)]
        ):
            raise FactorCampaignVerificationError("horse lineage or authority differs")
        folder = result_path.parent
        initial, initial_sha = _load_state(folder / "INITIAL.pt")
        best, best_sha = _load_state(folder / "BEST.pt")
        final, final_sha = _load_state(folder / "FINAL.pt")
        checkpoint_count += 3
        if (
            initial_sha != horse.get("initial_weight_sha256")
            or best_sha != horse.get("best_weight_sha256")
            or final_sha != horse.get("final_weight_sha256")
        ):
            raise FactorCampaignVerificationError("checkpoint hash differs")
        best_effect = _weight_effect(initial, best)
        final_effect = _weight_effect(initial, final)
        _assert_effect(best_effect, horse["weight_effect"])
        _assert_effect(final_effect, horse["final_weight_effect"])
        if best_effect["changed_scalars"] > 0:
            changed_horses += 1
        initial_hashes_by_seed[seed].add(initial_sha)

        for split in ("holdout", "anchor"):
            bank = rebuilt_eval[held][split]
            logit_parts = [
                manual_mlp_logits(best, chunk) for chunk in bank["features"].split(2048)
            ]
            logits = torch.cat(logit_parts)
            metrics, predictions = independent_metrics(
                logits,
                bank["labels"],
                min_stable_support=int(configuration["evaluation_min_class_support"]),
            )
            max_metric_delta = max(
                max_metric_delta, _assert_metric_receipt(horse[split], metrics)
            )
            prediction_receipts.append(
                {
                    "held_sector": held,
                    "arm": arm,
                    "seed": seed,
                    "split": split,
                    "prediction_ledger_sha256": _prediction_receipt(
                        held_sector=held,
                        arm=arm,
                        seed=seed,
                        split=split,
                        features=bank["features"],
                        labels=bank["labels"],
                        predictions=predictions,
                        logits=logits,
                    ),
                }
            )
        horse_rows.append(horse)
        if len(horse_sha) != 64:
            raise FactorCampaignVerificationError("horse receipt hash width differs")

    if changed_horses != len(discovered):
        raise FactorCampaignVerificationError(
            "not every completed horse changed weights"
        )
    if any(len(values) > 1 for values in initial_hashes_by_seed.values()):
        raise FactorCampaignVerificationError("matched initialization hashes differ")

    complete = set(discovered) == expected_horses
    result_sha: str | None = None
    gate_sha: str | None = None
    aggregate_exact = False
    gate_exact = False
    verdict = "RUNNING_PARTIAL_AUDIT_NO_SELECTION"
    if complete:
        result, result_sha = _verify_json(
            campaign_root / "RESULT.json", "result_sha256"
        )
        gate, gate_sha = _verify_json(
            campaign_root / "STRATIFIED_GATE.json", "gate_sha256"
        )
        if (
            result.get("schema") != CAMPAIGN_SCHEMA
            or result.get("state") != COMPLETE_STATE
            or result.get("campaign_sha256") != campaign_sha
            or result.get("configuration") != configuration
            or result.get("dataset_manifests") != dataset_manifests
            or result.get("selection_manifests") != selection_manifests
        ):
            raise FactorCampaignVerificationError("completed result lineage differs")
        if any(
            bool(value.get(field))
            for value in (result, gate)
            for field in ("promotion_authorized", "partial_unfreeze_authorized")
        ):
            raise FactorCampaignVerificationError("completed authority flag was raised")
        result_rows = {
            (int(row["held_sector"]), str(row["arm"]), int(row["seed"])): row
            for row in result.get("horses", ())
        }
        replay_rows = {
            (int(row["held_sector"]), str(row["arm"]), int(row["seed"])): row
            for row in horse_rows
        }
        if result_rows != replay_rows:
            raise FactorCampaignVerificationError("result/horse ledger differs")
        rebuilt_aggregate = recompute_aggregate(horse_rows, configuration=configuration)
        if rebuilt_aggregate != result.get("aggregate"):
            raise FactorCampaignVerificationError("independent aggregate differs")
        aggregate_exact = True
        rebuilt_gate = recompute_gate(result, configuration=configuration)
        if rebuilt_gate != gate:
            raise FactorCampaignVerificationError("independent gate differs")
        gate_exact = True
        verdict = rebuilt_gate["verdict"]
    elif not allow_running:
        raise FactorCampaignVerificationError("campaign is not complete")

    body: dict[str, Any] = {
        "schema": VERIFY_SCHEMA,
        "campaign_root": str(campaign_root),
        "campaign_sha256": campaign_sha,
        "result_sha256": result_sha,
        "gate_sha256": gate_sha,
        "campaign_state": COMPLETE_STATE if complete else RUNNING_STATE,
        "primary_arm": primary,
        "controls": list(controls),
        "expected_horses": len(expected_horses),
        "verified_horses": len(discovered),
        "verified_checkpoints": checkpoint_count,
        "verified_banks": len(verified_banks),
        "authority_rebuilt_evaluation_banks": len(held_sectors) * 2,
        "selection_receipts": selection_receipts,
        "prediction_receipts": prediction_receipts,
        "prediction_ledger_set_sha256": sha256_json(prediction_receipts),
        "max_metric_absolute_delta": max_metric_delta,
        "all_completed_horses_changed_weights": True,
        "matched_initializations_verified": True,
        "raw_predictions_recomputed": True,
        "producer_metrics_not_trusted": True,
        "aggregate_recomputed_exactly": aggregate_exact,
        "gate_recomputed_exactly": gate_exact,
        "verdict": verdict,
        "implementation_sha256": implementation_sha,
        "source_hashes": authority.source_hashes,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    return {**body, "verification_sha256": sha256_json(body)}


__all__ = [
    "FactorCampaignVerificationError",
    "independent_metrics",
    "manual_mlp_logits",
    "recompute_aggregate",
    "recompute_gate",
    "verify_factor_campaign",
]
