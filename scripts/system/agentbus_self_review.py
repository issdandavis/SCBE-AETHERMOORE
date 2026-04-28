#!/usr/bin/env python3
"""
Propose-only self-review for the public agent bus.

Reads `docs/static/agent-data/index.json` and `latest-*.json`, scores them
against five concrete defect categories, and writes a structured suggestion
artifact to `artifacts/agent_bus/self_review_<timestamp>.json`
(schema: scbe-agentbus-self-review-v1).

Caller decides which suggestions to promote into agent-router.yml — this
script never edits the bus or the workflow.

Categories:
    1. confidence_variance      (HIGH)  — research findings share a single confidence value
    2. sources_vs_findings_ratio (MEDIUM)— findings_count / sources_checked < 0.7 AND
                                          `source_outcomes` does not document every source
    3. silent_error             (HIGH)  — ratio < 0.7 AND errors:[] AND
                                          `source_outcomes` is missing or incomplete
    4. title_sanity             (LOW/MEDIUM)
        a. title_equals_description (LOW)    — both fields collapsed to the same value
        b. extraction_partial       (MEDIUM) — word_count > 200 but headings=[] and description empty
    5. freshness                (HIGH/MEDIUM) — index.json `updated` older than 12h

Exit code 0 if no HIGH-severity findings, 1 otherwise.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "scbe-agentbus-self-review-v1"
DEFAULT_DATA_DIR = Path("docs/static/agent-data")
DEFAULT_OUTPUT_DIR = Path("artifacts/agent_bus")

FRESHNESS_SOFT_HOURS = 12.0
FRESHNESS_HARD_HOURS = 24.0
RATIO_FLOOR = 0.7
EXTRACTION_WORD_FLOOR = 200


@dataclass
class Finding:
    category: str
    severity: str  # "high" | "medium" | "low"
    observation: str
    suggestion: str
    evidence: Dict[str, Any] = field(default_factory=dict)


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def check_confidence_variance(research: Optional[Dict[str, Any]]) -> List[Finding]:
    if not research:
        return []
    findings = research.get("findings") or []
    confidences = [f.get("confidence") for f in findings if isinstance(f.get("confidence"), (int, float))]
    if len(confidences) < 2:
        return []
    distinct = sorted(set(confidences))
    if len(distinct) > 1:
        return []
    return [
        Finding(
            category="confidence_variance",
            severity="high",
            observation=(
                f"All {len(confidences)} research findings share a single confidence value "
                f"{set(confidences)}; this looks like a hardcoded constant rather than a real score."
            ),
            suggestion=(
                "Replace the hardcoded confidence with a derived score: e.g. weight by "
                "snippet length, query-term overlap, source domain reputation, or content "
                "recency. Until then, drop the field rather than publish a fake score."
            ),
            evidence={"confidences": confidences, "distinct": distinct},
        )
    ]


def _source_outcomes_cover_drops(research: Dict[str, Any]) -> bool:
    """True if `source_outcomes` accounts for every checked source with a status."""
    sources_checked = research.get("sources_checked")
    outcomes = research.get("source_outcomes")
    if not isinstance(sources_checked, int) or sources_checked <= 0:
        return False
    if not isinstance(outcomes, list) or len(outcomes) < sources_checked:
        return False
    for entry in outcomes:
        if not isinstance(entry, dict):
            return False
        status = entry.get("status")
        if not isinstance(status, str) or not status:
            return False
    return True


def check_sources_vs_findings(research: Optional[Dict[str, Any]]) -> List[Finding]:
    if not research:
        return []
    sources_checked = research.get("sources_checked")
    findings_list = research.get("findings") or []
    findings_count = len(findings_list)
    if not isinstance(sources_checked, int) or sources_checked <= 0:
        return []
    ratio = findings_count / sources_checked
    if ratio >= RATIO_FLOOR:
        return []
    if _source_outcomes_cover_drops(research):
        return []
    return [
        Finding(
            category="sources_vs_findings_ratio",
            severity="medium",
            observation=(
                f"sources_checked={sources_checked} but findings={findings_count} "
                f"(ratio {ratio:.2f} < floor {RATIO_FLOOR}). Drop is silent."
            ),
            suggestion=(
                "Track per-source outcome (matched | empty | error | rate_limited) and "
                "surface a `source_outcomes` array. Don't silently discard."
            ),
            evidence={
                "sources_checked": sources_checked,
                "findings_count": findings_count,
                "ratio": round(ratio, 4),
            },
        )
    ]


def check_silent_error(research: Optional[Dict[str, Any]]) -> List[Finding]:
    if not research:
        return []
    sources_checked = research.get("sources_checked")
    findings_list = research.get("findings") or []
    errors = research.get("errors")
    if not isinstance(sources_checked, int) or sources_checked <= 0:
        return []
    ratio = len(findings_list) / sources_checked
    if ratio >= RATIO_FLOOR:
        return []
    if errors:
        return []
    if _source_outcomes_cover_drops(research):
        return []
    return [
        Finding(
            category="silent_error",
            severity="high",
            observation=(
                f"Findings/sources ratio is {ratio:.2f} but errors:[] is empty — " "losses are not being reported."
            ),
            suggestion=(
                "When a source contributes zero findings, append a structured entry to "
                "`errors` (or rename to `source_outcomes`) with "
                "reason=empty|timeout|http_error|parse_failure."
            ),
            evidence={
                "sources_checked": sources_checked,
                "findings_count": len(findings_list),
                "errors": errors or [],
            },
        )
    ]


def check_title_sanity(monitor: Optional[Dict[str, Any]]) -> List[Finding]:
    if not monitor:
        return []
    out: List[Finding] = []
    sites = monitor.get("sites") or []
    for site in sites:
        url = site.get("url", "")
        title = (site.get("title") or "").strip()
        description = (site.get("description") or "").strip()
        word_count = site.get("word_count") or 0
        headings = site.get("headings") or []

        if title and description and title == description:
            out.append(
                Finding(
                    category="title_equals_description",
                    severity="low",
                    observation=(
                        f"{url}: title and description are identical " "— both probably fell back to the same meta tag."
                    ),
                    suggestion=(
                        "Distinguish title (document title) from description (meta or "
                        "first heading). Fallback to first h1/h2 instead of duplicating title."
                    ),
                    evidence={"url": url, "title": title, "description": description},
                )
            )

        if word_count > EXTRACTION_WORD_FLOOR and not headings and not description:
            out.append(
                Finding(
                    category="extraction_partial",
                    severity="medium",
                    observation=(
                        f"{url}: word_count={word_count} but headings=[] and "
                        "description is empty — content was scraped but structure "
                        "was not extracted."
                    ),
                    suggestion=(
                        "Add a fallback heading/description pass: for HN-style sites "
                        "with custom DOM, use site-specific selectors "
                        "(e.g. .titleline, .athing) instead of generic h1/h2/meta."
                    ),
                    evidence={
                        "url": url,
                        "word_count": word_count,
                        "headings": headings,
                        "description": description,
                    },
                )
            )
    return out


def check_freshness(index: Optional[Dict[str, Any]], now: Optional[datetime] = None) -> List[Finding]:
    if not index:
        return []
    updated = index.get("updated")
    if not updated:
        return []
    try:
        ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
    except ValueError:
        return []
    now = now or datetime.now(timezone.utc)
    age_hours = (now - ts).total_seconds() / 3600.0
    if age_hours < FRESHNESS_SOFT_HOURS:
        return []
    severity = "high" if age_hours > FRESHNESS_HARD_HOURS else "medium"
    return [
        Finding(
            category="freshness",
            severity=severity,
            observation=(
                f"index.json updated={updated} is {age_hours:.1f}h old "
                f"(soft floor {FRESHNESS_SOFT_HOURS}h, hard floor {FRESHNESS_HARD_HOURS}h)."
            ),
            suggestion=(
                "Investigate the agent-router cron — either schedule is paused, "
                "the workflow is failing silently, or auto-merge is stuck."
            ),
            evidence={"updated": updated, "age_hours": round(age_hours, 2)},
        )
    ]


def build_report(data_dir: Path = DEFAULT_DATA_DIR, now: Optional[datetime] = None) -> Dict[str, Any]:
    index = _load_json(data_dir / "index.json")
    research = _load_json(data_dir / "latest-research.json")
    monitor = _load_json(data_dir / "latest-monitor.json")

    findings: List[Finding] = []
    findings.extend(check_confidence_variance(research))
    findings.extend(check_sources_vs_findings(research))
    findings.extend(check_silent_error(research))
    findings.extend(check_title_sanity(monitor))
    findings.extend(check_freshness(index, now=now))

    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for f in findings:
        if f.severity in severity_counts:
            severity_counts[f.severity] += 1

    generated = (now or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": generated,
        "inputs": {
            "index_present": index is not None,
            "research_present": research is not None,
            "monitor_present": monitor is not None,
        },
        "severity_counts": severity_counts,
        "findings_count": len(findings),
        "findings": [asdict(f) for f in findings],
        "notes": "Propose-only. Caller decides which suggestions to promote into agent-router.yml.",
    }


def write_report(report: Dict[str, Any], output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = report["generated_at_utc"].replace(":", "").replace("-", "")
    out = output_dir / f"self_review_{stamp}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out


def main(argv: Optional[List[str]] = None) -> int:
    argv = argv or sys.argv[1:]
    data_dir = DEFAULT_DATA_DIR
    output_dir = DEFAULT_OUTPUT_DIR
    if argv:
        data_dir = Path(argv[0])
    if len(argv) > 1:
        output_dir = Path(argv[1])

    report = build_report(data_dir=data_dir)
    out = write_report(report, output_dir=output_dir)

    sev = report["severity_counts"]
    print(f"wrote {out}")
    print(f"  high={sev['high']} medium={sev['medium']} low={sev['low']} total={report['findings_count']}")

    return 1 if sev["high"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
