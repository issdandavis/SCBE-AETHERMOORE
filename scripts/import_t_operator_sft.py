#!/usr/bin/env python3
"""Import Kimi T-operator SFT records into the repo training format."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    REPO_ROOT
    / "artifacts"
    / "incoming"
    / "kimi_agent_binary_cheat_sheet_feedback_20260425"
    / "t_operator_sft.jsonl"
)
DEFAULT_OUTPUT = REPO_ROOT / "training-data" / "sft" / "t_operator_v1.sft.jsonl"
DEFAULT_MANIFEST = REPO_ROOT / "training-data" / "sft" / "t_operator_v1_manifest.json"

DEFAULT_SYSTEM = (
    "You are an SCBE mathematical compiler. Translate standard functions into "
    "T-operator and EML operator constructions, preserve RPN/tree notation, "
    "and mark verification status explicitly."
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
    ):
        if not line.strip():
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise ValueError(f"line {line_no} is not a JSON object")
        rows.append(parsed)
    return rows


def _record_id(index: int, row: dict[str, Any]) -> str:
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    key = (
        metadata.get("function_key")
        or metadata.get("function_name")
        or f"row_{index:04d}"
    )
    safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(key)).strip("_")
    return f"t_operator_v1_{index:04d}_{safe[:48]}"


def convert_record(
    index: int, row: dict[str, Any], source_sha256: str
) -> dict[str, Any]:
    instruction = str(row.get("instruction", "")).strip()
    input_text = str(row.get("input", "")).strip()
    output_text = str(row.get("output", "")).strip()
    system_text = str(row.get("system", "")).strip() or DEFAULT_SYSTEM
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}

    return {
        "id": _record_id(index, row),
        "track": "t_operator_eml_symbolic_compiler",
        "source_type": "kimi_agent_binary_cheat_sheet_feedback",
        "quality": "reference" if metadata.get("verified", False) else "candidate",
        "messages": [
            {"role": "system", "content": system_text},
            {"role": "user", "content": f"{instruction}\n\n{input_text}".strip()},
            {"role": "assistant", "content": output_text},
        ],
        "metadata": {
            **metadata,
            "source_sha256": source_sha256,
            "operator_primitives": ["T(x,y,z)", "EML(x,y)"],
            "verification_policy": "hybrid_numeric_bootstrap",
        },
    }


def import_dataset(source: Path, output: Path, manifest: Path) -> dict[str, Any]:
    if not source.exists():
        raise FileNotFoundError(source)

    source_sha = _sha256(source)
    source_rows = _load_jsonl(source)
    converted = [
        convert_record(index, row, source_sha)
        for index, row in enumerate(source_rows, start=1)
    ]

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for record in converted:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")

    verified = sum(1 for record in converted if record["quality"] == "reference")
    manifest_payload = {
        "schema_version": "t_operator_sft_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_path": str(source),
        "source_sha256": source_sha,
        "output_path": str(output.relative_to(REPO_ROOT)),
        "record_count": len(converted),
        "verified_count": verified,
        "candidate_count": len(converted) - verified,
        "track": "t_operator_eml_symbolic_compiler",
        "training_rule": (
            "Use T/EML records as symbolic compiler examples. Treat floating-point "
            "operator prototypes as research artifacts, not consensus signatures."
        ),
    }
    manifest.write_text(
        json.dumps(manifest_payload, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return manifest_payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    manifest = import_dataset(args.source, args.output, args.manifest)
    print(
        json.dumps(manifest, indent=2)
        if args.json
        else f"wrote {manifest['record_count']} records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
