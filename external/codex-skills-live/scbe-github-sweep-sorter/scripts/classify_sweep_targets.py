#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from pathlib import PurePosixPath


KEEP_ROOTS = {"src", "tests", "docs", "scripts", "schemas", "config", ".github", "api", "agents", "packages"}
ARCHIVE_ROOTS = {"artifacts", "training", "exports", "content"}
IGNORE_NAMES = {
    ".cache",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
    "build",
    ".playwright-mcp",
    ".playwright-cli",
}


def classify_path(path: str) -> str:
    pure = PurePosixPath(path.replace("\\", "/"))
    parts = pure.parts
    if not parts:
        return "manual-review"

    if any(part in IGNORE_NAMES for part in parts):
        return "ignore-or-cache"

    root = parts[0]
    if root in KEEP_ROOTS:
        return "keep-in-repo"
    if root in ARCHIVE_ROOTS:
        return "archive-or-cloud"
    if "security" in path.lower() or "auth" in path.lower():
        return "security-now"
    return "manual-review"


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify sweep targets into repo buckets.")
    parser.add_argument("paths", nargs="*", help="Paths to classify")
    parser.add_argument("--from-json", help="JSON file containing a list of paths or objects with a path field")
    args = parser.parse_args()

    items: list[str] = list(args.paths)
    if args.from_json:
        data = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    items.append(item)
                elif isinstance(item, dict) and "path" in item:
                    items.append(str(item["path"]))

    results = [{"path": path, "bucket": classify_path(path)} for path in items]
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
