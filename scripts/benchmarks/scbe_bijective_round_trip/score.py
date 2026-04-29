#!/usr/bin/env python3
"""Round-trip scorer for the SCBE Bijective Tongue Coder Kaggle benchmark.

Self-contained: no SCBE-internal imports. Safe to run inside a Kaggle scoring
notebook with stdlib only.

Score per row:
    raw = token_recall * structural_preservation
    raw = 0 if hard_fail (empty pred / decode error / no parseable structure)
    final_row_score in [0, 1]

Leaderboard score is the unweighted mean of per-row scores. Higher is better.

Usage:
    python score.py --holdout holdout.jsonl --submission submission.csv \
        --out report.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = "scbe_bijective_round_trip_score_v1"

# Recognised tongue codes; submission tokens drawn from these may be case-folded.
TONGUE_CODES = ("KO", "AV", "RU", "CA", "UM", "DR")

# Codeblock fences we accept as "well-formed".
CODEBLOCK_RE = re.compile(r"```([a-zA-Z0-9_+-]*)\n(.*?)```", re.DOTALL)
SLOT_MARKER_RE = re.compile(r"#slot\s*:\s*([a-zA-Z0-9_]+)")
TONGUE_HEADER_RE = re.compile(r"###\s*TONGUE\s*:\s*([A-Z]{2})")


def _tokenize(text: str) -> list[str]:
    """Tokenize like a code-aware lexer: identifiers, numbers, single punct."""
    text = text or ""
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+|[^\sA-Za-z0-9_]", text)
    return [t for t in tokens if t.strip()]


def _lcs_length(a: list[str], b: list[str]) -> int:
    """Length of longest common subsequence (DP)."""
    if not a or not b:
        return 0
    n, m = len(a), len(b)
    if n * m > 4_000_000:
        a = a[:2000]
        b = b[:2000]
        n, m = len(a), len(b)
    prev = [0] * (m + 1)
    for i in range(1, n + 1):
        cur = [0] * (m + 1)
        ai = a[i - 1]
        for j in range(1, m + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
            else:
                cur[j] = prev[j] if prev[j] >= cur[j - 1] else cur[j - 1]
        prev = cur
    return prev[m]


def token_recall(prediction: str, reference: str) -> float:
    """Order-aware recall: |LCS(pred, ref)| / |ref|."""
    ref_tokens = _tokenize(reference)
    if not ref_tokens:
        return 0.0
    pred_tokens = _tokenize(prediction)
    if not pred_tokens:
        return 0.0
    lcs = _lcs_length(pred_tokens, ref_tokens)
    return lcs / len(ref_tokens)


def _ref_signature(reference: str, task: str) -> dict[str, Any]:
    """Extract the structural targets the prediction must hit."""
    codeblocks = CODEBLOCK_RE.findall(reference)
    slots = SLOT_MARKER_RE.findall(reference)
    tongues = TONGUE_HEADER_RE.findall(reference)
    return {
        "codeblock_count": len(codeblocks),
        "slot_count": len(slots),
        "tongue_count": len(tongues),
        "task": task,
    }


def structural_preservation(prediction: str, reference: str, task: str) -> float:
    """Fraction of structural targets the prediction reproduces."""
    sig = _ref_signature(reference, task)
    expected_targets = []
    actual_targets = []

    if sig["codeblock_count"] > 0:
        expected_targets.append(sig["codeblock_count"])
        actual_targets.append(len(CODEBLOCK_RE.findall(prediction)))

    if sig["slot_count"] > 0:
        expected_targets.append(sig["slot_count"])
        actual_targets.append(len(SLOT_MARKER_RE.findall(prediction)))

    if sig["tongue_count"] > 0:
        expected_targets.append(sig["tongue_count"])
        actual_targets.append(len(TONGUE_HEADER_RE.findall(prediction)))

    if not expected_targets:
        return 1.0 if (prediction or "").strip() else 0.0

    parts = []
    for exp, act in zip(expected_targets, actual_targets):
        if exp <= 0:
            continue
        parts.append(min(act, exp) / exp)
    return sum(parts) / len(parts) if parts else 0.0


def is_hard_fail(prediction: str) -> bool:
    if not prediction or not prediction.strip():
        return True
    if "DECODE_ERROR" in prediction.upper():
        return True
    return False


def score_row(prediction: str, reference: str, meta: dict[str, Any]) -> dict[str, Any]:
    task = str(meta.get("task", "unknown"))
    if is_hard_fail(prediction):
        return {
            "task": task,
            "token_recall": 0.0,
            "structural_preservation": 0.0,
            "row_score": 0.0,
            "hard_fail": True,
        }
    tr = token_recall(prediction, reference)
    sp = structural_preservation(prediction, reference, task)
    return {
        "task": task,
        "token_recall": round(tr, 6),
        "structural_preservation": round(sp, 6),
        "row_score": round(tr * sp, 6),
        "hard_fail": False,
    }


def load_holdout(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_submission(path: Path) -> dict[str, str]:
    """Read submission.csv with columns: id,prediction."""
    out: dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "id" not in reader.fieldnames or "prediction" not in reader.fieldnames:
            raise ValueError("submission must have columns: id,prediction")
        for row in reader:
            rid = (row.get("id") or "").strip()
            if not rid:
                continue
            out[rid] = row.get("prediction") or ""
    return out


def score(
    holdout_rows: list[dict[str, Any]],
    submission: dict[str, str],
) -> dict[str, Any]:
    per_row: list[dict[str, Any]] = []
    by_task: dict[str, list[float]] = {}
    by_tongue: dict[str, list[float]] = {}

    for row in holdout_rows:
        rid = str(row["id"])
        meta = row.get("meta", {})
        ref = row["reference"]
        pred = submission.get(rid, "")

        s = score_row(pred, ref, meta)
        s["id"] = rid
        per_row.append(s)

        by_task.setdefault(s["task"], []).append(s["row_score"])
        for tongue_key in ("tongue", "src", "dst"):
            tcode = meta.get(tongue_key)
            if tcode in TONGUE_CODES:
                by_tongue.setdefault(tcode, []).append(s["row_score"])

    n = len(per_row)
    overall = sum(r["row_score"] for r in per_row) / n if n else 0.0
    return {
        "schema": SCHEMA,
        "n_rows": n,
        "overall_score": round(overall, 6),
        "task_breakdown": {
            t: {"n": len(v), "mean": round(sum(v) / len(v), 6)} for t, v in sorted(by_task.items())
        },
        "tongue_breakdown": {
            t: {"n": len(v), "mean": round(sum(v) / len(v), 6)} for t, v in sorted(by_tongue.items())
        },
        "per_row": per_row,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--holdout", required=True, type=Path, help="holdout JSONL with id, reference, meta")
    parser.add_argument("--submission", required=True, type=Path, help="submission CSV with id,prediction columns")
    parser.add_argument("--out", type=Path, default=None, help="Write JSON report to this path")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    holdout_rows = load_holdout(args.holdout)
    submission = load_submission(args.submission)
    report = score(holdout_rows, submission)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        if not args.quiet:
            print(f"wrote {args.out}")

    if not args.quiet:
        print(f"overall_score = {report['overall_score']:.4f}  (n={report['n_rows']})")
        for task, info in report["task_breakdown"].items():
            print(f"  {task:>16s}: mean={info['mean']:.4f}  n={info['n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
