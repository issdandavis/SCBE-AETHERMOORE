#!/usr/bin/env python3
"""Deterministic benchmark for the six-lane command transport.

This is a structural codec check, not a radio, audio, cryptographic, or noisy
channel benchmark. It measures exact command-tape size, lossless compression,
five-plus-one parity overhead, every single-lane erasure, every two-lane
erasure, lane corruption detection, and Sacred Tongue byte-token round trips.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from itertools import combinations
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.semantic_opcode_vm import assemble  # noqa: E402
from src.fleet.bijective_frequency_transport import (  # noqa: E402
    BijectiveTransportError,
    TONGUE_ORDER,
    bundle_metrics,
    encode_program,
    prove_lane_token_bijections,
    recover_program,
)

SCHEMA_VERSION = "scbe_bijective_frequency_transport_benchmark_v1"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "artifacts"
    / "benchmarks"
    / "fleet_transport"
    / "bijective_frequency_transport.json"
)

TEN_COMMAND_PROGRAM = "; ".join(
    (
        "LOAD r0 4",
        "LOAD r1 6",
        "ADD r0 2",
        "COMPARE r0 6",
        "VERIFY",
        "STORE r0 1",
        "MEMORY_BIND 1",
        "HASH",
        "SEAL",
        "HALT",
    )
)


def _corrupt_lane(bundle, tongue: str):
    lanes = []
    for lane in bundle.lanes:
        if lane.tongue == tongue:
            changed = bytes((lane.symbols[0] ^ 0x01,)) + lane.symbols[1:]
            lane = replace(lane, symbols=changed)
        lanes.append(lane)
    return replace(bundle, lanes=tuple(lanes))


def run_benchmark() -> dict[str, Any]:
    bundle = encode_program(TEN_COMMAND_PROGRAM)
    expected = assemble(TEN_COMMAND_PROGRAM)
    direct = recover_program(bundle)

    single_erasure = {}
    for tongue in TONGUE_ORDER:
        recovered = recover_program(bundle, unavailable_lanes=(tongue,))
        single_erasure[tongue] = {
            "exact": recovered.program == expected,
            "used_parity": recovered.used_parity,
            "erased_lanes": list(recovered.erased_lanes),
        }

    corruption = {}
    for tongue in TONGUE_ORDER:
        recovered = recover_program(_corrupt_lane(bundle, tongue))
        corruption[tongue] = {
            "detected": tongue in recovered.erased_lanes,
            "exact_after_recovery": recovered.program == expected,
            "used_parity": recovered.used_parity,
        }

    double_erasure = {}
    for pair in combinations(TONGUE_ORDER, 2):
        key = "+".join(pair)
        try:
            recover_program(bundle, unavailable_lanes=pair)
        except BijectiveTransportError as exc:
            double_erasure[key] = {"rejected": True, "reason": str(exc)}
        else:
            double_erasure[key] = {"rejected": False, "reason": ""}

    token_bijections = prove_lane_token_bijections(bundle)
    metrics = bundle_metrics(bundle)
    raw_wire_bytes = bundle.packed_bytes
    repetition_wire_bytes = bundle.packed_bytes * len(TONGUE_ORDER)
    braid_wire_bytes = bundle.wire_symbol_bytes
    return {
        "schema_version": SCHEMA_VERSION,
        "fixture": {
            "program": TEN_COMMAND_PROGRAM,
            "command_count": bundle.command_count,
            "program_sha256": bundle.payload_sha256,
            "lane_order": list(TONGUE_ORDER),
            "lane_transforms": {lane.tongue: lane.transform for lane in bundle.lanes},
            "lane_frequencies_hz": {
                lane.tongue: lane.harmonic_frequency_hz for lane in bundle.lanes
            },
        },
        "metrics": metrics,
        "controls": {
            "raw_single_lane_wire_bytes": raw_wire_bytes,
            "sixfold_repetition_wire_bytes": repetition_wire_bytes,
            "five_plus_one_parity_wire_bytes": braid_wire_bytes,
            "parity_vs_repetition_reduction": 1.0
            - (braid_wire_bytes / repetition_wire_bytes),
        },
        "checks": {
            "direct_exact": direct.program == expected,
            "all_single_erasure_exact": all(
                row["exact"] for row in single_erasure.values()
            ),
            "all_single_corruption_detected": all(
                row["detected"] for row in corruption.values()
            ),
            "all_single_corruption_exact_after_recovery": all(
                row["exact_after_recovery"] for row in corruption.values()
            ),
            "all_double_erasure_rejected": all(
                row["rejected"] for row in double_erasure.values()
            ),
            "all_tongue_views_bijective": all(token_bijections.values()),
        },
        "single_erasure": single_erasure,
        "single_corruption": corruption,
        "double_erasure": double_erasure,
        "tongue_bijections": token_bijections,
        "claim_status": {
            "exact_round_trip": "SUPPORTED_STRUCTURAL",
            "single_lane_recovery": "SUPPORTED_STRUCTURAL",
            "two_lane_recovery": "OUTSIDE_CONTRACT",
            "free_capacity": "REFUTED_BY_ACCOUNTING",
            "adversarial_authentication": "NOT_TESTED_USE_OUTER_ENVELOPE",
            "physical_frequency_channel": "NOT_TESTED",
        },
        "scope": (
            "Deterministic software codec only. Wire-byte counts exclude the signed outer envelope. "
            "Tongue/frequency labels do not establish RF or acoustic channel performance."
        ),
    }


def write_report(payload: dict[str, Any], output: Path) -> tuple[Path, Path]:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown = output.with_suffix(".md")
    metrics = payload["metrics"]
    controls = payload["controls"]
    checks = payload["checks"]
    lines = [
        "# Bijective Frequency Transport Benchmark",
        "",
        f"- Commands: {metrics['commands']}",
        f"- Source UTF-8 bytes: {metrics['source_utf8_bytes']}",
        f"- Semantic opcode bytes: {metrics['opcode_bytes']}",
        f"- Packed bytes ({metrics['codec']}): {metrics['packed_bytes']}",
        f"- Five-plus-one wire symbols: {metrics['wire_symbol_bytes']}",
        f"- Coding overhead: {metrics['coding_overhead_ratio']:.4f}x packed payload",
        (
            "- Wire-symbol reduction versus six full copies: "
            f"{controls['parity_vs_repetition_reduction']:.2%}"
        ),
        "",
        "| Check | Result |",
        "| --- | --- |",
        f"| Direct exact round trip | {checks['direct_exact']} |",
        f"| Every one-lane erasure recovered | {checks['all_single_erasure_exact']} |",
        f"| Every one-lane corruption detected | {checks['all_single_corruption_detected']} |",
        (
            "| Every detected one-lane corruption recovered exactly | "
            f"{checks['all_single_corruption_exact_after_recovery']} |"
        ),
        f"| Every two-lane erasure rejected | {checks['all_double_erasure_rejected']} |",
        f"| All six tongue views bijective | {checks['all_tongue_views_bijective']} |",
        "",
        "This proves the software framing and one-erasure contract for the fixture. "
        "It does not test RF/audio modulation, adversarial authentication, or physical hardware.",
    ]
    markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output, markdown


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = run_benchmark()
    json_path, markdown_path = write_report(payload, args.output)
    print(
        json.dumps(
            {
                "json": str(json_path),
                "markdown": str(markdown_path),
                "checks": payload["checks"],
                "claim_status": payload["claim_status"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
