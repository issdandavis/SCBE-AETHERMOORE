#!/usr/bin/env python3
"""SCBE reaction packet CLI.

Small utility surface for auditing and comparing reaction-state packets. The
commands are intentionally stdlib-only so they can run anywhere the repo runs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.reaction_state import packet_from_dict


def load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_packets(value: Any) -> list[dict[str, Any]]:
    """Find reaction packets inside a packet file or benchmark report."""

    if isinstance(value, dict) and value.get("schema_version") == "scbe_reaction_state_packet_v1":
        return [value]
    packets: list[dict[str, Any]] = []
    if isinstance(value, dict):
        packet = value.get("reaction_state_packet")
        if isinstance(packet, dict):
            packets.append(packet)
        for key, child in value.items():
            if key == "reaction_state_packet":
                continue
            packets.extend(find_packets(child))
    elif isinstance(value, list):
        for item in value:
            packets.extend(find_packets(item))
    return packets


def audit_packet(path: str) -> dict[str, Any]:
    data = load_json(path)
    packets = find_packets(data)
    rows = []
    for index, packet_data in enumerate(packets):
        packet = packet_from_dict(packet_data)
        rows.append(
            {
                "index": index,
                "packet_hash": packet.packet_hash,
                "hash_ok": packet.verify_hash(),
                "domain": packet.domain,
                "bounded_operation": packet.bounded_operation,
                "classification": packet.classification,
                "source_identity": packet.source.identity,
                "target_identity": packet.target.identity,
                "loss_count": len(packet.loss_notes),
                "engraving_count": len(packet.semantic_engravings),
                "claim_boundary": packet.claim_boundary,
            }
        )
    return {
        "schema_version": "scbe_reaction_audit_v1",
        "path": path,
        "packet_count": len(rows),
        "ok": bool(rows) and all(row["hash_ok"] for row in rows),
        "packets": rows,
    }


def compare_packets(left_path: str, right_path: str) -> dict[str, Any]:
    left = find_packets(load_json(left_path))
    right = find_packets(load_json(right_path))
    left_hashes = {packet.get("packet_hash") for packet in left}
    right_hashes = {packet.get("packet_hash") for packet in right}
    left_classes = {packet.get("classification") for packet in left}
    right_classes = {packet.get("classification") for packet in right}
    return {
        "schema_version": "scbe_reaction_compare_v1",
        "left": left_path,
        "right": right_path,
        "left_packet_count": len(left),
        "right_packet_count": len(right),
        "shared_packet_hashes": sorted(hash_value for hash_value in left_hashes & right_hashes if hash_value),
        "left_only_packet_hashes": sorted(hash_value for hash_value in left_hashes - right_hashes if hash_value),
        "right_only_packet_hashes": sorted(hash_value for hash_value in right_hashes - left_hashes if hash_value),
        "classification_changed": left_classes != right_classes,
        "left_classifications": sorted(str(item) for item in left_classes if item),
        "right_classifications": sorted(str(item) for item in right_classes if item),
    }


def print_human_audit(payload: dict[str, Any]) -> None:
    print(f"reaction audit: ok={payload['ok']} packets={payload['packet_count']}")
    for row in payload["packets"]:
        print(
            f"- #{row['index']} {row['classification']} hash_ok={row['hash_ok']} "
            f"{row['source_identity']} -> {row['target_identity']}"
        )


def print_human_compare(payload: dict[str, Any]) -> None:
    print(
        "reaction compare: "
        f"left={payload['left_packet_count']} right={payload['right_packet_count']} "
        f"classification_changed={payload['classification_changed']}"
    )
    if payload["shared_packet_hashes"]:
        print(f"shared hashes: {len(payload['shared_packet_hashes'])}")
    if payload["left_only_packet_hashes"]:
        print(f"left only: {len(payload['left_only_packet_hashes'])}")
    if payload["right_only_packet_hashes"]:
        print(f"right only: {len(payload['right_only_packet_hashes'])}")


def main() -> int:
    parser = argparse.ArgumentParser(prog="scbe react")
    sub = parser.add_subparsers(dest="cmd", required=True)
    audit = sub.add_parser("audit")
    audit.add_argument("--packet", required=True)
    audit.add_argument("--json", action="store_true")
    compare = sub.add_parser("compare")
    compare.add_argument("--left", required=True)
    compare.add_argument("--right", required=True)
    compare.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.cmd == "audit":
        payload = audit_packet(args.packet)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_human_audit(payload)
        return 0 if payload["ok"] else 1
    if args.cmd == "compare":
        payload = compare_packets(args.left, args.right)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_human_compare(payload)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
