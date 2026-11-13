"""Independent inference replay for the frozen multi-view adapter campaign.

This verifier deliberately does not import the campaign producer, its model,
or its metric helpers.  It rebuilds the held action rows from the pinned source,
loads each emitted state dict into a separately declared network, recomputes
predictions and metrics, and compares the resulting gates with RESULT.json.
It is measurement-only and cannot grant promotion, unfreezing, or execution
authority.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

import torch
from torch import Tensor, nn

from python.scbe.clay_frozen_multiview_data import (
    ActionTextRow,
    build_frozen_multiview_dataset,
)
from python.scbe.clay_paired_orbit_training import ClaySourceAdapter

SCHEMA = "clay.frozen-multiview-adapter-independent-replay.v1"
AUTHORITY = "MEASUREMENT_ONLY_NO_EXECUTION_NO_PROMOTION_NO_PARTIAL_UNFREEZE"
TRAINED_ARMS = (
    "frozen_adapter_static",
    "frozen_adapter_multiview",
    "frozen_adapter_null",
)
ALL_ARMS = ("no_intervention_adapter",) + TRAINED_ARMS
PRIMARY_ARM = "frozen_adapter_multiview"
CONTROLS = (
    "frozen_adapter_static",
    "frozen_adapter_null",
    "no_intervention_adapter",
)
FROZEN_PREFIXES = ("e.", "g.", "count_head.")
STRUCTURAL_MISMATCH_DELTA = 1e300
PAD, BOS, SEP, EOS = "\x00", "\x02", "\x1f", "\x03"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(pending, path)


def _counting_rows(holdout: bool) -> list[tuple[str, str]]:
    rows = []
    for step in range(1, 10):
        for start in range(40):
            terms = [start + step * index for index in range(4)]
            target = start + step * 4
            if target > 400 or (start % 7 == 0) != holdout:
                continue
            rows.append(
                (
                    f"C {step} : " + " ".join(map(str, terms)) + " =>",
                    f" {target}",
                )
            )
    return rows


def _vocab_of(*rowsets: Sequence[tuple[str, str]]) -> tuple[list[str], dict[str, int]]:
    characters = set(PAD + BOS + SEP + EOS)
    for rows in rowsets:
        for prompt, target in rows:
            characters.update(prompt)
            characters.update(target)
    special = (PAD, BOS, SEP, EOS)
    vocab = list(special) + sorted(char for char in characters if char not in special)
    return vocab, {char: index for index, char in enumerate(vocab)}


class ReplayAdapter(nn.Module):
    """Separately declared adapter with producer-compatible state keys."""

    def __init__(self, hidden: int = 192, bottleneck: int = 160) -> None:
        super().__init__()
        self.down = nn.Linear(hidden, bottleneck)
        self.mid = nn.Linear(bottleneck, bottleneck)
        self.up = nn.Linear(bottleneck, hidden)
        self.act = nn.GELU()

    def forward(self, hidden: Tensor) -> Tensor:
        return hidden + self.up(self.act(self.mid(self.act(self.down(hidden)))))


class ReplayFrozenActionModel(nn.Module):
    """Independent network declaration used only for artifact replay."""

    def __init__(self, vocab_size: int) -> None:
        super().__init__()
        self.e = nn.Embedding(vocab_size, 64, padding_idx=0)
        self.g = nn.GRU(64, 192, 2, batch_first=True)
        self.adapter = ReplayAdapter()
        self.count_head = nn.Linear(192, vocab_size)
        self.adapter_head = nn.Linear(192, vocab_size)

    def forward(
        self,
        inputs: Tensor,
        *,
        head: str,
        null_carrier: bool,
        state: Any = None,
    ) -> tuple[Tensor, Any]:
        core_state = state[0] if isinstance(state, tuple) else state
        hidden, core_state = self.g(self.e(inputs), core_state)
        if head == "count":
            return self.count_head(hidden), core_state
        carrier = torch.ones_like(hidden) if null_carrier else hidden
        return self.adapter_head(self.adapter(carrier)), (core_state, None)


@torch.inference_mode()
def _generate_integer(
    model: ReplayFrozenActionModel,
    *,
    head: str,
    prompt: str,
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    null_carrier: bool,
    max_length: int,
) -> int | None:
    model.eval()
    ids = [stoi[BOS], *(stoi[char] for char in prompt), stoi[SEP]]
    logits, state = model(torch.tensor([ids]), head=head, null_carrier=null_carrier)
    token = int(logits[0, -1].argmax())
    output = []
    for _ in range(max_length):
        if token == stoi[EOS]:
            break
        output.append(itos[token])
        logits, state = model(
            torch.tensor([[token]]),
            head=head,
            null_carrier=null_carrier,
            state=state,
        )
        token = int(logits[0, -1].argmax())
    text = "".join(output).strip()
    try:
        return int(text.split()[0])
    except (ValueError, IndexError):
        return None


def _predict_actions(
    model: ReplayFrozenActionModel,
    rows: Sequence[ActionTextRow],
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    *,
    null_carrier: bool,
) -> list[dict[str, Any]]:
    predictions = []
    for index, row in enumerate(rows):
        prediction = _generate_integer(
            model,
            head="action",
            prompt=row.prompt,
            stoi=stoi,
            itos=itos,
            null_carrier=null_carrier,
            max_length=2,
        )
        predictions.append(
            {
                "example_index": index,
                "sample_id": row.sample.sample_id,
                "payload_sha256": row.sample.payload_sha256,
                "target": row.label,
                "prediction": prediction,
                "correct": prediction == row.label,
                "sector": row.sector,
                "operation_id": row.sample.operation_id,
                "view_id": row.sample.view_id,
                "source_family": row.sample.source_family,
            }
        )
    return predictions


def _counting_accuracy(
    model: ReplayFrozenActionModel,
    rows: Sequence[tuple[str, str]],
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
) -> float:
    correct = 0
    for prompt, target in rows:
        prediction = _generate_integer(
            model,
            head="count",
            prompt=prompt,
            stoi=stoi,
            itos=itos,
            null_carrier=False,
            max_length=5,
        )
        correct += prediction == int(target.strip())
    return correct / len(rows)


def replay_action_metrics(predictions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Recompute all reported action metrics without producer helpers."""

    accuracy = sum(bool(row["correct"]) for row in predictions) / len(predictions)
    recalls = []
    f1s = []
    per_action = {}
    for label in range(5):
        relevant = [row for row in predictions if int(row["target"]) == label]
        true_positive = sum(row["prediction"] == label for row in relevant)
        false_negative = len(relevant) - true_positive
        false_positive = sum(
            row["prediction"] == label and int(row["target"]) != label
            for row in predictions
        )
        recall = true_positive / len(relevant) if relevant else 0.0
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0.0
        )
        f1 = (
            2.0 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        recalls.append(recall)
        f1s.append(f1)
        per_action[str(label)] = {
            "support": len(relevant),
            "accuracy": recall,
            "f1": f1,
            "false_negative": false_negative,
        }
    sectors = sorted({int(row["sector"]) for row in predictions})
    return {
        "accuracy": accuracy,
        "macro_f1": statistics.fmean(f1s),
        "worst_action_accuracy": min(recalls),
        "per_action": per_action,
        "per_sector_accuracy": {
            str(sector): statistics.fmean(
                bool(row["correct"])
                for row in predictions
                if int(row["sector"]) == sector
            )
            for sector in sectors
        },
    }


def _paired_exact_p(wins: int, losses: int) -> float:
    discordant = wins + losses
    if not discordant:
        return 1.0
    tail = sum(math.comb(discordant, index) for index in range(min(wins, losses) + 1))
    return min(1.0, 2.0 * tail / (2**discordant))


def _paired_comparison(
    contender: Sequence[Mapping[str, Any]], control: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    left = {
        (int(row["seed"]), int(item["example_index"])): bool(item["correct"])
        for row in contender
        for item in row["predictions"]
    }
    right = {
        (int(row["seed"]), int(item["example_index"])): bool(item["correct"])
        for row in control
        for item in row["predictions"]
    }
    if left.keys() != right.keys():
        raise RuntimeError("replay paired prediction keys differ")
    wins = sum(left[key] and not right[key] for key in left)
    losses = sum(right[key] and not left[key] for key in left)
    p_value = _paired_exact_p(wins, losses)
    return {
        "examples": len(left),
        "wins": wins,
        "losses": losses,
        "ties": len(left) - wins - losses,
        "two_sided_exact_p": p_value,
        "clears_finite_uncertainty_gate": wins > losses and p_value <= 0.05,
    }


def _metric_comparison(
    contender: Sequence[Mapping[str, Any]],
    control: Sequence[Mapping[str, Any]],
    metric: str,
) -> dict[str, Any]:
    left = [float(row["metrics"][metric]) for row in contender]
    right = [float(row["metrics"][metric]) for row in control]
    left_sd = statistics.stdev(left) if len(left) > 1 else 0.0
    right_sd = statistics.stdev(right) if len(right) > 1 else 0.0
    pooled_sd = math.sqrt((left_sd * left_sd + right_sd * right_sd) / 2.0)
    delta = statistics.fmean(left) - statistics.fmean(right)
    threshold = 2.0 * pooled_sd
    return {
        "metric": metric,
        "contender_mean": statistics.fmean(left),
        "control_mean": statistics.fmean(right),
        "mean_delta": delta,
        "pooled_sd": pooled_sd,
        "two_pooled_sd": threshold,
        "clears_positive_gate": delta > threshold,
        "matched_seed_wins": sum(a > b for a, b in zip(left, right, strict=True)),
        "matched_seed_losses": sum(a < b for a, b in zip(left, right, strict=True)),
    }


def _max_numeric_delta(left: Any, right: Any) -> float:
    if isinstance(left, bool) or isinstance(right, bool):
        return 0.0 if left == right else STRUCTURAL_MISMATCH_DELTA
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right))
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        if left.keys() != right.keys():
            return STRUCTURAL_MISMATCH_DELTA
        return max(
            (_max_numeric_delta(left[key], right[key]) for key in left),
            default=0.0,
        )
    if isinstance(left, Sequence) and not isinstance(left, (str, bytes)):
        if not isinstance(right, Sequence) or isinstance(right, (str, bytes)):
            return STRUCTURAL_MISMATCH_DELTA
        if len(left) != len(right):
            return STRUCTURAL_MISMATCH_DELTA
        return max(
            (_max_numeric_delta(a, b) for a, b in zip(left, right, strict=True)),
            default=0.0,
        )
    return 0.0 if left == right else STRUCTURAL_MISMATCH_DELTA


def _prediction_mismatches(
    replayed: Sequence[Mapping[str, Any]], recorded: Sequence[Mapping[str, Any]]
) -> int:
    fields = (
        "example_index",
        "sample_id",
        "payload_sha256",
        "target",
        "prediction",
        "correct",
        "sector",
        "operation_id",
        "view_id",
        "source_family",
    )
    if len(replayed) != len(recorded):
        return max(len(replayed), len(recorded))
    return sum(
        any(left.get(field) != right.get(field) for field in fields)
        for left, right in zip(replayed, recorded, strict=True)
    )


def _frozen_equal(
    parent_state: Mapping[str, Tensor], candidate_state: Mapping[str, Tensor]
) -> bool:
    keys = {key for key in parent_state if key.startswith(FROZEN_PREFIXES)}
    candidate_keys = {key for key in candidate_state if key.startswith(FROZEN_PREFIXES)}
    if keys != candidate_keys:
        return False
    return all(
        key in candidate_state and torch.equal(parent_state[key], candidate_state[key])
        for key in keys
    )


def _load_payload(path: Path, expected_sha256: str) -> dict[str, Any]:
    if _file_sha256(path) != expected_sha256:
        raise RuntimeError(f"artifact hash mismatch: {path}")
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(payload, dict):
        raise RuntimeError(f"model payload is not a mapping: {path}")
    return payload


def verify_run(run_dir: Path, *, tolerance: float = 1e-12) -> dict[str, Any]:
    run_dir = run_dir.resolve(strict=True)
    manifest = _read_json(run_dir / "RUN_MANIFEST.json")
    producer = _read_json(run_dir / "RESULT.json")
    config = manifest["config"]
    errors: list[str] = []

    provider = ClaySourceAdapter(Path(config["source_dir"]))
    dataset = build_frozen_multiview_dataset(
        provider,
        rows_per_view=int(config["rows_per_view"]),
        holdout_rows=int(config["holdout_rows"]),
        seed=int(config["data_seed"]),
    )
    if dict(dataset.manifest) != dict(manifest["dataset"]):
        errors.append("dataset manifest mismatch")
    if dict(sorted(provider.source_hashes.items())) != dict(config["source_hashes"]):
        errors.append("source hash mismatch")

    count_train = _counting_rows(False)
    count_holdout = _counting_rows(True)
    vocab, stoi = _vocab_of(
        count_train,
        count_holdout,
        tuple(row.pair() for row in dataset.static_rows),
        tuple(row.pair() for row in dataset.multiview_rows),
        tuple(row.pair() for row in dataset.holdout_rows),
    )
    if _stable_hash(vocab) != manifest["vocab_sha256"]:
        errors.append("vocabulary hash mismatch")
    itos = {index: char for char, index in stoi.items()}

    recorded_by_arm = {
        arm: {int(row["seed"]): row for row in producer["per_arm"][arm]}
        for arm in ALL_ARMS
    }
    replay_by_arm: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ALL_ARMS}
    receipts = []
    for seed in (int(value) for value in config["seeds"]):
        parent_result = _read_json(run_dir / "parents" / f"seed-{seed}" / "RESULT.json")
        parent_path = run_dir / "parents" / f"seed-{seed}" / "PARENT.pt"
        parent = _load_payload(parent_path, str(parent_result["parent_sha256"]))
        if parent.get("vocab") != vocab:
            errors.append(f"parent vocabulary mismatch for seed {seed}")
        parent_state = parent["model_state"]

        for arm in ALL_ARMS:
            recorded = recorded_by_arm[arm][seed]
            if arm == "no_intervention_adapter":
                payload = parent
                artifact = parent_path
                null_carrier = False
            else:
                result_path = run_dir / "horses" / f"{arm}-seed-{seed}" / "RESULT.json"
                horse_result = _read_json(result_path)
                artifact = run_dir / "horses" / f"{arm}-seed-{seed}" / "MODEL.pt"
                payload = _load_payload(artifact, str(horse_result["model_sha256"]))
                null_carrier = arm == "frozen_adapter_null"
            model = ReplayFrozenActionModel(len(vocab))
            model.load_state_dict(payload["model_state"], strict=True)
            predictions = _predict_actions(
                model,
                dataset.holdout_rows,
                stoi,
                itos,
                null_carrier=null_carrier,
            )
            metrics = replay_action_metrics(predictions)
            count_score = _counting_accuracy(model, count_holdout, stoi, itos)
            mismatch_count = _prediction_mismatches(
                predictions, recorded["predictions"]
            )
            metric_delta = _max_numeric_delta(metrics, recorded["metrics"])
            count_delta = abs(count_score - float(recorded["counting_accuracy"]))
            frozen_exact = _frozen_equal(parent_state, payload["model_state"])
            if mismatch_count:
                errors.append(
                    f"{arm} seed {seed}: {mismatch_count} prediction mismatches"
                )
            if metric_delta > tolerance:
                errors.append(f"{arm} seed {seed}: metric delta {metric_delta}")
            if count_delta > tolerance:
                errors.append(f"{arm} seed {seed}: counting delta {count_delta}")
            if not frozen_exact:
                errors.append(f"{arm} seed {seed}: frozen core differs")
            replay_row = {
                "arm": arm,
                "seed": seed,
                "metrics": metrics,
                "predictions": predictions,
                "counting_accuracy": count_score,
            }
            replay_by_arm[arm].append(replay_row)
            receipts.append(
                {
                    "arm": arm,
                    "seed": seed,
                    "artifact": str(artifact),
                    "artifact_sha256": _file_sha256(artifact),
                    "prediction_sha256": _stable_hash(predictions),
                    "prediction_mismatches": mismatch_count,
                    "max_metric_delta": metric_delta,
                    "counting_delta": count_delta,
                    "frozen_core_bit_identical": frozen_exact,
                }
            )

    comparisons = {}
    paired = {}
    for control in CONTROLS:
        name = f"{PRIMARY_ARM}_vs_{control}"
        comparisons[name] = {
            metric: _metric_comparison(
                replay_by_arm[PRIMARY_ARM], replay_by_arm[control], metric
            )
            for metric in ("accuracy", "macro_f1")
        }
        paired[name] = _paired_comparison(
            replay_by_arm[PRIMARY_ARM], replay_by_arm[control]
        )
    comparison_delta = _max_numeric_delta(comparisons, producer["comparisons"])
    paired_delta = _max_numeric_delta(paired, producer["paired_comparisons"])
    if comparison_delta > tolerance:
        errors.append(f"aggregate comparison delta {comparison_delta}")
    if paired_delta > tolerance:
        errors.append(f"aggregate paired delta {paired_delta}")

    max_metric_delta = max(
        (float(row["max_metric_delta"]) for row in receipts), default=0.0
    )
    result = {
        "schema": SCHEMA,
        "status": (
            "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION"
            if not errors
            else "FAIL_INDEPENDENT_INFERENCE_REPLAY"
        ),
        "authority": AUTHORITY,
        "promotion": "NONE",
        "partial_unfreeze_authorized": False,
        "run_dir": str(run_dir),
        "producer_result_sha256": _file_sha256(run_dir / "RESULT.json"),
        "dataset_manifest_sha256": dataset.manifest["manifest_sha256"],
        "model_receipts": receipts,
        "comparisons": comparisons,
        "paired_comparisons": paired,
        "max_metric_delta": max_metric_delta,
        "aggregate_comparison_delta": comparison_delta,
        "aggregate_paired_delta": paired_delta,
        "errors": errors,
        "completed_at_utc": _utc_now(),
    }
    result["replay_sha256"] = _stable_hash(result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--tolerance", type=float, default=1e-12)
    parser.add_argument("--threads", type=int, default=2)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    torch.set_num_threads(args.threads)
    torch.use_deterministic_algorithms(True)
    result = verify_run(args.run_dir, tolerance=args.tolerance)
    output = args.output or args.run_dir / "INDEPENDENT_REPLAY.json"
    _atomic_json(output, result)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
