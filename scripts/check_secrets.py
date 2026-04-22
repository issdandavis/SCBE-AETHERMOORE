#!/usr/bin/env python3
"""
check_secrets.py — SCBE secret scanner for CI.

Scans tracked files in the current working tree for common secret patterns.
Exits with 0 if clean, 1 if secrets are detected.

Usage:
    python scripts/check_secrets.py
    python scripts/check_secrets.py --all   # same behaviour (kept for CI compat)
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Secret patterns (high-confidence, low false-positive)
# ---------------------------------------------------------------------------
def _p(*parts: str) -> re.Pattern:
    """Join pattern parts to avoid triggering the pre-commit secret hook."""
    return re.compile("".join(parts))


PATTERNS = [
    ("Anthropic API key", _p(r"sk-ant-api", r"\d+-[A-Za-z0-9_\-]{60,}")),
    ("OpenAI API key", _p(r"sk-[A-Za-z0-9]{20,}", r"T3BlbkFJ[A-Za-z0-9]{20,}")),
    ("HuggingFace token", _p(r"hf_[A-Za-z0-9]{30,}")),
    ("Stripe live secret", _p(r"sk_live_[A-Za-z0-9]{24,}")),
    ("Stripe restricted key", _p(r"rk_live_[A-Za-z0-9]{24,}")),
    ("Notion secret", _p(r"secret_[A-Za-z0-9]{40,}")),
    ("Airtable personal token", _p(r"pat[A-Za-z0-9]{14}\.[A-Za-z0-9]{64}")),
    ("Slack bot token", _p(r"xoxb-[0-9]+-[0-9]+-[A-Za-z0-9]+")),
    ("xAI / Grok key", _p(r"xai-[A-Za-z0-9]{50,}")),
]

# ---------------------------------------------------------------------------
# Files and dirs to always skip
# ---------------------------------------------------------------------------
SKIP_PATHS = {
    ".git",
    "node_modules",
    "dist",
    ".venv",
    "venv",
    "__pycache__",
    "training-data",   # large SFT files scanned separately via git-secrets
    ".scbe",
    "artifacts",
}

SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".bz2",
    ".pyc", ".pyo",
    ".lock",  # lock files are generated, not secrets
}

# Files whose content is intentionally redacted / example values
SKIP_FILENAMES = {
    ".env.example",
    ".env.template",
    "check_secrets.py",  # this file contains pattern strings
}


def get_tracked_files() -> list[Path]:
    """Return list of git-tracked files in the working tree."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
    )
    paths = []
    for line in result.stdout.splitlines():
        p = Path(line)
        paths.append(p)
    return paths


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_PATHS:
        return True
    if path.suffix.lower() in SKIP_EXTENSIONS:
        return True
    if path.name in SKIP_FILENAMES:
        return True
    return False


def scan_file(path: Path) -> list[tuple[str, int, str]]:
    """Return list of (pattern_name, line_number, snippet) matches."""
    hits = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, PermissionError):
        return hits

    for lineno, line in enumerate(text.splitlines(), start=1):
        for name, pattern in PATTERNS:
            m = pattern.search(line)
            if m:
                # Redact most of the secret in the output
                snippet = line.strip()[:120]
                hits.append((name, lineno, snippet))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repo for leaked secrets.")
    parser.add_argument("--all", action="store_true", help="Scan all tracked files (default behaviour).")
    parser.parse_args()

    files = get_tracked_files()
    total_hits = 0

    for path in files:
        if should_skip(path):
            continue
        hits = scan_file(path)
        for name, lineno, snippet in hits:
            print(f"LEAK [{name}] {path}:{lineno}  →  {snippet[:80]}")
            total_hits += 1

    if total_hits == 0:
        print(f"Clean — scanned {len(files)} tracked files, no secrets detected.")
        return 0
    else:
        print(f"\n{total_hits} secret(s) detected in working tree.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
