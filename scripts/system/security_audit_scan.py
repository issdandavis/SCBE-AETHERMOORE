#!/usr/bin/env python3
"""Quick security audit: scan repo for potential secret exposure."""

import json
import os
import re

PATTERNS = {
    "api_key": re.compile(r"[aA][pP][iI][_\-]?[kK][eE][yY][\s]*[=:]+[\s]*[\"\']?[a-zA-Z0-9_\-]{20,}"),
    "secret": re.compile(r"[sS][eE][cC][rR][eE][tT][\s]*[=:]+[\s]*[\"\']?[a-zA-Z0-9_\-]{16,}"),
    "token": re.compile(r"[tT][oO][kK][eE][nN][\s]*[=:]+[\s]*[\"\']?[a-zA-Z0-9_\-]{20,}"),
    "password": re.compile(r"[pP][aA][sS][sS][wW][oO][rR][dD][\s]*[=:]+[\s]*[\"\']?[^\s\"\']{8,}"),
    "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "stripe_key": re.compile(r"sk_(live|test)_[0-9a-zA-Z]{24,}"),
    "hf_token": re.compile(r"hf_[a-zA-Z0-9]{34,}"),
    "github_pat": re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    "gemini_key": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    "private_key": re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
}

EXCLUDE = {
    ".git", "node_modules", "__pycache__", ".pytest_cache",
    ".tmp-build", "artifacts/build-tmp", "artifacts/pytest_temp_root", "dist",
}
EXCLUDE_EXTS = {
    ".pyc", ".jpg", ".png", ".gif", ".ico", ".woff", ".woff2",
    ".ttf", ".eot", ".mp3", ".mp4", ".pdf", ".zip", ".tar", ".gz",
}


def main():
    findings = []
    files_scanned = 0

    scan_roots = ["src", "python", "api", "scripts", "config", "deploy", "docker", "tests", ".github", "docs"]
    for scan_root in scan_roots:
        if not os.path.isdir(scan_root):
            continue
        for root, dirs, files in os.walk(scan_root):
            dirs[:] = [d for d in dirs if d not in EXCLUDE and not d.startswith(".tmp")]
            for fname in files:
                if any(fname.endswith(ext) for ext in EXCLUDE_EXTS):
                    continue
                path = os.path.join(root, fname)
                # Skip files >1MB
                try:
                    if os.path.getsize(path) > 1_000_000:
                        continue
                except OSError:
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue
                files_scanned += 1
                for pattern_name, pattern in PATTERNS.items():
                    for match in pattern.finditer(content):
                        line_num = content[:match.start()].count("\n") + 1
                        snippet = content[max(0, match.start() - 20):min(len(content), match.end() + 20)]
                        findings.append({
                            "file": path,
                            "line": line_num,
                            "pattern": pattern_name,
                            "snippet": snippet.replace("\n", " ")[:80],
                        })

    # Deduplicate
    seen = set()
    unique = []
    for f in findings:
        key = (f["file"], f["line"], f["pattern"])
        if key not in seen:
            seen.add(key)
            unique.append(f)

    report = {
        "files_scanned": files_scanned,
        "findings_count": len(unique),
        "findings": unique,
        "note": "Review findings manually—many are likely false positives in example code, comments, or test fixtures.",
    }

    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/security_audit_2026-05-03.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"Files scanned: {files_scanned}")
    print(f"Potential findings: {len(unique)}")
    for f in unique[:20]:
        print(f"  {f['file']} line {f['line']} - {f['pattern']}: {f['snippet'][:60]}")


if __name__ == "__main__":
    main()
