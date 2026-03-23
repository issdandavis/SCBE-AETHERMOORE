#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path

CANONICAL_TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TIMBRE_KEYS = [
    "warmth",
    "brightness",
    "weight",
    "grain",
    "openness",
    "tension",
    "softness",
    "silence_affinity",
]
BREATH_KINDS = {"micro", "soft", "full", "shaken"}


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_packet(packet):
    errors = []
    warnings = []

    for key in ("speaker", "text"):
        if key not in packet:
            errors.append(f"missing required top-level field: {key}")

    tongue_mix = packet.get("tongue_mix")
    if not isinstance(tongue_mix, dict):
        errors.append("missing or invalid tongue_mix")
    else:
        missing = [key for key in CANONICAL_TONGUES if key not in tongue_mix]
        extra = [key for key in tongue_mix.keys() if key not in CANONICAL_TONGUES]
        if missing:
            errors.append(f"tongue_mix missing keys: {', '.join(missing)}")
        if extra:
            errors.append(f"tongue_mix has non-canonical keys: {', '.join(extra)}")
        values_ok = True
        for key in CANONICAL_TONGUES:
            if key in tongue_mix and not _is_number(tongue_mix[key]):
                values_ok = False
                errors.append(f"tongue_mix[{key}] is not numeric")
        if values_ok and not missing:
            total = sum(float(tongue_mix[key]) for key in CANONICAL_TONGUES)
            if abs(total - 1.0) > 0.02:
                errors.append(f"tongue_mix sums to {total:.4f}, expected 1.0 +/- 0.02")

    timbre = packet.get("timbre")
    if not isinstance(timbre, dict):
        errors.append("missing or invalid timbre")
    else:
        missing = [key for key in TIMBRE_KEYS if key not in timbre]
        if missing:
            errors.append(f"timbre missing keys: {', '.join(missing)}")
        for key in TIMBRE_KEYS:
            if key in timbre and not _is_number(timbre[key]):
                errors.append(f"timbre[{key}] is not numeric")

    breath_plan = packet.get("breath_plan")
    if not isinstance(breath_plan, list):
        errors.append("missing or invalid breath_plan")
    else:
        for idx, item in enumerate(breath_plan):
            if not isinstance(item, dict):
                errors.append(f"breath_plan[{idx}] is not an object")
                continue
            kind = item.get("kind")
            duration_ms = item.get("duration_ms")
            if kind not in BREATH_KINDS:
                errors.append(f"breath_plan[{idx}].kind is invalid: {kind}")
            if not _is_number(duration_ms) or duration_ms <= 0:
                errors.append(f"breath_plan[{idx}].duration_ms must be a positive number")

    phase = packet.get("phase")
    if not isinstance(phase, dict):
        warnings.append("phase missing or invalid")

    render = packet.get("render")
    if not isinstance(render, dict):
        warnings.append("render missing or invalid")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "canonical_tongues": CANONICAL_TONGUES,
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: validate_voice_packet.py <packet.json>", file=sys.stderr)
        sys.exit(2)

    packet_path = Path(sys.argv[1])
    if not packet_path.exists():
        print(json.dumps({"valid": False, "errors": [f"file not found: {packet_path}"], "warnings": []}, indent=2))
        sys.exit(1)

    try:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"valid": False, "errors": [f"failed to read json: {exc}"], "warnings": []}, indent=2))
        sys.exit(1)

    result = validate_packet(packet)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
