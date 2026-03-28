"""Code Governance Gate — Real-time checks on every push, pull, and PR.

Owner (issdandavis) has full access. Everyone else earns trust.
No injection. No stolen code. Follow the rules and the law.

Usage:
    python scripts/security/code_governance_gate.py check-pr 752
    python scripts/security/code_governance_gate.py check-push
    python scripts/security/code_governance_gate.py check-diff HEAD~1
    python scripts/security/code_governance_gate.py audit
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent

# =========================================================================== #
#  Owner identity — the one person with CORE trust
# =========================================================================== #

OWNER = {
    "github": "issdandavis",
    "email": ["issdandavis@proton.me", "issdandavis7795@gmail.com",
              "aethermoregames@pm.me", "issdandavis@users.noreply.github.com"],
    "name": "Issac Daniel Davis",
}

# =========================================================================== #
#  Injection detection patterns (red team / blue team knowledge)
# =========================================================================== #

INJECTION_PATTERNS = [
    # Credential theft
    (re.compile(r"eval\s*\(\s*['\"].*(?:fetch|http|xhr|ajax)", re.I), "CODE_INJECTION", "CRITICAL",
     "Dynamic eval with network call — potential exfiltration"),
    (re.compile(r"subprocess\.(?:call|run|Popen)\s*\([^)]*shell\s*=\s*True", re.I), "SHELL_INJECTION", "HIGH",
     "Shell=True subprocess — command injection risk"),
    (re.compile(r"os\.system\s*\(", re.I), "SHELL_INJECTION", "HIGH",
     "os.system call — command injection risk"),

    # Backdoor patterns
    (re.compile(r"socket\.connect\s*\(\s*\(['\"](?!127\.0\.0\.1|localhost)", re.I), "BACKDOOR", "CRITICAL",
     "Outbound socket to external host — potential C2"),
    (re.compile(r"exec\s*\(\s*(?:base64|codecs)\.(?:b64decode|decode)", re.I), "OBFUSCATED_EXEC", "CRITICAL",
     "Executing base64-decoded content — obfuscated payload"),
    (re.compile(r"__import__\s*\(\s*['\"](?:ctypes|subprocess|socket|http)", re.I), "DYNAMIC_IMPORT", "HIGH",
     "Dynamic import of dangerous module"),

    # Exfiltration
    (re.compile(r"requests\.(?:post|put)\s*\(\s*['\"]https?://(?!(?:127\.0\.0\.1|localhost|api\.github\.com|huggingface\.co|api\.stripe\.com))", re.I),
     "EXFILTRATION", "MEDIUM", "HTTP POST to unknown external host"),
    (re.compile(r"webhook\s*=\s*['\"]https?://(?!(?:hooks\.slack\.com|discord\.com))", re.I), "EXFILTRATION", "MEDIUM",
     "Webhook to unknown host"),

    # Token/secret injection
    (re.compile(r"(?:password|secret|token|api_key)\s*=\s*['\"][^'\"]{8,}['\"]", re.I), "HARDCODED_SECRET", "HIGH",
     "Hardcoded secret in source code"),
    (re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"), "PRIVATE_KEY", "CRITICAL",
     "Private key in source code"),

    # Workflow poisoning
    (re.compile(r"actions/checkout@(?!v[34])", re.I), "UNSAFE_ACTION", "MEDIUM",
     "GitHub Action checkout not pinned to v3/v4"),
    (re.compile(r"\$\{\{\s*github\.event\.(?:issue|pull_request)\.(?:title|body)", re.I), "WORKFLOW_INJECTION", "HIGH",
     "Untrusted input in GitHub Actions expression"),

    # Dependency attacks
    (re.compile(r"pip install\s+(?!-r\s|-e\s).*--index-url\s+https?://(?!pypi\.org)", re.I), "SUPPLY_CHAIN", "HIGH",
     "pip install from non-PyPI index"),
    (re.compile(r"npm install\s+.*--registry\s+https?://(?!registry\.npmjs\.org)", re.I), "SUPPLY_CHAIN", "HIGH",
     "npm install from non-npmjs registry"),

    # File system attacks
    (re.compile(r"(?:chmod|chown)\s+(?:777|666|a\+rwx)", re.I), "PERM_ESCALATION", "HIGH",
     "World-writable permissions"),
    (re.compile(r"rm\s+-rf\s+/(?!\w)", re.I), "DESTRUCTIVE", "CRITICAL",
     "Recursive delete from root"),
]

# Files that should NEVER be modified by non-owner
PROTECTED_FILES = [
    ".github/workflows/ci.yml",
    ".github/workflows/scbe.yml",
    "SECURITY.md",
    "config/connector_oauth/.env.connector.oauth",
    "config/connector_oauth/.vault.sacred",
]

# File patterns that should never appear in a PR
FORBIDDEN_FILE_PATTERNS = [
    re.compile(r"\.env$"),
    re.compile(r"\.pem$"),
    re.compile(r"\.key$"),
    re.compile(r"id_rsa"),
    re.compile(r"credentials\.json$"),
    re.compile(r"\.vault\.sacred$"),
]


@dataclass
class Finding:
    """A single security finding."""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    category: str
    message: str
    file: str = ""
    line: int = 0
    evidence: str = ""


@dataclass
class GateResult:
    """Result of running the code governance gate."""
    decision: str  # PASS, WARN, BLOCK
    author_is_owner: bool
    findings: List[Finding] = field(default_factory=list)
    files_checked: int = 0
    lines_checked: int = 0

    def add(self, finding: Finding):
        self.findings.append(finding)

    @property
    def critical_count(self):
        return sum(1 for f in self.findings if f.severity == "CRITICAL")

    @property
    def high_count(self):
        return sum(1 for f in self.findings if f.severity == "HIGH")


def run_cmd(cmd: str) -> str:
    """Run a shell command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=str(ROOT))
    return result.stdout.strip()


def is_owner(author: str) -> bool:
    """Check if the author is the repo owner."""
    author_lower = author.lower().strip()
    if author_lower == OWNER["github"].lower():
        return True
    if any(author_lower == e.lower() for e in OWNER["email"]):
        return True
    if OWNER["name"].lower() in author_lower:
        return True
    return False


def check_diff(diff_text: str, result: GateResult):
    """Scan a diff for injection patterns."""
    current_file = ""
    line_num = 0

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            match = re.search(r"b/(.+)$", line)
            if match:
                current_file = match.group(1)
                line_num = 0
            continue

        if line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            if match:
                line_num = int(match.group(1))
            continue

        if not line.startswith("+") or line.startswith("+++"):
            if not line.startswith("-"):
                line_num += 1
            continue

        # This is an added line
        added_content = line[1:]  # strip the +
        result.lines_checked += 1

        for pattern, category, severity, message in INJECTION_PATTERNS:
            if pattern.search(added_content):
                result.add(Finding(
                    severity=severity,
                    category=category,
                    message=message,
                    file=current_file,
                    line=line_num,
                    evidence=added_content[:100].strip(),
                ))

        line_num += 1

    # Check for forbidden files
    files_in_diff = re.findall(r"diff --git a/.+ b/(.+)", diff_text)
    for f in files_in_diff:
        result.files_checked += 1
        for forbidden in FORBIDDEN_FILE_PATTERNS:
            if forbidden.search(f):
                result.add(Finding(
                    severity="CRITICAL",
                    category="FORBIDDEN_FILE",
                    message=f"Sensitive file type in diff: {f}",
                    file=f,
                ))

        # Protected files check (non-owner only)
        if not result.author_is_owner and f in PROTECTED_FILES:
            result.add(Finding(
                severity="HIGH",
                category="PROTECTED_FILE",
                message=f"Non-owner modifying protected file: {f}",
                file=f,
            ))


def decide(result: GateResult) -> str:
    """Make the governance decision."""
    if result.critical_count > 0 and not result.author_is_owner:
        return "BLOCK"
    if result.critical_count > 0 and result.author_is_owner:
        return "WARN"  # Owner gets warned, not blocked
    if result.high_count >= 3:
        return "BLOCK"
    if result.high_count > 0:
        return "WARN"
    return "PASS"


def check_pr(pr_number: int) -> GateResult:
    """Check a GitHub PR."""
    pr_json = run_cmd(f"gh pr view {pr_number} --json author,files,additions,deletions,headRefName,title")
    pr_data = json.loads(pr_json)
    author = pr_data.get("author", {}).get("login", "unknown")

    result = GateResult(decision="PASS", author_is_owner=is_owner(author))

    # Get the diff
    diff = run_cmd(f"gh pr diff {pr_number}")
    check_diff(diff, result)

    # Check author trust
    if not result.author_is_owner:
        result.add(Finding(
            severity="INFO",
            category="EXTERNAL_AUTHOR",
            message=f"PR by external contributor: {author}",
        ))

    result.decision = decide(result)
    return result, pr_data


def check_push_diff(ref: str = "HEAD~1") -> GateResult:
    """Check local diff before push."""
    author = run_cmd("git config user.email")
    result = GateResult(decision="PASS", author_is_owner=is_owner(author))

    diff = run_cmd(f"git diff {ref} HEAD")
    if not diff:
        diff = run_cmd("git diff --cached")
    if not diff:
        diff = run_cmd("git diff")

    check_diff(diff, result)
    result.decision = decide(result)
    return result


def print_result(result: GateResult, context: str = ""):
    """Print gate result."""
    symbols = {"PASS": "[PASS]", "WARN": "[WARN]", "BLOCK": "[BLOCK]"}
    _colors = {"PASS": "", "WARN": "", "BLOCK": ""}

    print(f"\nCODE GOVERNANCE GATE — {context}")
    print("=" * 60)
    print(f"  Decision: {symbols[result.decision]} {result.decision}")
    print(f"  Author is owner: {result.author_is_owner}")
    print(f"  Files checked: {result.files_checked}")
    print(f"  Lines checked: {result.lines_checked}")
    print(f"  Findings: {len(result.findings)} ({result.critical_count} critical, {result.high_count} high)")

    if result.findings:
        print(f"\n  Findings:")
        for f in sorted(result.findings, key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}[x.severity]):
            marker = {"CRITICAL": "!!!", "HIGH": "!!", "MEDIUM": "!", "LOW": ".", "INFO": "i"}[f.severity]
            print(f"    {marker} [{f.severity:8s}] {f.category}: {f.message}")
            if f.file:
                print(f"              {f.file}:{f.line}")
            if f.evidence:
                print(f"              > {f.evidence[:80]}")
    else:
        print(f"\n  No security findings. Clean.")

    print()


def main():
    parser = argparse.ArgumentParser(description="Code Governance Gate")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("check-pr", help="Check a GitHub PR")
    p.add_argument("number", type=int)

    _p2 = sub.add_parser("check-push", help="Check local changes before push")

    p3 = sub.add_parser("check-diff", help="Check diff against a ref")
    p3.add_argument("ref", default="HEAD~1", nargs="?")

    sub.add_parser("audit", help="Show recent gate decisions")

    args = parser.parse_args()

    if args.command == "check-pr":
        result, pr_data = check_pr(args.number)
        title = pr_data.get("title", "?")
        author = pr_data.get("author", {}).get("login", "?")
        print_result(result, f"PR #{args.number}: {title} (by {author})")

    elif args.command == "check-push":
        result = check_push_diff()
        print_result(result, "Pre-push check")

    elif args.command == "check-diff":
        result = check_push_diff(args.ref)
        print_result(result, f"Diff against {args.ref}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
