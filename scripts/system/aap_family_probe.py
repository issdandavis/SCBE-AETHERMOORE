#!/usr/bin/env python3
"""Probe AAP tabular solver choices across the provided training family.

This is a local-only evaluator for the 16 public meta-datasets. It does not use
Kaggle submissions. It writes a compact receipt that can be used to choose the
agent prompt/model recipe for future AAP submissions.
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


DEFAULT_DATA_DIR = Path(r"C:\Users\issda\kaggle\aap\competition\data")
DEFAULT_OUT = Path(r"C:\Users\issda\SCBE-AETHERMOORE\reports\aap_family_probe.json")
RNG = 20260716


def cp(pred: Any) -> np.ndarray:
    arr = np.asarray(pred, dtype=float)
    arr = np.where(np.isfinite(arr), arr, 0.5)
    return np.clip(arr, 1e-6, 1 - 1e-6)


def auc(y: Any, pred: Any) -> float:
    y_arr = np.asarray(y)
    p_arr = np.asarray(pred)
    try:
        if len(np.unique(y_arr)) < 2 or len(np.unique(p_arr)) < 2:
            return 0.5
        return float(roc_auc_score(y_arr, p_arr))
    except Exception:
        return 0.5


def proba(model: Any, x: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        p = model.predict_proba(x)
        if getattr(p, "ndim", 1) == 2 and p.shape[1] > 1:
            return cp(p[:, 1])
        return cp(np.ravel(p))
    if hasattr(model, "decision_function"):
        z = np.clip(model.decision_function(x), -30, 30)
        return cp(1.0 / (1.0 + np.exp(-z)))
    return cp(model.predict(x))


def rank01(pred: Any) -> np.ndarray:
    p = np.asarray(pred, dtype=float)
    order = np.argsort(p, kind="mergesort")
    ranked = np.empty(len(p), dtype=float)
    ranked[order] = np.linspace(0.001, 0.999, len(p)) if len(p) > 1 else 0.5
    return cp(ranked)


def build_features(train_x: pd.DataFrame, test_x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    n_train = len(train_x)
    all_x = pd.concat([train_x, test_x], ignore_index=True, sort=False)
    out = pd.DataFrame(index=range(len(all_x)))
    numeric_names: list[str] = []

    for col in all_x.columns:
        s = all_x[col]
        numeric = pd.to_numeric(s, errors="coerce")
        numeric_ratio = float(numeric.notna().mean()) if len(numeric) else 0.0
        if pd.api.types.is_numeric_dtype(s) or numeric_ratio > 0.9:
            med = float(numeric.iloc[:n_train].median()) if numeric.iloc[:n_train].notna().any() else 0.0
            vals = numeric.fillna(med).replace([np.inf, -np.inf], med).astype(float)
            out[col] = vals
            numeric_names.append(col)
            if numeric.isna().any():
                out[col + "__na"] = numeric.isna().astype(float)
            if len(vals) and float(np.nanpercentile(np.abs(vals), 99)) > 10:
                out[col + "__logabs"] = np.sign(vals) * np.log1p(np.abs(vals))
        else:
            cat = s.astype("object").where(s.notna(), "__NA__").astype(str)
            codes, _ = pd.factorize(cat, sort=True)
            out[col + "__code"] = codes.astype(float)
            out[col + "__freq"] = cat.map(cat.value_counts(normalize=True)).astype(float)
            for val in cat.iloc[:n_train].value_counts().head(6).index:
                safe = str(val).replace(" ", "_").replace("/", "_")[:24]
                out[f"{col}__is__{safe}"] = (cat == val).astype(float)

    out["__missing_count"] = all_x.isna().sum(axis=1).astype(float)
    out["__missing_frac"] = out["__missing_count"] / max(1, all_x.shape[1])
    if numeric_names:
        nums = out[[c for c in numeric_names if c in out.columns]].astype(float)
        out["__num_mean"] = nums.mean(axis=1)
        out["__num_std"] = nums.std(axis=1).fillna(0.0)
        out["__num_min"] = nums.min(axis=1)
        out["__num_max"] = nums.max(axis=1)

    out = out.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return out.iloc[:n_train].reset_index(drop=True), out.iloc[n_train:].reset_index(drop=True)


def detect_columns(train: pd.DataFrame, test: pd.DataFrame, sample: pd.DataFrame) -> tuple[str, str, str]:
    id_col = str(sample.columns[0])
    pred_col = str(sample.columns[-1])
    target_candidates = [c for c in train.columns if c not in test.columns]
    target_col = "target" if "target" in target_candidates else target_candidates[0]
    return target_col, id_col, pred_col


def model_specs() -> list[tuple[str, Any]]:
    specs: list[tuple[str, Any]] = [
        (
            "et",
            lambda seed: ExtraTreesClassifier(
                n_estimators=360,
                max_features="sqrt",
                min_samples_leaf=2,
                class_weight="balanced",
                random_state=seed,
                n_jobs=-1,
            ),
        ),
        (
            "rf",
            lambda seed: RandomForestClassifier(
                n_estimators=280,
                max_features="sqrt",
                min_samples_leaf=3,
                class_weight="balanced_subsample",
                random_state=seed,
                n_jobs=-1,
            ),
        ),
        (
            "hgb",
            lambda seed: HistGradientBoostingClassifier(
                max_iter=360,
                learning_rate=0.035,
                max_leaf_nodes=31,
                l2_regularization=0.05,
                early_stopping=True,
                random_state=seed,
            ),
        ),
        (
            "lr",
            lambda seed: make_pipeline(
                SimpleImputer(strategy="median"),
                StandardScaler(),
                LogisticRegression(max_iter=1000, C=0.8, class_weight="balanced"),
            ),
        ),
    ]
    try:
        from lightgbm import LGBMClassifier

        specs.insert(
            0,
            (
                "lgbm",
                lambda seed: LGBMClassifier(
                    n_estimators=650,
                    learning_rate=0.03,
                    num_leaves=31,
                    min_child_samples=18,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    reg_lambda=1.0,
                    random_state=seed,
                    n_jobs=-1,
                    verbose=-1,
                ),
            ),
        )
    except Exception:
        pass
    try:
        from xgboost import XGBClassifier

        specs.insert(
            1,
            (
                "xgb",
                lambda seed: XGBClassifier(
                    n_estimators=550,
                    max_depth=4,
                    learning_rate=0.035,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    reg_lambda=1.2,
                    min_child_weight=2.0,
                    random_state=seed,
                    n_jobs=-1,
                    tree_method="hist",
                    eval_metric="auc",
                ),
            ),
        )
    except Exception:
        pass
    return specs


def solve_dataset(dataset: Path, max_models: int | None = None) -> dict[str, Any]:
    train = pd.read_csv(dataset / "train.csv")
    test = pd.read_csv(dataset / "test.csv")
    sample = pd.read_csv(dataset / "sample_submission.csv")
    solution = pd.read_csv(dataset / "solution.csv")
    target_col, id_col, pred_col = detect_columns(train, test, sample)
    y = pd.to_numeric(train[target_col], errors="coerce").fillna(0).astype(int).values

    train_x = train.drop(columns=[c for c in [target_col, id_col] if c in train.columns])
    test_x = test.drop(columns=[c for c in [id_col] if c in test.columns]).reindex(columns=train_x.columns)
    x_train, x_test = build_features(train_x, test_x)

    n_splits = 5 if len(y) >= 1200 and min(np.bincount(y, minlength=2)) >= 5 else 3
    folds = list(StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RNG).split(x_train, y))

    specs = model_specs()
    if max_models:
        specs = specs[:max_models]

    true = pd.to_numeric(solution[pred_col] if pred_col in solution.columns else solution.iloc[:, -1], errors="coerce").fillna(0).astype(int).values
    results: list[dict[str, Any]] = []
    for name, factory in specs:
        try:
            oof = np.zeros(len(y), dtype=float)
            test_pred = np.zeros(len(x_test), dtype=float)
            for fold, (fit_idx, val_idx) in enumerate(folds):
                model = factory(RNG + fold)
                model.fit(x_train.iloc[fit_idx], y[fit_idx])
                oof[val_idx] = proba(model, x_train.iloc[val_idx])
                test_pred += proba(model, x_test) / len(folds)
            cv_auc = auc(y, oof)
            public_auc = auc(true, test_pred)
            if public_auc < 0.5:
                public_auc_inv = auc(true, 1.0 - test_pred)
            else:
                public_auc_inv = public_auc
            results.append(
                {
                    "model": name,
                    "cv_auc": cv_auc,
                    "test_auc": public_auc,
                    "best_or_inverted_auc": public_auc_inv,
                }
            )
        except Exception as exc:
            results.append({"model": name, "error": str(exc)[:300]})

    usable = [row for row in results if "test_auc" in row]
    blends: list[dict[str, Any]] = []
    if usable:
        # Refit predictions are already captured only in result metrics here; blend
        # optimization is left to the submitted agent. Report model rankings.
        best = max(usable, key=lambda row: row["test_auc"])
        blends.append({"name": "best_single", "test_auc": best["test_auc"], "model": best["model"]})

    return {
        "dataset": dataset.name,
        "rows": len(train),
        "test_rows": len(test),
        "features": len(train_x.columns),
        "target_mean": float(np.mean(y)),
        "models": results,
        "summary": blends,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe AAP model family performance.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-models", type=int)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    datasets = sorted(path for path in args.data_dir.glob("train_*") if path.is_dir())
    rows = [solve_dataset(dataset, max_models=args.max_models) for dataset in datasets]
    model_scores: dict[str, list[float]] = {}
    for row in rows:
        for model in row["models"]:
            if "test_auc" in model:
                model_scores.setdefault(model["model"], []).append(float(model["test_auc"]))
    leaderboard = [
        {"model": name, "mean_auc": float(np.mean(scores)), "median_auc": float(np.median(scores)), "n": len(scores)}
        for name, scores in sorted(model_scores.items())
    ]
    leaderboard.sort(key=lambda row: row["mean_auc"], reverse=True)
    payload = {"datasets": rows, "leaderboard": leaderboard}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"wrote {args.out}")
        print(json.dumps({"leaderboard": leaderboard[:8]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
