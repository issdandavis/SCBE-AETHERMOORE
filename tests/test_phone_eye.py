from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_build_capture_metadata_tracks_serial_and_paths(tmp_path):
    from scripts.system.phone_eye import build_capture_metadata

    payload = build_capture_metadata(
        serial="emulator-5554",
        latest_path=tmp_path / "eye_latest.png",
        latest_xml_path=tmp_path / "eye_latest.xml",
        latest_nav_path=tmp_path / "eye_latest.nav.json",
        session_dir=str(tmp_path / "session"),
        status={"top_activity": "chrome"},
        history_path=str(tmp_path / "frame.png"),
    )

    assert payload["serial"] == "emulator-5554"
    assert payload["latest_path"].endswith("eye_latest.png")
    assert payload["latest_xml_path"].endswith("eye_latest.xml")
    assert payload["latest_nav_path"].endswith("eye_latest.nav.json")
    assert payload["history_path"].endswith("frame.png")
    assert payload["status"]["top_activity"] == "chrome"


def test_capture_writes_stable_latest_files(tmp_path, monkeypatch):
    from scripts.system import phone_eye

    screenshot = tmp_path / "raw.png"
    screenshot.write_bytes(b"x" * 1200)
    ui_dump = tmp_path / "raw.xml"
    # fmt: off
    ui_dump.write_text(  # noqa: E501
        '<?xml version=\'1.0\' encoding=\'UTF-8\' standalone=\'yes\' ?>\n'
        '<hierarchy rotation="0">\n'
        '  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.android.chrome" clickable="false" enabled="true" focused="false" scrollable="false" bounds="[0,0][540,1200]">\n'  # noqa: E501
        '    <node index="0" text="Webtoon Viewer" resource-id="" class="android.webkit.WebView" package="com.android.chrome" clickable="false" enabled="true" focused="true" scrollable="true" bounds="[0,275][540,1139]" />\n'  # noqa: E501
        '    <node index="1" text="10.0.2.2:8088/polly-pad.html" resource-id="com.android.chrome:id/url_bar" class="android.widget.EditText" package="com.android.chrome" clickable="true" enabled="true" focused="false" scrollable="false" bounds="[210,136][267,267]" />\n'  # noqa: E501
        '  </node>\n'
        '</hierarchy>\n',
        encoding="utf-8",
    )
    # fmt: on

    class FakeHand:
        def __init__(self, serial: str = ""):
            self.serial = serial
            self.session_dir = tmp_path / "session"
            self.session_dir.mkdir(exist_ok=True)

        def observe(self, name: str, include_ui_dump: bool = True):
            return {
                "screenshot": {"artifact_path": str(screenshot)},
                "ui_dump": {"artifact_path": str(ui_dump)},
                "status": {"serial": "emulator-5554", "session_dir": str(self.session_dir), "top_activity": "chrome"},
            }

    monkeypatch.setattr(phone_eye, "HydraAndroidHand", FakeHand)
    monkeypatch.setattr(phone_eye, "OUT_DIR", tmp_path)
    monkeypatch.setattr(phone_eye, "LATEST", tmp_path / "eye_latest.png")
    monkeypatch.setattr(phone_eye, "LATEST_XML", tmp_path / "eye_latest.xml")
    monkeypatch.setattr(phone_eye, "LATEST_NAV", tmp_path / "eye_latest.nav.json")
    monkeypatch.setattr(phone_eye, "LATEST_META", tmp_path / "eye_latest.json")
    monkeypatch.setattr(phone_eye, "HISTORY_DIR", tmp_path / "history")

    payload = phone_eye.capture()

    assert payload["serial"] == "emulator-5554"
    assert (tmp_path / "eye_latest.png").exists()
    assert (tmp_path / "eye_latest.xml").exists()
    assert (tmp_path / "eye_latest.nav.json").exists()
    assert "polly-pad.html" in (tmp_path / "eye_latest.nav.json").read_text(encoding="utf-8")
