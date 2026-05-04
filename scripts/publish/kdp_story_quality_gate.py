"""
Story-quality gate for AI-assisted or AI-generated KDP submissions.

This gate is deliberately about reader value and author portfolio quality, not
whether AI was involved. AI disclosure belongs to KDP compliance; this file asks
whether the book itself is coherent enough to publish.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_PACKET = REPO / "content" / "book" / "story_quality_packet.json"
DEFAULT_OUT = REPO / "artifacts" / "book" / "kdp" / "story-quality-gate.json"
DEFAULT_MD = REPO / "artifacts" / "book" / "kdp" / "story-quality-gate.md"

WEIGHTS = {
    "whole_story_coherence": 1.35,
    "character_continuity": 1.15,
    "plot_causality": 1.20,
    "prose_readability": 1.00,
    "originality_and_reader_value": 1.10,
    "portfolio_fit": 0.90,
    "production_readiness": 0.80,
}


def load_packet(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"story quality packet missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def score_packet(packet: dict[str, Any]) -> dict[str, Any]:
    dimensions = packet.get("dimensions", {})
    findings: list[dict[str, Any]] = []
    weighted_total = 0.0
    weight_total = 0.0
    blockers: list[str] = []

    for name, weight in WEIGHTS.items():
        rec = dimensions.get(name)
        if not isinstance(rec, dict):
            blockers.append(f"missing dimension: {name}")
            findings.append({"dimension": name, "status": "HOLD", "score": None, "weight": weight, "message": "missing"})
            continue
        raw_score = rec.get("score")
        evidence_refs = rec.get("evidence_refs") or []
        if not isinstance(raw_score, (int, float)) or not (1 <= float(raw_score) <= 10):
            blockers.append(f"invalid score for {name}")
            findings.append({"dimension": name, "status": "HOLD", "score": raw_score, "weight": weight, "message": "score must be 1-10"})
            continue
        if not evidence_refs:
            blockers.append(f"missing evidence for {name}")
        score = float(raw_score)
        weighted_total += score * weight
        weight_total += weight
        findings.append(
            {
                "dimension": name,
                "status": "PASS" if score >= 7 and evidence_refs else "HOLD",
                "score": score,
                "weight": weight,
                "weighted_points": round(score * weight, 3),
                "evidence_refs": evidence_refs,
                "note": rec.get("note", ""),
            }
        )

    score_100 = round((weighted_total / weight_total) * 10, 2) if weight_total else 0.0
    min_publishable = int(packet.get("minimum_publishable_score", 75))
    min_portfolio = int(packet.get("minimum_portfolio_score", 85))

    if blockers:
        decision = "HOLD"
        tier = "incomplete_review"
    elif score_100 >= min_portfolio:
        decision = "PASS"
        tier = "portfolio_ready"
    elif score_100 >= min_publishable:
        decision = "PASS"
        tier = "publishable_with_review"
    elif score_100 >= 60:
        decision = "HOLD"
        tier = "draft_needs_revision"
    else:
        decision = "HOLD"
        tier = "do_not_publish_quality_risk"

    return {
        "schema_version": "scbe_kdp_story_quality_gate_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "title": packet.get("title", ""),
        "author": packet.get("author", ""),
        "decision": decision,
        "quality_tier": tier,
        "score": score_100,
        "minimum_publishable_score": min_publishable,
        "minimum_portfolio_score": min_portfolio,
        "blockers": blockers,
        "findings": findings,
        "next_action": (
            "continue to formatting and KDP acceptance gates"
            if decision == "PASS"
            else "revise weak dimensions or complete missing review evidence"
        ),
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# KDP Story Quality Gate",
        "",
        f"- Decision: **{report['decision']}**",
        f"- Tier: `{report['quality_tier']}`",
        f"- Score: `{report['score']}`",
        f"- Title: {report['title']}",
        f"- Author: {report['author']}",
        "",
        "## Findings",
        "",
    ]
    for finding in report["findings"]:
        lines.append(
            f"- {finding['status']} `{finding['dimension']}` score={finding['score']} "
            f"weight={finding['weight']} :: {finding.get('note', '')}"
        )
    if report["blockers"]:
        lines.extend(["", "## Blockers", ""])
        for blocker in report["blockers"]:
            lines.append(f"- {blocker}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the KDP story quality gate.")
    parser.add_argument("--packet", default=str(DEFAULT_PACKET))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--markdown", default=str(DEFAULT_MD))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    packet = load_packet(Path(args.packet))
    report = score_packet(packet)
    out = Path(args.out)
    md = Path(args.markdown)
    out.parent.mkdir(parents=True, exist_ok=True)
    md.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, md)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"[kdp-story] decision={report['decision']} tier={report['quality_tier']} score={report['score']}")
        print(f"[kdp-story] json={out}")
        print(f"[kdp-story] markdown={md}")
    return 0 if report["decision"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
