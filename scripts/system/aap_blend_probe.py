#!/usr/bin/env python3
"""Probe AAP blend recipes across the provided training-family datasets."""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.system.aap_family_probe import (  # noqa: E402
    DEFAULT_DATA_DIR,
    auc,
    build_features,
    cp,
    detect_columns,
    model_specs,
    proba,
    rank01,
)


DEFAULT_OUT = REPO_ROOT / "reports" / "aap_blend_probe.json"
RNG = 20260716


def weighted_blend(items: list[dict[str, Any]], *, mode: str, k: int | None = None) -> np.ndarray:
    chosen = items[:k] if k else items
    weights = np.array([max(0.01, float(row["cv_auc"]) - 0.5) for row in chosen], dtype=float)
    weights = weights / weights.sum()
    raw = sum(w * row["pred"] for w, row in zip(weights, chosen))
    ranked = sum(w * rank01(row["pred"]) for w, row in zip(weights, chosen))
    if mode == "raw":
        return cp(raw)
    if mode == "rank":
        return cp(ranked)
    if mode == "rank70":
        return cp(0.30 * raw + 0.70 * ranked)
    return cp(0.60 * raw + 0.40 * ranked)


def named_blend(preds: dict[str, dict[str, Any]], names: list[str], *, mode: str) -> np.ndarray | None:
    rows = [preds[name] for name in names if name in preds]
    if not rows:
        return None
    rows.sort(key=lambda row: row["cv_auc"], reverse=True)
    return weighted_blend(rows, mode=mode)


def solve_dataset(dataset: Path) -> dict[str, Any]:
    train = pd.read_csv(dataset / "train.csv")
    test = pd.read_csv(dataset / "test.csv")
    sample = pd.read_csv(dataset / "sample_submission.csv")
    solution = pd.read_csv(dataset / "solution.csv")
    target_col, id_col, pred_col = detect_columns(train, test, sample)
    y = pd.to_numeric(train[target_col], errors="coerce").fillna(0).astype(int).values

    train_x = train.drop(columns=[c for c in [target_col, id_col] if c in train.columns])
    test_x = test.drop(columns=[c for c in [id_col] if c in test.columns]).reindex(columns=train_x.columns)
    x_train, x_test = build_features(train_x, test_x)
    true = pd.to_numeric(solution[pred_col] if pred_col in solution.columns else solution.iloc[:, -1], errors="coerce").fillna(0).astype(int).values

    from sklearn.model_selection import StratifiedKFold

    n_splits = 5 if len(y) >= 1200 and min(np.bincount(y, minlength=2)) >= 5 else 3
    folds = list(StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RNG).split(x_train, y))
    preds: dict[str, dict[str, Any]] = {}
    model_rows: list[dict[str, Any]] = []

    for name, factory in model_specs():
        start = time.time()
        try:
            oof = np.zeros(len(y), dtype=float)
            pred = np.zeros(len(x_test), dtype=float)
            for fold, (fit_idx, val_idx) in enumerate(folds):
                model = factory(RNG + fold)
                model.fit(x_train.iloc[fit_idx], y[fit_idx])
                oof[val_idx] = proba(model, x_train.iloc[val_idx])
                pred += proba(model, x_test) / len(folds)
            cv_auc = auc(y, oof)
            if cv_auc < 0.5:
                oof = 1.0 - oof
                pred = 1.0 - pred
                cv_auc = auc(y, oof)
            test_auc = auc(true, pred)
            row = {
                "name": name,
                "cv_auc": cv_auc,
                "test_auc": test_auc,
                "seconds": round(time.time() - start, 3),
                "pred": cp(pred),
            }
            preds[name] = row
            model_rows.append({k: v for k, v in row.items() if k != "pred"})
        except Exception as exc:
            model_rows.append({"name": name, "error": str(exc)[:240]})

    ranked = sorted(preds.values(), key=lambda row: row["cv_auc"], reverse=True)
    candidates: dict[str, np.ndarray] = {}
    if ranked:
        for row in ranked:
            candidates[f"single_{row['name']}"] = row["pred"]
        for k in (2, 3, 4, 5):
            if len(ranked) >= k:
                candidates[f"top{k}_mix"] = weighted_blend(ranked, mode="mix", k=k)
                candidates[f"top{k}_raw"] = weighted_blend(ranked, mode="raw", k=k)
                candidates[f"top{k}_rank"] = weighted_blend(ranked, mode="rank", k=k)
                candidates[f"top{k}_rank70"] = weighted_blend(ranked, mode="rank70", k=k)
        fixed_groups = {
            "hgb_lgbm_mix": ["hgb", "lgbm"],
            "hgb_lgbm_rf_mix": ["hgb", "lgbm", "rf"],
            "hgb_lgbm_rf_lr_mix": ["hgb", "lgbm", "rf", "lr"],
            "tree_all_mix": ["hgb", "lgbm", "rf", "et"],
            "all_mix": ["hgb", "lgbm", "rf", "et", "lr"],
            "all_rank": ["hgb", "lgbm", "rf", "et", "lr"],
        }
        for cname, names in fixed_groups.items():
            mode = "rank" if cname.endswith("_rank") else "mix"
            pred = named_blend(preds, names, mode=mode)
            if pred is not None:
                candidates[cname] = pred

    candidate_rows = [
        {"candidate": name, "test_auc": auc(true, pred)}
        for name, pred in candidates.items()
    ]
    candidate_rows.sort(key=lambda row: row["test_auc"], reverse=True)
    return {
        "dataset": dataset.name,
        "rows": len(train),
        "features": len(train_x.columns),
        "models": model_rows,
        "candidates": candidate_rows,
        "best": candidate_rows[0] if candidate_rows else None,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe AAP blend recipes.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    datasets = sorted(path for path in args.data_dir.glob("train_*") if path.is_dir())
    rows = [solve_dataset(dataset) for dataset in datasets]
    scores: dict[str, list[float]] = {}
    for row in rows:
        for cand in row.get("candidates", []):
            scores.setdefault(cand["candidate"], []).append(float(cand["test_auc"]))
    leaderboard = [
        {
            "candidate": name,
            "mean_auc": float(np.mean(vals)),
            "median_auc": float(np.median(vals)),
            "min_auc": float(np.min(vals)),
            "n": len(vals),
        }
        for name, vals in scores.items()
    ]
    leaderboard.sort(key=lambda row: row["mean_auc"], reverse=True)
    payload = {"datasets": rows, "leaderboard": leaderboard}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"wrote {args.out}")
        print(json.dumps({"leaderboard": leaderboard[:12]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
