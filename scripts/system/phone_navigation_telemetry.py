#!/usr/bin/env python3
"""Build route/text/tap-target telemetry from Android UI dumps."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.browser.hydra_android_hand import HydraAndroidHand


BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")
URL_RE = re.compile(r"^[a-z0-9.-]+(?::\d+)?/[^\s]+$", re.IGNORECASE)


def parse_bounds(raw: str) -> Optional[Dict[str, int]]:
    match = BOUNDS_RE.match((raw or "").strip())
    if not match:
        return None
    x1, y1, x2, y2 = (int(part) for part in match.groups())
    width = max(0, x2 - x1)
    height = max(0, y2 - y1)
    return {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "width": width,
        "height": height,
        "center_x": x1 + (width // 2),
        "center_y": y1 + (height // 2),
        "area": width * height,
    }


def _walk_nodes(node: ET.Element, depth: int = 0) -> Iterable[Dict[str, Any]]:
    bounds = parse_bounds(node.attrib.get("bounds", ""))
    summary = {
        "depth": depth,
        "text": (node.attrib.get("text") or "").strip(),
        "content_desc": (node.attrib.get("content-desc") or "").strip(),
        "resource_id": (node.attrib.get("resource-id") or "").strip(),
        "class_name": (node.attrib.get("class") or "").strip(),
        "package": (node.attrib.get("package") or "").strip(),
        "clickable": node.attrib.get("clickable") == "true",
        "enabled": node.attrib.get("enabled") != "false",
        "focusable": node.attrib.get("focusable") == "true",
        "focused": node.attrib.get("focused") == "true",
        "scrollable": node.attrib.get("scrollable") == "true",
        "selected": node.attrib.get("selected") == "true",
        "bounds": bounds,
    }
    yield summary
    for child in list(node):
        yield from _walk_nodes(child, depth + 1)


def _node_label(node: Dict[str, Any]) -> str:
    for value in (node["text"], node["content_desc"]):
        if value:
            return value
    resource_id = node["resource_id"]
    if resource_id:
        return resource_id.rsplit("/", 1)[-1]
    class_name = node["class_name"]
    return class_name.rsplit(".", 1)[-1] if class_name else "node"


def _route_url(nodes: List[Dict[str, Any]]) -> str:
    for node in nodes:
        resource_id = node["resource_id"]
        text = node["text"]
        if resource_id.endswith("url_bar") and text:
            return text
    for node in nodes:
        text = node["text"]
        if text and URL_RE.match(text):
            return text
    return ""


def _page_title(nodes: List[Dict[str, Any]]) -> str:
    for node in nodes:
        if node["class_name"] == "android.webkit.WebView" and node["text"]:
            return node["text"]
    return ""


def _visible_text(nodes: List[Dict[str, Any]]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for node in nodes:
        if not node["text"]:
            continue
        bounds = node["bounds"]
        if not bounds or bounds["area"] <= 0:
            continue
        text = node["text"]
        if text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def _tap_targets(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    targets: List[Dict[str, Any]] = []
    for node in nodes:
        if not node["enabled"] or not node["clickable"]:
            continue
        bounds = node["bounds"]
        if not bounds or bounds["area"] <= 0:
            continue
        targets.append(
            {
                "label": _node_label(node),
                "text": node["text"],
                "content_desc": node["content_desc"],
                "resource_id": node["resource_id"],
                "class_name": node["class_name"],
                "focused": node["focused"],
                "bounds": bounds,
            }
        )
    targets.sort(key=lambda item: (item["bounds"]["y1"], item["bounds"]["x1"], -item["bounds"]["area"]))
    return targets


def _scrollables(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for node in nodes:
        if not node["scrollable"]:
            continue
        bounds = node["bounds"]
        if not bounds or bounds["area"] <= 0:
            continue
        items.append(
            {
                "label": _node_label(node),
                "class_name": node["class_name"],
                "resource_id": node["resource_id"],
                "bounds": bounds,
            }
        )
    items.sort(key=lambda item: item["bounds"]["area"], reverse=True)
    return items


def build_navigation_telemetry(
    xml_path: Path,
    *,
    screenshot_path: str = "",
    status: Optional[Dict[str, Any]] = None,
    source: str = "xml",
) -> Dict[str, Any]:
    root = ET.fromstring(xml_path.read_text(encoding="utf-8"))
    nodes = list(_walk_nodes(root))
    package_name = next((node["package"] for node in nodes if node["package"]), "")
    focused = next((node for node in nodes if node["focused"]), None)
    telemetry = {
        "source": source,
        "xml_path": str(xml_path),
        "screenshot_path": screenshot_path,
        "rotation": int(root.attrib.get("rotation", "0") or 0),
        "package_name": package_name,
        "page_title": _page_title(nodes),
        "route_url": _route_url(nodes),
        "visible_text": _visible_text(nodes),
        "tap_targets": _tap_targets(nodes),
        "scrollables": _scrollables(nodes),
        "focused_node": {
            "label": _node_label(focused),
            "resource_id": focused["resource_id"],
            "class_name": focused["class_name"],
            "bounds": focused["bounds"],
        }
        if focused
        else None,
        "status": status or {},
    }
    telemetry["summary"] = {
        "visible_text_count": len(telemetry["visible_text"]),
        "tap_target_count": len(telemetry["tap_targets"]),
        "scrollable_count": len(telemetry["scrollables"]),
    }
    return telemetry


def _default_output_path(xml_path: Path) -> Path:
    return xml_path.with_suffix(".telemetry.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build navigation telemetry from an Android UI dump")
    parser.add_argument("--xml", help="Existing UI dump XML path")
    parser.add_argument("--observe", action="store_true", help="Capture a fresh screenshot and UI dump first")
    parser.add_argument("--name", default="navigation", help="Observation base name when --observe is used")
    parser.add_argument("--serial", default="", help="ADB serial to target when --observe is used")
    parser.add_argument("--adb-path", default="", help="Explicit adb path when --observe is used")
    parser.add_argument("--output", default="", help="Output telemetry JSON path")
    args = parser.parse_args()

    xml_path: Optional[Path] = Path(args.xml) if args.xml else None
    screenshot_path = ""
    status: Dict[str, Any] = {}
    source = "xml"

    if args.observe:
        hand = HydraAndroidHand(serial=args.serial, adb_path=args.adb_path)
        observed = hand.observe(name=args.name, include_ui_dump=True)
        xml_path = Path(observed["ui_dump"]["artifact_path"])
        screenshot_path = observed["screenshot"]["artifact_path"]
        status = observed.get("status", {})
        source = "observe"

    if not xml_path:
        raise SystemExit("--xml or --observe is required")

    payload = build_navigation_telemetry(
        xml_path,
        screenshot_path=screenshot_path,
        status=status,
        source=source,
    )
    output_path = Path(args.output) if args.output else _default_output_path(xml_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output_path), "route_url": payload["route_url"], "targets": payload["summary"]["tap_target_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
