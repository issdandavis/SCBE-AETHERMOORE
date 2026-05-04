"""
Acceptance gate for KDP manuscript uploads.

The gate is intentionally local and conservative. It does not decide whether a
book is "good art"; it checks that the upload packet has enough evidence for a
human author/publisher to make a defensible Kindle Direct Publishing submission.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_BOOK_ROOT = REPO / "content" / "book"
DEFAULT_STAGE_DIR = REPO / "artifacts" / "book" / "kdp"
DEFAULT_PACKET = DEFAULT_BOOK_ROOT / "kdp_submission_packet.json"

EXPECTED_AUTHOR = "Issac Daniel Davis"
MIN_WORDS = 20_000
MAX_WORDS = 250_000
PASS_SCORE = 85
AI_DISCLOSURE_VALUES = {"ai_generated", "ai_assisted", "human_created", "none"}


@dataclass
class Finding:
    gate_id: str
    status: str
    points: int
    max_points: int
    message: str
    evidence: dict[str, Any]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def markdown_sources(reader_dir: Path) -> list[Path]:
    if not reader_dir.exists():
        return []
    return sorted(
        p
        for p in reader_dir.glob("*.md")
        if p.name != "the-six-tongues-protocol-full.md" and not p.name.startswith(".")
    )


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def source_stats(reader_dir: Path) -> dict[str, Any]:
    files = markdown_sources(reader_dir)
    word_count = 0
    placeholder_hits: list[dict[str, str]] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        word_count += count_words(text)
        for line_no, line in enumerate(text.splitlines(), start=1):
            if re.search(r"\b(TODO|FIXME|TK|PLACEHOLDER|INSERT HERE)\b", line, re.IGNORECASE):
                placeholder_hits.append({"file": str(path), "line": str(line_no), "text": line.strip()[:160]})
                if len(placeholder_hits) >= 20:
                    break
    return {"files": files, "word_count": word_count, "placeholder_hits": placeholder_hits}


def gate_sources(book_root: Path) -> Finding:
    stats = source_stats(book_root / "reader-edition")
    file_count = len(stats["files"])
    word_count = stats["word_count"]
    placeholder_hits = stats["placeholder_hits"]
    ok = file_count >= 3 and MIN_WORDS <= word_count <= MAX_WORDS and not placeholder_hits
    points = 20 if ok else 0
    if file_count < 3:
        message = "reader-edition source files are missing or too sparse"
    elif word_count < MIN_WORDS:
        message = f"word count below publication floor: {word_count}"
    elif word_count > MAX_WORDS:
        message = f"word count above configured review ceiling: {word_count}"
    elif placeholder_hits:
        message = "source contains unresolved placeholder markers"
    else:
        message = "source manuscript is present, sized, and placeholder-clean"
    return Finding(
        "G1_source_manuscript",
        "PASS" if ok else "HOLD",
        points,
        20,
        message,
        {"source_file_count": file_count, "word_count": word_count, "placeholder_hits": placeholder_hits[:5]},
    )


def gate_artifacts(book_root: Path, manuscript: Path | None) -> Finding:
    docx = book_root / "the-six-tongues-protocol-kdp.docx"
    candidates = [p for p in [docx, manuscript] if p is not None]
    existing = [p for p in candidates if p.exists() and p.is_file() and p.stat().st_size > 10_000]
    ok = bool(existing)
    points = 15 if ok else 0
    evidence = {
        "artifacts": [
            {"path": str(p), "bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in existing
        ]
    }
    return Finding(
        "G2_upload_artifact",
        "PASS" if ok else "HOLD",
        points,
        15,
        "upload artifact exists and is large enough for review" if ok else "no reviewable DOCX/EPUB artifact found",
        evidence,
    )


def gate_identity(book_root: Path) -> Finding:
    checked = [book_root / "build_kdp.py", book_root / "HOUSE_STYLE.md", book_root / "INDEX.md"]
    missing = [str(p) for p in checked if not p.exists()]
    mismatches: list[str] = []
    for path in checked:
        if path.exists() and EXPECTED_AUTHOR not in path.read_text(encoding="utf-8", errors="replace"):
            mismatches.append(str(path))
    ok = not missing and not mismatches
    return Finding(
        "G3_identity_metadata",
        "PASS" if ok else "HOLD",
        15 if ok else 0,
        15,
        "title/author metadata uses the expected author name" if ok else "author metadata needs review",
        {"expected_author": EXPECTED_AUTHOR, "missing": missing, "mismatches": mismatches},
    )


def gate_ai_disclosure(packet_path: Path) -> Finding:
    if not packet_path.exists():
        return Finding(
            "G4_ai_disclosure",
            "HOLD",
            0,
            20,
            "KDP AI disclosure packet is missing",
            {"required_packet": str(packet_path)},
        )
    try:
        packet = read_json(packet_path)
    except Exception as exc:
        return Finding(
            "G4_ai_disclosure",
            "HOLD",
            0,
            20,
            f"KDP AI disclosure packet is not valid JSON: {exc}",
            {"packet": str(packet_path)},
        )
    disclosure = packet.get("ai_content_disclosure", {})
    required = ["text", "cover_images", "interior_images", "translations"]
    missing = [key for key in required if disclosure.get(key) not in AI_DISCLOSURE_VALUES]
    human_review = bool(packet.get("human_review", {}).get("approved_for_kdp_upload"))
    ok = not missing and human_review
    return Finding(
        "G4_ai_disclosure",
        "PASS" if ok else "HOLD",
        20 if ok else 0,
        20,
        "AI disclosure and human review decision are recorded"
        if ok
        else "AI disclosure and human review decision must be completed before upload",
        {
            "packet": str(packet_path),
            "missing_or_invalid_fields": missing,
            "human_review_approved": human_review,
            "disclosure": disclosure,
        },
    )


def gate_quality_docs(book_root: Path) -> Finding:
    required = [
        book_root / "HOUSE_STYLE.md",
        book_root / "KDP_PAPERBACK_FORMAT_SPEC.md",
        book_root / "FINAL_TOPOGRAPHY.md",
        book_root / "MARKET_COMP_ANALYSIS_2025_2026.md",
    ]
    missing = [str(p) for p in required if not p.exists()]
    ok = not missing
    return Finding(
        "G5_quality_context",
        "PASS" if ok else "HOLD",
        10 if ok else 0,
        10,
        "format, craft, and market review docs are present" if ok else "quality review context is incomplete",
        {"missing": missing, "required": [str(p) for p in required]},
    )


def gate_kdp_policy() -> Finding:
    policy_refs = [
        "https://kdp.amazon.com/en_US/help/topic/G200672390",
        "https://kdp.amazon.com/en_US/publish",
    ]
    return Finding(
        "G6_policy_refs",
        "PASS",
        5,
        5,
        "KDP policy references are attached for human review",
        {"policy_refs": policy_refs, "checked_at": datetime.now(timezone.utc).isoformat()},
    )


def gate_review_reports(stage_dir: Path) -> Finding:
    required = {
        "story_quality": stage_dir / "story-quality-gate.json",
        "visual_format": stage_dir / "visual-format-report.json",
    }
    missing = [str(p) for p in required.values() if not p.exists()]
    decisions: dict[str, str] = {}
    scores: dict[str, Any] = {}
    invalid: list[str] = []
    for name, path in required.items():
        if not path.exists():
            continue
        try:
            report = read_json(path)
        except Exception as exc:
            invalid.append(f"{path}: {exc}")
            continue
        decisions[name] = str(report.get("decision", ""))
        if "score" in report:
            scores[name] = report.get("score")
    ok = not missing and not invalid and all(v == "PASS" for v in decisions.values())
    return Finding(
        "G7_story_and_visual_reviews",
        "PASS" if ok else "HOLD",
        15 if ok else 0,
        15,
        "story-quality and visual-format reports passed"
        if ok
        else "story-quality and visual-format reports must pass before upload",
        {"missing": missing, "invalid": invalid, "decisions": decisions, "scores": scores},
    )


def run_gate(book_root: Path, packet_path: Path, manuscript: Path | None, stage_dir: Path) -> dict[str, Any]:
    findings = [
        gate_sources(book_root),
        gate_artifacts(book_root, manuscript),
        gate_identity(book_root),
        gate_ai_disclosure(packet_path),
        gate_quality_docs(book_root),
        gate_kdp_policy(),
        gate_review_reports(stage_dir),
    ]
    score = sum(f.points for f in findings)
    max_score = sum(f.max_points for f in findings)
    blockers = [f for f in findings if f.status != "PASS"]
    decision = "PASS" if score >= PASS_SCORE and not blockers else "HOLD"
    return {
        "schema_version": "scbe_kdp_acceptance_gate_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "score": score,
        "max_score": max_score,
        "pass_score": PASS_SCORE,
        "book_root": str(book_root),
        "packet_path": str(packet_path),
        "stage_dir": str(stage_dir),
        "findings": [asdict(f) for f in findings],
        "next_action": (
            "safe to continue to guided KDP upload; final Publish remains human-confirmed"
            if decision == "PASS"
            else "complete HOLD findings before upload"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the SCBE KDP acceptance gate.")
    parser.add_argument("--book-root", default=str(DEFAULT_BOOK_ROOT))
    parser.add_argument("--packet", default=str(DEFAULT_PACKET))
    parser.add_argument("--manuscript", default="")
    parser.add_argument("--stage-dir", default=str(DEFAULT_STAGE_DIR))
    parser.add_argument("--out", default=str(DEFAULT_STAGE_DIR / "acceptance-gate.json"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    book_root = Path(args.book_root).resolve()
    packet = Path(args.packet).resolve()
    manuscript = Path(args.manuscript).resolve() if args.manuscript else None
    stage_dir = Path(args.stage_dir).resolve()
    report = run_gate(book_root, packet, manuscript, stage_dir)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"[kdp-gate] decision={report['decision']} score={report['score']}/{report['max_score']}")
        print(f"[kdp-gate] report={out}")
        for finding in report["findings"]:
            print(f"  {finding['status']} {finding['gate_id']}: {finding['message']}")

    return 0 if report["decision"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
