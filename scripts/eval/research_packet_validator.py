"""research_packet_validator: check a research note against the AetherMoore Research Packet Standard.

Turns docs/research/RESEARCH_PACKET_STANDARD.md from prose into a CI-checkable gate. A note claiming a
research GRADE must carry the required sections for that grade -- above all the CLAIM BOUNDARY (the
anti-overclaim section the whole repo's honesty discipline rests on) and the SOURCE LEDGER (provenance).
Composes with claim_evidence_crosswalk.py: that one checks a verified CLAIM backs evidence; this one checks
a research PACKET is structured to be trustworthy in the first place. Does NOT judge the science -- only
that the packet declares its grade, its limits, and its sources, so nothing gets sold as more than it is.

    python scripts/eval/research_packet_validator.py docs/research/SOME_NOTE.md --grade research_brief
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

GRADES = ["idea_seed", "research_brief", "research_packet", "validation_packet", "peer_review_candidate"]

# The 13 required sections (RESEARCH_PACKET_STANDARD), each matched by keyword(s) against the note's headings.
SECTION_KEYS = {
    "title": ["title"],
    "abstract": ["abstract", "summary", "thesis", "overview"],
    "raw_idea": ["raw idea", "idea", "thesis", "concept", "hypothesis"],
    "research_question": ["research question", "question"],
    "background": ["background", "why this is real", "related work", "relationship to research", "prior"],
    "source_ledger": ["source ledger", "sources", "citation", "references", "bibliography"],
    "mechanism": ["mechanism", "system model", "core model", "how this maps", "architecture", "design"],
    "validation_plan": ["validation", "bench", "benchmark", "experiment", "measurement", "evaluation"],
    "risks": ["risk", "failure mode", "safety", "harm", "limitation"],
    "claim_boundary": ["claim boundary", "claim", "do not claim", "honest limit", "scope"],
    "review_ledger": ["review ledger", "review", "red-team", "critique", "ten-pass", "adversarial"],
    "open_questions": ["open question", "unknown", "future", "next step"],
    "publication_status": ["publication status", "status", "grade"],
}

# Minimum sections per grade (idea seeds need little; research-grade needs the full structure).
GRADE_MIN = {
    "idea_seed": ["title", "raw_idea", "claim_boundary"],
    "research_brief": ["title", "abstract", "research_question", "source_ledger", "claim_boundary"],
    "research_packet": list(SECTION_KEYS),
    "validation_packet": list(SECTION_KEYS),
    "peer_review_candidate": list(SECTION_KEYS) + ["review_ledger"],
}


def _headings(text: str) -> List[str]:
    return [m.group(1).strip().lower() for m in re.finditer(r"^#{1,6}\s+(.+?)\s*$", text or "", re.M)]


def _present(section: str, headings: List[str], lowered_text: str) -> bool:
    if section == "title":
        return bool(headings)  # the note's first heading IS its title (the literal word isn't required)
    keys = SECTION_KEYS[section]
    if any(any(k in h for k in keys) for h in headings):
        return True
    # claim_boundary and source_ledger are load-bearing -> also accept a body mention, not only a heading
    if section in ("claim_boundary", "source_ledger"):
        return any(k in lowered_text for k in keys)
    return False


def validate(text: str, grade: Optional[str] = None) -> Dict[str, Any]:
    """Validate a note against the standard. `grade` is the grade it CLAIMS (default: research_brief). A note
    must carry the minimum sections for its grade, AND a claim boundary (required at every grade -- the
    anti-overclaim spine). Returns the structured report; ok=True iff it meets its grade + has a claim boundary."""
    grade = (grade or "research_brief").strip()
    headings = _headings(text)
    low = (text or "").lower()
    present = [s for s in SECTION_KEYS if _present(s, headings, low)]
    valid_grade = grade in GRADES
    needed = GRADE_MIN.get(grade, GRADE_MIN["research_brief"])
    missing_for_grade = [s for s in needed if s not in present]
    has_claim_boundary = "claim_boundary" in present
    has_source_ledger = "source_ledger" in present
    meets_grade = valid_grade and not missing_for_grade
    return {
        "claimed_grade": grade,
        "valid_grade": valid_grade,
        "sections_present": present,
        "sections_missing_for_grade": missing_for_grade,
        "all_13_missing": [s for s in SECTION_KEYS if s not in present],
        "has_claim_boundary": has_claim_boundary,
        "has_source_ledger": has_source_ledger,
        "meets_grade": meets_grade,
        "ok": meets_grade and has_claim_boundary,
    }


def render(path: str, r: Dict[str, Any]) -> str:
    mark = "OK  " if r["ok"] else "FAIL"
    lines = [
        "[%s] %s  (grade=%s, %d/13 sections)" % (mark, path, r["claimed_grade"], len(r["sections_present"])),
        "  claim boundary: %s   source ledger: %s" % (r["has_claim_boundary"], r["has_source_ledger"]),
    ]
    if r["sections_missing_for_grade"]:
        lines.append("  missing for this grade: %s" % ", ".join(r["sections_missing_for_grade"]))
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="research-packet-validator", description=__doc__.splitlines()[0])
    ap.add_argument("path", help="the research note (.md) to validate")
    ap.add_argument("--grade", default="research_brief", choices=GRADES)
    a = ap.parse_args(argv)
    text = Path(a.path).read_text(encoding="utf-8")
    r = validate(text, a.grade)
    print(render(a.path, r))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
