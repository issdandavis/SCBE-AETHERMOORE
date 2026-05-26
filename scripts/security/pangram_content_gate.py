#!/usr/bin/env python3
"""
Pangram Content Gate — External AI-authorship verification for SCBE publishing pipeline.

Uses Pangram Labs v3 API to scan text for AI-generated content before publication.
Designed as a reference-benchmark integration: SCBE's 14-layer pipeline makes the
ALLOW/DENY decision; Pangram provides an independent authorship signal.

Usage:
    python scripts/security/pangram_content_gate.py scan-file ./chapter01.md
    python scripts/security/pangram_content_gate.py scan-text "The quick brown fox..."
    python scripts/security/pangram_content_gate.py scan-dir ./docs/writing/ --max-files 10
    python scripts/security/pangram_content_gate.py verify-manuscript ./build/WATERSHED.epub
    cat article.md | python scripts/security/pangram_content_gate.py scan-stdin

Environment:
    PANGRAM_API_KEY — required for API access
    PANGRAM_MAX_FRACTION_AI — block threshold (default 0.30)
    PANGRAM_MAX_FRACTION_AI_ASSISTED — warn threshold (default 0.50)
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

# SCBE imports (best-effort)
try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent.parent

# =============================================================================
# CONFIGURATION
# =============================================================================

PANGRAM_API_URL = "https://text.api.pangram.com/v3"
PANGRAM_API_KEY_ENV = "PANGRAM_API_KEY"

# Tiered thresholds aligned with SCBE governance semantics
DEFAULT_BLOCK_THRESHOLD = 0.30   # fraction_ai > 0.30 → BLOCK (likely AI-generated)
DEFAULT_WARN_THRESHOLD = 0.50    # fraction_ai_assisted > 0.50 → WARN (heavy editing)
MIN_WORDS_FOR_SCAN = 50          # Pangram v3.2 minimum

# File extensions we care about for manuscript scanning
TEXT_EXTENSIONS = {".md", ".txt", ".rst", ".tex", ".html", ".xml"}
EPUB_EXTENSIONS = {".epub"}


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class PangramWindow:
    """A single window (segment) from Pangram's Adaptive Boundaries analysis."""
    start_index: int
    end_index: int
    label: str          # e.g. "AI", "Human", "AI-Assisted"
    confidence: str     # e.g. "High", "Medium", "Low"
    ai_assistance_score: float
    text_preview: str = ""


@dataclass
class PangramResult:
    """Normalized result from Pangram v3 API."""
    headline: str
    prediction_short: str
    fraction_ai: float
    fraction_ai_assisted: float
    fraction_human: float
    windows: List[PangramWindow] = field(default_factory=list)
    public_dashboard_link: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class GateFinding:
    """SCBE-style finding for content authenticity."""
    severity: str       # BLOCK, WARN, INFO
    category: str
    message: str
    file: str = ""
    fraction_ai: float = 0.0
    fraction_ai_assisted: float = 0.0
    windows: List[PangramWindow] = field(default_factory=list)


@dataclass
class ContentGateResult:
    """Aggregate result for a content scan."""
    decision: str = "PASS"       # PASS, WARN, BLOCK
    files_checked: int = 0
    words_checked: int = 0
    findings: List[GateFinding] = field(default_factory=list)
    api_calls_used: int = 0
    api_calls_remaining: Optional[int] = None

    def add(self, finding: GateFinding):
        self.findings.append(finding)

    @property
    def block_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "BLOCK")

    @property
    def warn_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "WARN")


# =============================================================================
# PANGRAM CLIENT
# =============================================================================

class PangramClient:
    """Minimal v3 API client. No external SDK dependency."""

    def __init__(self, api_key: Optional[str] = None):
        if requests is None:
            raise RuntimeError("requests is required. Install: pip install requests")
        self.api_key = api_key or os.environ.get(PANGRAM_API_KEY_ENV)
        if not self.api_key:
            raise RuntimeError(
                f"Pangram API key required. Set {PANGRAM_API_KEY_ENV} environment variable."
            )
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        })

    def scan(self, text: str, public_dashboard: bool = False) -> PangramResult:
        """Submit text to Pangram v3 and return normalized result."""
        if len(text.split()) < MIN_WORDS_FOR_SCAN:
            # Return a synthetic "human" result for short texts
            return PangramResult(
                headline="Text too short for analysis",
                prediction_short="Human",
                fraction_ai=0.0,
                fraction_ai_assisted=0.0,
                fraction_human=1.0,
            )

        payload: Dict[str, Any] = {"text": text}
        if public_dashboard:
            payload["public_dashboard_link"] = True

        resp = self.session.post(PANGRAM_API_URL, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        windows = []
        for w in data.get("windows", []):
            windows.append(PangramWindow(
                start_index=w.get("start_index", 0),
                end_index=w.get("end_index", 0),
                label=w.get("label", "Unknown"),
                confidence=w.get("confidence", "Unknown"),
                ai_assistance_score=w.get("ai_assistance_score", 0.0),
                text_preview=text[w.get("start_index", 0):w.get("end_index", 0)][:120],
            ))

        return PangramResult(
            headline=data.get("headline", "Unknown"),
            prediction_short=data.get("prediction_short", "Unknown"),
            fraction_ai=data.get("fraction_ai", 0.0),
            fraction_ai_assisted=data.get("fraction_ai_assisted", 0.0),
            fraction_human=data.get("fraction_human", 0.0),
            windows=windows,
            public_dashboard_link=data.get("public_dashboard_link"),
            raw_response=data,
        )


# =============================================================================
# GATE LOGIC
# =============================================================================

class PangramContentGate:
    """SCBE governance gate wrapping Pangram detection."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        block_threshold: float = DEFAULT_BLOCK_THRESHOLD,
        warn_threshold: float = DEFAULT_WARN_THRESHOLD,
        client: Optional[PangramClient] = None,
    ):
        self.client = client or PangramClient(api_key)
        self.block_threshold = block_threshold
        self.warn_threshold = warn_threshold

    def evaluate(self, pangram_result: PangramResult, source_file: str = "") -> GateFinding:
        """Map Pangram result to SCBE gate finding."""
        if pangram_result.fraction_ai > self.block_threshold:
            return GateFinding(
                severity="BLOCK",
                category="AI_Authorship",
                message=(
                    f"High AI fraction ({pangram_result.fraction_ai:.0%}) exceeds "
                    f"block threshold ({self.block_threshold:.0%}). "
                    f"Prediction: {pangram_result.headline}"
                ),
                file=source_file,
                fraction_ai=pangram_result.fraction_ai,
                fraction_ai_assisted=pangram_result.fraction_ai_assisted,
                windows=pangram_result.windows,
            )
        elif pangram_result.fraction_ai_assisted > self.warn_threshold:
            return GateFinding(
                severity="WARN",
                category="AI_Assistance",
                message=(
                    f"Elevated AI-assisted fraction ({pangram_result.fraction_ai_assisted:.0%}) "
                    f"exceeds warn threshold ({self.warn_threshold:.0%})."
                ),
                file=source_file,
                fraction_ai=pangram_result.fraction_ai,
                fraction_ai_assisted=pangram_result.fraction_ai_assisted,
                windows=pangram_result.windows,
            )
        else:
            return GateFinding(
                severity="INFO",
                category="Human_Authored",
                message=(
                    f"Pass. AI={pangram_result.fraction_ai:.0%}, "
                    f"Assisted={pangram_result.fraction_ai_assisted:.0%}, "
                    f"Human={pangram_result.fraction_human:.0%}"
                ),
                file=source_file,
                fraction_ai=pangram_result.fraction_ai,
                fraction_ai_assisted=pangram_result.fraction_ai_assisted,
                windows=pangram_result.windows,
            )

    def scan_text(self, text: str, source_file: str = "") -> ContentGateResult:
        """Scan a single text block."""
        result = ContentGateResult()
        result.files_checked = 1
        result.words_checked = len(text.split())

        try:
            pr = self.client.scan(text)
            result.api_calls_used += 1
        except Exception as exc:
            result.add(GateFinding(
                severity="WARN",
                category="API_ERROR",
                message=f"Pangram API failed: {exc}",
                file=source_file,
            ))
            result.decision = "WARN"
            return result

        finding = self.evaluate(pr, source_file)
        result.add(finding)
        result.decision = finding.severity if finding.severity in ("BLOCK", "WARN") else "PASS"
        return result

    def scan_file(self, file_path: Path) -> ContentGateResult:
        """Scan a single file."""
        text = file_path.read_text(encoding="utf-8")
        # Strip Markdown syntax for cleaner analysis
        text = _strip_markdown(text)
        return self.scan_text(text, source_file=str(file_path))

    def scan_directory(
        self, dir_path: Path, max_files: Optional[int] = None
    ) -> ContentGateResult:
        """Scan all text files in a directory."""
        result = ContentGateResult()
        files = [f for f in dir_path.rglob("*") if f.suffix.lower() in TEXT_EXTENSIONS]
        if max_files:
            files = files[:max_files]

        for fp in files:
            sub = self.scan_file(fp)
            result.files_checked += sub.files_checked
            result.words_checked += sub.words_checked
            result.api_calls_used += sub.api_calls_used
            result.findings.extend(sub.findings)

        # Aggregate decision
        if any(f.severity == "BLOCK" for f in result.findings):
            result.decision = "BLOCK"
        elif any(f.severity == "WARN" for f in result.findings):
            result.decision = "WARN"
        else:
            result.decision = "PASS"
        return result

    def verify_epub(self, epub_path: Path) -> ContentGateResult:
        """Extract text from EPUB and scan chapters individually."""
        result = ContentGateResult()
        with zipfile.ZipFile(epub_path, "r") as zf:
            html_files = [
                name for name in zf.namelist()
                if name.lower().endswith((".xhtml", ".html"))
            ]
            for name in sorted(html_files):
                text = _strip_html_tags(zf.read(name).decode("utf-8", errors="ignore"))
                if len(text.split()) < MIN_WORDS_FOR_SCAN:
                    continue
                sub = self.scan_text(text, source_file=Path(name).name)
                result.files_checked += sub.files_checked
                result.words_checked += sub.words_checked
                result.api_calls_used += sub.api_calls_used
                result.findings.extend(sub.findings)

        if any(f.severity == "BLOCK" for f in result.findings):
            result.decision = "BLOCK"
        elif any(f.severity == "WARN" for f in result.findings):
            result.decision = "WARN"
        else:
            result.decision = "PASS"
        return result


# =============================================================================
# UTILITIES
# =============================================================================

def _strip_markdown(text: str) -> str:
    """Remove common Markdown syntax for cleaner analysis."""
    # Headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    # Bold/italic
    text = re.sub(r"[*_]{1,2}", "", text)
    # Links
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Images
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)
    # Code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


def _strip_html_tags(text: str) -> str:
    """Remove HTML tags."""
    return html.unescape(re.sub(r"<[^>]+>", " ", text))


# =============================================================================
# CLI
# =============================================================================

def _print_result(result: ContentGateResult, json_mode: bool = False):
    if json_mode:
        print(json.dumps({
            "decision": result.decision,
            "files_checked": result.files_checked,
            "words_checked": result.words_checked,
            "api_calls_used": result.api_calls_used,
            "findings": [
                {
                    "severity": f.severity,
                    "category": f.category,
                    "message": f.message,
                    "file": f.file,
                    "fraction_ai": f.fraction_ai,
                    "fraction_ai_assisted": f.fraction_ai_assisted,
                    "window_count": len(f.windows),
                }
                for f in result.findings
            ],
        }, indent=2))
        return

    print(f"\n{'='*60}")
    print(f"PANGRAM CONTENT GATE RESULT: {result.decision}")
    print(f"{'='*60}")
    print(f"Files checked : {result.files_checked}")
    print(f"Words checked : {result.words_checked}")
    print(f"API calls used: {result.api_calls_used}")
    print(f"{'-'*60}")

    for f in result.findings:
        print(f"\n[{f.severity}] {f.category}")
        print(f"  File: {f.file or '(stdin)'}")
        print(f"  Msg : {f.message}")
        if f.windows:
            print(f"  Windows ({len(f.windows)}):")
            for w in f.windows[:3]:
                print(f"    [{w.label}/{w.confidence}] {w.text_preview[:80]}...")
            if len(f.windows) > 3:
                print(f"    ... and {len(f.windows) - 3} more")

    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Pangram Content Gate — AI authorship verification for SCBE",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable"
    )
    parser.add_argument(
        "--block-threshold", type=float, default=DEFAULT_BLOCK_THRESHOLD,
        help=f"Fraction AI that triggers BLOCK (default {DEFAULT_BLOCK_THRESHOLD})"
    )
    parser.add_argument(
        "--warn-threshold", type=float, default=DEFAULT_WARN_THRESHOLD,
        help=f"Fraction AI-assisted that triggers WARN (default {DEFAULT_WARN_THRESHOLD})"
    )
    parser.add_argument(
        "--allow-missing-key",
        action="store_true",
        help="Skip the gate with WARN instead of failing when PANGRAM_API_KEY is absent.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # scan-text
    p_text = sub.add_parser("scan-text", help="Scan raw text string")
    p_text.add_argument("text", help="Text to scan")

    # scan-file
    p_file = sub.add_parser("scan-file", help="Scan a single file")
    p_file.add_argument("path", type=Path, help="File path")

    # scan-stdin
    sub.add_parser("scan-stdin", help="Scan text from stdin")

    # scan-dir
    p_dir = sub.add_parser("scan-dir", help="Scan all text files in directory")
    p_dir.add_argument("path", type=Path, help="Directory path")
    p_dir.add_argument("--max-files", type=int, default=None)

    # verify-manuscript
    p_epub = sub.add_parser("verify-manuscript", help="Scan EPUB manuscript")
    p_epub.add_argument("path", type=Path, help="Path to .epub file")

    args = parser.parse_args()

    try:
        gate = PangramContentGate(
            block_threshold=args.block_threshold,
            warn_threshold=args.warn_threshold,
        )
    except RuntimeError as exc:
        if not args.allow_missing_key:
            raise
        result = ContentGateResult(decision="WARN")
        result.add(GateFinding(
            severity="WARN",
            category="CONFIG_MISSING",
            message=str(exc),
        ))
        _print_result(result, json_mode=args.json)
        sys.exit(0)

    if args.command == "scan-text":
        result = gate.scan_text(args.text)
    elif args.command == "scan-file":
        result = gate.scan_file(args.path)
    elif args.command == "scan-stdin":
        text = sys.stdin.read()
        result = gate.scan_text(text, source_file="(stdin)")
    elif args.command == "scan-dir":
        result = gate.scan_directory(args.path, max_files=args.max_files)
    elif args.command == "verify-manuscript":
        result = gate.verify_epub(args.path)
    else:
        parser.print_help()
        sys.exit(1)

    _print_result(result, json_mode=args.json)
    sys.exit(0 if result.decision == "PASS" else 1)


if __name__ == "__main__":
    main()
