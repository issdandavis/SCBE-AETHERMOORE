#!/usr/bin/env python3
"""Train the H-JEPA L1->L2 predictor head on the fixture corpus.

Loads the benign-vs-adversarial fixture corpus, builds (X, Y) training
matrices, runs manual SGD with momentum on the MSE loss, and saves the
learned weights to ``artifacts/hjepa/predictor_v1.npz``.

Reports baseline (identity-stack) MSE, final MSE, and the loss
trajectory at a few checkpoints. Idempotent: re-running overwrites the
weights file.

Usage:
    python scripts/train_hjepa_predictor.py
    python scripts/train_hjepa_predictor.py --epochs 1500 --learning-rate 0.005
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.hjepa_predictor import (  # noqa: E402
    DEFAULT_WEIGHTS_PATH,
    baseline_weights,
    build_training_pairs,
    fixture_corpus,
    initial_weights,
    mse_loss,
    save_weights,
    train,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=800)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--momentum", type=float, default=0.9)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=DEFAULT_WEIGHTS_PATH)
    args = parser.parse_args()

    corpus = fixture_corpus()
    benign = sum(1 for label, _ in corpus if label == "benign")
    adversarial = sum(1 for label, _ in corpus if label == "adversarial")
    print(f"corpus: {len(corpus)} pairs ({benign} benign + {adversarial} adversarial)")

    X, Y = build_training_pairs(corpus)
    print(f"matrices: X{X.shape}  Y{Y.shape}")

    baseline = baseline_weights()
    initial = initial_weights(seed=args.seed)
    baseline_mse = mse_loss(baseline, X, Y)
    initial_mse = mse_loss(initial, X, Y)
    print(f"baseline MSE (deterministic identity stack):   {baseline_mse:.8f}")
    print(f"initial MSE  (identity + epsilon noise):       {initial_mse:.8f}")

    print(f"training: epochs={args.epochs}, lr={args.learning_rate}, " f"momentum={args.momentum}, seed={args.seed}")
    trained = train(
        initial,
        X,
        Y,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        momentum=args.momentum,
        seed=args.seed,
    )
    final_mse = mse_loss(trained, X, Y)
    history = trained.train_loss_history
    checkpoints = [0, len(history) // 4, len(history) // 2, 3 * len(history) // 4, len(history) - 1]
    print("loss trajectory:")
    for cp in checkpoints:
        print(f"  epoch {cp:>4d}: {history[cp]:.8f}")
    print(f"final MSE:                                     {final_mse:.8f}")
    print(
        f"improvement vs baseline:                       "
        f"{baseline_mse - final_mse:+.8f} "
        f"({100.0 * (baseline_mse - final_mse) / max(baseline_mse, 1e-12):+.1f}%)"
    )

    output_path = save_weights(trained, args.output)
    rel = output_path.resolve().relative_to(REPO_ROOT.resolve()) if output_path.is_absolute() else output_path
    print(f"weights saved to: {rel}")

    summary = {
        "ok": True,
        "schema_version": trained.schema_version,
        "corpus_size": len(corpus),
        "baseline_mse": baseline_mse,
        "initial_mse": initial_mse,
        "final_mse": final_mse,
        "improvement_pct": 100.0 * (baseline_mse - final_mse) / max(baseline_mse, 1e-12),
        "epochs": args.epochs,
        "learning_rate": args.learning_rate,
        "momentum": args.momentum,
        "weights_path": str(rel),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
