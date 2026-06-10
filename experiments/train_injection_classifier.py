#!/usr/bin/env python3
"""
Train a linear classifier on the bit signatures produced by
injection_to_bits.py. Reports AUC on held-out test splits per source.

Feature vector per prompt (all from bit_signature, no text understanding):
  - byte_len
  - byte_entropy
  - phi_weight_sum (normalized)
  - 16 bit_histogram counts (normalized)
  - per-tongue even/odd counts (normalized) — 12 features
  Total: 31 features
"""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
from sklearn.model_selection import train_test_split

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]


def to_features(rec: dict) -> list[float]:
    sig = rec["bit_signature"]
    blen = max(rec["byte_len"], 1)
    feats = [
        float(rec["byte_len"]),
        float(sig["byte_entropy"]),
        float(sig["phi_weight_sum"]) / blen,
    ]
    for c in sig["bit_histogram"]:
        feats.append(float(c) / blen)
    for t in TONGUES:
        p = sig["token_parity"].get(t, {})
        feats.append(float(p.get("even", 0)) / blen)
        feats.append(float(p.get("odd", 0)) / blen)
    return feats


def load_jsonl(path: Path):
    X, y, sources = [], [], []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            label = rec["label"]
            if label in ("malicious", "jailbreak"):
                y.append(1)
            elif label == "benign":
                y.append(0)
            else:
                continue
            X.append(to_features(rec))
            sources.append(rec["source"])
    return np.array(X), np.array(y), np.array(sources)


def main() -> int:
    path = Path("/tmp/injection_bit_signatures_slim.jsonl")
    print(f"Loading {path}...")
    X, y, sources = load_jsonl(path)
    print(f"  samples: {len(X)}  features: {X.shape[1]}")
    print(f"  positive (malicious/jailbreak): {int(y.sum())}")
    print(f"  negative (benign): {int(len(y) - y.sum())}")
    print()

    X_train, X_test, y_train, y_test, src_train, src_test = train_test_split(
        X, y, sources, test_size=0.2, random_state=42, stratify=y
    )
    print(f"train: {len(X_train)}  test: {len(X_test)}")
    print()

    print("=== Logistic Regression ===")
    lr = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0, solver="lbfgs")
    lr.fit(X_train, y_train)
    probs_lr = lr.predict_proba(X_test)[:, 1]
    preds_lr = (probs_lr > 0.5).astype(int)
    print(f"  AUC:      {roc_auc_score(y_test, probs_lr):.4f}")
    print(f"  Accuracy: {accuracy_score(y_test, preds_lr):.4f}")
    print(classification_report(y_test, preds_lr, target_names=["benign", "malicious"], digits=4))

    print("=== Gradient Boosting (depth=4, n=120) ===")
    gb = GradientBoostingClassifier(n_estimators=120, max_depth=4, learning_rate=0.1, random_state=42)
    gb.fit(X_train, y_train)
    probs_gb = gb.predict_proba(X_test)[:, 1]
    preds_gb = (probs_gb > 0.5).astype(int)
    print(f"  AUC:      {roc_auc_score(y_test, probs_gb):.4f}")
    print(f"  Accuracy: {accuracy_score(y_test, preds_gb):.4f}")
    print(classification_report(y_test, preds_gb, target_names=["benign", "malicious"], digits=4))

    print()
    print("=== Per-source AUC (gradient boosting) ===")
    for src in sorted(set(sources)):
        mask = src_test == src
        if mask.sum() < 10:
            continue
        y_s, p_s = y_test[mask], probs_gb[mask]
        if len(set(y_s)) < 2:
            print(f"  {src}: SKIP (all one class in test)")
            continue
        print(f"  {src}: AUC={roc_auc_score(y_s, p_s):.4f}  n={int(mask.sum())}")

    print()
    print("=== Leave-one-source-out (gradient boosting) ===")
    for holdout in sorted(set(sources)):
        train_mask = sources != holdout
        test_mask = sources == holdout
        if len(set(y[test_mask])) < 2:
            print(f"  holdout={holdout}: SKIP")
            continue
        gb_h = GradientBoostingClassifier(n_estimators=120, max_depth=4, learning_rate=0.1, random_state=42)
        gb_h.fit(X[train_mask], y[train_mask])
        probs_h = gb_h.predict_proba(X[test_mask])[:, 1]
        auc_h = roc_auc_score(y[test_mask], probs_h)
        print(f"  holdout={holdout}: AUC={auc_h:.4f}  n_train={int(train_mask.sum())}  n_test={int(test_mask.sum())}")

    model_path = Path("/tmp/injection_bit_classifier.pkl")
    with model_path.open("wb") as f:
        pickle.dump({
            "model": gb,
            "feature_names": [
                "byte_len", "byte_entropy", "phi_weight_sum_norm",
            ] + [f"bit_hist_{i}" for i in range(16)] + [
                f"parity_{t}_{kind}" for t in TONGUES for kind in ("even", "odd")
            ],
        }, f)
    print(f"\nSaved model to {model_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
