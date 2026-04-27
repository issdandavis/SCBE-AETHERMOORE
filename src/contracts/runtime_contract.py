"""Shared runtime-packet contract for GeoSeal API and CLI surfaces."""

from __future__ import annotations

import hashlib
import re
from typing import Any


LANGUAGE_ROUTE = {
    "python": ("KO", "Python"),
    "py": ("KO", "Python"),
    "typescript": ("AV", "TypeScript"),
    "javascript": ("AV", "JavaScript"),
    "rust": ("RU", "Rust"),
    "c": ("CA", "C"),
    "julia": ("UM", "Julia"),
    "haskell": ("DR", "Haskell"),
}


def detect_command_key(content: str) -> str:
    """Infer the smallest supported operation key from source text."""
    text = content or ""
    fn_match = re.search(r"\b(?:def|function|fn)\s+([A-Za-z_][A-Za-z0-9_]*)", text)
    if fn_match:
        name = fn_match.group(1).lower()
        if "add" in name or "sum" in name:
            return "add"
        if "sub" in name:
            return "sub"
        if "mul" in name:
            return "mul"
        if "div" in name:
            return "div"
        if "even" in name:
            return "mod"
    if "+" in text:
        return "add"
    if "-" in text:
        return "sub"
    if "*" in text:
        return "mul"
    if "/" in text:
        return "div"
    return "identity"


def inspect_runtime_packet(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic runtime packet from source content."""
    language_raw = str(payload.get("language") or "python").lower()
    route_tongue, lane_language = LANGUAGE_ROUTE.get(language_raw, ("KO", language_raw.title()))
    content = str(payload.get("content") or "")
    source_name = str(payload.get("source_name") or "<memory>")
    command_key = detect_command_key(content)
    content_sha256 = hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()
    return {
        "schema_version": "geoseal-runtime-packet-v1",
        "source_name": source_name,
        "source_sha256": content_sha256,
        "lane_language": lane_language,
        "input_language": language_raw,
        "route_tongue": route_tongue,
        "route_language": lane_language,
        "command_key": command_key,
        "operative_command": f"arithmetic:{command_key}" if command_key != "identity" else "identity:pass",
        "key_slot": "A1" if command_key == "add" else "A0",
        "binary_input": "000000",
        "support_commands": ["sub", "mul", "div"] if command_key == "add" else [],
    }

