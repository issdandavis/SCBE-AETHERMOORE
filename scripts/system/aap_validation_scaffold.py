#!/usr/bin/env python3
"""Build a portable Autonomous Agent Prediction validation scaffold.

This does not run a Kaggle submission. It creates a submission-root-safe agent
package plus an outer dashboard/manifest so SCBE/GeoSeal can use the competition
as a practical validation harness for budgeted tool-loop training work.
"""

from __future__ import annotations

import argparse
import json
import os
import textwrap
import zipfile
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_OUT_DIR = Path(r"C:\dev\aap_validation\scbe_aap_agent")
DEFAULT_DASHBOARD_DIR = Path(r"C:\dev\aap_validation")


AGENT_YAML = """\
name: scbe-aap-budgeted-tabular-agent
model: gemini-3.1-flash-lite
instruction: !include prompts/system.md
tools:
  - run_command
  - write_file
  - edit_file
  - submit_predictions
  - select_submission
  - get_status
skills:
  - skills/tabular_binary_solver
"""


SYSTEM_PROMPT = """\
# SCBE AAP Budgeted Tabular Agent

You are running inside Kaggle Autonomous Agent Prediction (Beta).

Core objective: maximize AUC ROC on the current binary-classification mini-competition while staying inside:

- max_time_minutes: 60
- max_submissions: 30
- max_budget_usd: 2.00
- allowed tools only: run_command, write_file, edit_file, submit_predictions, select_submission, get_status, and declared agent_tool subagents if present

Model choice:

- default model: gemini-3.1-flash-lite
- price: $0.25/M input, $0.025/M cached input, $1.50/M output
- do not use gemini-3.5-flash or gemini-3.1-pro-preview as the main agent unless the config is explicitly changed after local evidence

Critical session rule: do not send a plaintext final response until after you have submitted and selected the best available submissions. A plaintext response with no tool call ends the session.

Operating pattern:

1. Call get_status first and write down remaining submissions/time if available.
2. Run the packaged solver script:

```bash
python skills/tabular_binary_solver/scripts/solve_tabular_binary.py --out-dir work/scbe_aap_outputs
```

3. Read `work/scbe_aap_outputs/aap_run_ledger.json`.
4. Submit only the top ranked candidate CSV files from the ledger. Start with the best ensemble and two diverse model candidates. Do not spend all 30 submissions unless public scores are still materially moving.
5. After each submit, call get_status, record the public score in `work/scbe_aap_outputs/submission_scores.json`, and keep a ranking.
6. If public scores plateau, stop submitting and select the best two successful submissions.
7. Only after select_submission succeeds, provide a short plaintext summary.

Tool discipline:

- Use run_command for deterministic data work.
- Use edit_file only for small repairs to packaged scripts.
- Do not path-traverse outside the competition root.
- Do not use internet access or non-harness tools.
- Keep every generated artifact under `work/scbe_aap_outputs/`.
- Keep model output short. Long explanations burn budget and do not improve AUC.

Modeling discipline:

- Treat this as synthetic tabular binary classification.
- Prefer robust ensembles over a single clever model.
- Use cross-validation only as a ranking guide; public score is the selection signal.
- Track every candidate file, local OOF AUC, and public score in the ledger.
- If a model fails, keep the failure receipt and continue with the remaining models.
"""


SKILL_MD = """\
---
name: tabular_binary_solver
description: Deterministic tabular binary-classification solver for Kaggle Autonomous Agent Prediction mini-competitions.
---

# Tabular Binary Solver Skill

Run the solver from the competition root:

```bash
python skills/tabular_binary_solver/scripts/solve_tabular_binary.py --out-dir work/scbe_aap_outputs
```

It will:

- find `train.csv`, `test.csv`, and `sample_submission.csv`
- infer the target and ID columns
- build numeric/categorical features with safe missing-value handling
- train multiple sklearn models with OOF AUC receipts
- write several candidate submission CSV files
- write `aap_run_ledger.json` ranking candidate files for submit_predictions

The script never calls submit_predictions itself. The top-level agent must submit candidates through the official harness tool and select the best two.
"""


SOLVER_SCRIPT = r'''#!/usr/bin/env python3
"""Budgeted tabular binary solver for Autonomous Agent Prediction sessions."""

from __future__ import annotations

import argparse
import json
import math
import os
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def find_competition_root(start: Path) -> Path:
    candidates = [start, *start.parents]
    for root in candidates:
        if (root / "train.csv").exists() and (root / "test.csv").exists() and (root / "sample_submission.csv").exists():
            return root
    for root, dirs, files in os.walk(start):
        depth = Path(root).relative_to(start).parts
        if len(depth) > 4:
            dirs[:] = []
            continue
        names = set(files)
        if {"train.csv", "test.csv", "sample_submission.csv"} <= names:
            return Path(root)
    raise FileNotFoundError("Could not find train.csv, test.csv, and sample_submission.csv from current working tree.")


def infer_columns(train: pd.DataFrame, test: pd.DataFrame, sample: pd.DataFrame) -> tuple[str, str | None, str]:
    extra = [c for c in train.columns if c not in test.columns]
    target = "target" if "target" in train.columns else (extra[0] if extra else train.columns[-1])
    sample_cols = list(sample.columns)
    pred_col = sample_cols[-1]
    id_col = None
    if len(sample_cols) >= 2:
        maybe_id = sample_cols[0]
        if maybe_id in test.columns:
            id_col = maybe_id
    if id_col is None:
        for name in ("id", "ID", "row_id", "index"):
            if name in test.columns and name != target:
                id_col = name
                break
    return target, id_col, pred_col


def safe_float_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.replace([np.inf, -np.inf], np.nan)
    for col in out.columns:
        if out[col].dtype == "object" or str(out[col].dtype).startswith("category"):
            continue
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def build_features(train: pd.DataFrame, test: pd.DataFrame, target: str, id_col: str | None):
    drop_cols = [target]
    if id_col:
        drop_cols.append(id_col)
    train_x = train.drop(columns=[c for c in drop_cols if c in train.columns])
    test_x = test.drop(columns=[c for c in ([id_col] if id_col else []) if c in test.columns])
    combo = pd.concat([train_x, test_x], axis=0, ignore_index=True)

    numeric_cols = []
    categorical_cols = []
    for col in combo.columns:
        converted = pd.to_numeric(combo[col], errors="coerce")
        non_na_ratio = converted.notna().mean()
        if combo[col].dtype != "object" or non_na_ratio > 0.85:
            combo[col] = converted
            numeric_cols.append(col)
        else:
            categorical_cols.append(col)

    feature_parts = []
    if numeric_cols:
        numeric = safe_float_frame(combo[numeric_cols]).astype("float32")
        missing_counts = numeric.isna().sum(axis=1).astype("float32")
        medians = numeric.median(axis=0).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        filled = numeric.fillna(medians).clip(-1e9, 1e9)
        feature_parts.append(filled)

        row_stats = pd.DataFrame(
            {
                "__row_nan_count": missing_counts,
                "__row_mean": filled.mean(axis=1).astype("float32"),
                "__row_std": filled.std(axis=1).fillna(0).astype("float32"),
                "__row_min": filled.min(axis=1).astype("float32"),
                "__row_max": filled.max(axis=1).astype("float32"),
                "__row_nonzero": (filled != 0).sum(axis=1).astype("float32"),
            }
        )
        feature_parts.append(row_stats)

        if len(numeric_cols) <= 250:
            miss = numeric.isna().astype("int8")
            miss.columns = [f"{c}__isna" for c in numeric_cols]
            feature_parts.append(miss)

    if categorical_cols:
        cat_parts = []
        for col in categorical_cols:
            s = combo[col].astype("string").fillna("__NA__")
            n = int(s.nunique(dropna=False))
            if n <= 64:
                dummies = pd.get_dummies(s, prefix=col, dummy_na=False, dtype="int8")
                cat_parts.append(dummies)
            else:
                freq = s.map(s.value_counts(normalize=True)).astype("float32").rename(f"{col}__freq")
                codes = pd.Series(pd.factorize(s)[0], name=f"{col}__code").astype("float32")
                cat_parts.append(pd.concat([freq, codes], axis=1))
        if cat_parts:
            feature_parts.append(pd.concat(cat_parts, axis=1))

    if not feature_parts:
        raise ValueError("No usable feature columns found.")

    x_all = pd.concat(feature_parts, axis=1)
    x_all = x_all.replace([np.inf, -np.inf], np.nan).fillna(0.0).astype("float32")
    n_train = len(train)
    return x_all.iloc[:n_train].to_numpy(dtype=np.float32), x_all.iloc[n_train:].to_numpy(dtype=np.float32), list(x_all.columns)


def rank01(values: np.ndarray) -> np.ndarray:
    s = pd.Series(values)
    ranked = s.rank(method="average").to_numpy(dtype=np.float64)
    if len(ranked) <= 1:
        return np.full_like(values, 0.5, dtype=np.float64)
    return (ranked - 1.0) / (len(ranked) - 1.0)


def clip_probs(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    return np.clip(values, 1e-5, 1.0 - 1e-5)


def model_specs(seed: int, n_features: int):
    k32 = max(1, min(32, n_features))
    k64 = max(1, min(64, n_features))
    return [
        (
            "tiny_nn_k32_h4",
            make_pipeline(
                SimpleImputer(strategy="median"),
                SelectKBest(f_classif, k=k32),
                StandardScaler(),
                MLPClassifier(
                    hidden_layer_sizes=(4,),
                    activation="relu",
                    alpha=0.02,
                    learning_rate_init=0.003,
                    max_iter=350,
                    early_stopping=True,
                    n_iter_no_change=20,
                    random_state=seed,
                ),
            ),
        ),
        (
            "tiny_nn_k64_h8",
            make_pipeline(
                SimpleImputer(strategy="median"),
                SelectKBest(f_classif, k=k64),
                StandardScaler(),
                MLPClassifier(
                    hidden_layer_sizes=(8,),
                    activation="relu",
                    alpha=0.015,
                    learning_rate_init=0.002,
                    max_iter=350,
                    early_stopping=True,
                    n_iter_no_change=20,
                    random_state=seed + 1,
                ),
            ),
        ),
        (
            "hgb",
            HistGradientBoostingClassifier(
                max_iter=180,
                learning_rate=0.045,
                max_leaf_nodes=31,
                l2_regularization=0.02,
                random_state=seed,
            ),
        ),
        (
            "extra_trees",
            ExtraTreesClassifier(
                n_estimators=320,
                min_samples_leaf=2,
                max_features="sqrt",
                bootstrap=False,
                n_jobs=-1,
                random_state=seed,
            ),
        ),
        (
            "rf_shallow",
            RandomForestClassifier(
                n_estimators=220,
                min_samples_leaf=3,
                max_features="sqrt",
                n_jobs=-1,
                random_state=seed,
            ),
        ),
        (
            "logreg",
            make_pipeline(
                SimpleImputer(strategy="median"),
                StandardScaler(with_mean=False),
                LogisticRegression(C=0.35, solver="liblinear", max_iter=1000, random_state=seed),
            ),
        ),
    ]


def size_proxy(name: str, n_features: int) -> dict:
    if name == "tiny_nn_k32_h4":
        k = max(1, min(32, n_features))
        params = (k * 4) + 4 + (4 * 1) + 1
        return {"family": "micro_neural_net", "selected_features": k, "hidden_units": 4, "approx_params": int(params)}
    if name == "tiny_nn_k64_h8":
        k = max(1, min(64, n_features))
        params = (k * 8) + 8 + (8 * 1) + 1
        return {"family": "micro_neural_net", "selected_features": k, "hidden_units": 8, "approx_params": int(params)}
    if name == "logreg":
        return {"family": "linear_baseline", "selected_features": int(n_features), "hidden_units": 0, "approx_params": int(n_features + 1)}
    return {"family": "heavy_tabular_baseline", "selected_features": int(n_features), "hidden_units": None, "approx_params": None}


def fit_predict_candidates(x: np.ndarray, y: np.ndarray, x_test: np.ndarray, max_minutes: float):
    start = time.time()
    y = np.asarray(y).astype(int)
    pos = int(y.sum())
    neg = int(len(y) - pos)
    if len(np.unique(y)) != 2:
        raise ValueError("Target is not binary after conversion.")
    n_splits = 5 if min(pos, neg) >= 5 and len(y) >= 100 else 3
    n_splits = max(2, min(n_splits, pos, neg))
    folds = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=20260716)

    candidates = []
    failures = []
    for name, model in model_specs(20260716, x.shape[1]):
        elapsed_min = (time.time() - start) / 60.0
        if elapsed_min > max_minutes * 0.72:
            failures.append({"model": name, "error": "time_budget_skip", "elapsed_minutes": elapsed_min})
            continue
        try:
            oof = np.zeros(len(y), dtype=np.float64)
            test_fold = np.zeros((len(x_test), n_splits), dtype=np.float64)
            for fold_idx, (tr_idx, va_idx) in enumerate(folds.split(x, y)):
                fold_model = model
                # Recreate the model by cloning through sklearn where possible.
                from sklearn.base import clone

                fold_model = clone(model)
                fold_model.fit(x[tr_idx], y[tr_idx])
                if hasattr(fold_model, "predict_proba"):
                    oof[va_idx] = fold_model.predict_proba(x[va_idx])[:, 1]
                    test_fold[:, fold_idx] = fold_model.predict_proba(x_test)[:, 1]
                else:
                    oof[va_idx] = fold_model.predict(x[va_idx])
                    test_fold[:, fold_idx] = fold_model.predict(x_test)
            auc = float(roc_auc_score(y, oof))
            test_pred = clip_probs(test_fold.mean(axis=1))
            candidates.append({"name": name, "oof_auc": auc, "pred": test_pred, "oof": clip_probs(oof), "size_proxy": size_proxy(name, x.shape[1])})
        except Exception as exc:
            failures.append({"model": name, "error": str(exc), "traceback": traceback.format_exc(limit=6)})

    if not candidates:
        raise RuntimeError(f"All models failed: {failures}")

    ordered = sorted(candidates, key=lambda item: item["oof_auc"], reverse=True)
    preds = np.vstack([item["pred"] for item in ordered])
    aucs = np.array([max(0.5001, item["oof_auc"]) for item in ordered], dtype=np.float64)
    weights = np.maximum(aucs - 0.5, 0.001)
    weights = weights / weights.sum()
    weighted = clip_probs((preds.T @ weights).ravel())
    mean = clip_probs(preds.mean(axis=0))
    rank_mean = clip_probs(np.vstack([rank01(p) for p in preds]).mean(axis=0))

    ensemble_items = [
        {"name": "ensemble_auc_weighted", "oof_auc": float(np.average(aucs, weights=weights)), "pred": weighted, "size_proxy": {"family": "ensemble", "approx_params": None}},
        {"name": "ensemble_mean", "oof_auc": float(np.mean(aucs)), "pred": mean, "size_proxy": {"family": "ensemble", "approx_params": None}},
        {"name": "ensemble_rank_mean", "oof_auc": float(np.mean(aucs) - 0.0001), "pred": rank_mean, "size_proxy": {"family": "ensemble", "approx_params": None}},
    ]
    return sorted(ensemble_items + ordered, key=lambda item: item["oof_auc"], reverse=True), failures


def write_submission(sample: pd.DataFrame, pred_col: str, preds: np.ndarray, path: Path) -> None:
    sub = sample.copy()
    sub[pred_col] = clip_probs(preds)
    sub.to_csv(path, index=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="work/scbe_aap_outputs")
    parser.add_argument("--max-minutes", type=float, default=38.0)
    args = parser.parse_args()

    start = time.time()
    cwd = Path.cwd()
    root = find_competition_root(cwd)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    submissions_dir = out_dir / "submissions"
    submissions_dir.mkdir(parents=True, exist_ok=True)

    train = pd.read_csv(root / "train.csv")
    test = pd.read_csv(root / "test.csv")
    sample = pd.read_csv(root / "sample_submission.csv")
    target, id_col, pred_col = infer_columns(train, test, sample)
    y = pd.to_numeric(train[target], errors="coerce").fillna(0).astype(int).to_numpy()
    x, x_test, feature_names = build_features(train, test, target, id_col)
    candidates, failures = fit_predict_candidates(x, y, x_test, args.max_minutes)

    ledger_candidates = []
    for idx, item in enumerate(candidates):
        file_name = f"{idx + 1:02d}_{item['name']}.csv"
        path = submissions_dir / file_name
        write_submission(sample, pred_col, item["pred"], path)
        ledger_candidates.append(
            {
                "rank": idx + 1,
                "name": item["name"],
                "local_oof_auc": round(float(item["oof_auc"]), 8),
                "size_proxy": item.get("size_proxy", {}),
                "file": str(path.as_posix()),
            }
        )

    ledger = {
        "schema_version": "scbe_aap_run_ledger_v1",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "competition_root": str(root),
        "train_shape": list(train.shape),
        "test_shape": list(test.shape),
        "feature_count": len(feature_names),
        "target": target,
        "id_col": id_col,
        "prediction_col": pred_col,
        "class_balance": {"positive": int(y.sum()), "negative": int(len(y) - y.sum())},
        "candidates": ledger_candidates,
        "failures": failures,
        "elapsed_seconds": round(time.time() - start, 3),
        "submit_recommendation": "Submit ranks 1, 2, and the best single-model candidate first; then stop if public scores plateau.",
    }
    (out_dir / "aap_run_ledger.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    (out_dir / "README_NEXT_STEPS.md").write_text(
        "# AAP solver outputs\n\n"
        "Submit candidate CSV files using the official submit_predictions tool, starting from the top of `aap_run_ledger.json`.\n"
        "After each submission, record public scores in `submission_scores.json` and select the best two.\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "ledger": str(out_dir / "aap_run_ledger.json"), "candidates": ledger_candidates[:5]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


README = """\
# SCBE Autonomous Agent Prediction Scaffold

This scaffold packages a budgeted tabular agent for Kaggle Autonomous Agent Prediction (Beta).

Purpose for SCBE:

- outside validation of whether our tool loops produce better ML work under strict budget
- practical receipts for execution, validation, repair, and submission selection
- a competition-shaped test for lightweight local governance and MiniCPM/GeoSeal routing later

Model budget:

| Model ID | Input / 1M | Cached input / 1M | Output / 1M | Role |
| --- | ---: | ---: | ---: | --- |
| `gemini-3.1-flash-lite` | `$0.25` | `$0.025` | `$1.50` | default main agent |
| `gemini-3.5-flash` | `$1.50` | `$0.15` | `$9.00` | backup only |
| `gemini-3.1-pro-preview` | `$2.00` | `$0.20` | `$12.00` | rare fallback only |

The package defaults to Flash Lite because the solver script should do the heavy work. The model should route, call tools, read ledgers, submit candidates, and select final submissions.

Important boundary:

The Kaggle harness can only use tools declared by the competition. GeoSeal is an outer development system. Any GeoSeal/Rubix logic that should run inside the competition must be compiled into submission-root-safe prompts, skills, or scripts.

Generated files:

- `agent.yaml` main config
- `prompts/system.md` budgeted operating prompt
- `skills/tabular_binary_solver/SKILL.md` skill manifest
- `skills/tabular_binary_solver/scripts/solve_tabular_binary.py` deterministic ML solver with micro neural-net candidates

Local validation target:

Use the competition dataset's `validate_submission.py` and `run_local_eval.py` after downloading the official data. This generator does not run those checks automatically.
"""


def html_escape(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_dashboard(manifest: dict, dashboard_path: Path) -> None:
    rows = [
        ("Harness budget", "60 min, 30 submissions, $2 LLM spend"),
        ("Default model", "gemini-3.1-flash-lite: $0.25/M input, $0.025/M cached input, $1.50/M output"),
        ("Data shape", "18 synthetic binary-classification datasets; 16 training-family datasets plus public/private eval sessions"),
        ("Inner metric", "AUC ROC with public feedback per mini-competition"),
        ("Outer validation goal", "Measure whether SCBE tools improve budgeted autonomous ML work"),
        ("Inside-harness rule", "Only packaged prompts/skills/scripts and allowed tools are usable"),
    ]
    cards = "\n".join(
        f"<section class='card'><h3>{html_escape(k)}</h3><p>{html_escape(v)}</p></section>" for k, v in rows
    )
    files = "\n".join(f"<li><code>{html_escape(path)}</code></li>" for path in manifest["files"])
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SCBE AAP Validation Dashboard</title>
  <style>
    :root {{
      --ink: #17211b;
      --paper: #f6f1e5;
      --line: #253c2e;
      --accent: #c46b2e;
      --green: #2d6b4f;
    }}
    body {{
      margin: 0;
      font-family: Georgia, 'Times New Roman', serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 20% 15%, rgba(196,107,46,.18), transparent 28rem),
        linear-gradient(135deg, #f6f1e5, #e8dfcc);
    }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 34px 22px 56px; }}
    h1 {{ font-size: clamp(2rem, 5vw, 4.3rem); line-height: .92; margin: 0 0 12px; letter-spacing: -.05em; }}
    .subtitle {{ font-size: 1.08rem; max-width: 820px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; margin: 28px 0; }}
    .card {{ border: 2px solid var(--line); border-radius: 18px; padding: 16px; background: rgba(255,255,255,.45); box-shadow: 6px 6px 0 rgba(37,60,46,.18); }}
    .card h3 {{ margin: 0 0 8px; color: var(--green); font-size: 1rem; text-transform: uppercase; letter-spacing: .08em; }}
    .flow {{ border-left: 8px solid var(--accent); padding-left: 18px; margin: 26px 0; }}
    code {{ background: rgba(23,33,27,.08); padding: 2px 5px; border-radius: 5px; }}
    li {{ margin: 6px 0; }}
  </style>
</head>
<body>
<main>
  <h1>AAP validation cockpit</h1>
  <p class="subtitle">A portable agent scaffold for testing whether SCBE/GeoSeal-style tool loops can perform under a strict Kaggle autonomous-agent budget.</p>
  <div class="grid">{cards}</div>
  <section class="card">
    <h3>Execution loop</h3>
    <div class="flow">
      <p><strong>get_status</strong> -> run packaged solver -> write ledger -> submit ranked CSVs -> record public scores -> select best two -> final response.</p>
      <p>The inner agent avoids visual UI. The outer GeoSeal dashboard is for us.</p>
    </div>
  </section>
  <section class="card">
    <h3>Generated files</h3>
    <ul>{files}</ul>
  </section>
  <section class="card">
    <h3>Next command</h3>
    <p><code>python validate_submission.py path/to/submission.zip</code> after the official dataset is available locally.</p>
  </section>
</main>
</body>
</html>
"""
    dashboard_path.write_text(html, encoding="utf-8")


def write_file(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def build_scaffold(out_dir: Path, dashboard_dir: Path, force: bool, make_zip: bool) -> dict:
    files = {
        "agent.yaml": AGENT_YAML,
        "prompts/system.md": SYSTEM_PROMPT,
        "skills/tabular_binary_solver/SKILL.md": SKILL_MD,
        "skills/tabular_binary_solver/scripts/solve_tabular_binary.py": SOLVER_SCRIPT,
        "README.md": README,
    }
    written = []
    for rel, content in files.items():
        path = out_dir / rel
        write_file(path, content, force=force)
        written.append(str(path))

    manifest = {
        "schema_version": "scbe_aap_validation_scaffold_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "out_dir": str(out_dir),
        "competition": "Autonomous Agent Prediction (Beta)",
        "recommended_model": "gemini-3.1-flash-lite",
        "model_prices_per_1m_tokens": {
            "gemini-3.1-flash-lite": {"display_name": "Gemini 3.1 Flash Lite", "input": 0.25, "cached_input": 0.025, "output": 1.50, "role": "default main agent"},
            "gemini-3.5-flash": {"display_name": "Gemini 3.5 Flash", "input": 1.50, "cached_input": 0.15, "output": 9.00, "role": "backup only"},
            "gemini-3.1-pro-preview": {"display_name": "Gemini 3.1 Pro Preview", "input": 2.00, "cached_input": 0.20, "output": 12.00, "role": "rare fallback only"},
        },
        "budget": {"max_time_minutes": 60, "max_submissions": 30, "max_budget_usd": 2.0},
        "allowed_tools": ["run_command", "write_file", "edit_file", "submit_predictions", "select_submission", "get_status"],
        "files": sorted(files.keys()),
        "inside_harness_boundary": "GeoSeal logic must be packaged as prompts, skills, or scripts under the submission root.",
        "next_steps": [
            "Download official competition data locally when ready.",
            "Run validate_submission.py against the generated zip.",
            "Run run_local_eval.py against train_01 through train_16 to build an outside validation ledger.",
            "Use public-score feedback sparingly in official sessions and select best two submissions.",
        ],
    }
    write_file(out_dir / "validation_manifest.json", json.dumps(manifest, indent=2), force=True)
    written.append(str(out_dir / "validation_manifest.json"))

    dashboard_dir.mkdir(parents=True, exist_ok=True)
    dashboard_path = dashboard_dir / "aap_validation_dashboard.html"
    build_dashboard({**manifest, "files": sorted(files.keys()) + ["validation_manifest.json"]}, dashboard_path)
    written.append(str(dashboard_path))

    zip_path = None
    if make_zip:
        zip_path = out_dir.with_suffix(".zip")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for rel in sorted(files.keys()) + ["validation_manifest.json"]:
                zf.write(out_dir / rel, rel)
        written.append(str(zip_path))
    return {**manifest, "written": written, "dashboard": str(dashboard_path), "zip": str(zip_path) if zip_path else None}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SCBE AAP validation scaffold.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--dashboard-dir", default=str(DEFAULT_DASHBOARD_DIR))
    parser.add_argument("--force", action="store_true", help="Overwrite existing scaffold files.")
    parser.add_argument("--zip", action="store_true", help="Also write a submission zip next to the scaffold directory.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    manifest = build_scaffold(Path(args.out_dir), Path(args.dashboard_dir), force=args.force, make_zip=args.zip)
    if args.json:
        print(json.dumps({"ok": True, **manifest}, indent=2))
    else:
        print(f"AAP scaffold: {manifest['out_dir']}")
        print(f"Dashboard: {manifest['dashboard']}")
        if manifest.get("zip"):
            print(f"Zip: {manifest['zip']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
