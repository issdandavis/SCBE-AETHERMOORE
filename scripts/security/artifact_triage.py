#!/usr/bin/env python3
"""Defensive artifact triage for unknown code or binary files.

This is the system-integration version of the reverse-engineering ladder:
start with strings, infer capabilities, assign risk, and emit a governance
receipt. It does not execute the artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA_VERSION = "scbe_artifact_triage_v1"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "security" / "artifact_triage"

SECRET_PATTERNS = [
    re.compile(r"hf_[A-Za-z0-9_=-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9_=-]{12,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_=-]{12,}"),
    re.compile(r"(?i)(token|secret|password|api[_-]?key)\s*[:=]\s*[^\s,;]+"),
]

INDICATOR_RULES: list[tuple[str, str, int, re.Pattern[str]]] = [
    ("dynamic_code_execution", "CRITICAL", 28, re.compile(r"\b(eval|exec)\s*\(|base64\.b64decode|Function\s*\(", re.I)),
    ("shell_execution", "HIGH", 20, re.compile(r"\b(os\.system|subprocess\.Popen|subprocess\.run|child_process|powershell|cmd\.exe)\b", re.I)),
    ("network_callback", "HIGH", 18, re.compile(r"https?://|socket\.connect|requests\.(post|put)|fetch\s*\(", re.I)),
    ("persistence_terms", "HIGH", 16, re.compile(r"\b(run key|startup|schtasks|launch agent|registry|crontab)\b", re.I)),
    ("credential_access_terms", "HIGH", 16, re.compile(r"\b(credentials?|keychain|browser cookies?|\.ssh|id_rsa|wallet)\b", re.I)),
    ("filesystem_modification", "MEDIUM", 10, re.compile(r"\b(rm\s+-rf|unlink|deletefile|remove-item|writefile|open\s*\(.+['\"]w)\b", re.I)),
    ("obfuscation_markers", "MEDIUM", 10, re.compile(r"\b(fromcharcode|atob|packed|upx|xor|rot13)\b", re.I)),
    ("debug_reverse_engineering_markers", "INFO", 2, re.compile(r"\b(strings|ghidra|ida|gdb|breakpoint|symbolic execution|angr)\b", re.I)),
]


@dataclass(frozen=True)
class IndicatorHit:
    rule_id: str
    severity: str
    weight: int
    evidence: str


@dataclass
class ArtifactReport:
    schema: str
    artifact_path: str
    artifact_sha256: str
    created_at_utc: str
    size_bytes: int
    file_kind: str
    printable_ratio: float
    entropy: float
    extracted_string_count: int
    sample_strings: list[str]
    traditional_controls: dict | None = None
    indicators: list[IndicatorHit] = field(default_factory=list)
    risk_score: int = 0
    decision: str = "ALLOW"
    recommended_next_steps: list[str] = field(default_factory=list)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def redact_text(value: str) -> str:
    out = value
    for pattern in SECRET_PATTERNS:
        out = pattern.sub("[REDACTED]", out)
    return out


def public_path(path: Path) -> str:
    raw = str(path.resolve())
    replacements = {
        str(REPO_ROOT): "%REPO%",
        str(Path.home()): "%USERPROFILE%",
    }
    out = raw
    for source, replacement in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        out = out.replace(source, replacement)
    return redact_text(out)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def byte_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = [0] * 256
    for byte in data:
        counts[byte] += 1
    total = len(data)
    entropy = 0.0
    for count in counts:
        if count:
            p = count / total
            entropy -= p * math.log2(p)
    return round(entropy, 4)


def extract_ascii_strings(data: bytes, min_length: int = 5, max_strings: int = 5000) -> list[str]:
    strings: list[str] = []
    current = bytearray()
    for byte in data:
        if 32 <= byte <= 126:
            current.append(byte)
            continue
        if len(current) >= min_length:
            strings.append(current.decode("ascii", errors="replace"))
            if len(strings) >= max_strings:
                return strings
        current.clear()
    if len(current) >= min_length and len(strings) < max_strings:
        strings.append(current.decode("ascii", errors="replace"))
    return [redact_text(item) for item in strings]


def printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    printable = sum(1 for byte in data if byte in (9, 10, 13) or 32 <= byte <= 126)
    return round(printable / len(data), 4)


def file_kind(path: Path, data: bytes) -> str:
    suffix = path.suffix.lower()
    if data.startswith(b"MZ"):
        return "pe_binary"
    if data.startswith(b"\x7fELF"):
        return "elf_binary"
    if data.startswith(b"PK\x03\x04"):
        return "zip_like"
    if suffix in {".py", ".js", ".ts", ".tsx", ".ps1", ".sh", ".yml", ".yaml", ".json", ".html"}:
        return "source_or_config"
    if printable_ratio(data) > 0.82:
        return "text_like"
    return "binary_or_blob"


def find_indicators(strings: Iterable[str]) -> list[IndicatorHit]:
    hits: list[IndicatorHit] = []
    seen: set[tuple[str, str]] = set()
    for text in strings:
        evidence = text.strip()
        if not evidence:
            continue
        for rule_id, severity, weight, pattern in INDICATOR_RULES:
            if not pattern.search(evidence):
                continue
            clipped = redact_text(evidence[:180])
            key = (rule_id, clipped)
            if key in seen:
                continue
            seen.add(key)
            hits.append(IndicatorHit(rule_id=rule_id, severity=severity, weight=weight, evidence=clipped))
    return hits


def run_traditional_controls(path: Path) -> dict | None:
    """Run local AV-style baseline controls without making this module hard to import."""
    script = REPO_ROOT / "scripts" / "security" / "traditional_security_layers.py"
    if not script.exists():
        return None
    spec = importlib.util.spec_from_file_location("_scbe_traditional_security_layers", script)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.report_to_dict(module.evaluate_artifact(path))


def decide(score: int, hits: list[IndicatorHit], kind: str) -> str:
    critical = any(hit.severity == "CRITICAL" for hit in hits)
    high_count = sum(1 for hit in hits if hit.severity == "HIGH")
    if critical or score >= 45:
        return "DENY"
    if high_count or score >= 18 or kind in {"pe_binary", "elf_binary", "zip_like"}:
        return "QUARANTINE"
    return "ALLOW"


def next_steps(decision: str, kind: str, hits: list[IndicatorHit]) -> list[str]:
    steps = [
        "Do not execute the artifact during triage.",
        "Preserve the SHA-256 receipt and extracted indicator list.",
    ]
    if decision in {"QUARANTINE", "DENY"}:
        steps.extend(
            [
                "Move the artifact to an isolated review folder or delete it if it is not required.",
                "If the file came from a PR or dependency, block merge until provenance and purpose are explained.",
                "Run deeper static analysis in a sandboxed toolchain before any dynamic analysis.",
            ]
        )
    if kind in {"pe_binary", "elf_binary", "zip_like"}:
        steps.append("Require explicit approval before unpacking or dynamic inspection.")
    if any(hit.rule_id == "network_callback" for hit in hits):
        steps.append("Identify every external host and verify whether it is expected by the product.")
    if any(hit.rule_id == "credential_access_terms" for hit in hits):
        steps.append("Check whether the artifact attempts credential discovery or embeds secret-looking material.")
    return steps


def merge_decision(current: str, candidate: str) -> str:
    rank = {"ALLOW": 0, "QUARANTINE": 1, "DENY": 2}
    return candidate if rank.get(candidate, 0) > rank.get(current, 0) else current


def triage_artifact(path: Path, max_bytes: int = 5_000_000) -> ArtifactReport:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)
    raw = path.read_bytes()
    scanned = raw[:max_bytes]
    strings = extract_ascii_strings(scanned)
    kind = file_kind(path, scanned)
    hits = find_indicators(strings)
    traditional = run_traditional_controls(path)
    if traditional:
        for control in traditional.get("controls", []):
            weight = int(control.get("weight", 0))
            if weight <= 0:
                continue
            hits.append(
                IndicatorHit(
                    rule_id=f"traditional_{control.get('control', 'unknown')}",
                    severity=str(control.get("severity", "INFO")),
                    weight=weight,
                    evidence=str(control.get("message", ""))[:180],
                )
            )
    score = sum(hit.weight for hit in hits)
    decision = decide(score, hits, kind)
    if traditional:
        decision = merge_decision(decision, str(traditional.get("decision", "ALLOW")))
    return ArtifactReport(
        schema=SCHEMA_VERSION,
        artifact_path=public_path(path),
        artifact_sha256=sha256_file(path),
        created_at_utc=now_utc(),
        size_bytes=path.stat().st_size,
        file_kind=kind,
        printable_ratio=printable_ratio(scanned),
        entropy=byte_entropy(scanned),
        extracted_string_count=len(strings),
        sample_strings=strings[:25],
        traditional_controls=traditional,
        indicators=hits[:100],
        risk_score=score,
        decision=decision,
        recommended_next_steps=next_steps(decision, kind, hits),
    )


def report_to_dict(report: ArtifactReport) -> dict:
    return {
        "schema": report.schema,
        "artifact_path": report.artifact_path,
        "artifact_sha256": report.artifact_sha256,
        "created_at_utc": report.created_at_utc,
        "size_bytes": report.size_bytes,
        "file_kind": report.file_kind,
        "printable_ratio": report.printable_ratio,
        "entropy": report.entropy,
        "extracted_string_count": report.extracted_string_count,
        "sample_strings": report.sample_strings,
        "traditional_controls": report.traditional_controls,
        "indicators": [hit.__dict__ for hit in report.indicators],
        "risk_score": report.risk_score,
        "decision": report.decision,
        "recommended_next_steps": report.recommended_next_steps,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="File to inspect without executing it")
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = triage_artifact(args.artifact)
    payload = report_to_dict(report)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{report.artifact_sha256[:16]}.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            f"[artifact-triage] {report.decision} score={report.risk_score} "
            f"kind={report.file_kind} indicators={len(report.indicators)} report={public_path(out_path)}"
        )
    return 2 if report.decision == "DENY" else 1 if report.decision == "QUARANTINE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
