#!/usr/bin/env python3
"""Independent read-only replay of the Layer-14A predictive audio probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import wave

import numpy as np
import torch

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

RUN_ROOT = Path(r"C:\dev\clay-training-runs\l14a-predictive-audio-20261110\full-v1")
OUTPUT = Path(r"C:\dev\clay-training-runs\l14a-predictive-audio-20261110\full-v1-independent-replay-v2")
SOURCES = {
    "teacher-tracing-code": Path(r"C:\dev\clay-training-runs\teacher-loop-videos-20261109\audio\tracing_code.wav"),
    "teacher-tracing-lists": Path(r"C:\dev\clay-training-runs\teacher-loop-videos-20261109\audio\tracing_lists.wav"),
    "teacher-tracing-nested-loops": Path(
        r"C:\dev\clay-training-runs\teacher-loop-videos-20261109\audio\tracing_nested_loops.wav"
    ),
}
WINDOW_SAMPLES = 8_000
SAMPLE_RATE = 16_000
SILENT_RMS = 0.008
FEATURE_WIDTH = 12
CLASS_COUNT = 3
PROBABILITY_ATOL = 2e-6


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _stable_seed(*parts: str) -> int:
    return int.from_bytes(hashlib.sha256("\0".join(parts).encode()).digest()[:8], "big")


def _scores(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as handle:
        if (handle.getnchannels(), handle.getsampwidth(), handle.getframerate()) != (1, 2, SAMPLE_RATE):
            raise RuntimeError(f"unexpected replay WAV format: {path}")
        samples = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2").astype(np.float64)
    samples /= 32768.0
    usable = samples.size // WINDOW_SAMPLES * WINDOW_SAMPLES
    windows = samples[:usable].reshape(-1, WINDOW_SAMPLES)
    rms = np.sqrt(np.mean(np.square(windows), axis=1))
    score = np.clip(np.log1p(100.0 * rms) / math.log(101.0), 0.0, 1.0).astype(np.float32)
    score[rms <= SILENT_RMS] = 0.0
    return score


def _observation(score: float) -> SpectralObservation:
    status = ObservationStatus.SILENT if score == 0.0 else ObservationStatus.OBSERVED
    return SpectralObservation(status, float(score), SAMPLE_RATE, 4_000.0)


def replay_features(scores: np.ndarray, source_id: str) -> dict[str, np.ndarray]:
    """Separate implementation of every producer feature arm."""

    router = PredictiveSensoryTritRouter()
    candidate = np.zeros((scores.size, FEATURE_WIDTH), dtype=np.float32)
    raw_lags = np.zeros_like(candidate)
    raw_current = np.zeros_like(candidate)
    no_adaptation = np.zeros_like(candidate)
    no_omission = np.zeros_like(candidate)
    previous = 0.0
    ema = 0.0
    for index, scalar in enumerate(scores.tolist()):
        observation = _observation(float(scalar))
        frame = router.process(observation, precision=1.0)
        predicted = 0.0 if frame.predicted is None else float(frame.predicted)
        residual = 0.0 if frame.residual is None else float(frame.residual)
        observed = float(observation.status is ObservationStatus.OBSERVED)
        omission = float(frame.omission)
        candidate[index] = (
            scalar,
            predicted,
            residual,
            frame.adaptation,
            frame.precision,
            omission,
            frame.route_score,
            frame.state.primary,
            frame.state.mirror,
            abs(residual),
            previous,
            observed,
        )
        no_adaptation[index] = candidate[index]
        no_adaptation[index, 3] = 0.0
        no_adaptation[index, 6] = abs(residual) + 0.5 * omission
        no_omission[index] = candidate[index]
        no_omission[index, 5] = 0.0
        no_omission[index, 6] = abs(residual) - 0.25 * float(frame.adaptation)
        no_omission[index, 8] = observed
        delta = float(scalar) - previous
        ema = float(scalar) if index == 0 else 0.8 * ema + 0.2 * float(scalar)
        raw_lags[index, :8] = (
            scalar,
            previous,
            delta,
            abs(delta),
            float(scalar) * previous,
            ema,
            observed,
            1.0 - observed,
        )
        raw_current[index, :3] = (scalar, observed, 1.0 - observed)
        previous = float(scalar)
    rng = np.random.default_rng(_stable_seed(source_id, "shuffled-binding"))
    shuffled = candidate[rng.permutation(scores.size)].copy()
    random_rng = np.random.default_rng(_stable_seed(source_id, "random-features"))
    random_features = random_rng.standard_normal((scores.size, FEATURE_WIDTH), dtype=np.float32)
    return {
        "predictive_trits": candidate,
        "raw_lags": raw_lags,
        "raw_current": raw_current,
        "no_adaptation": no_adaptation,
        "no_omission": no_omission,
        "shuffled_binding": shuffled,
        "random_features": random_features,
        "zero_features": np.zeros_like(candidate),
    }


def _targets(scores: np.ndarray, threshold: float) -> np.ndarray:
    delta = scores[1:] - scores[:-1]
    return np.where(delta < -threshold, 0, np.where(delta > threshold, 2, 1)).astype(np.int64)


def _balanced(targets: np.ndarray, predictions: np.ndarray) -> float:
    return float(np.mean([np.mean(predictions[targets == value] == value) for value in range(CLASS_COUNT)]))


def _argmax_matches_or_is_tied(saved_prediction: int, probabilities: np.ndarray) -> tuple[bool, bool]:
    """Classify a replay argmax without treating CPU/GPU near-ties as divergence."""
    replay_prediction = int(probabilities.argmax())
    if replay_prediction == saved_prediction:
        return True, False
    saved_is_numerically_maximal = float(probabilities.max() - probabilities[saved_prediction]) <= PROBABILITY_ATOL
    return saved_is_numerically_maximal, saved_is_numerically_maximal


def replay(run_root: Path, output: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite replay root: {output}")
    output.mkdir(parents=True, exist_ok=True)
    matrix_path = run_root / "MATRIX_RESULT.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    if matrix.get("schema") != "scbe.l14a-predictive-audio-campaign.v1" or matrix.get("horse_count") != 120:
        raise RuntimeError("source matrix is not the complete preregistered campaign")
    source_scores = {source_id: _scores(path) for source_id, path in SOURCES.items()}
    source_features = {source_id: replay_features(source_scores[source_id], source_id) for source_id in source_scores}
    prediction_mismatches = 0
    argmax_tie_variances = 0
    probability_mismatches = 0
    metric_mismatches = 0
    threshold_mismatches = 0
    horse_receipts = []
    ledger_digest = hashlib.sha256()
    for held_source in matrix["sources"]:
        train_ids = [source_id for source_id in sorted(SOURCES) if source_id != held_source]
        train_delta = np.concatenate(
            [np.abs(source_scores[source_id][1:] - source_scores[source_id][:-1]) for source_id in train_ids]
        )
        expected_threshold = float(np.quantile(train_delta, 1.0 / 3.0))
        for seed in matrix["seeds"]:
            for arm in matrix["arms"]:
                root = run_root / "horses" / f"hold-{held_source}__{arm}__{seed}"
                horse = json.loads((root / "RESULT.json").read_text(encoding="utf-8"))
                checkpoint_path = root / horse["checkpoint"]["path"]
                if _sha256(checkpoint_path) != horse["checkpoint"]["sha256"]:
                    raise RuntimeError(f"checkpoint hash mismatch: {checkpoint_path}")
                checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
                threshold = float(checkpoint["target_threshold"])
                threshold_mismatches += int(not math.isclose(threshold, expected_threshold, abs_tol=1e-12))
                features = source_features[held_source][arm][:-1]
                mean = np.asarray(checkpoint["feature_mean"], dtype=np.float32)
                std = np.asarray(checkpoint["feature_std"], dtype=np.float32)
                normalized = (features - mean) / std
                weight = checkpoint["model"]["weight"].detach().cpu().numpy().astype(np.float32)
                bias = checkpoint["model"]["bias"].detach().cpu().numpy().astype(np.float32)
                logits = normalized @ weight.T + bias
                logits -= logits.max(axis=1, keepdims=True)
                probabilities = np.exp(logits.astype(np.float64))
                probabilities /= probabilities.sum(axis=1, keepdims=True)
                predictions = probabilities.argmax(axis=1)
                targets = _targets(source_scores[held_source], threshold)
                saved = [
                    json.loads(line)
                    for line in (root / horse["prediction_ledger"]["path"]).read_text(encoding="utf-8").splitlines()
                ]
                local_prediction = 0
                local_tie_variance = 0
                local_probability = 0
                canonical_predictions = predictions.copy()
                for index, (target, prediction, probability, prior) in enumerate(
                    zip(targets, predictions, probabilities, saved, strict=True)
                ):
                    expected_id = f"{held_source}:{index:06d}"
                    identity_match = prior["record_id"] == expected_id and prior["target"] == int(target)
                    argmax_match, tie_variance = _argmax_matches_or_is_tied(int(prior["prediction"]), probability)
                    prediction_match = identity_match and argmax_match
                    probability_match = np.allclose(
                        np.asarray(prior["probabilities"], dtype=np.float64),
                        probability,
                        atol=PROBABILITY_ATOL,
                        rtol=0.0,
                    )
                    if identity_match and probability_match and tie_variance:
                        canonical_predictions[index] = int(prior["prediction"])
                        local_tie_variance += 1
                    local_prediction += int(not prediction_match)
                    local_probability += int(not probability_match)
                    ledger_digest.update(
                        _canonical(
                            {
                                "held_source": held_source,
                                "arm": arm,
                                "seed": seed,
                                "record_id": expected_id,
                                "prediction": int(prediction),
                                "target": int(target),
                            }
                        )
                        + b"\n"
                    )
                cross_entropy = float(
                    -np.log(np.clip(probabilities[np.arange(targets.size), targets], 1e-30, 1)).mean()
                )
                balanced = _balanced(targets, canonical_predictions)
                accuracy = float(np.mean(canonical_predictions == targets))
                metric_match = (
                    math.isclose(cross_entropy, float(horse["cross_entropy"]), abs_tol=2e-6)
                    and math.isclose(balanced, float(horse["balanced_accuracy"]), abs_tol=1e-12)
                    and math.isclose(accuracy, float(horse["accuracy"]), abs_tol=1e-12)
                )
                prediction_mismatches += local_prediction
                argmax_tie_variances += local_tie_variance
                probability_mismatches += local_probability
                metric_mismatches += int(not metric_match)
                horse_receipts.append(
                    {
                        "horse": root.name,
                        "checkpoint_sha256": horse["checkpoint"]["sha256"],
                        "prediction_mismatches": local_prediction,
                        "argmax_tie_variances": local_tie_variance,
                        "probability_mismatches": local_probability,
                        "metric_match": metric_match,
                    }
                )
    passed = not (prediction_mismatches or probability_mismatches or metric_mismatches or threshold_mismatches)
    core = {
        "schema": "scbe.l14a-predictive-audio-independent-replay.v2",
        "source_run": str(run_root.resolve(strict=True)),
        "source_matrix_sha256": _sha256(matrix_path),
        "horse_count": len(horse_receipts),
        "prediction_mismatches": prediction_mismatches,
        "argmax_tie_variances": argmax_tie_variances,
        "probability_mismatches": probability_mismatches,
        "metric_mismatches": metric_mismatches,
        "threshold_mismatches": threshold_mismatches,
        "ledger_sha256": ledger_digest.hexdigest(),
        "horse_receipts": horse_receipts,
        "status": "PASS_READ_ONLY_INFERENCE_REPLAY_NO_PROMOTION" if passed else "FAIL_PRESERVED_NO_PROMOTION",
        "promotion": "NONE",
        "partial_unfreeze": "NONE",
        "training": False,
    }
    result = {**core, "result_sha256": hashlib.sha256(_canonical(core)).hexdigest()}
    _atomic_json(output / "REPLAY_RESULT.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=RUN_ROOT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = replay(args.run_root, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
