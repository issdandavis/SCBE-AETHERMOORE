#!/usr/bin/env python3
"""Pre-commit secret scanner — blocks commits containing API keys.

Run manually:  python scripts/check_secrets.py
Auto-run:      Set up as git pre-commit hook (see below)

Setup as pre-commit hook:
    cp scripts/check_secrets.py .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
"""

import re
import subprocess
import sys

PATTERNS = [
    (r"sk-ant-api\S{10,}", "Anthropic API key"),
    (r"sk-proj-\S{10,}", "OpenAI API key"),
    (r"ghp_[A-Za-z0-9]{30,}", "GitHub PAT"),
    (r"gho_[A-Za-z0-9]{30,}", "GitHub OAuth"),
    (r"AKIA[A-Z0-9]{16}", "AWS Access Key"),
    (r"(?:sk|rk)_live_[A-Za-z0-9_-]{20,}", "Stripe live key"),
    (r"(?:sk|rk)_test_[A-Za-z0-9_-]{20,}", "Stripe test key"),
    (r"hf_[A-Za-z0-9]{30,}", "HuggingFace token"),
    (r"KGAT_[A-Za-z0-9]{20,}", "Kaggle token"),
    (r"xai-[A-Za-z0-9]{20,}", "xAI API key"),
    (r"SAM-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "SAM.gov API key"),
    (r"glpat-[A-Za-z0-9_-]{20,}", "GitLab PAT"),
    (r"eyJ[A-Za-z0-9_-]{50,}\.[A-Za-z0-9_-]{50,}", "JWT token"),
]

def check_staged_files():
    """Check all staged files for secrets."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True
    )
    files = [f.strip() for f in result.stdout.splitlines() if f.strip()]

    found = []
    for filepath in files:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            for pattern, name in PATTERNS:
                matches = re.findall(pattern, content)
                for m in matches:
                    if "[SCRUBBED" not in m:
                        found.append((filepath, name, m[:20] + "..."))
        except FileNotFoundError:
            pass

    return found


def check_all_files():
    """Check entire repo for secrets (manual scan mode)."""
    import os
    found = []
    skip_dirs = {"node_modules", ".git", "dist", "__pycache__", ".venv"}
    check_exts = {".py", ".ts", ".js", ".json", ".jsonl", ".md", ".html", ".yaml", ".yml", ".txt", ".env"}

    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in check_exts:
                continue
            path = os.path.join(root, f)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                for pattern, name in PATTERNS:
                    matches = re.findall(pattern, content)
                    for m in matches:
                        if "[SCRUBBED" not in m:
                            found.append((path, name, m[:20] + "..."))
            except:
                pass

    return found


if __name__ == "__main__":
    # Default: check staged files (pre-commit hook mode)
    # Pass --all for full repo scan (manual mode)
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        print("Scanning entire repo for secrets...")
        found = check_all_files()
    else:
        found = check_staged_files()

    if found:
        print(f"\n{'='*60}")
        print(f"BLOCKED: {len(found)} SECRET(S) DETECTED")
        print(f"{'='*60}")
        for path, name, preview in found:
            print(f"  [{name}] {path}: {preview}")
        print(f"\nReplace secrets with [SCRUBBED:type] before committing.")
        print(f"{'='*60}")
        sys.exit(1)
    else:
        print("No secrets found. Safe to commit.")
        sys.exit(0)
