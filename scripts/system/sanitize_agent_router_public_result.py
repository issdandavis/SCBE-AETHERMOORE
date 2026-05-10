#!/usr/bin/env python3
"""Sanitize agent-router result envelopes before publishing them to Pages.

The full CI artifact can keep stderr/stdout tails for debugging. The public
`docs/static/agent-data/latest-*.json` feed should not carry environment
warnings, auth configuration details, or credential-shaped strings.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SENSITIVE_TEXT_RE = re.compile(
    r"\b("
    r"api[_-]?key|api[_-]?keys|token|secret|password|credential|bearer|authorization|"
    r"SCBE_API_KEYS|HF_TOKEN|GITHUB_TOKEN|GMAIL_APP_PASS|PROTONMAIL_BRIDGE_PASSWORD"
    r")\b",
    re.IGNORECASE,
)

TAIL_KEYS = {"stderr_tail", "stdout_tail", "stderr", "stdout", "logs", "log_tail"}
REDACTED_TAIL = "[redacted from public agent-data feed; see private workflow artifact]"


def _sanitize_value(key: str | None, value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _sanitize_value(str(k), v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(key, item) for item in value]
    if isinstance(value, str):
        if key in TAIL_KEYS and SENSITIVE_TEXT_RE.search(value):
            return REDACTED_TAIL
        if key and SENSITIVE_TEXT_RE.search(key):
            return REDACTED_TAIL
    return value


def sanitize_result(data: dict[str, Any]) -> dict[str, Any]:
    """Return a public-safe copy of an agent-router result object."""

    sanitized = _sanitize_value(None, data)
    if not isinstance(sanitized, dict):
        raise TypeError("agent-router result must be a JSON object")
    sanitized["public_sanitized"] = True
    return sanitized


def main() -> int:
    parser = argparse.ArgumentParser(description="Sanitize agent-router JSON before public Pages publishing")
    parser.add_argument("--input", required=True, help="Input JSON file")
    parser.add_argument("--output", required=True, help="Output JSON file")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    sanitized = sanitize_result(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(sanitized, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
