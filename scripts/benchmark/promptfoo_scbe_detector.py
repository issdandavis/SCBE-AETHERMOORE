#!/usr/bin/env python3
"""Promptfoo bridge for the SCBE adversarial detection gate.

Reads one JSON object from stdin:
    {"prompt": "..."}

Writes one JSON object to stdout:
    {"decision": "BLOCK"|"ALLOW", ...}

This keeps Promptfoo as the external open-source eval runner while SCBE remains
the local system under test.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.adversarial.attack_corpus import BASELINE_CLEAN  # noqa: E402
from tests.adversarial.scbe_harness import SCBEDetectionGate  # noqa: E402


def evaluate_prompt(prompt: str) -> dict[str, Any]:
    gate = SCBEDetectionGate()
    gate.calibrate([item["prompt"] for item in BASELINE_CLEAN])

    try:
        decoded = json.loads(prompt)
    except json.JSONDecodeError:
        decoded = None

    if isinstance(decoded, dict) and isinstance(decoded.get("sequence"), list):
        steps = []
        any_detected = False
        for index, step in enumerate(decoded["sequence"], start=1):
            result = gate.process(
                str(step), attack_id=str(index), attack_class="sequence"
            )
            any_detected = any_detected or result.detected
            steps.append(
                {
                    "step": index,
                    "decision": "BLOCK" if result.detected else "ALLOW",
                    "signals": result.detection_signals,
                    "harmonic_cost": result.harmonic_cost,
                    "spin_magnitude": result.spin_magnitude,
                }
            )
        return {
            "decision": "BLOCK" if any_detected else "ALLOW",
            "detected": any_detected,
            "steps": steps,
        }

    result = gate.process(prompt)
    return {
        "decision": "BLOCK" if result.detected else "ALLOW",
        "detected": result.detected,
        "signals": result.detection_signals,
        "spin_code": result.spin_code,
        "spin_magnitude": result.spin_magnitude,
        "harmonic_cost": result.harmonic_cost,
        "dominant_tongue": result.dominant_tongue,
    }


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        prompt = str(payload.get("prompt", ""))
        print(json.dumps(evaluate_prompt(prompt), sort_keys=True))
        return 0
    except Exception as exc:  # pragma: no cover - defensive bridge boundary
        print(json.dumps({"decision": "ERROR", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
