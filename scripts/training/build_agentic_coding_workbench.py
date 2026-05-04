#!/usr/bin/env python3
"""Build the local agentic coding workbench corpus.

This is the compatibility entrypoint used by ``npm run training:agentic-workbench``.
It rebuilds the deterministic agentic-coding sidecar corpora and writes a small
manifest so training preflight can point at a real artifact instead of a stale
script path.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "training-data" / "agentic_coding"
SFT_DIR = REPO_ROOT / "training-data" / "sft"
MANIFEST_PATH = (
    REPO_ROOT / "artifacts" / "training_hub" / "agentic_coding_workbench_manifest.json"
)


GENERATORS = [
    ("seed_dataset", ["scripts/training/build_agentic_seed.py"]),
    ("from_skills", ["scripts/training/generate_agentic_sft.py"]),
    ("ambiguity_action_traces", ["scripts/training/generate_ambiguity_action_sft.py"]),
    ("packet_traces", ["scripts/training/generate_packet_traces_sft.py"]),
    ("jupiter_ring_feedback", ["scripts/training/build_jupiter_ring_feedback.py"]),
    ("geoshell_pair_agent", ["scripts/training_data/build_geoshell_pair_agent_sft.py"]),
]

EXTRA_JSONL = [
    SFT_DIR / "geoshell_pair_agent_v1_train.sft.jsonl",
    SFT_DIR / "geoshell_pair_agent_v1_holdout.sft.jsonl",
]


def _jsonl_count(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _run(script: list[str]) -> None:
    subprocess.run([sys.executable, *script], cwd=REPO_ROOT, check=True)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    for _name, script in GENERATORS:
        _run(script)

    files = []
    for path in sorted(OUT_DIR.glob("*.jsonl")) + [
        path for path in EXTRA_JSONL if path.exists()
    ]:
        files.append(
            {
                "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "rows": _jsonl_count(path),
                "bytes": path.stat().st_size,
            }
        )

    manifest = {
        "schema_version": "scbe_agentic_coding_workbench_manifest_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "generators": [
            {"name": name, "script": " ".join(script)} for name, script in GENERATORS
        ],
        "files": files,
        "total_rows": sum(row["rows"] for row in files),
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "manifest": str(MANIFEST_PATH.relative_to(REPO_ROOT)),
                "total_rows": manifest["total_rows"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
