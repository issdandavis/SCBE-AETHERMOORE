"""Run the experimental multi-storage interaction mesh on repo notes."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from hydra.lattice25d_ops import NoteRecord, load_notes_from_glob, sample_notes
from src.knowledge.storage_interaction_mesh import StorageInteractionMesh

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "system_audit" / "storage_interaction_mesh"


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_notes(patterns: list[str], max_notes: int) -> list[NoteRecord]:
    if not patterns:
        return sample_notes(min(max_notes, 12))

    notes: list[NoteRecord] = []
    per_pattern = max(1, max_notes // max(1, len(patterns)))
    for pattern in patterns:
        notes.extend(load_notes_from_glob(pattern, max_notes=per_pattern, source="repo", authority="public"))
        if len(notes) >= max_notes:
            break
    return notes[:max_notes]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the SCBE experimental storage interaction mesh.")
    parser.add_argument(
        "--notes-glob",
        action="append",
        default=[],
        help="Repo-relative glob for markdown/text notes. May be provided multiple times.",
    )
    parser.add_argument("--max-notes", type=int, default=24, help="Maximum notes to ingest.")
    parser.add_argument("--focus-phase", type=float, default=0.5, help="Governance attachment ring phase.")
    parser.add_argument("--focus-bandwidth", type=float, default=0.18, help="Attachment ring bandwidth.")
    parser.add_argument("--output-json", default="", help="Optional explicit artifact path.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    notes = _load_notes(list(args.notes_glob), max(1, args.max_notes))
    mesh = StorageInteractionMesh(
        focus_phase_rad=args.focus_phase,
        focus_bandwidth=args.focus_bandwidth,
        fold_negative_vectors=True,
        fold_threshold=0.15,
    )
    mesh.ingest_notes(notes)

    payload = {
        "experiment": "storage_interaction_mesh",
        "timestamp_utc": _timestamp(),
        "note_count": len(notes),
        "note_sources": sorted({note.source for note in notes}),
        "patterns": list(args.notes_glob),
        "mesh": mesh.export_state(),
    }

    out_path = Path(args.output_json) if args.output_json else ARTIFACT_ROOT / f"{payload['timestamp_utc']}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
