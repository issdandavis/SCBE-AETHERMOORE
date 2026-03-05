from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_GLOBS = ("**/*.md", "**/*.txt")
DEFAULT_EXCLUDES = {
    ".git",
    "node_modules",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    "artifacts",
}


def iter_note_files(root: Path, globs: Iterable[str]) -> Iterable[Path]:
    seen: set[Path] = set()
    for pattern in globs:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            if any(part in DEFAULT_EXCLUDES for part in path.parts):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield path


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory local notes for GitHub promotion.")
    parser.add_argument("--root", default=".", help="Root directory to scan.")
    parser.add_argument("--out", default="artifacts/notes_manifest.json", help="Output JSON path.")
    parser.add_argument("--max", type=int, default=5000, help="Maximum files to emit.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for idx, path in enumerate(iter_note_files(root, DEFAULT_GLOBS)):
        if idx >= args.max:
            break
        stat = path.stat()
        rows.append(
            {
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "bytes": stat.st_size,
                "modified_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

    rows.sort(key=lambda x: (x["path"]))
    payload = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "root": str(root),
        "total": len(rows),
        "files": rows,
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} entries to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
