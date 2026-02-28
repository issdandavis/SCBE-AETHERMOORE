#!/usr/bin/env python
"""
Train hook scaffold for M6 SphereMesh.

This is a deterministic runtime/training harness that consumes JSONL events,
runs them through the six-sphere mesh, and emits state artifacts for analysis.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Dict, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.geoseed.m6_spheremesh import M6Event, M6SphereMesh


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M6 SphereMesh training scaffold")
    parser.add_argument(
        "--input-jsonl",
        default="training-data/funnel/sft_pairs.jsonl",
        help="Input JSONL containing prompt/response or summary fields",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=200,
        help="Maximum events to consume",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/m6_spheremesh",
        help="Output directory for reports",
    )
    return parser.parse_args()


def infer_tongue_vector(payload: Dict[str, object]) -> Dict[str, float]:
    vector = {"KO": 0.0, "AV": 0.0, "RU": 0.0, "CA": 0.0, "UM": 0.0, "DR": 0.0}

    # Direct tongue label from metadata has first priority.
    tongue = None
    if isinstance(payload.get("metadata"), dict):
        tongue = payload["metadata"].get("tongue")
    tongue = tongue or payload.get("tongue")

    if isinstance(tongue, str) and tongue.upper() in vector:
        vector[tongue.upper()] = 1.0
        return vector

    # Lightweight keyword prior if no explicit tongue was provided.
    text = " ".join(
        str(payload.get(k, "")) for k in ["summary", "prompt", "response", "context"]
    ).lower()

    keyword_map = {
        "KO": ["intent", "goal", "control"],
        "AV": ["transport", "route", "metadata"],
        "RU": ["policy", "rule", "governance"],
        "CA": ["compute", "model", "code"],
        "UM": ["security", "redact", "secret"],
        "DR": ["schema", "contract", "signature"],
    }

    for tongue_code, words in keyword_map.items():
        for word in words:
            if word in text:
                vector[tongue_code] += 1.0

    if sum(vector.values()) <= 0.0:
        vector["KO"] = 1.0

    return vector


def event_summary(payload: Dict[str, object]) -> str:
    return (
        str(payload.get("summary") or "").strip()
        or str(payload.get("prompt") or "").strip()
        or str(payload.get("context") or "").strip()
        or "m6 mesh event"
    )


def iter_jsonl(path: Path) -> Iterable[Dict[str, object]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def main() -> int:
    args = parse_args()
    input_path = Path(args.input_jsonl)
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    mesh = M6SphereMesh(resolution=1, signal_dim=64)

    records: List[Dict[str, object]] = []
    for idx, payload in enumerate(iter_jsonl(input_path)):
        if idx >= args.max_events:
            break

        record_id = str(payload.get("record_id") or f"event-{idx:06d}")
        event = M6Event(
            record_id=record_id,
            summary=event_summary(payload),
            tongue_vector=infer_tongue_vector(payload),
            metadata={"source": str(input_path), "index": idx},
        )
        records.append(mesh.ingest_event(event, steps=1))

    # Example Sacred Egg gate validation in the loop artifact.
    egg = mesh.register_egg(
        egg_id="m6-bootstrap-egg",
        required_tongues=["KO", "CA", "UM"],
        min_phi_weight=10.0,
        ttl_seconds=3600,
    )
    hatch_ok, hatch_reason = mesh.hatch_egg("m6-bootstrap-egg", ["KO", "CA", "UM"])

    transition_scores = {
        "KO_to_CA": mesh.score_transition("KO", "CA"),
        "CA_to_UM": mesh.score_transition("CA", "UM"),
        "DR_to_AV": mesh.score_transition("DR", "AV"),
    }

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_jsonl": str(input_path),
        "events_consumed": len(records),
        "egg_test": {
            "egg_id": egg.egg_id,
            "hatched": hatch_ok,
            "reason": hatch_reason,
        },
        "transition_scores": transition_scores,
        "snapshot": mesh.snapshot(),
        "sample_records": records[:5],
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = output_dir / f"m6_training_report_{stamp}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({"status": "ok", "report": str(out_path), "events": len(records)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
