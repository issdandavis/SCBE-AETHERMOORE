from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# fmt: off
SAMPLE_XML = (
    '<?xml version=\'1.0\' encoding=\'UTF-8\' standalone=\'yes\' ?>\n'
    '<hierarchy rotation="0">\n'
    '  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.android.chrome" clickable="false" enabled="true" focused="false" scrollable="false" bounds="[0,0][540,1200]">\n'  # noqa: E501
    '    <node index="0" text="Webtoon Viewer" resource-id="" class="android.webkit.WebView" package="com.android.chrome" clickable="false" enabled="true" focused="true" scrollable="true" bounds="[0,275][540,1139]">\n'  # noqa: E501
    '      <node index="0" text="Chapter 1: Protocol Handshake" resource-id="" class="android.widget.TextView" package="com.android.chrome" clickable="false" enabled="true" focused="false" scrollable="false" bounds="[23,275][446,359]" />\n'  # noqa: E501
    '      <node index="1" text="Tap once for controls" resource-id="" class="android.widget.TextView" package="com.android.chrome" clickable="false" enabled="true" focused="false" scrollable="false" bounds="[133,1007][406,1109]" />\n'  # noqa: E501
    '      <node index="2" text="STORY" resource-id="" class="android.widget.Button" package="com.android.chrome" clickable="true" enabled="true" focused="false" scrollable="false" bounds="[336,991][517,1083]" />\n'  # noqa: E501
    '    </node>\n'
    '    <node index="1" text="10.0.2.2:8088/reader.html?chapter=ch01&amp;variant=generated" resource-id="com.android.chrome:id/url_bar" class="android.widget.EditText" package="com.android.chrome" clickable="true" enabled="true" focused="false" scrollable="false" bounds="[210,136][267,267]" />\n'  # noqa: E501
    '    <node index="2" text="" resource-id="com.android.chrome:id/home_button" class="android.widget.ImageButton" package="com.android.chrome" content-desc="Open the home page" clickable="true" enabled="true" focused="false" scrollable="false" bounds="[0,128][126,275]" />\n'  # noqa: E501
    '    <node index="3" text="Ghost" resource-id="" class="android.widget.Button" package="com.android.chrome" clickable="true" enabled="true" focused="false" scrollable="false" bounds="[0,0][0,0]" />\n'  # noqa: E501
    '  </node>\n'
    '</hierarchy>\n'
)
# fmt: on


def test_parse_bounds_extracts_geometry():
    from scripts.system.phone_navigation_telemetry import parse_bounds

    bounds = parse_bounds("[336,991][517,1083]")

    assert bounds == {
        "x1": 336,
        "y1": 991,
        "x2": 517,
        "y2": 1083,
        "width": 181,
        "height": 92,
        "center_x": 426,
        "center_y": 1037,
        "area": 16652,
    }


def test_build_navigation_telemetry_extracts_route_text_and_targets(tmp_path):
    from scripts.system.phone_navigation_telemetry import build_navigation_telemetry

    xml_path = tmp_path / "window_dump.xml"
    xml_path.write_text(SAMPLE_XML, encoding="utf-8")

    payload = build_navigation_telemetry(
        xml_path, screenshot_path="eye_latest.png", status={"top_activity": "chrome"}
    )

    assert payload["package_name"] == "com.android.chrome"
    assert payload["page_title"] == "Webtoon Viewer"
    assert (
        payload["route_url"]
        == "10.0.2.2:8088/reader.html?chapter=ch01&variant=generated"
    )
    assert "Chapter 1: Protocol Handshake" in payload["visible_text"]
    assert payload["scrollables"][0]["label"] == "Webtoon Viewer"
    assert [target["label"] for target in payload["tap_targets"]] == [
        "Open the home page",
        "10.0.2.2:8088/reader.html?chapter=ch01&variant=generated",
        "STORY",
    ]
    assert payload["summary"]["tap_target_count"] == 3
    assert payload["status"]["top_activity"] == "chrome"
