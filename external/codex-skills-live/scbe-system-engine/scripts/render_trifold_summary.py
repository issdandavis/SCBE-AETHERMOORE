#!/usr/bin/env python
"""Render tri-fold SCBE action summary from JSON input."""

from __future__ import annotations

import json
import sys
from typing import Any


def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        print("Expected JSON input on stdin.", file=sys.stderr)
        return 2

    data: dict[str, Any] = json.loads(raw)
    build = data.get("build", {})
    document = data.get("document", {})
    route = data.get("route", {})

    print("action_summary:")
    print("  build:")
    print(f"    layers_touched: {json.dumps(build.get('layers_touched', []))}")
    print(f"    files_changed: {json.dumps(build.get('files_changed', []))}")
    print(f"    tests_added_or_run: {json.dumps(build.get('tests_added_or_run', []))}")
    print("  document:")
    print(f"    specs_or_cards_updated: {json.dumps(document.get('specs_or_cards_updated', []))}")
    print(f"    rationale: {json.dumps(document.get('rationale', ''))}")
    print("  route:")
    print(f"    services_to_update: {json.dumps(route.get('services_to_update', []))}")
    print(f"    pending_integrations: {json.dumps(route.get('pending_integrations', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
