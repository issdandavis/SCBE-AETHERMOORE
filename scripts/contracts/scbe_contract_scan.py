#!/usr/bin/env python3
"""SCONE-class static prefilter for Solidity smart contracts.

Honest scope: this is a regex/heuristic static scanner for the four
vulnerability classes called out in the Anthropic Red SCONE-bench paper
(red.anthropic.com/2025/smart-contracts/). It is NOT an AI-driven audit
and will miss any vulnerability that requires multi-function reasoning,
data-flow analysis, or symbolic execution — including the cross-function
zero-days that frontier models found in SCONE-bench.

Use this as a fast pre-filter before paying for AI-driven audit, not as
a replacement for one. Once the user has an Anthropic External Researcher
Access credit (or hosted dispatch is unlocked), the same surface can be
backed by a governance-gated Claude call producing a stronger receipt.

Vulnerability classes checked (each yields its own finding type):
  1. missing_view_or_pure_modifier        — read-only-intent fn lacks `view`/`pure`
  2. missing_access_control_on_financial  — `*transfer*`/`*withdraw*`/`*fee*`/`*payout*` fns lacking msg.sender / owner / auth gate
  3. unvalidated_critical_address         — address param assigned to storage without `require(addr != address(0))`
  4. payable_without_value_check          — `payable` fn that never references `msg.value`

Receipt schema: scbe.contract_scan.v1
  - SCBE_CONTRACT_SCAN_PASS=1 if zero findings
  - SCBE_CONTRACT_SCAN_PASS=0 otherwise, with findings list
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

SCHEMA_VERSION = "scbe.contract_scan.v1"

# Severity tiers map onto the SCBE L13 governance tiers.
SEVERITY_TO_TIER = {
    "high": "DENY",
    "medium": "ESCALATE",
    "low": "QUARANTINE",
}


@dataclass
class Finding:
    rule: str
    severity: str  # "high" | "medium" | "low"
    line: int
    function: Optional[str]
    detail: str

    def tier(self) -> str:
        return SEVERITY_TO_TIER.get(self.severity, "ESCALATE")


@dataclass
class ScanResult:
    schema_version: str
    receipt: str  # "SCBE_CONTRACT_SCAN_PASS=1" | "SCBE_CONTRACT_SCAN_PASS=0"
    file_path: str
    file_sha256: str
    line_count: int
    function_count: int
    findings: List[Finding] = field(default_factory=list)
    rules_run: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.findings

    def to_dict(self) -> dict:
        d = asdict(self)
        d["findings"] = [asdict(f) for f in self.findings]
        for f in d["findings"]:
            f["tier"] = SEVERITY_TO_TIER.get(f["severity"], "ESCALATE")
        return d


# ---------------------------------------------------------------------------
# Function discovery — minimal regex parser, NOT a full Solidity grammar.
# ---------------------------------------------------------------------------

FUNCTION_PATTERN = re.compile(
    r"""
    \bfunction\s+
    (?P<name>[A-Za-z_][A-Za-z0-9_]*)
    \s*\(
    (?P<params>[^)]*)
    \)
    (?P<modifiers>[^{;]*)
    (?P<body_or_semi>[{;])
    """,
    re.VERBOSE,
)

RETURN_RE = re.compile(r"\breturn(?:s)?\b")
STATE_MUTATING_RE = re.compile(
    r"\b(?:emit|require|revert)\b"  # not strictly state-mutating but indicators
    r"|"
    r"=\s*(?!=)",  # assignment (=, not ==)
)
EVENT_EMIT_RE = re.compile(r"\bemit\s+[A-Za-z_]")


@dataclass
class FunctionSpan:
    name: str
    line: int
    params: str
    modifiers: str
    body: str


def find_functions(source: str) -> List[FunctionSpan]:
    """Find each Solidity function with its (best-effort) body span."""
    out: List[FunctionSpan] = []
    for m in FUNCTION_PATTERN.finditer(source):
        line = source.count("\n", 0, m.start()) + 1
        body = ""
        if m.group("body_or_semi") == "{":
            # Brace-balance from the opening brace to extract the body.
            start = m.end() - 1  # position of the '{'
            depth = 0
            end = start
            for i in range(start, len(source)):
                ch = source[i]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            body = source[start:end]
        out.append(
            FunctionSpan(
                name=m.group("name"),
                line=line,
                params=m.group("params").strip(),
                modifiers=m.group("modifiers").strip(),
                body=body,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Rule 1: missing view/pure modifier on read-only-intent function.
#
# Heuristic: function has a `returns(...)` clause, has no `=` assignment in
# its body, no `emit`, no `.call{...}` / `.transfer(...)` / `.send(...)`,
# AND no `view`/`pure`/`constant` modifier. That looks like an intended
# read-only function whose missing modifier permits state mutation.
# ---------------------------------------------------------------------------

WRITE_INDICATORS_RE = re.compile(
    r"\.call\s*\{|\.transfer\s*\(|\.send\s*\(|\+\+|--|\bdelete\s+|\bpush\s*\(|\bpop\s*\("
)


def rule_missing_view_or_pure(fn: FunctionSpan, source_lines: List[str]) -> List[Finding]:
    out: List[Finding] = []
    if not RETURN_RE.search(fn.modifiers):
        return out
    if re.search(r"\b(?:view|pure|constant)\b", fn.modifiers):
        return out
    body = fn.body
    if "{" not in body or "}" not in body:
        return out
    # Strip comments before scanning for state ops.
    body_stripped = re.sub(r"//[^\n]*", "", body)
    body_stripped = re.sub(r"/\*.*?\*/", "", body_stripped, flags=re.DOTALL)
    assigns = re.search(r"(?<![=!<>])=(?!=)", body_stripped)
    emits = EVENT_EMIT_RE.search(body_stripped)
    writes = WRITE_INDICATORS_RE.search(body_stripped)
    if not (assigns or emits or writes):
        out.append(
            Finding(
                rule="missing_view_or_pure_modifier",
                severity="medium",
                line=fn.line,
                function=fn.name,
                detail=(
                    f"function {fn.name!r} returns a value, performs no detectable "
                    "state mutation, but lacks 'view'/'pure'/'constant'. SCONE-bench "
                    "vulnerability #1 — a caller can invoke this function in a "
                    "state-mutating context to inflate balances or bypass "
                    "intended read-only semantics."
                ),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Rule 2: missing access control on financial-impact functions.
# ---------------------------------------------------------------------------

FINANCIAL_NAME_RE = re.compile(
    r"(?i)(transfer|withdraw|fee|payout|claim|distribute|mint|burn|sweep|drain)"
)
ACCESS_CONTROL_RE = re.compile(
    r"\bmsg\.sender\b|\bonlyOwner\b|\bonlyRole\b|\b_checkOwner\b|"
    r"\brequire\s*\(\s*(?:owner|admin|authorized|whitelisted)\b"
    r"|\bauth(?:orized)?\b|\bgovernanceOnly\b|\bonlyGovernance\b"
)
EXTERNAL_OR_PUBLIC_RE = re.compile(r"\b(?:external|public)\b")


def rule_missing_access_control(fn: FunctionSpan, source_lines: List[str]) -> List[Finding]:
    out: List[Finding] = []
    if not FINANCIAL_NAME_RE.search(fn.name):
        return out
    if not EXTERNAL_OR_PUBLIC_RE.search(fn.modifiers):
        return out
    if re.search(r"\b(?:view|pure|constant)\b", fn.modifiers):
        return out
    if ACCESS_CONTROL_RE.search(fn.modifiers) or ACCESS_CONTROL_RE.search(fn.body):
        return out
    out.append(
        Finding(
            rule="missing_access_control_on_financial",
            severity="high",
            line=fn.line,
            function=fn.name,
            detail=(
                f"public/external function {fn.name!r} appears financial "
                "(transfer/withdraw/fee/payout/mint/burn/claim) but does not "
                "reference msg.sender, onlyOwner, onlyRole, or any "
                "require-based authorization. SCONE-bench vulnerability #2 — "
                "an arbitrary caller can extract or redirect funds."
            ),
        )
    )
    return out


# ---------------------------------------------------------------------------
# Rule 3: address parameter assigned to storage without zero-address validation.
# ---------------------------------------------------------------------------

ADDRESS_PARAM_RE = re.compile(r"\baddress(?:\s+payable)?\s+([A-Za-z_][A-Za-z0-9_]*)")


def rule_unvalidated_address(fn: FunctionSpan, source_lines: List[str]) -> List[Finding]:
    out: List[Finding] = []
    if "{" not in fn.body:
        return out
    for m in ADDRESS_PARAM_RE.finditer(fn.params):
        param = m.group(1)
        assign_re = re.compile(rf"\b[A-Za-z_][A-Za-z0-9_]*\s*=\s*{re.escape(param)}\b")
        if not assign_re.search(fn.body):
            continue
        # Look for a require(...) referencing the param near the assignment.
        guard_re = re.compile(
            rf"\brequire\s*\([^)]*\b{re.escape(param)}\b[^)]*!=[^)]*address\s*\(\s*0\s*\)",
            re.DOTALL,
        )
        if guard_re.search(fn.body):
            continue
        # Also accept the inverse `address(0) != param` form.
        guard_re_2 = re.compile(
            rf"\brequire\s*\([^)]*address\s*\(\s*0\s*\)[^)]*!=[^)]*\b{re.escape(param)}\b",
            re.DOTALL,
        )
        if guard_re_2.search(fn.body):
            continue
        out.append(
            Finding(
                rule="unvalidated_critical_address",
                severity="medium",
                line=fn.line,
                function=fn.name,
                detail=(
                    f"function {fn.name!r} assigns the address parameter "
                    f"{param!r} to storage without a 'require({param} != address(0))' "
                    "guard. SCONE-bench vulnerability class #4 — zero-address "
                    "writes brick the contract or hand control to an unrecoverable "
                    "default address."
                ),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Rule 4: payable function with no msg.value reference.
# ---------------------------------------------------------------------------


def rule_payable_without_value_check(
    fn: FunctionSpan, source_lines: List[str]
) -> List[Finding]:
    out: List[Finding] = []
    if not re.search(r"\bpayable\b", fn.modifiers):
        return out
    if "{" not in fn.body:
        return out
    if re.search(r"\bmsg\.value\b", fn.body):
        return out
    # Skip the fallback `receive() external payable` and `fallback()` which
    # are payable by language convention and may legitimately ignore msg.value.
    if fn.name in ("receive", "fallback"):
        return out
    out.append(
        Finding(
            rule="payable_without_value_check",
            severity="low",
            line=fn.line,
            function=fn.name,
            detail=(
                f"payable function {fn.name!r} never references msg.value. "
                "A caller may send ETH that the contract accepts but does not "
                "validate or attribute, enabling silent value misrouting."
            ),
        )
    )
    return out


RULES = [
    ("missing_view_or_pure_modifier", rule_missing_view_or_pure),
    ("missing_access_control_on_financial", rule_missing_access_control),
    ("unvalidated_critical_address", rule_unvalidated_address),
    ("payable_without_value_check", rule_payable_without_value_check),
]


def scan_source(source: str, file_path: str) -> ScanResult:
    """Run every SCONE-class rule against a single Solidity source."""
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    lines = source.splitlines()
    functions = find_functions(source)
    findings: List[Finding] = []
    for _, rule_fn in RULES:
        for fn in functions:
            findings.extend(rule_fn(fn, lines))
    receipt = "SCBE_CONTRACT_SCAN_PASS=1" if not findings else "SCBE_CONTRACT_SCAN_PASS=0"
    return ScanResult(
        schema_version=SCHEMA_VERSION,
        receipt=receipt,
        file_path=file_path,
        file_sha256=digest,
        line_count=len(lines),
        function_count=len(functions),
        findings=findings,
        rules_run=[name for name, _ in RULES],
        notes=[
            "Static heuristic prefilter — does NOT replace AI-driven audit.",
            "Cross-function and data-flow exploits will be missed (see SCONE-bench paper).",
        ],
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scbe-contract-scan",
        description=(
            "SCONE-class static prefilter for Solidity smart contracts. "
            "Honest about scope: regex/heuristic, not an AI-driven audit."
        ),
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="path to a .sol file (or omit and pipe source to stdin)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON receipt")
    parser.add_argument(
        "--fail-on-finding",
        action="store_true",
        help="exit code 1 if any finding present (default: always exit 0)",
    )
    args = parser.parse_args(argv)

    if args.path:
        try:
            source = Path(args.path).read_text(encoding="utf-8")
            file_path = str(Path(args.path).resolve())
        except FileNotFoundError:
            sys.stderr.write(f"scbe contract scan: file not found: {args.path}\n")
            return 2
    else:
        source = sys.stdin.read()
        file_path = "<stdin>"

    result = scan_source(source, file_path)
    payload = result.to_dict()

    if args.json:
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    else:
        sys.stdout.write(f"SCBE contract scan: {result.receipt}\n")
        sys.stdout.write(f"File:     {result.file_path}\n")
        sys.stdout.write(f"SHA-256:  {result.file_sha256}\n")
        sys.stdout.write(
            f"Lines:    {result.line_count}    Functions: {result.function_count}\n"
        )
        if not result.findings:
            sys.stdout.write("No SCONE-class findings.\n")
        else:
            sys.stdout.write(f"Findings ({len(result.findings)}):\n")
            for f in result.findings:
                sys.stdout.write(
                    f"  [{f.severity.upper()} -> {SEVERITY_TO_TIER.get(f.severity)}] "
                    f"line {f.line} fn={f.function} rule={f.rule}\n"
                )
                sys.stdout.write(f"      {f.detail}\n")
        sys.stdout.write("\nNotes:\n")
        for n in result.notes:
            sys.stdout.write(f"  - {n}\n")

    if args.fail_on_finding and result.findings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
