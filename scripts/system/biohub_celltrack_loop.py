#!/usr/bin/env python3
"""GeoSeal loop for Biohub cell-tracking score work.

This mirrors the ARC/Rubix loop pattern for the Biohub lane:

candidate table(s) -> local score/proxy gates -> dashboard -> receipt.

It deliberately does not submit to Kaggle.  It is a result-routing surface so we
can compare output CSVs against the 0.902 anchor before spending submissions.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import time
from pathlib import Path
from subprocess import run
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CELLTRACK_ROOT = Path(r"C:\dev\celltrack")
DEFAULT_OUT = CELLTRACK_ROOT / "analysis" / "geoseal_biohub_loop_latest"
DEFAULT_BASE = CELLTRACK_ROOT / "intel_public_0902" / "praxel_output" / "submission.csv"
DEFAULT_GT = CELLTRACK_ROOT / "local_gt"

DEFAULT_CANDIDATES = [
    ("exp058_0901", CELLTRACK_ROOT / "intel_public_0902" / "beicicc_exp058_output" / "submission.csv"),
    ("kin1_0900", CELLTRACK_ROOT / "intel_public_0902" / "lucas_kin1_output" / "submission.csv"),
    ("hoct_correction_smoke", CELLTRACK_ROOT / "analysis" / "hoct_correction_probe_smoke" / "correction_probe_submission.csv"),
]


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")


def _json_load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_last_json(text: str) -> Any | None:
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _run_step(cmd: list[str], cwd: Path = CELLTRACK_ROOT, timeout: int = 3600) -> dict[str, Any]:
    started = time.time()
    proc = run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    return {
        "cmd": cmd,
        "cwd": str(cwd),
        "returncode": proc.returncode,
        "seconds": round(time.time() - started, 3),
        "stdout_tail": proc.stdout[-6000:],
        "stderr_tail": proc.stderr[-6000:],
        "stdout_json": _parse_last_json(proc.stdout),
    }


def _candidate_pairs(args: argparse.Namespace) -> list[tuple[str, Path]]:
    if args.candidate:
        return [(label, Path(path)) for label, path in args.candidate]
    return [(label, path) for label, path in DEFAULT_CANDIDATES if path.exists()]


def _base_pair(args: argparse.Namespace) -> tuple[str, Path]:
    if args.base:
        label, path = args.base
        return label, Path(path)
    return "praxel_0902", DEFAULT_BASE


def _safe_label(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)


def run_score(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = args.out_dir / "score"
    base_label, base_path = _base_pair(args)
    candidates = _candidate_pairs(args)
    if not base_path.exists():
        raise SystemExit(f"Base submission not found: {base_path}")
    if not candidates:
        raise SystemExit("No candidates were provided or found.")

    cmd = [
        sys.executable,
        str(CELLTRACK_ROOT / "tools" / "score_selected_biohub_candidates.py"),
        "--gt-root",
        str(args.gt_root),
        "--base",
        base_label,
        str(base_path),
        "--output-dir",
        str(out_dir),
    ]
    for label, path in candidates:
        if not path.exists():
            raise SystemExit(f"Candidate {label} not found: {path}")
        cmd.extend(["--candidate", label, str(path)])
    score_step = _run_step(cmd)

    compare_cmd = [
        sys.executable,
        str(CELLTRACK_ROOT / "tools" / "compare_submission_tables.py"),
        "--base-label",
        base_label,
        "--base",
        str(base_path),
        "--output-json",
        str(out_dir / "table_compare.json"),
        "--output-md",
        str(out_dir / "table_compare.md"),
    ]
    for label, path in candidates:
        compare_cmd.extend(["--candidate", label, str(path)])
    compare_step = _run_step(compare_cmd)

    gate_steps = []
    gate_dir = out_dir / "public_gates"
    for label, path in candidates:
        gate_cmd = [
            sys.executable,
            str(CELLTRACK_ROOT / "tools" / "candidate_public_gate.py"),
            "--root",
            str(CELLTRACK_ROOT),
            "--anchor",
            base_label,
            "--anchor-path",
            str(base_path),
            "--anchor-score",
            str(args.anchor_score),
            "--candidate",
            str(path),
            "--output",
            str(gate_dir / f"{_safe_label(label)}_public_gate.json"),
        ]
        gate_steps.append(_run_step(gate_cmd))

    score_json = out_dir / "selected_candidate_calibration.json"
    rows = _json_load(score_json).get("rows", []) if score_json.exists() else []
    best_row = max(rows, key=lambda row: float(row.get("local_score", -1.0)), default=None)
    gates = []
    for path in sorted(gate_dir.glob("*_public_gate.json")):
        try:
            gates.append(_json_load(path))
        except (OSError, json.JSONDecodeError):
            continue

    payload = {
        "ok": score_step["returncode"] == 0 and compare_step["returncode"] == 0 and all(step["returncode"] == 0 for step in gate_steps),
        "mode": "score",
        "base": {"label": base_label, "path": str(base_path), "public_score": args.anchor_score},
        "candidates": [{"label": label, "path": str(path)} for label, path in candidates],
        "paths": {
            "out_dir": str(out_dir),
            "score_json": str(score_json),
            "score_csv": str(out_dir / "selected_candidate_calibration.csv"),
            "score_md": str(out_dir / "selected_candidate_calibration.md"),
            "table_compare_json": str(out_dir / "table_compare.json"),
            "table_compare_md": str(out_dir / "table_compare.md"),
            "public_gate_dir": str(gate_dir),
        },
        "best_local_row": best_row,
        "public_gates": gates,
        "commands": [score_step, compare_step, *gate_steps],
    }
    _json_write(args.out_dir / "biohub_score_receipt.json", payload)
    return payload


def _training_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    roots = args.train_output_dir or [
        CELLTRACK_ROOT / "analysis" / "hoct_multiview_kaggle_train_output_v6",
        CELLTRACK_ROOT / "analysis" / "hoct_multiview_kaggle_train_output_v5",
        CELLTRACK_ROOT / "analysis" / "hoct_multiview_kaggle_train_output_v4",
        CELLTRACK_ROOT / "analysis" / "hoct_multiview_kaggle_train_output_v3",
        CELLTRACK_ROOT / "analysis" / "hoct_multiview_kaggle_train_output",
    ]
    items = []
    breakthrough_items = []
    no_submit_violations = []
    for root in roots:
        root = Path(root)
        item: dict[str, Any] = {"root": str(root), "exists": root.exists()}
        if root.exists():
            summary_candidates = [
                root / "multiview_training_summary.json",
                root / "BREAKTHROUGH_DECISION.json",
                root / "multiview_sweep_summary.json",
                root / "observer_multispeed" / "multispeed_observations_summary.json",
                root / "correction_probe_artifacts" / "correction_probe_summary.json",
            ]
            item["summaries"] = []
            for path in summary_candidates:
                if path.exists():
                    try:
                        payload = _json_load(path)
                        item["summaries"].append({"path": str(path), "payload": payload})
                        if path.name == "BREAKTHROUGH_DECISION.json":
                            item["breakthrough"] = payload
                            if payload.get("breakthrough"):
                                breakthrough_items.append({"root": str(root), "decision": payload})
                    except json.JSONDecodeError:
                        item["summaries"].append({"path": str(path), "error": "json_decode_error"})
            item["sentinel"] = (root / "TRAIN_ONLY_NO_SUBMISSION.txt").exists()
            item["has_submission_csv"] = (root / "submission.csv").exists()
            if item["has_submission_csv"]:
                no_submit_violations.append(str(root / "submission.csv"))
            item["files"] = [
                {"name": path.name, "bytes": path.stat().st_size}
                for path in sorted(root.glob("*"))
                if path.is_file()
            ][:24]
        items.append(item)
    payload = {
        "ok": True,
        "mode": "check-train",
        "breakthrough_found": bool(breakthrough_items),
        "breakthroughs": breakthrough_items,
        "no_submit_violations": no_submit_violations,
        "train_outputs": items,
    }
    _json_write(args.out_dir / "biohub_train_artifacts_receipt.json", payload)
    return payload


def _metric(row: dict[str, Any], key: str, default: Any = "") -> Any:
    value = row.get(key, default)
    if isinstance(value, float):
        return f"{value:.6f}"
    return value


def _render_dashboard(args: argparse.Namespace, score_payload: dict[str, Any] | None = None, train_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    score_path = args.out_dir / "biohub_score_receipt.json"
    if score_payload is None and score_path.exists():
        score_payload = _json_load(score_path)
    train_path = args.out_dir / "biohub_train_artifacts_receipt.json"
    if train_payload is None and train_path.exists():
        train_payload = _json_load(train_path)

    score_rows = []
    score_json = args.out_dir / "score" / "selected_candidate_calibration.json"
    if score_json.exists():
        score_rows = _json_load(score_json).get("rows", [])
    gates = (score_payload or {}).get("public_gates", [])

    table_rows = []
    for row in sorted(score_rows, key=lambda item: float(item.get("local_score", -1.0)), reverse=True):
        table_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('label', '')))}</td>"
            f"<td>{_metric(row, 'local_score')}</td>"
            f"<td>{_metric(row, 'local_adj')}</td>"
            f"<td>{_metric(row, 'local_edge_j')}</td>"
            f"<td>{_metric(row, 'local_div_j')}</td>"
            f"<td>{html.escape(str(row.get('edge_fp', '')))} / {html.escape(str(row.get('edge_fn', '')))}</td>"
            f"<td>{html.escape(str(row.get('division_tp', '')))} / {html.escape(str(row.get('division_fp', '')))} / {html.escape(str(row.get('division_fn', '')))}</td>"
            f"<td>{html.escape(str(row.get('nodes', '')))}</td>"
            f"<td>{html.escape(str(row.get('edges', '')))}</td>"
            f"<td>{html.escape(str(row.get('edge_p99_um', '')))}</td>"
            "</tr>"
        )

    gate_cards = []
    for gate in gates:
        gate_cards.append(
            "<section class='card'>"
            f"<h2>{html.escape(str(Path(str(gate.get('candidate', 'candidate'))).name))}</h2>"
            f"<p><b>estimate:</b> {gate.get('estimated_public_score')} "
            f"(<b>delta:</b> {gate.get('estimated_delta_vs_anchor')})</p>"
            f"<pre>{html.escape(json.dumps(gate.get('risk_flags', []), indent=2))}</pre>"
            "</section>"
        )

    train_html = html.escape(json.dumps(train_payload or {}, indent=2, sort_keys=True)[:12000])
    score_html = html.escape(json.dumps(score_payload or {}, indent=2, sort_keys=True)[:12000])
    doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Biohub GeoSeal Loop</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#f7faf8;color:#17201b;margin:22px}}
h1{{font-size:28px;margin-bottom:6px}}h2{{font-size:18px}}
table{{border-collapse:collapse;background:white;width:100%;margin:14px 0}}
td,th{{border:1px solid #d5ded8;padding:7px 8px;text-align:right}}td:first-child,th:first-child{{text-align:left}}
th{{background:#e8f1eb}}.card{{background:white;border:1px solid #cbd8d0;border-radius:6px;padding:12px;margin:12px 0}}
pre{{background:#111827;color:#eef6ef;padding:12px;overflow:auto;border-radius:6px;max-height:420px}}
.muted{{color:#58635d}}
</style></head>
<body>
<h1>Biohub GeoSeal Loop</h1>
<p class="muted">Candidate table -> local score -> public-shape gate -> dashboard -> receipt. No Kaggle submission.</p>
<h2>Local Calibration</h2>
<table><thead><tr><th>label</th><th>local</th><th>adj</th><th>edge_j</th><th>div_j</th><th>edge FP/FN</th><th>div TP/FP/FN</th><th>nodes</th><th>edges</th><th>edge p99 um</th></tr></thead>
<tbody>{''.join(table_rows)}</tbody></table>
<h2>Public-Shape Gates</h2>
{''.join(gate_cards) or '<p>No gate results found.</p>'}
<h2>Train Artifacts</h2><pre>{train_html}</pre>
<h2>Receipt</h2><pre>{score_html}</pre>
</body></html>
"""
    out = args.out_dir / "biohub_loop_dashboard.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    payload = {"ok": True, "mode": "dashboard", "dashboard": str(out), "rows": len(score_rows), "gates": len(gates)}
    _json_write(args.out_dir / "biohub_dashboard_receipt.json", payload)
    return payload


def run_loop(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    score_payload = run_score(args)
    train_payload = _training_artifacts(args)
    dashboard_payload = _render_dashboard(args, score_payload=score_payload, train_payload=train_payload)
    payload = {
        "ok": bool(score_payload.get("ok")) and bool(train_payload.get("ok")) and bool(dashboard_payload.get("ok")),
        "mode": "loop",
        "seconds": round(time.time() - started, 3),
        "score": score_payload,
        "train_artifacts": train_payload,
        "dashboard": dashboard_payload,
        "paths": {
            "out_dir": str(args.out_dir),
            "receipt": str(args.receipt),
            "dashboard": dashboard_payload.get("dashboard"),
        },
        "notes": [
            "This loop does not submit to Kaggle.",
            "Use the public-shape gate and local score as promotion filters, not as a leaderboard oracle.",
        ],
    }
    _json_write(args.receipt, payload)
    return payload


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Biohub cell-tracking GeoSeal score/dashboard loops.")
    parser.add_argument("action", nargs="?", choices=["score", "dashboard", "loop", "check-train"], default="loop")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--gt-root", type=Path, default=DEFAULT_GT)
    parser.add_argument("--base", nargs=2, metavar=("LABEL", "PATH"))
    parser.add_argument("--candidate", action="append", nargs=2, metavar=("LABEL", "PATH"))
    parser.add_argument("--anchor-score", type=float, default=0.902)
    parser.add_argument("--train-output-dir", action="append", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    args.out_dir = Path(args.out_dir)
    args.receipt = Path(args.receipt) if args.receipt else args.out_dir / "biohub_loop_receipt.json"

    if args.action == "score":
        payload = run_score(args)
    elif args.action == "check-train":
        payload = _training_artifacts(args)
    elif args.action == "dashboard":
        payload = _render_dashboard(args)
    else:
        payload = run_loop(args)

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    else:
        print(f"Biohub GeoSeal {args.action}: {'ok' if payload.get('ok') else 'failed'}")
        if payload.get("paths"):
            print(json.dumps(payload["paths"], indent=2, sort_keys=True))
        elif payload.get("dashboard"):
            print(f"dashboard: {payload['dashboard']}")
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
