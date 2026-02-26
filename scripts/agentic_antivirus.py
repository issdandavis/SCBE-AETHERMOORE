#!/usr/bin/env python3
"""Agentic antivirus and GeoSeal-style corpus immune helper for repository triage."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


IGNORE_DIRS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "node_modules",
    "artifacts",
    "dist",
    "build",
    "coverage",
    "__pycache__",
}

SIGNATURES = {
    "hardcoded_api_key": {
        "pattern": r"(?i)(api[_-]?key|api[_-]?token|secret[_-]?key|private[_-]?key)\s*[:=]\s*[\"']?[A-Za-z0-9+/=._-]{20,}[\"']?",
        "severity": "high",
        "phase": "UM",
    },
    "aws_secret": {
        "pattern": r"AKIA[0-9A-Z]{16}",
        "severity": "critical",
        "phase": "UM",
    },
    "password_in_source": {
        "pattern": r"(?i)password\s*[:=]\s*[\"'][^\"']{8,}[\"']",
        "severity": "medium",
        "phase": "RU",
    },
    "command_injection_risk": {
        "pattern": r"\b(exec|eval|subprocess\.Popen|os\.system)\s*\(",
        "severity": "high",
        "phase": "CA",
    },
    "insecure_http": {
        "pattern": r"http://[^\s'\"]+",
        "severity": "low",
        "phase": "AV",
    },
    "open_redirect_risk": {
        "pattern": r"\b(location\.href|window\.location|redirect)\s*[:=]",
        "severity": "medium",
        "phase": "DR",
    },
    "unsafe_shell_pattern": {
        "pattern": r"\b(rm\s+-rf|del\s+/|sudo\s+)|\bchmod\s+777\b",
        "severity": "high",
        "phase": "DR",
    },
}

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
PHASE_TOLERANCE = {"KO": 0.0, "AV": 60 / 57, "RU": 120 / 57, "CA": 180 / 57, "UM": 240 / 57, "DR": 300 / 57}


@dataclass
class Finding:
    path: str
    line_no: int
    signature: str
    severity: str
    snippet: str
    phase: str
    confidence: float


@dataclass
class ChunkState:
    chunk_id: str
    path: str
    line_no: int
    risk_score: float
    trust_score: float
    ring: str
    phase: str
    findings: List[Finding] = field(default_factory=list)
    quarantine: bool = False


def _is_text_file(path: Path) -> bool:
    try:
        data = path.read_bytes()
        data.decode("utf-8")
        return True
    except Exception:
        return False


def _scan_file(path: Path) -> List[Finding]:
    if not _is_text_file(path):
        return []

    findings: List[Finding] = []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for idx, line in enumerate(lines, start=1):
        for sig_name, cfg in SIGNATURES.items():
            match = re.search(cfg["pattern"], line)
            if not match:
                continue
            findings.append(
                Finding(
                    path=str(path),
                    line_no=idx,
                    signature=sig_name,
                    severity=cfg["severity"],
                    snippet=line.strip()[:240],
                    phase=cfg.get("phase", "KO"),
                    confidence=0.84,
                )
            )
    return findings


def _scan_tree(root: Path) -> List[Finding]:
    patterns = {".py", ".ts", ".js", ".tsx", ".json", ".yml", ".yaml", ".md", ".ini", ".env", ".sh", ".ps1"}
    findings: List[Finding] = []
    for entry in root.rglob("*"):
        if not entry.is_file():
            continue

        parts = set(entry.parts)
        if any(part in IGNORE_DIRS for part in parts):
            continue

        if entry.suffix.lower() not in patterns and entry.name not in {".env", "env.example"}:
            continue

        findings.extend(_scan_file(entry))

    return findings


def _severity_weight(severity: str) -> float:
    return {"critical": 1.0, "high": 0.85, "medium": 0.6, "low": 0.35}.get(severity, 0.2)


def _phase_to_tone_index(phase: str) -> float:
    return PHASE_TOLERANCE.get(phase, 0.0)


def _chunk_id(path: Path, line_no: int) -> str:
    return f"{path}:{line_no}"


def _build_chunk_map(findings: List[Finding], ring_core: float, ring_outer: float) -> Tuple[List[ChunkState], Dict[str, Any]]:
    by_path = {}
    for finding in findings:
        by_path.setdefault(finding.path, []).append(finding)

    chunks: List[ChunkState] = []
    quarantine_chunks: List[str] = []
    ring_counts = {k: 0 for k in ["core", "outer", "blocked"]}
    phase_counts = {k: 0 for k in TONGUES}

    for path, file_findings in by_path.items():
        for finding in file_findings:
            phase_counts[finding.phase] = phase_counts.get(finding.phase, 0) + 1

    # Build line-level chunk scores and assign trust rings.
    for finding in findings:
        key = _chunk_id(Path(finding.path), finding.line_no)
        chunk_index = next(
            (idx for idx, chunk in enumerate(chunks) if chunk.chunk_id == key),
            None,
        )

        if chunk_index is None:
            chunk = ChunkState(
                chunk_id=key,
                path=finding.path,
                line_no=finding.line_no,
                risk_score=0.0,
                trust_score=1.0,
                ring="core",
                phase=finding.phase,
                findings=[],
                quarantine=False,
            )
            chunks.append(chunk)
            chunk_index = len(chunks) - 1

        chunks[chunk_index].findings.append(finding)

    # Score chunks, assign phase trust rings, apply quarantine pressure.
    for chunk in chunks:
        score = 0.0
        high_confidence_count = 0
        for f in chunk.findings:
            score += _severity_weight(f.severity) * f.confidence
            if f.severity in {"critical", "high"}:
                high_confidence_count += 1

        # Add phase divergence pressure.
        phase_delta = abs(_phase_to_tone_index(chunk.phase) - _phase_to_tone_index("KO")) / 60.0
        score += phase_delta * 0.6

        # Add local neighbor pressure from file density.
        file_count = max(1, len([item for item in chunks if item.path == chunk.path]))
        neighbor_pressure = min(1.0, (file_count - 1) * 0.12)
        score += neighbor_pressure

        score = min(1.0, score / 3.0)
        chunk.risk_score = round(score, 4)
        chunk.trust_score = round(1.0 - chunk.risk_score, 4)
        if chunk.trust_score >= ring_core:
            chunk.ring = "core"
        elif chunk.trust_score >= ring_outer:
            chunk.ring = "outer"
        else:
            chunk.ring = "blocked"

        chunk.quarantine = len(chunk.findings) >= 3 and high_confidence_count >= 1
        if chunk.quarantine:
            quarantine_chunks.append(chunk.chunk_id)
            chunk.risk_score = min(1.0, chunk.risk_score + 0.1)
            chunk.trust_score = max(0.0, 1.0 - chunk.risk_score)
            chunk.ring = "blocked"

        ring_counts[chunk.ring] = ring_counts.get(chunk.ring, 0) + 1

    # Push weakly isolated file-level quarantine if a file has repeated high-risk findings.
    for path, file_findings in by_path.items():
        critical = sum(1 for f in file_findings if f.severity == "critical")
        if len(file_findings) >= 4 and critical >= 1:
            for chunk in chunks:
                if chunk.path == path and not chunk.quarantine:
                    chunk.quarantine = True
                    chunk.ring = "blocked"
                    chunk.risk_score = min(1.0, chunk.risk_score + 0.15)
                    chunk.trust_score = max(0.0, 1.0 - chunk.risk_score)

    # rebuild ring counts after file-level quarantine corrections
    ring_counts = {k: 0 for k in ["core", "outer", "blocked"]}
    for chunk in chunks:
        ring_counts[chunk.ring] = ring_counts.get(chunk.ring, 0) + 1

    geoseal_metrics = {
        "total_chunks": len(chunks),
        "quarantine_count": sum(1 for c in chunks if c.quarantine),
        "ring_distribution": ring_counts,
        "phase_distribution": phase_counts,
        "file_finding_distribution": {k: len(v) for k, v in sorted(by_path.items())},
    }
    return chunks, geoseal_metrics


def _risk_summary(findings: List[Finding], target_rules: List[str], chunks: List[ChunkState]) -> Dict[str, Any]:
    counts = {k: 0 for k in ["critical", "high", "medium", "low"]}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1

    score = 0.0
    for finding in findings:
        score += _severity_weight(finding.severity) * finding.confidence

    max_score = max(1.0, len(findings))
    normalized = min(1.0, score / max_score)
    if normalized >= 0.80:
        risk = "high"
    elif normalized >= 0.50:
        risk = "medium"
    else:
        risk = "low"

    risk_by_ring = {
        "core": sum(1 for chunk in chunks if chunk.ring == "core"),
        "outer": sum(1 for chunk in chunks if chunk.ring == "outer"),
        "blocked": sum(1 for chunk in chunks if chunk.ring == "blocked"),
    }
    if risk_by_ring["blocked"] > 0:
        risk = "high"
    elif risk_by_ring["outer"] > 0 and normalized > 0.45:
        risk = "medium"

    return {
        "risk_level": risk,
        "risk_score": round(normalized, 4),
        "severity_counts": counts,
        "target_rules": target_rules,
        "signature_coverage": sorted({f.signature for f in findings}),
    }


def _make_task_summary(
    report_path: Path,
    summary: Dict[str, Any],
    findings: List[Finding],
    chunks: List[ChunkState],
    top_rules: List[str],
) -> str:
    lines = [
        "# Agentic Antivirus / GeoSeal Triage Report",
        f"Generated: {summary['generated_at']}",
        f"Repo: {summary['repo_root']}",
        f"Risk: {summary['risk_level'].upper()} (score {summary['risk_score']})",
        f"Findings: {summary['total_findings']}",
        "",
        "## Severity Counts",
    ]
    for level, count in summary["severity_counts"].items():
        lines.append(f"- {level}: {count}")

    geoseal = summary.get("geoseal")
    if geoseal:
        lines.extend(
            [
                "",
                "## GeoSeal Ringing Summary",
                f"- Total chunks assessed: {geoseal['total_chunks']}",
                f"- Quarantine count: {geoseal['quarantine_count']}",
                f"- Core rings: {geoseal['ring_distribution']['core']}",
                f"- Outer rings: {geoseal['ring_distribution']['outer']}",
                f"- Blocked rings: {geoseal['ring_distribution']['blocked']}",
                "- Top phase tags:",
            ]
        )
        for phase, count in sorted(geoseal.get("phase_distribution", {}).items()):
            lines.append(f"  - {phase}: {count}")

    lines.extend(["", "## Top Findings", ""])
    for finding in findings[:40]:
        lines.append(f"- {finding.severity.upper()} [{finding.signature}] {finding.path}:{finding.line_no}")
        lines.append(f"  - phase={finding.phase}, confidence={finding.confidence}")
        lines.append(f"  - {finding.snippet}")

    if not findings:
        lines.append("No matching threats found.")

    lines.extend(["", "## Quarantine Candidates"])
    quarantine_chunks = [chunk for chunk in chunks if chunk.quarantine]
    if not quarantine_chunks:
        lines.append("No quarantine candidates.")
    else:
        for chunk in sorted(quarantine_chunks, key=lambda c: (-len(c.findings), c.risk_score), reverse=False)[:40]:
            lines.append(
                f"- {chunk.chunk_id} | ring={chunk.ring} risk={chunk.risk_score} trust={chunk.trust_score} phase={chunk.phase}"
            )

    lines.extend(["", "## Recommended Actions"])
    for rule in top_rules:
        lines.append(f"- {rule}")
    if geoseal:
        lines.extend(
            [
                "- Remove or isolate all blocked chunks and rerun GeoSeal quarantine.",
                "- Move quarantined files to review lanes and reduce execution permissions until fixed.",
            ]
        )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return str(report_path)


def run_antivirus_scan(root: Path, with_geoseal: bool, ring_core: float, ring_outer: float) -> Tuple[List[Finding], Dict[str, Any], List[ChunkState]]:
    findings = _scan_tree(root)
    chunks = []
    geoseal: Optional[Dict[str, Any]] = None
    if with_geoseal:
        chunks, geoseal = _build_chunk_map(findings, ring_core=ring_core, ring_outer=ring_outer)
    return findings, geoseal or {}, chunks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a lightweight static + GeoSeal-style antivirus pass")
    parser.add_argument("--repo-root", default="C:/Users/issda/SCBE-AETHERMOORE-working")
    parser.add_argument("--output", default="artifacts/agentic_antivirus_report.json")
    parser.add_argument("--summary", default="artifacts/agentic_antivirus_report.md")
    parser.add_argument("--geoseal", action="store_true", help="Enable GeoSeal trust-lattice scoring")
    parser.add_argument("--ring-core", type=float, default=0.70, help="Trust threshold for CORE ring")
    parser.add_argument("--ring-outer", type=float, default=0.45, help="Trust threshold for OUTER ring")
    parser.add_argument("--run-id", default=None, help="Optional tag for runbook/traceability")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.repo_root).resolve()
    ring_core = max(0.0, min(1.0, args.ring_core))
    ring_outer = max(0.0, min(1.0, args.ring_outer))

    findings, geoseal, chunks = run_antivirus_scan(root, args.geoseal, ring_core=ring_core, ring_outer=ring_outer)
    findings_payload = [
        {
            "path": f.path,
            "line_no": f.line_no,
            "signature": f.signature,
            "severity": f.severity,
            "phase": f.phase,
            "snippet": f.snippet,
            "confidence": f.confidence,
        }
        for f in findings
    ]

    chunks_payload = [
        {
            "chunk_id": chunk.chunk_id,
            "path": chunk.path,
            "line_no": chunk.line_no,
            "risk_score": chunk.risk_score,
            "trust_score": chunk.trust_score,
            "ring": chunk.ring,
            "phase": chunk.phase,
            "quarantine": chunk.quarantine,
            "findings": [f.signature for f in chunk.findings],
        }
        for chunk in chunks
    ]

    summary = _risk_summary(findings, sorted({f.signature for f in findings}), chunks)
    summary.update(
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "repo_root": str(root),
            "total_findings": len(findings),
            "run_id": args.run_id or secrets.token_hex(4),
            "engine": "heuristic+geoseal" if args.geoseal else "heuristic",
            "ring_thresholds": {"core": ring_core, "outer": ring_outer},
            "geoseal": {
                "enabled": bool(args.geoseal),
                "total_chunks": geoseal.get("total_chunks", 0),
                "quarantine_count": geoseal.get("quarantine_count", 0),
                "ring_distribution": geoseal.get("ring_distribution", {}),
                "phase_distribution": geoseal.get("phase_distribution", {}),
                "file_finding_distribution": geoseal.get("file_finding_distribution", {}),
            },
        }
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_payload = {
        "summary": summary,
        "findings": findings_payload,
        "chunks": chunks_payload,
    }
    output_path.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")

    markdown_path = Path(args.summary)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    _make_task_summary(markdown_path, summary, findings, chunks, sorted(summary["signature_coverage"]))

    report_text = json.loads(output_path.read_text(encoding="utf-8"))
    print("Antivirus report written to:", output_path)
    print("Antivirus summary written to:", markdown_path)
    print("Total findings:", len(findings))
    print("Risk level:", report_text["summary"]["risk_level"])
    if args.geoseal:
        geoseal_summary = report_text["summary"]["geoseal"]
        print(
            "GeoSeal chunks:",
            f"core={geoseal_summary['ring_distribution'].get('core', 0)}",
            f"outer={geoseal_summary['ring_distribution'].get('outer', 0)}",
            f"blocked={geoseal_summary['ring_distribution'].get('blocked', 0)}",
        )
        print("Quarantine chunks:", geoseal_summary["quarantine_count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
