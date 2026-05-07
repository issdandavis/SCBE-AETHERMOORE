#!/usr/bin/env python3
"""Layer 14 radio brief generator and transcript verifier.

This is a no-cost proof harness for the L14 audio lane:

    system status -> governed radio script -> voice packet -> transcript receipt

The module intentionally stops before TTS. Real audio renderers can consume the
voice packet later, while this harness already tests whether required anchors
survive the script/transcript boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CANONICAL_TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
SPEECH_LABELS = ("Assessment", "Signal", "Warning", "Action")

DEFAULT_TONGUE_MIX = {
    "KO": 0.18,
    "AV": 0.14,
    "RU": 0.24,
    "CA": 0.18,
    "UM": 0.10,
    "DR": 0.16,
}

DECISION_TONGUE_BIAS = {
    "ALLOW": "AV",
    "QUARANTINE": "RU",
    "ESCALATE": "KO",
    "DENY": "UM",
}


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def status_digest(status: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(status).encode("utf-8")).hexdigest()


def normalize_tongue_mix(raw: dict[str, float] | None, decision: str = "") -> dict[str, float]:
    mix = {key: float(DEFAULT_TONGUE_MIX[key]) for key in CANONICAL_TONGUES}
    if raw:
        for key in CANONICAL_TONGUES:
            if key in raw:
                mix[key] = max(0.0, float(raw[key]))

    bias_key = DECISION_TONGUE_BIAS.get(decision.upper())
    if bias_key:
        mix[bias_key] += 0.08

    total = sum(mix.values()) or 1.0
    normalized = {key: round(mix[key] / total, 6) for key in CANONICAL_TONGUES}
    # Correct rounding drift deterministically on DR, the final canonical key.
    drift = round(1.0 - sum(normalized.values()), 6)
    normalized["DR"] = round(normalized["DR"] + drift, 6)
    return normalized


def _clean_sentence(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text.rstrip(".") if text else fallback


def _anchor_sentence(anchors: list[str]) -> str:
    if not anchors:
        return "No required anchors were supplied"
    rendered = "; ".join(anchor.strip() for anchor in anchors if anchor.strip())
    return f"Required anchors: {rendered}"


def build_radio_script(status: dict[str, Any]) -> str:
    """Build a short audit-radio script using original speech-act labels."""
    title = _clean_sentence(status.get("title"), "SCBE Layer 14 radio check")
    decision = _clean_sentence(status.get("decision"), "QUARANTINE").upper()
    summary = _clean_sentence(status.get("summary"), "Status packet received")
    warning = _clean_sentence(status.get("warning"), "Verify anchors before promotion")
    action = _clean_sentence(status.get("action"), "Save receipt and wait for the next gate")
    anchors = [str(item) for item in status.get("required_anchors", [])]

    lines = [
        f"Assessment: {title}. Decision is {decision}.",
        f"Signal: {summary}. {_anchor_sentence(anchors)}.",
        f"Warning: {warning}.",
        f"Action: {action}.",
    ]
    return "\n".join(lines)


def build_voice_packet(status: dict[str, Any], script: str) -> dict[str, Any]:
    decision = str(status.get("decision", "QUARANTINE")).upper()
    tongue_mix = normalize_tongue_mix(status.get("tongue_mix"), decision=decision)
    ru = tongue_mix["RU"]
    ko = tongue_mix["KO"]
    um = tongue_mix["UM"]
    av = tongue_mix["AV"]
    ca = tongue_mix["CA"]
    dr = tongue_mix["DR"]

    return {
        "speaker": str(status.get("speaker", "AetherMoore Radio Audit Voice")),
        "text": script,
        "tongue_mix": tongue_mix,
        "timbre": {
            "warmth": round(0.35 + av * 0.8, 4),
            "brightness": round(0.35 + ca * 0.9, 4),
            "weight": round(0.38 + dr * 0.9, 4),
            "grain": round(0.25 + ru * 0.7, 4),
            "openness": round(0.40 + av * 0.5, 4),
            "tension": round(0.25 + max(ko, ru, um) * 0.8, 4),
            "softness": round(0.25 + av * 0.6, 4),
            "silence_affinity": round(0.18 + um * 0.8, 4),
        },
        "breath_plan": [
            {"index": 0, "kind": "micro", "before_token": "Assessment", "duration_ms": 90},
            {"index": 1, "kind": "soft", "before_token": "Warning", "duration_ms": 140},
        ],
        "phase": {
            "line_phase": round((ko + ca) % 1.0, 4),
            "pause_skew": round(0.1 + um * 0.6, 4),
            "stress_bias": "front-loaded" if decision in {"ESCALATE", "DENY"} else "balanced",
        },
        "render": {
            "rate": round(0.92 + ko * 0.5 - um * 0.2, 4),
            "pitch_shift_st": round(ca * 3.0 - dr * 1.5, 4),
            "dynamic_range": round(0.42 + max(ko, ru) * 0.5, 4),
            "breath_gain_db": -24.0,
            "pause_gain": round(0.62 + ru * 0.3, 4),
            "attack_ms": 24,
            "release_ms": 92,
        },
    }


def verify_transcript(script: str, transcript: str, anchors: list[str]) -> dict[str, Any]:
    """Score whether a transcript preserves labels and required anchors."""
    transcript_lower = transcript.lower()
    script_lower = script.lower()
    required_labels = [f"{label.lower()}:" for label in SPEECH_LABELS]

    missing_labels = [label for label in required_labels if label not in transcript_lower]
    missing_anchors = [anchor for anchor in anchors if anchor.lower() not in transcript_lower]
    script_labels_missing = [label for label in required_labels if label not in script_lower]

    total_checks = len(required_labels) + len(anchors)
    failed_checks = len(missing_labels) + len(missing_anchors)
    score = 1.0 if total_checks == 0 else round((total_checks - failed_checks) / total_checks, 4)

    return {
        "ok": not missing_labels and not missing_anchors and not script_labels_missing,
        "score": score,
        "missing_labels": missing_labels,
        "missing_anchors": missing_anchors,
        "script_labels_missing": script_labels_missing,
    }


def build_receipt(status: dict[str, Any], transcript: str | None = None) -> dict[str, Any]:
    script = build_radio_script(status)
    anchors = [str(item) for item in status.get("required_anchors", [])]
    transcript_text = transcript if transcript is not None else script
    packet = build_voice_packet(status, script)
    transcript_check = verify_transcript(script, transcript_text, anchors)

    return {
        "schema_version": "scbe_l14_radio_brief_receipt_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "contract_id": "l14_bidirectional_audio_feature_v1",
        "status_sha256": status_digest(status),
        "mode": "script_transcript_loopback",
        "script": script,
        "transcript": transcript_text,
        "transcript_check": transcript_check,
        "voice_packet": packet,
        "audio": {
            "rendered": False,
            "path": None,
            "note": "TTS/audio rendering intentionally deferred; this receipt verifies governed script anchors first.",
        },
    }


def write_receipt(receipt: dict[str, Any], outdir: Path) -> dict[str, str]:
    outdir.mkdir(parents=True, exist_ok=True)
    script_path = outdir / "l14_radio_brief.txt"
    packet_path = outdir / "l14_radio_voice_packet.json"
    receipt_path = outdir / "l14_radio_receipt.json"

    script_path.write_text(receipt["script"] + "\n", encoding="utf-8")
    packet_path.write_text(json.dumps(receipt["voice_packet"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "script": str(script_path),
        "voice_packet": str(packet_path),
        "receipt": str(receipt_path),
    }


def _default_status() -> dict[str, Any]:
    return {
        "title": "SCBE chemistry v7 raw-anchor repair",
        "decision": "QUARANTINE",
        "summary": "The scaffolded gate passed, but raw generation still mutates exact anchors",
        "warning": "Do not promote until raw pass rate improves on the frozen gate",
        "action": "Run the repair profile only when controlled GPU budget is approved",
        "required_anchors": ["NaCl", "queue_drain_guard", "carboxylic acid", "not a molecule"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Layer 14 radio brief receipt.")
    parser.add_argument("--input", help="JSON status packet. Uses a built-in demo packet when omitted.")
    parser.add_argument("--transcript", help="Optional transcript text or path to verify. Defaults to script loopback.")
    parser.add_argument("--outdir", default="artifacts/l14_radio/latest", help="Output directory.")
    parser.add_argument("--json", action="store_true", help="Print compact JSON summary.")
    args = parser.parse_args()

    if args.input:
        status = json.loads(Path(args.input).read_text(encoding="utf-8"))
    else:
        status = _default_status()

    transcript = None
    if args.transcript:
        maybe_path = Path(args.transcript)
        transcript = maybe_path.read_text(encoding="utf-8") if maybe_path.exists() else args.transcript

    receipt = build_receipt(status, transcript=transcript)
    paths = write_receipt(receipt, Path(args.outdir))
    summary = {
        "ok": receipt["transcript_check"]["ok"],
        "score": receipt["transcript_check"]["score"],
        "status_sha256": receipt["status_sha256"],
        "paths": paths,
    }

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(receipt["script"])
        print()
        print(f"receipt: {paths['receipt']}")
        print(f"voice_packet: {paths['voice_packet']}")
        print(f"transcript_ok: {summary['ok']} score={summary['score']}")
    return 0 if receipt["transcript_check"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
