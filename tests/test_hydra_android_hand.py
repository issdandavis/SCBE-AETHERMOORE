from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_parse_adb_devices_extracts_metadata():
    from src.browser.hydra_android_hand import parse_adb_devices

    output = """List of devices attached
emulator-5554 device product:sdk_gphone64_x86_64 model:sdk_gphone64_x86_64 transport_id:4
R58M1234567 unauthorized usb:1-1 transport_id:8
"""

    devices = parse_adb_devices(output)

    assert len(devices) == 2
    assert devices[0]["serial"] == "emulator-5554"
    assert devices[0]["ready"] is True
    assert devices[0]["is_emulator"] is True
    assert devices[0]["metadata"]["model"] == "sdk_gphone64_x86_64"
    assert devices[1]["state"] == "unauthorized"


def test_pick_primary_serial_prefers_ready_emulator():
    from src.browser.hydra_android_hand import pick_primary_serial

    devices = [
        {"serial": "R58M1234567", "ready": True, "is_emulator": False},
        {"serial": "emulator-5554", "ready": True, "is_emulator": True},
    ]

    assert pick_primary_serial(devices) == "emulator-5554"


def test_parse_wm_size_and_density_support_override_values():
    from src.browser.hydra_android_hand import parse_wm_density, parse_wm_size

    size = parse_wm_size("Physical size: 1080x2400\nOverride size: 1080x2200\n")
    density = parse_wm_density("Physical density: 420\nOverride density: 360\n")

    assert size["physical"] == {"width": 1080, "height": 2400}
    assert size["override"] == {"width": 1080, "height": 2200}
    assert density["physical"] == 420
    assert density["override"] == 360


def test_encode_input_text_preserves_spaces_and_escapes():
    from src.browser.hydra_android_hand import encode_input_text

    assert encode_input_text("Took you long enough") == "Took%syou%slong%senough"
    assert encode_input_text("A&B") == "A\\&B"


def test_build_webtoon_preview_plan_alternates_capture_and_swipe():
    from src.browser.hydra_android_hand import build_webtoon_preview_plan

    plan = build_webtoon_preview_plan(width=1080, height=2400, steps=3, capture_prefix="ch01")

    assert [task["action"] for task in plan] == ["screencap", "swipe", "screencap", "swipe", "screencap"]
    assert plan[0]["name"] == "ch01_00"
    assert plan[-1]["name"] == "ch01_02"
    assert plan[1]["x1"] == 540
    assert plan[1]["y1"] > plan[1]["y2"]


def test_hydra_android_hand_initializes_six_fingers(tmp_path):
    from src.browser.hydra_android_hand import HydraAndroidHand

    hand = HydraAndroidHand(head_id="webtoon-preview", artifact_root=tmp_path)

    assert hand.head_id == "webtoon-preview"
    assert len(hand.fingers) == 6
    assert hand.session_dir.exists()
