#!/usr/bin/env python3
"""claim_gate_adapter.py

Converts SCBE claim evidence rows into either:
1. BLOCK/READY evidence stamps for non-statistical claims.
2. validation_gate.py-compatible report JSON for statistical model/eval claims.

This script does not run tests, models, or cloud jobs. It only translates saved
claim metadata into a gate-ready shape.

Expected use:
  python scripts/system/claim_gate_adapter.py artifacts/ai_brain/claim_gate_manifest.json --out artifacts/ai_brain/gate_reports

If a claim has `validation.baseline`, `validation.trained`, and `validation.control`,
a `validation_gate` JSON report is emitted for that claim. Otherwise the claim is
stamped based on whether code/test/artifact paths are present.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_ROOT = REPO_ROOT / "python"
for candidate in (REPO_ROOT, PYTHON_ROOT):
    s = str(candidate)
    if s not in sys.path:
        sys.path.insert(0, s)

try:
    from scbe.transference_gate import decode_text
except Exception:  # pragma: no cover - fallback keeps this adapter standalone
    decode_text = None


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return text[:80] or "claim"


def has_items(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0


def evidence_stamp(row: dict[str, Any]) -> dict[str, Any]:
    code_ok = has_items(row.get("code_paths"))
    test_ok = has_items(row.get("test_paths"))
    artifact_ok = has_items(row.get("artifact_paths"))
    if code_ok and test_ok and artifact_ok:
        status = "READY_FOR_RELEASE_REVIEW"
    elif code_ok and test_ok:
        status = "BLOCKED_MISSING_RESULT_ARTIFACT"
    elif code_ok:
        status = "BLOCKED_MISSING_TEST_AND_ARTIFACT"
    else:
        status = "BLOCKED_MISSING_CODE_EVIDENCE"
    return {
        "claim_id": row.get("claim_id"),
        "claim": row.get("claim"),
        "status": status,
        "code_ok": code_ok,
        "test_ok": test_ok,
        "artifact_ok": artifact_ok,
        "notes": row.get("notes", ""),
    }


def validation_report(row: dict[str, Any]) -> dict[str, Any] | None:
    validation = row.get("validation") or {}
    required = ["baseline", "trained", "control"]
    if not all(k in validation for k in required):
        return None
    return {
        "claim": validation.get("claim_type", "capability"),
        "baseline": validation["baseline"],
        "trained": validation["trained"],
        "control": validation["control"],
        "verifier_id": validation.get("verifier_id", ""),
        "generator_id": validation.get("generator_id", ""),
        "verifier_independent": bool(validation.get("verifier_independent", False)),
        "min_n_for_perfect": int(validation.get("min_n_for_perfect", 50)),
        "source_claim_id": row.get("claim_id"),
        "source_claim": row.get("claim"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", help="claim gate manifest JSON")
    parser.add_argument("--out", default="artifacts/ai_brain/gate_reports")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = manifest_path.read_bytes()
    if decode_text is not None:
        text, _, _, _ = decode_text(raw)
    else:
        text = raw.decode("utf-8-sig")
    data = json.loads(text)
    rows = data.get("claims", [])
    stamps = []
    emitted_reports = []

    for row in rows:
        stamps.append(evidence_stamp(row))
        report = validation_report(row)
        if report is not None:
            name = slugify(str(row.get("claim_id") or row.get("claim") or "claim"))
            out_path = out_dir / f"{name}.validation_gate.json"
            out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
            emitted_reports.append(str(out_path))

    summary = {
        "source_manifest": str(manifest_path),
        "claim_count": len(rows),
        "emitted_validation_gate_reports": emitted_reports,
        "stamps": stamps,
    }
    summary_path = out_dir / "claim_gate_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
