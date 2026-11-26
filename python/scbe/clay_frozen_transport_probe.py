"""Locate action-information loss inside a frozen byte-token Clay parent.

This diagnostic never trains or mutates a checkpoint.  It rebuilds the exact
source-disjoint dataset recorded by a frozen-multiview campaign, verifies the
dataset receipt, and compares fixed linear probes over:

* the canonical 37-value float state reconstructed from its byte tokens; and
* the terminal hidden carrier produced by the frozen counting GRU.

If the float probe is strong while the hidden probe is weak, the evidence
supports input-facing adaptation rather than a wider downstream adapter.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import struct
import sys
from typing import Any, Mapping, Sequence

import numpy as np
import torch


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_feature(prompt: str, *, byte_token_base: int, width: int) -> np.ndarray:
    """Recover canonical big-endian float32 values from one action prompt."""

    token_text = prompt[3:-3]
    payload = bytes(ord(token) - byte_token_base for token in token_text)
    expected = width * 4
    if len(payload) != expected:
        raise ValueError(f"expected {expected} feature bytes, received {len(payload)}")
    return np.asarray(struct.unpack(f">{width}f", payload), dtype=np.float32)


def _standardized_design(
    train: np.ndarray, test: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    mean = train.mean(axis=0, dtype=np.float64)
    scale = train.std(axis=0, dtype=np.float64)
    scale[scale < 1e-12] = 1.0
    train_z = (train.astype(np.float64) - mean) / scale
    test_z = (test.astype(np.float64) - mean) / scale
    return (
        np.column_stack((np.ones(len(train_z)), train_z)),
        np.column_stack((np.ones(len(test_z)), test_z)),
    )


def ridge_predictions(
    train: np.ndarray,
    labels: np.ndarray,
    test: np.ndarray,
    *,
    class_count: int,
    alpha: float = 1.0,
) -> np.ndarray:
    """Return a fixed standardized one-vs-all ridge classifier."""

    design, test_design = _standardized_design(train, test)
    targets = np.eye(class_count, dtype=np.float64)[labels]
    penalty = np.eye(design.shape[1], dtype=np.float64) * float(alpha)
    penalty[0, 0] = 0.0
    weights = np.linalg.solve(
        design.T @ design + penalty,
        design.T @ targets,
    )
    return np.asarray((test_design @ weights).argmax(axis=1), dtype=np.int64)


def centroid_predictions(
    train: np.ndarray,
    labels: np.ndarray,
    test: np.ndarray,
    *,
    class_count: int,
) -> np.ndarray:
    """Return nearest-class-centroid predictions in standardized space."""

    design, test_design = _standardized_design(train, test)
    train_z = design[:, 1:]
    test_z = test_design[:, 1:]
    centroids = np.stack(
        [train_z[labels == label].mean(axis=0) for label in range(class_count)]
    )
    distance = ((test_z[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
    return np.asarray(distance.argmin(axis=1), dtype=np.int64)


def probe_report(
    train: np.ndarray,
    labels: np.ndarray,
    test: np.ndarray,
    test_labels: np.ndarray,
    *,
    shuffle_seed: int,
) -> dict[str, Any]:
    class_count = int(max(labels.max(), test_labels.max())) + 1
    ridge = ridge_predictions(train, labels, test, class_count=class_count)
    centroid = centroid_predictions(train, labels, test, class_count=class_count)
    shuffled = labels.copy()
    np.random.default_rng(shuffle_seed).shuffle(shuffled)
    shuffled_ridge = ridge_predictions(
        train,
        shuffled,
        test,
        class_count=class_count,
    )
    return {
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "width": int(train.shape[1]),
        "nearest_centroid_accuracy": float(np.mean(centroid == test_labels)),
        "ridge_alpha_1_accuracy": float(np.mean(ridge == test_labels)),
        "shuffled_label_ridge_accuracy": float(np.mean(shuffled_ridge == test_labels)),
    }


@torch.inference_mode()
def hidden_carriers(
    model: torch.nn.Module,
    rows: Sequence[Any],
    stoi: Mapping[str, int],
    *,
    bos: str,
    sep: str,
    batch_size: int,
    device: str,
) -> np.ndarray:
    """Read the causal carrier used to predict the first action token."""

    result: list[np.ndarray] = []
    model.eval()
    for begin in range(0, len(rows), batch_size):
        batch = rows[begin : begin + batch_size]
        encoded = [
            [stoi[bos], *(stoi[token] for token in row.prompt), stoi[sep]]
            for row in batch
        ]
        lengths = {len(item) for item in encoded}
        if len(lengths) != 1:
            raise ValueError("action prompts must have fixed token width")
        inputs = torch.tensor(encoded, dtype=torch.long, device=device)
        hidden, _ = model.g(model.e(inputs))
        result.append(hidden[:, -1].detach().cpu().numpy().astype(np.float32))
    return np.concatenate(result, axis=0)


def _labels(rows: Sequence[Any]) -> np.ndarray:
    return np.asarray([int(row.label) for row in rows], dtype=np.int64)


def _raw_features(
    rows: Sequence[Any], *, byte_token_base: int, width: int
) -> np.ndarray:
    return np.stack(
        [
            decode_feature(
                row.prompt,
                byte_token_base=byte_token_base,
                width=width,
            )
            for row in rows
        ]
    )


def _load_exact_modules(manifest: Mapping[str, Any]) -> tuple[Any, Any, Path]:
    runner_path = Path(str(manifest["runner"])).resolve(strict=True)
    data_path = Path(str(manifest["data_builder"])).resolve(strict=True)
    if file_sha256(runner_path) != manifest["runner_sha256"]:
        raise RuntimeError("campaign runner changed after admission")
    if file_sha256(data_path) != manifest["data_builder_sha256"]:
        raise RuntimeError("campaign data builder changed after admission")
    repo_root = runner_path.parents[2]
    sys.path.insert(0, str(repo_root))
    adapter_module = importlib.import_module(
        "python.scbe.clay_frozen_multiview_adapter"
    )
    data_module = importlib.import_module("python.scbe.clay_frozen_multiview_data")
    if Path(adapter_module.__file__).resolve() != runner_path:
        raise RuntimeError("imported runner does not match campaign runner")
    if Path(data_module.__file__).resolve() != data_path:
        raise RuntimeError("imported data builder does not match campaign builder")
    return adapter_module, data_module, repo_root


def run_probe(
    run_dir: Path,
    *,
    seeds: Sequence[int] | None = None,
    threads: int = 1,
    batch_size: int = 128,
) -> dict[str, Any]:
    run_dir = run_dir.resolve(strict=True)
    manifest_path = run_dir / "RUN_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    adapter_module, data_module, _ = _load_exact_modules(manifest)
    config = manifest["config"]
    provider = adapter_module.ClaySourceAdapter(Path(config["source_dir"]))
    dataset = data_module.build_frozen_multiview_dataset(
        provider,
        rows_per_view=int(config["rows_per_view"]),
        holdout_rows=int(config["holdout_rows"]),
        seed=int(config["data_seed"]),
    )
    expected_manifest = manifest["dataset"]["manifest_sha256"]
    if dataset.manifest["manifest_sha256"] != expected_manifest:
        raise RuntimeError("regenerated dataset differs from admitted campaign")

    byte_token_base = int(dataset.manifest["byte_token_base"])
    feature_width = int(dataset.manifest["feature_width"])
    holdout_labels = _labels(dataset.holdout_rows)
    raw_holdout = _raw_features(
        dataset.holdout_rows,
        byte_token_base=byte_token_base,
        width=feature_width,
    )
    banks = {
        "static": dataset.static_rows,
        "multiview": dataset.multiview_rows,
    }
    raw = {
        name: probe_report(
            _raw_features(
                rows,
                byte_token_base=byte_token_base,
                width=feature_width,
            ),
            _labels(rows),
            raw_holdout,
            holdout_labels,
            shuffle_seed=991 + index,
        )
        for index, (name, rows) in enumerate(banks.items())
    }

    completed = sorted(
        int(path.name.removeprefix("seed-"))
        for path in (run_dir / "parents").glob("seed-*")
        if (path / "PARENT.pt").is_file() and (path / "RESULT.json").is_file()
    )
    selected = completed if seeds is None else [int(seed) for seed in seeds]
    if not selected:
        raise RuntimeError("no completed parent checkpoints are available")
    missing = sorted(set(selected) - set(completed))
    if missing:
        raise RuntimeError(f"parent checkpoints are incomplete: {missing}")

    torch.set_num_threads(int(threads))
    hidden_reports = []
    for seed in selected:
        parent_dir = run_dir / "parents" / f"seed-{seed}"
        parent_result = json.loads(
            (parent_dir / "RESULT.json").read_text(encoding="utf-8")
        )
        parent_path = parent_dir / "PARENT.pt"
        if file_sha256(parent_path) != parent_result["parent_sha256"]:
            raise RuntimeError(f"parent hash differs for seed {seed}")
        parent = torch.load(parent_path, map_location="cpu", weights_only=False)
        vocab = list(parent["vocab"])
        stoi = {token: index for index, token in enumerate(vocab)}
        model = adapter_module.FrozenActionModel(len(vocab))
        model.load_state_dict(parent["model_state"])
        held_hidden = hidden_carriers(
            model,
            dataset.holdout_rows,
            stoi,
            bos=adapter_module.BOS,
            sep=adapter_module.SEP,
            batch_size=batch_size,
            device="cpu",
        )
        reports = {}
        for index, (name, rows) in enumerate(banks.items()):
            reports[name] = probe_report(
                hidden_carriers(
                    model,
                    rows,
                    stoi,
                    bos=adapter_module.BOS,
                    sep=adapter_module.SEP,
                    batch_size=batch_size,
                    device="cpu",
                ),
                _labels(rows),
                held_hidden,
                holdout_labels,
                shuffle_seed=1991 + 17 * seed + index,
            )
        hidden_reports.append(
            {
                "seed": seed,
                "parent_sha256": parent_result["parent_sha256"],
                "counting_accuracy": parent_result["counting_accuracy"],
                "banks": reports,
            }
        )

    return {
        "schema": "clay.frozen-byte-transport-probe.v1",
        "authority": "READ_ONLY_DIAGNOSTIC_NO_TRAINING_NO_PROMOTION",
        "campaign_manifest_sha256": file_sha256(manifest_path),
        "dataset_manifest_sha256": expected_manifest,
        "selected_parent_seeds": selected,
        "raw_feature_probes": raw,
        "frozen_gru_hidden_probes": hidden_reports,
        "interpretation_rule": (
            "Strong raw geometry with weak hidden geometry nominates an "
            "action-gated byte-embedding or first-input thaw; it does not "
            "authorize promotion."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--seeds", default="")
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    seeds = tuple(int(value) for value in args.seeds.split(",") if value)
    result = run_probe(
        args.run_dir,
        seeds=seeds or None,
        threads=args.threads,
        batch_size=args.batch_size,
    )
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
