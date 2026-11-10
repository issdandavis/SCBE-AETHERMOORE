#!/usr/bin/env python3
"""Source-disjoint probe of the typed Layer-14A predictive audio sidecar."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import statistics
import sys
import wave

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from symphonic_cipher.scbe_aethermoore.ai_brain.predictive_sensory_trits import (  # noqa: E402
    PredictiveSensoryTritRouter,
)
from symphonic_cipher.scbe_aethermoore.layer_contracts import (  # noqa: E402
    ObservationStatus,
    SpectralObservation,
)

SCHEMA = "scbe.l14a-predictive-audio-campaign.v1"
HORSE_SCHEMA = "scbe.l14a-predictive-audio-horse.v1"
CHECKPOINT_SCHEMA = "scbe.l14a-predictive-audio-checkpoint.v1"
FEATURE_WIDTH = 12
CLASS_COUNT = 3
PARAMETER_COUNT = FEATURE_WIDTH * CLASS_COUNT + CLASS_COUNT
WINDOW_SAMPLES = 8_000
SAMPLE_RATE = 16_000
SILENT_RMS = 0.008
SEEDS = (202615011, 202615047, 202615079, 202615113, 202615149)
STEPS = 400
ARMS = (
    "predictive_trits",
    "raw_lags",
    "raw_current",
    "no_adaptation",
    "no_omission",
    "shuffled_binding",
    "random_features",
    "zero_features",
)
SOURCES = {
    "teacher-tracing-code": Path(r"C:\dev\clay-training-runs\teacher-loop-videos-20261109\audio\tracing_code.wav"),
    "teacher-tracing-lists": Path(r"C:\dev\clay-training-runs\teacher-loop-videos-20261109\audio\tracing_lists.wav"),
    "teacher-tracing-nested-loops": Path(
        r"C:\dev\clay-training-runs\teacher-loop-videos-20261109\audio\tracing_nested_loops.wav"
    ),
}
EXPECTED_AUDIO_HASHES = {
    "teacher-tracing-code": "34d47d6339afae9bee965858df6a04c3a989f98522c7d3d4c4325d423719212d",
    "teacher-tracing-lists": "0874e06bd429533997acdaeadfcbd7ed554d5184393c192bbe122338b9cc9c62",
    "teacher-tracing-nested-loops": "5fa198de393c796fc47d3d47eac91d19ca1dd83c599fd3d4f4565d7253a52de3",
}
MANIFEST = Path(r"C:\dev\clay-training-runs\teacher-loop-videos-20261109\dataset\teacher_video_corpus.json")
EXPECTED_MANIFEST_HASH = "4d88f440dd0ef1a4faba6ba8d6d0449326789bbe32be4d1b2c3d633df442f053"
PREREGISTRATION = ROOT / "docs" / "research" / "L14A_PREDICTIVE_AUDIO_PREREGISTRATION_20261110.md"
SYSTEM_MAP = ROOT / "docs" / "research" / "L14A_PREDICTIVE_AUDIO_SYSTEM_MAP_20261110.md"
INVENTORY = Path(r"C:\dev\clay-training-runs\l14a-predictive-audio-20261110\PREBUILD_SYSTEM_INVENTORY.json")
DEFAULT_OUTPUT = Path(r"C:\dev\clay-training-runs\l14a-predictive-audio-20261110\full-v1")


@dataclass(frozen=True)
class SourcePacket:
    source_id: str
    scores: np.ndarray
    features: dict[str, np.ndarray]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _atomic_jsonl(path: Path, rows: list[dict]) -> str:
    encoded = b"".join((canonical_json(row) + "\n").encode("ascii") for row in rows)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_bytes(encoded)
    os.replace(temporary, path)
    return hashlib.sha256(encoded).hexdigest()


def _atomic_torch(path: Path, value: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(value, temporary)
    os.replace(temporary, path)
    return sha256_file(path)


def _stable_seed(*parts: str) -> int:
    payload = "\0".join(parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def load_audio_scores(path: Path) -> np.ndarray:
    """Load one authority WAV and emit fixed non-overlapping bounded RMS scores."""

    with wave.open(str(path), "rb") as handle:
        if (handle.getnchannels(), handle.getsampwidth(), handle.getframerate()) != (1, 2, SAMPLE_RATE):
            raise RuntimeError(f"unexpected WAV authority format: {path}")
        samples = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2").astype(np.float32)
    samples /= 32768.0
    usable = samples.size // WINDOW_SAMPLES * WINDOW_SAMPLES
    if usable < WINDOW_SAMPLES * 3:
        raise RuntimeError(f"audio authority is too short: {path}")
    windows = samples[:usable].reshape(-1, WINDOW_SAMPLES)
    rms = np.sqrt(np.mean(windows * windows, axis=1, dtype=np.float64))
    scores = np.log1p(100.0 * rms) / math.log(101.0)
    scores = np.clip(scores, 0.0, 1.0).astype(np.float32)
    scores[rms <= SILENT_RMS] = 0.0
    return scores


def _observation(score: float) -> SpectralObservation:
    status = ObservationStatus.SILENT if score == 0.0 else ObservationStatus.OBSERVED
    return SpectralObservation(status=status, score=float(score), sample_rate_hz=SAMPLE_RATE, cutoff_hz=4_000.0)


def features_from_scores(scores: np.ndarray, source_id: str) -> dict[str, np.ndarray]:
    """Build all feature arms; causal arms at t consume scores only through t."""

    values = np.asarray(scores, dtype=np.float32)
    if values.ndim != 1 or values.size < 3 or not np.all(np.isfinite(values)):
        raise ValueError("scores must be a finite one-dimensional sequence with at least three values")
    router = PredictiveSensoryTritRouter()
    candidate: list[list[float]] = []
    no_adaptation: list[list[float]] = []
    no_omission: list[list[float]] = []
    raw_lags: list[list[float]] = []
    raw_current: list[list[float]] = []
    previous = 0.0
    ema = 0.0
    for index, value in enumerate(values.tolist()):
        observation = _observation(float(value))
        frame = router.process(observation, precision=1.0)
        predicted = float(frame.predicted or 0.0)
        residual = float(frame.residual or 0.0)
        observed_flag = float(observation.status is ObservationStatus.OBSERVED)
        silent_flag = 1.0 - observed_flag
        base = [
            float(value),
            predicted,
            residual,
            float(frame.adaptation),
            float(frame.precision),
            float(frame.omission),
            float(frame.route_score),
            float(frame.state.primary),
            float(frame.state.mirror),
            abs(residual),
            previous,
            observed_flag,
        ]
        candidate.append(base)
        no_adaptation.append([*base[:3], 0.0, base[4], base[5], abs(residual) + 0.5 * base[5], *base[7:]])
        mirror_without_omission = 1.0 if observed_flag else 0.0
        no_omission.append(
            [
                *base[:5],
                0.0,
                abs(residual) - 0.25 * float(frame.adaptation),
                base[7],
                mirror_without_omission,
                *base[9:],
            ]
        )
        delta = float(value) - previous
        ema = float(value) if index == 0 else 0.8 * ema + 0.2 * float(value)
        raw_lags.append(
            [
                float(value),
                previous,
                delta,
                abs(delta),
                float(value) * previous,
                ema,
                observed_flag,
                silent_flag,
                0,
                0,
                0,
                0,
            ]
        )
        raw_current.append([float(value), observed_flag, silent_flag, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        previous = float(value)
    arrays = {
        "predictive_trits": np.asarray(candidate, dtype=np.float32),
        "raw_lags": np.asarray(raw_lags, dtype=np.float32),
        "raw_current": np.asarray(raw_current, dtype=np.float32),
        "no_adaptation": np.asarray(no_adaptation, dtype=np.float32),
        "no_omission": np.asarray(no_omission, dtype=np.float32),
    }
    rng = np.random.default_rng(_stable_seed(source_id, "shuffled-binding"))
    arrays["shuffled_binding"] = arrays["predictive_trits"][rng.permutation(values.size)].copy()
    random_rng = np.random.default_rng(_stable_seed(source_id, "random-features"))
    arrays["random_features"] = random_rng.standard_normal((values.size, FEATURE_WIDTH), dtype=np.float32)
    arrays["zero_features"] = np.zeros((values.size, FEATURE_WIDTH), dtype=np.float32)
    if set(arrays) != set(ARMS) or any(array.shape != (values.size, FEATURE_WIDTH) for array in arrays.values()):
        raise RuntimeError("feature arm shape mismatch")
    if not all(np.all(np.isfinite(array)) for array in arrays.values()):
        raise RuntimeError("non-finite feature packet")
    return arrays


def future_perturbation_count(scores: np.ndarray, source_id: str) -> int:
    """Count candidate prefix changes after perturbing only future observations."""

    split = max(2, scores.size // 2)
    changed = scores.copy()
    changed[split:] = changed[split:][::-1]
    original = features_from_scores(scores, source_id)["predictive_trits"][:split]
    perturbed = features_from_scores(changed, source_id)["predictive_trits"][:split]
    return int(np.count_nonzero(original != perturbed))


def load_packets(*, enforce_hashes: bool) -> dict[str, SourcePacket]:
    if enforce_hashes and sha256_file(MANIFEST) != EXPECTED_MANIFEST_HASH:
        raise RuntimeError("teacher corpus manifest hash changed")
    packets: dict[str, SourcePacket] = {}
    for source_id, path in SOURCES.items():
        if enforce_hashes and sha256_file(path) != EXPECTED_AUDIO_HASHES[source_id]:
            raise RuntimeError(f"audio authority changed: {source_id}")
        scores = load_audio_scores(path)
        if future_perturbation_count(scores, source_id):
            raise RuntimeError(f"future observations altered causal prefix: {source_id}")
        packets[source_id] = SourcePacket(source_id, scores, features_from_scores(scores, source_id))
    return packets


def _targets(scores: np.ndarray, threshold: float) -> np.ndarray:
    delta = scores[1:] - scores[:-1]
    return np.where(delta < -threshold, 0, np.where(delta > threshold, 2, 1)).astype(np.int64)


def _fold_arrays(
    packets: dict[str, SourcePacket], held_source: str, arm: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str], float]:
    train_ids = [source_id for source_id in sorted(packets) if source_id != held_source]
    if held_source in train_ids or len(train_ids) != 2:
        raise RuntimeError("source-disjoint fold construction failed")
    train_deltas = np.concatenate(
        [
            np.abs(packet.scores[1:] - packet.scores[:-1])
            for source_id, packet in packets.items()
            if source_id in train_ids
        ]
    )
    threshold = float(np.quantile(train_deltas, 1.0 / 3.0))
    train_x = np.concatenate([packets[source_id].features[arm][:-1] for source_id in train_ids])
    train_y = np.concatenate([_targets(packets[source_id].scores, threshold) for source_id in train_ids])
    held = packets[held_source]
    eval_x = held.features[arm][:-1]
    eval_y = _targets(held.scores, threshold)
    record_ids = [f"{held_source}:{index:06d}" for index in range(eval_y.size)]
    return train_x, train_y, eval_x, eval_y, record_ids, threshold


def _normalize(train_x: np.ndarray, eval_x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mean = train_x.mean(axis=0, dtype=np.float64).astype(np.float32)
    std = train_x.std(axis=0, dtype=np.float64).astype(np.float32)
    std[std < 1e-6] = 1.0
    return (train_x - mean) / std, (eval_x - mean) / std, mean, std


def _balanced_accuracy(targets: np.ndarray, predictions: np.ndarray) -> float:
    recalls = []
    for value in range(CLASS_COUNT):
        mask = targets == value
        if not np.any(mask):
            raise RuntimeError("held fold lost a target class")
        recalls.append(float(np.mean(predictions[mask] == targets[mask])))
    return statistics.fmean(recalls)


def _latest_checkpoint(root: Path) -> dict | None:
    pointer = root / "LATEST.json"
    if not pointer.exists():
        return None
    latest = json.loads(pointer.read_text(encoding="utf-8"))
    path = root / latest["path"]
    if sha256_file(path) != latest["sha256"]:
        raise RuntimeError(f"checkpoint pointer hash mismatch: {path}")
    return torch.load(path, map_location="cpu", weights_only=False)


def _save_checkpoint(
    root: Path, step: int, model: nn.Linear, optimizer: torch.optim.Optimizer, loss_trace: list
) -> None:
    slot = "checkpoint_A.pt" if (step // 50) % 2 == 0 else "checkpoint_B.pt"
    path = root / slot
    state = {
        "schema": CHECKPOINT_SCHEMA,
        "step": step,
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "loss_trace": loss_trace,
        "torch_rng_state": torch.get_rng_state(),
        "cuda_rng_state": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
    }
    digest = _atomic_torch(path, state)
    _atomic_json(root / "LATEST.json", {"schema": CHECKPOINT_SCHEMA, "path": slot, "sha256": digest, "step": step})


def _verify_completed(result_path: Path, held_source: str, arm: str, seed: int) -> dict:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if (result.get("held_source"), result.get("arm"), result.get("seed")) != (held_source, arm, seed):
        raise RuntimeError(f"horse identity mismatch: {result_path}")
    for field in ("checkpoint", "prediction_ledger"):
        path = result_path.parent / result[field]["path"]
        if sha256_file(path) != result[field]["sha256"]:
            raise RuntimeError(f"completed horse artifact changed: {path}")
    return result


def _run_horse(
    packets: dict[str, SourcePacket],
    output: Path,
    held_source: str,
    arm: str,
    seed: int,
    *,
    steps: int,
    device: torch.device,
) -> dict:
    root = output / "horses" / f"hold-{held_source}__{arm}__{seed}"
    result_path = root / "RESULT.json"
    if result_path.exists():
        return _verify_completed(result_path, held_source, arm, seed)
    if shutil.disk_usage("C:\\").free < 5 * 1024**3:
        raise RuntimeError("runtime disk gate fell below 5 GiB")
    root.mkdir(parents=True, exist_ok=True)
    train_x, train_y, eval_x, eval_y, record_ids, threshold = _fold_arrays(packets, held_source, arm)
    train_x, eval_x, mean, std = _normalize(train_x, eval_x)
    torch.manual_seed(seed)
    random.seed(seed)
    np.random.seed(seed & 0xFFFFFFFF)
    model = nn.Linear(FEATURE_WIDTH, CLASS_COUNT).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.03, weight_decay=1e-4)
    class_counts = np.bincount(train_y, minlength=CLASS_COUNT).astype(np.float32)
    class_weights = torch.tensor(train_y.size / (CLASS_COUNT * class_counts), dtype=torch.float32, device=device)
    x_train = torch.tensor(train_x, dtype=torch.float32, device=device)
    y_train = torch.tensor(train_y, dtype=torch.long, device=device)
    start_step = 0
    loss_trace: list[dict[str, float | int]] = []
    prior = _latest_checkpoint(root)
    if prior is not None:
        model.load_state_dict(prior["model"])
        optimizer.load_state_dict(prior["optimizer"])
        loss_trace = list(prior["loss_trace"])
        torch.set_rng_state(prior["torch_rng_state"])
        if device.type == "cuda" and prior["cuda_rng_state"]:
            torch.cuda.set_rng_state_all(prior["cuda_rng_state"])
        start_step = int(prior["step"])
    for step in range(start_step, steps):
        optimizer.zero_grad(set_to_none=True)
        logits = model(x_train)
        loss = F.cross_entropy(logits, y_train, weight=class_weights)
        if not torch.isfinite(loss):
            raise RuntimeError(f"non-finite loss in {held_source}/{arm}/{seed}")
        loss.backward()
        optimizer.step()
        completed = step + 1
        if completed % 50 == 0 or completed == steps:
            loss_trace.append({"step": completed, "loss": float(loss.detach().cpu())})
            _save_checkpoint(root, completed, model, optimizer, loss_trace)
    final_checkpoint = root / "FINAL_CHECKPOINT.pt"
    checkpoint_sha = _atomic_torch(
        final_checkpoint,
        {
            "schema": CHECKPOINT_SCHEMA,
            "step": steps,
            "held_source": held_source,
            "arm": arm,
            "seed": seed,
            "feature_mean": mean,
            "feature_std": std,
            "model": model.state_dict(),
            "target_threshold": threshold,
            "promotion_authorized": False,
            "partial_unfreeze_authorized": False,
        },
    )
    with torch.no_grad():
        logits = model(torch.tensor(eval_x, dtype=torch.float32, device=device))
        probabilities = torch.softmax(logits, dim=1).cpu().numpy()
        predictions = probabilities.argmax(axis=1)
        cross_entropy = float(F.cross_entropy(logits, torch.tensor(eval_y, dtype=torch.long, device=device)).cpu())
    ledger = [
        {
            "schema": "scbe.l14a-predictive-audio-prediction.v1",
            "record_id": record_id,
            "target": int(target),
            "prediction": int(prediction),
            "correct": bool(target == prediction),
            "probabilities": [float(value) for value in probability],
        }
        for record_id, target, prediction, probability in zip(
            record_ids, eval_y, predictions, probabilities, strict=True
        )
    ]
    ledger_path = root / "PREDICTIONS.jsonl"
    ledger_sha = _atomic_jsonl(ledger_path, ledger)
    result = {
        "schema": HORSE_SCHEMA,
        "held_source": held_source,
        "arm": arm,
        "seed": seed,
        "steps": steps,
        "device": str(device),
        "train_records": int(train_y.size),
        "eval_records": int(eval_y.size),
        "target_threshold": threshold,
        "target_counts": np.bincount(eval_y, minlength=CLASS_COUNT).tolist(),
        "trainable_parameters": sum(parameter.numel() for parameter in model.parameters()),
        "loss_trace": loss_trace,
        "cross_entropy": cross_entropy,
        "accuracy": float(np.mean(predictions == eval_y)),
        "balanced_accuracy": _balanced_accuracy(eval_y, predictions),
        "checkpoint": {"path": final_checkpoint.name, "sha256": checkpoint_sha},
        "prediction_ledger": {"path": ledger_path.name, "sha256": ledger_sha},
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    core = dict(result)
    result["result_sha256"] = hashlib.sha256(canonical_json(core).encode("ascii")).hexdigest()
    _atomic_json(result_path, result)
    return result


def _pooled_sd(left: list[float], right: list[float]) -> float:
    if len(left) < 2:
        return 0.0
    return math.sqrt((statistics.variance(left) + statistics.variance(right)) / 2.0)


def _finite_balanced_bound(target_counts: list[int]) -> float:
    variance = sum(0.25 / count for count in target_counts) / (CLASS_COUNT * CLASS_COUNT)
    return 2.0 * math.sqrt(2.0 * variance)


def _paired_exact(left: list[dict], right: list[dict]) -> dict:
    candidate_only = 0
    control_only = 0
    for first, second in zip(left, right, strict=True):
        if first["record_id"] != second["record_id"] or first["target"] != second["target"]:
            raise RuntimeError("paired prediction ledgers do not align")
        candidate_only += int(first["correct"] and not second["correct"])
        control_only += int(second["correct"] and not first["correct"])
    discordant = candidate_only + control_only
    if discordant == 0:
        probability = 1.0
    else:
        lower = min(candidate_only, control_only)
        tail = sum(math.comb(discordant, value) for value in range(lower + 1)) / (2**discordant)
        probability = min(1.0, 2.0 * tail)
    return {
        "candidate_only_correct": candidate_only,
        "control_only_correct": control_only,
        "discordant": discordant,
        "two_sided_exact_p": probability,
    }


def _ledger(output: Path, horse: dict) -> list[dict]:
    root = output / "horses" / f"hold-{horse['held_source']}__{horse['arm']}__{horse['seed']}"
    return [
        json.loads(line)
        for line in (root / horse["prediction_ledger"]["path"]).read_text(encoding="utf-8").splitlines()
    ]


def _aggregate(output: Path, horses: list[dict]) -> tuple[dict, dict, bool]:
    summaries: dict[str, dict[str, dict]] = {}
    comparisons: dict[str, dict[str, dict]] = {}
    gate = True
    for held_source in SOURCES:
        summaries[held_source] = {}
        rows_by_arm = {
            arm: [row for row in horses if row["held_source"] == held_source and row["arm"] == arm] for arm in ARMS
        }
        for arm, rows in rows_by_arm.items():
            balanced = [float(row["balanced_accuracy"]) for row in rows]
            summaries[held_source][arm] = {
                "balanced_accuracy_values": balanced,
                "balanced_accuracy_mean": statistics.fmean(balanced),
                "balanced_accuracy_sd": statistics.stdev(balanced) if len(balanced) > 1 else 0.0,
                "cross_entropy_values": [float(row["cross_entropy"]) for row in rows],
                "cross_entropy_mean": statistics.fmean(float(row["cross_entropy"]) for row in rows),
            }
        candidate = summaries[held_source]["predictive_trits"]
        comparisons[held_source] = {}
        for control in ARMS[1:]:
            right = summaries[held_source][control]
            deltas = [
                left - other
                for left, other in zip(
                    candidate["balanced_accuracy_values"], right["balanced_accuracy_values"], strict=True
                )
            ]
            target_counts = next(row for row in rows_by_arm["predictive_trits"])["target_counts"]
            required = max(
                2.0 * _pooled_sd(candidate["balanced_accuracy_values"], right["balanced_accuracy_values"]),
                _finite_balanced_bound(target_counts),
            )
            paired = []
            for seed in SEEDS:
                left_horse = next(row for row in rows_by_arm["predictive_trits"] if row["seed"] == seed)
                right_horse = next(row for row in rows_by_arm[control] if row["seed"] == seed)
                paired.append(
                    {"seed": seed, **_paired_exact(_ledger(output, left_horse), _ledger(output, right_horse))}
                )
            margin = float(candidate["balanced_accuracy_mean"]) - float(right["balanced_accuracy_mean"])
            passed = (
                sum(delta > 0 for delta in deltas) >= 4
                and sum(row["two_sided_exact_p"] <= 0.05 for row in paired) >= 4
                and margin > required
                and float(candidate["cross_entropy_mean"]) < float(right["cross_entropy_mean"])
            )
            comparisons[held_source][control] = {
                "paired_seed_deltas": deltas,
                "seed_wins": sum(delta > 0 for delta in deltas),
                "mean_margin": margin,
                "required_margin": required,
                "paired_exact": paired,
                "paired_exact_passes": sum(row["two_sided_exact_p"] <= 0.05 for row in paired),
                "candidate_cross_entropy_mean": candidate["cross_entropy_mean"],
                "control_cross_entropy_mean": right["cross_entropy_mean"],
                "passes": passed,
            }
            gate = gate and passed
    return summaries, comparisons, gate


def run_campaign(
    output: Path = DEFAULT_OUTPUT,
    *,
    seeds: tuple[int, ...] = SEEDS,
    steps: int = STEPS,
    device_name: str = "cuda",
    enforce_preregistered: bool = True,
) -> dict:
    global SEEDS
    if enforce_preregistered and (seeds != SEEDS or steps != STEPS or device_name != "cuda"):
        raise ValueError("campaign differs from preregistration")
    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA campaign requested without CUDA")
    if enforce_preregistered and shutil.disk_usage("C:\\").free < 25 * 1024**3:
        raise RuntimeError("campaign requires at least 25 GiB free on C:")
    SEEDS = tuple(seeds)
    packets = load_packets(enforce_hashes=enforce_preregistered)
    output.mkdir(parents=True, exist_ok=True)
    pin = {
        "schema": "scbe.l14a-predictive-audio-run-pin.v1",
        "seeds": list(seeds),
        "steps": steps,
        "device": device_name,
        "arms": list(ARMS),
        "sources": {source_id: {"path": str(path), "sha256": sha256_file(path)} for source_id, path in SOURCES.items()},
        "manifest_sha256": sha256_file(MANIFEST),
        "implementation_sha256": sha256_file(Path(__file__)),
        "preregistration_sha256": sha256_file(PREREGISTRATION),
        "system_map_sha256": sha256_file(SYSTEM_MAP),
        "inventory_sha256": sha256_file(INVENTORY),
        "feature_width": FEATURE_WIDTH,
        "trainable_parameters_per_arm": PARAMETER_COUNT,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    pin_path = output / "RUN_PIN.json"
    if pin_path.exists() and json.loads(pin_path.read_text(encoding="utf-8")) != pin:
        raise RuntimeError("run pin collision")
    _atomic_json(pin_path, pin)
    horses: list[dict] = []
    total = len(SOURCES) * len(ARMS) * len(seeds)
    device = torch.device(device_name)
    for held_source in SOURCES:
        for seed in seeds:
            for arm in ARMS:
                _atomic_json(
                    output / "STATUS.json",
                    {
                        "schema": SCHEMA,
                        "phase": "TRAINING",
                        "held_source": held_source,
                        "seed": seed,
                        "arm": arm,
                        "completed_horses": len(horses),
                        "total_horses": total,
                        "promotion_authorized": False,
                        "partial_unfreeze_authorized": False,
                    },
                )
                horses.append(_run_horse(packets, output, held_source, arm, seed, steps=steps, device=device))
    summaries, comparisons, gate = _aggregate(output, horses)
    result = {
        "schema": SCHEMA,
        "run_pin": {"path": pin_path.name, "sha256": sha256_file(pin_path)},
        "horse_count": len(horses),
        "seeds": list(seeds),
        "steps": steps,
        "device": device_name,
        "arms": list(ARMS),
        "sources": list(SOURCES),
        "future_perturbation_mismatches": {
            source_id: future_perturbation_count(packet.scores, source_id) for source_id, packet in packets.items()
        },
        "summaries": summaries,
        "comparisons": comparisons,
        "control_gate_passed": gate,
        "status": "PREDICTIVE_AUDIO_PROBE_PASS_NO_PROMOTION" if gate else "NO_PROMOTION_GATE_FAILED_OR_UNDERPOWERED",
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
        "existing_weights_modified": False,
    }
    core = dict(result)
    result["result_sha256"] = hashlib.sha256(canonical_json(core).encode("ascii")).hexdigest()
    _atomic_json(output / "MATRIX_RESULT.json", result)
    _atomic_json(
        output / "STATUS.json",
        {
            "schema": SCHEMA,
            "phase": "COMPLETE",
            "status": result["status"],
            "horse_count": len(horses),
            "result_sha256": result["result_sha256"],
            "promotion_authorized": False,
            "partial_unfreeze_authorized": False,
        },
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--steps", type=int, default=STEPS)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    parser.add_argument("--allow-development-configuration", action="store_true")
    args = parser.parse_args()
    result = run_campaign(
        args.output,
        seeds=tuple(args.seeds),
        steps=args.steps,
        device_name=args.device,
        enforce_preregistered=not args.allow_development_configuration,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
