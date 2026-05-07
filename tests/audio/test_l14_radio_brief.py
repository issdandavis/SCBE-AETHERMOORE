from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "l14_radio_brief.py"
SPEC = importlib.util.spec_from_file_location("l14_radio_brief", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def _status() -> dict:
    return {
        "title": "SCBE chemistry raw-anchor repair",
        "decision": "QUARANTINE",
        "summary": "Raw generation mutates exact chemistry and code anchors",
        "warning": "Do not promote until the frozen raw gate improves",
        "action": "Save the receipt and run v7 only under controlled budget",
        "required_anchors": ["NaCl", "queue_drain_guard", "carboxylic acid"],
    }


def test_radio_script_preserves_required_anchors() -> None:
    script = MODULE.build_radio_script(_status())

    assert "Assessment:" in script
    assert "Signal:" in script
    assert "Warning:" in script
    assert "Action:" in script
    assert "NaCl" in script
    assert "queue_drain_guard" in script
    assert "carboxylic acid" in script


def test_voice_packet_uses_canonical_tongues_and_sums_to_one() -> None:
    script = MODULE.build_radio_script(_status())
    packet = MODULE.build_voice_packet(_status(), script)

    assert list(packet["tongue_mix"].keys()) == ["KO", "AV", "RU", "CA", "UM", "DR"]
    assert abs(sum(packet["tongue_mix"].values()) - 1.0) < 1e-6
    assert set(packet["timbre"].keys()) == {
        "warmth",
        "brightness",
        "weight",
        "grain",
        "openness",
        "tension",
        "softness",
        "silence_affinity",
    }
    assert {item["kind"] for item in packet["breath_plan"]} <= {"micro", "soft", "full", "shaken"}


def test_transcript_check_fails_on_anchor_loss() -> None:
    status = _status()
    script = MODULE.build_radio_script(status)
    bad_transcript = script.replace("NaCl", "sodium chloride").replace("queue_drain_guard", "queue guard")

    check = MODULE.verify_transcript(script, bad_transcript, status["required_anchors"])

    assert check["ok"] is False
    assert "NaCl" in check["missing_anchors"]
    assert "queue_drain_guard" in check["missing_anchors"]
    assert check["score"] < 1.0


def test_receipt_loopback_passes_and_marks_audio_unrendered() -> None:
    receipt = MODULE.build_receipt(_status())

    assert receipt["schema_version"] == "scbe_l14_radio_brief_receipt_v1"
    assert receipt["contract_id"] == "l14_bidirectional_audio_feature_v1"
    assert receipt["transcript_check"]["ok"] is True
    assert receipt["audio"]["rendered"] is False
    assert receipt["voice_packet"]["text"] == receipt["script"]
