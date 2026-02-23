#!/usr/bin/env python3
"""Dataset auditor for SCBE training pipelines.

Provides:
- anomaly scoring per record (entropy/shape/secret-signature features)
- immutable-style hashchain root for auditability
- ALLOW/QUARANTINE decision gate
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


SECRET_MARKERS = (
    "hf_",
    "api_key",
    "secret",
    "token",
    "password",
    "aws_access_key",
)


def _text_of(rec: Dict[str, Any]) -> str:
    for k in ("text", "source_text", "message", "title"):
        if rec.get(k) is not None:
            return str(rec[k])
    return json.dumps(rec, sort_keys=True)


def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    freq: Dict[str, int] = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    n = float(len(text))
    ent = 0.0
    for c in freq.values():
        p = c / n
        ent -= p * math.log2(p)
    return float(ent)


def _ratio_symbols(text: str) -> float:
    if not text:
        return 0.0
    sym = sum(1 for ch in text if not ch.isalnum() and not ch.isspace())
    return sym / float(len(text))


def _anomaly_score(text: str) -> float:
    lower = text.lower()
    ent = _shannon_entropy(text)
    ent_norm = min(1.0, ent / 6.0)
    sym = min(1.0, _ratio_symbols(text) / 0.35)
    short_pen = 1.0 if len(text.strip()) < 60 else 0.0
    secret_hit = 1.0 if any(m in lower for m in SECRET_MARKERS) else 0.0
    score = 0.45 * ent_norm + 0.25 * sym + 0.15 * short_pen + 0.15 * secret_hit
    return float(max(0.0, min(1.0, score)))


def audit_dataset_records(
    records: Iterable[Dict[str, Any]],
    *,
    threshold: float = 0.78,
    max_flagged_ratio: float = 0.08,
) -> Dict[str, Any]:
    rows = list(records)
    if not rows:
        return {
            "status": "QUARANTINE",
            "reason": "empty dataset",
            "threshold": threshold,
            "sample_count": 0,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        }

    scores: List[float] = []
    flagged: List[Dict[str, Any]] = []
    chain = "GENESIS"
    for i, rec in enumerate(rows):
        text = _text_of(rec)
        score = _anomaly_score(text)
        scores.append(score)
        record_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        chain = hashlib.sha256(f"{chain}:{i}:{record_hash}".encode("utf-8")).hexdigest()
        if score >= threshold:
            flagged.append({"index": i, "score": round(score, 6), "preview": text[:140]})

    n = len(rows)
    flagged_ratio = len(flagged) / float(n)
    mean_score = sum(scores) / float(n)
    max_score = max(scores)
    quarantine = (max_score >= threshold) and (flagged_ratio > max_flagged_ratio)
    status = "QUARANTINE" if quarantine else "ALLOW"

    return {
        "status": status,
        "reason": "too many high-anomaly records" if quarantine else "dataset within policy",
        "threshold": float(threshold),
        "max_flagged_ratio": float(max_flagged_ratio),
        "sample_count": int(n),
        "flagged_count": int(len(flagged)),
        "flagged_ratio": round(float(flagged_ratio), 6),
        "mean_score": round(float(mean_score), 6),
        "max_score": round(float(max_score), 6),
        "hashchain_root": chain,
        "flagged_examples": flagged[:20],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit training JSONL dataset")
    parser.add_argument("--jsonl", required=True)
    parser.add_argument("--threshold", type=float, default=0.78)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    rows = _read_jsonl(Path(args.jsonl))
    report = audit_dataset_records(rows, threshold=args.threshold)
    out = Path(args.out) if args.out else Path(args.jsonl).with_suffix(".audit.json")
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Audit report written: {out}")
    print(f"status={report['status']} sample_count={report['sample_count']} flagged={report['flagged_count']}")
    return 0 if report["status"] == "ALLOW" else 2


if __name__ == "__main__":
    raise SystemExit(main())

