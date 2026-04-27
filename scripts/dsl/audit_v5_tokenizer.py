#!/usr/bin/env python3
"""Audit parser-critical DSL selector tokens for the v5 contract lane."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOLDOUT = ROOT / "training-data" / "sft" / "bijective_dsl_v5_holdout.sft.jsonl"
OUT = ROOT / "artifacts" / "dsl_eval_reports" / "v5_tokenizer_audit.json"


SELECTOR_RE = re.compile(r"well_select\(([^)\n]+)\)")
PRIMITIVE_RE = re.compile(r"^(well_select|tongue_shift|phi_weight|mobius_phase|breath|compose|vote|seal)\(", re.M)


def assistant_text(row: dict) -> str:
    return next((m.get("content", "") for m in row.get("messages", []) if m.get("role") == "assistant"), "")


def main() -> int:
    rows = [json.loads(line) for line in HOLDOUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    selectors = Counter()
    primitives = Counter()
    missing_contract_primitive = 0
    for row in rows:
        text = assistant_text(row)
        found = SELECTOR_RE.findall(text)
        primitive_found = PRIMITIVE_RE.findall(text)
        if not found and not primitive_found:
            missing_contract_primitive += 1
        selectors.update(found)
        primitives.update(primitive_found)

    failures = []
    if missing_contract_primitive:
        failures.append(f"missing contract primitive in {missing_contract_primitive} records")
    if not selectors and not primitives:
        failures.append("no contract tokens found")

    weighted_tokens = sorted(set(selectors) | set(primitives))
    payload = {
        "schema_version": "v5_tokenizer_audit_light_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input": str(HOLDOUT.relative_to(ROOT).as_posix()),
        "records": len(rows),
        "selectors": dict(selectors),
        "primitives": dict(primitives),
        "weighted_ce_symbol_count": len(weighted_tokens),
        "weighted_ce_symbols": weighted_tokens,
        "verdict": "PASS" if not failures else "FAIL",
        "failures": failures,
        "notes": "Lightweight audit: verifies the symbolic contract tokens that kernel_template.py upweights after model tokenizer encoding.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print(f"verdict={payload['verdict']}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
