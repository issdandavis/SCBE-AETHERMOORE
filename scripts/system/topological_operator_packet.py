#!/usr/bin/env python3
"""Emit deterministic topological T-tree packets for AI operation commands."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.tokenizer.topological_operator_tree import operator_signature_packet

DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "operator_trees" / "latest_packet.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_artifact(command: str) -> dict:
    packet = operator_signature_packet(command)
    return {
        "schema_version": "scbe-topological-operator-artifact-v1",
        "created_at_utc": _utc_now(),
        "command_chars": len(command),
        "command_sha256": packet["signature"]["sha256"],
        "packet": packet,
    }


def write_artifact(artifact: dict, output_path: Path = DEFAULT_OUTPUT) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic SCBE topological T-tree packet"
    )
    parser.add_argument(
        "--command",
        required=True,
        help="Operation command text, e.g. 'korah aelin dahru'",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    artifact = build_artifact(args.command)
    output_path = write_artifact(artifact, Path(args.output))
    summary = {
        "schema_version": artifact["schema_version"],
        "command_chars": artifact["command_chars"],
        "root_value": artifact["packet"]["root_value"],
        "signature_hex": artifact["packet"]["signature"]["hex"],
        "signature_binary": artifact["packet"]["signature"]["binary"],
        "floating_point_policy": artifact["packet"]["floating_point_policy"],
        "written": str(output_path),
    }
    print(json.dumps(artifact if args.json else summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
