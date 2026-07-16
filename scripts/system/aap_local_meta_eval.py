#!/usr/bin/env python3
"""Local meta-evaluation for Autonomous Agent Prediction scaffolds.

Runs the packaged SCBE AAP solver over data/train_01..train_16 and scores
candidate CSVs against solution.csv. This is an outer development tool; it is
not intended to run inside the Kaggle evaluation harness.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score


DEFAULT_AGENT_DIR = Path(r"C:\dev\aap_validation\scbe_aap_agent")
DEFAULT_OUT_DIR = Path(r"C:\dev\aap_validation\local_meta_eval")


def find_dataset_dirs(data_dir: Path) -> list[Path]:
    roots = []
    candidates = [data_dir, data_dir / "data"]
    for base in candidates:
        if not base.exists():
            continue
        roots.extend(sorted(p for p in base.glob("train_*") if p.is_dir()))
    filtered = []
    for path in roots:
        if (path / "train.csv").exists() and (path / "test.csv").exists() and (path / "sample_submission.csv").exists():
            filtered.append(path)
    return filtered


def infer_score_columns(sample: pd.DataFrame, solution: pd.DataFrame) -> tuple[str | None, str, str | None]:
    sample_cols = list(sample.columns)
    pred_col = sample_cols[-1]
    id_col = sample_cols[0] if len(sample_cols) >= 2 and sample_cols[0] in solution.columns else None
    usage_col = "Usage" if "Usage" in solution.columns else ("usage" if "usage" in solution.columns else None)

    if pred_col in solution.columns:
        target_col = pred_col
    else:
        excluded = {c for c in [id_col, usage_col] if c}
        possible = [c for c in solution.columns if c not in excluded]
        numeric = [c for c in possible if pd.api.types.is_numeric_dtype(solution[c])]
        target_col = numeric[-1] if numeric else possible[-1]
    return id_col, target_col, usage_col


def safe_auc(y_true: pd.Series, y_pred: pd.Series) -> float | None:
    y_true = pd.to_numeric(y_true, errors="coerce")
    y_pred = pd.to_numeric(y_pred, errors="coerce")
    mask = y_true.notna() & y_pred.notna()
    y_true = y_true[mask].astype(int)
    y_pred = y_pred[mask].astype(float)
    if len(y_true) < 2 or y_true.nunique() != 2:
        return None
    return float(roc_auc_score(y_true, y_pred))


def score_candidate(candidate_path: Path, sample: pd.DataFrame, solution: pd.DataFrame) -> dict:
    pred = pd.read_csv(candidate_path)
    id_col, target_col, usage_col = infer_score_columns(sample, solution)
    pred_col = list(sample.columns)[-1]

    if id_col and id_col in pred.columns:
        merged = solution.merge(pred[[id_col, pred_col]], on=id_col, how="left", suffixes=("_true", "_pred"))
        true_col = target_col
        pred_score_col = pred_col
        if target_col == pred_col and f"{pred_col}_true" in merged.columns:
            true_col = f"{pred_col}_true"
            pred_score_col = f"{pred_col}_pred"
    else:
        merged = solution.copy()
        merged["_prediction"] = pred[pred_col].to_numpy()[: len(merged)]
        true_col = target_col
        pred_score_col = "_prediction"

    scores = {"overall_auc": safe_auc(merged[true_col], merged[pred_score_col])}
    if usage_col:
        for usage_value, group in merged.groupby(usage_col):
            key = f"{str(usage_value).strip().lower()}_auc"
            scores[key] = safe_auc(group[true_col], group[pred_score_col])
    return scores


def run_solver(python_exe: str, solver_script: Path, dataset_dir: Path, out_dir: Path, max_minutes: float) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        python_exe,
        str(solver_script),
        "--out-dir",
        str(out_dir),
        "--max-minutes",
        str(max_minutes),
    ]
    start = time.time()
    proc = subprocess.run(cmd, cwd=str(dataset_dir), text=True, capture_output=True)
    return {
        "cmd": cmd,
        "cwd": str(dataset_dir),
        "returncode": proc.returncode,
        "elapsed_seconds": round(time.time() - start, 3),
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def write_dashboard(summary: dict, rows: list[dict], path: Path) -> None:
    top_rows = sorted(
        [r for r in rows if r.get("overall_auc") is not None],
        key=lambda r: (r.get("overall_auc") or -1.0),
        reverse=True,
    )[:30]
    table = "\n".join(
        "<tr>"
        f"<td>{r['dataset']}</td>"
        f"<td>{r['candidate']}</td>"
        f"<td>{r.get('overall_auc', '')}</td>"
        f"<td>{r.get('public_auc', '')}</td>"
        f"<td>{r.get('private_auc', '')}</td>"
        f"<td>{r.get('family', '')}</td>"
        f"<td>{r.get('approx_params', '')}</td>"
        "</tr>"
        for r in top_rows
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>AAP Local Meta Eval</title>
  <style>
    body {{ margin: 0; font-family: Georgia, 'Times New Roman', serif; background: #f4efe2; color: #17211b; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px; }}
    h1 {{ font-size: clamp(2rem, 5vw, 4rem); margin: 0 0 10px; letter-spacing: -.04em; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin: 22px 0; }}
    .card {{ border: 2px solid #253c2e; border-radius: 16px; padding: 14px; background: rgba(255,255,255,.52); box-shadow: 5px 5px 0 rgba(37,60,46,.18); }}
    .num {{ font-size: 1.8rem; font-weight: 700; color: #2d6b4f; }}
    table {{ width: 100%; border-collapse: collapse; background: rgba(255,255,255,.55); }}
    th, td {{ border-bottom: 1px solid rgba(37,60,46,.25); padding: 8px; text-align: left; }}
    th {{ color: #8a421e; text-transform: uppercase; font-size: .78rem; letter-spacing: .08em; }}
    code {{ background: rgba(23,33,27,.08); padding: 2px 5px; border-radius: 5px; }}
  </style>
</head>
<body>
<main>
  <h1>AAP local meta-eval</h1>
  <p>Outer validation for SCBE agent/tool-loop training against train_01 through train_16.</p>
  <div class="cards">
    <section class="card"><div class="num">{summary.get('datasets_scored', 0)}</div><div>datasets scored</div></section>
    <section class="card"><div class="num">{summary.get('candidate_rows', 0)}</div><div>candidate rows</div></section>
    <section class="card"><div class="num">{summary.get('best_overall_auc', '')}</div><div>best overall AUC</div></section>
    <section class="card"><div class="num">{summary.get('best_tiny_auc', '')}</div><div>best tiny NN AUC</div></section>
  </div>
  <h2>Top candidates</h2>
  <table>
    <thead><tr><th>dataset</th><th>candidate</th><th>overall</th><th>public</th><th>private</th><th>family</th><th>params</th></tr></thead>
    <tbody>{table}</tbody>
  </table>
  <p>Ledger: <code>{summary.get('ledger_csv', '')}</code></p>
</main>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local AAP meta-evaluation over train_01..train_16.")
    parser.add_argument("--data-dir", required=True, help="Official AAP dataset root or its data/ directory.")
    parser.add_argument("--agent-dir", default=str(DEFAULT_AGENT_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--max-datasets", type=int, default=16)
    parser.add_argument("--max-minutes-per-dataset", type=float, default=3.0)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    agent_dir = Path(args.agent_dir)
    out_dir = Path(args.out_dir)
    solver_script = agent_dir / "skills" / "tabular_binary_solver" / "scripts" / "solve_tabular_binary.py"
    if not solver_script.exists():
        raise FileNotFoundError(f"Solver not found: {solver_script}. Run geoseal aap-scaffold --force --zip first.")

    dataset_dirs = find_dataset_dirs(data_dir)[: args.max_datasets]
    if not dataset_dirs:
        raise FileNotFoundError(f"No train_XX dataset folders found under {data_dir}.")

    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    runs = []
    for dataset_dir in dataset_dirs:
        dataset_name = dataset_dir.name
        dataset_out = out_dir / dataset_name
        run = run_solver(args.python, solver_script, dataset_dir, dataset_out, args.max_minutes_per_dataset)
        runs.append({"dataset": dataset_name, **run})
        ledger_path = dataset_out / "aap_run_ledger.json"
        if run["returncode"] != 0 or not ledger_path.exists():
            rows.append({"dataset": dataset_name, "candidate": "__solver_failed__", "error": run["stderr_tail"] or run["stdout_tail"]})
            continue

        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        sample = pd.read_csv(dataset_dir / "sample_submission.csv")
        solution = pd.read_csv(dataset_dir / "solution.csv")
        for candidate in ledger.get("candidates", []):
            candidate_path = Path(candidate["file"])
            if not candidate_path.is_absolute():
                candidate_path = dataset_dir / candidate_path
            scores = score_candidate(candidate_path, sample, solution)
            size = candidate.get("size_proxy", {}) or {}
            rows.append(
                {
                    "dataset": dataset_name,
                    "candidate": candidate.get("name"),
                    "rank": candidate.get("rank"),
                    "local_oof_auc": candidate.get("local_oof_auc"),
                    "family": size.get("family"),
                    "approx_params": size.get("approx_params"),
                    "selected_features": size.get("selected_features"),
                    "hidden_units": size.get("hidden_units"),
                    "file": str(candidate_path),
                    **scores,
                }
            )

    ledger_csv = out_dir / "meta_eval_ledger.csv"
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with ledger_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    scored = [r for r in rows if isinstance(r.get("overall_auc"), float)]
    tiny = [r for r in scored if r.get("family") == "micro_neural_net"]
    best = max(scored, key=lambda r: r["overall_auc"], default={})
    best_tiny = max(tiny, key=lambda r: r["overall_auc"], default={})
    summary = {
        "schema_version": "scbe_aap_local_meta_eval_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_dir": str(data_dir),
        "agent_dir": str(agent_dir),
        "out_dir": str(out_dir),
        "datasets_found": len(dataset_dirs),
        "datasets_scored": len({r["dataset"] for r in scored}),
        "candidate_rows": len(rows),
        "best_overall_auc": round(best.get("overall_auc"), 6) if best else None,
        "best_overall_candidate": best,
        "best_tiny_auc": round(best_tiny.get("overall_auc"), 6) if best_tiny else None,
        "best_tiny_candidate": best_tiny,
        "ledger_csv": str(ledger_csv),
        "runs": runs,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_dashboard(summary, rows, out_dir / "index.html")

    if args.json:
        print(json.dumps({"ok": True, **summary}, indent=2))
    else:
        print(f"AAP meta-eval ledger: {ledger_csv}")
        print(f"Dashboard: {out_dir / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
