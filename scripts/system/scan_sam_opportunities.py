#!/usr/bin/env python3
"""Build a ranked, credential-safe SAM.gov opportunity report for SCBE."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from api.darpa_prep.sam_public import SamGovPublicClient

DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "gov-contracts" / "sam_gov_weekly.json"
NOTICE_TYPES = ("p", "r", "o", "k", "s")
CAPABILITY_TERMS: tuple[tuple[str, int], ...] = (
    ("post-quantum", 12),
    ("cryptograph", 8),
    ("adversarial machine learning", 12),
    ("artificial intelligence", 8),
    ("machine learning", 8),
    ("cybersecurity", 8),
    ("zero trust", 7),
    ("autonomous", 7),
    ("autonomy", 7),
    ("swarm", 9),
    ("navigation", 5),
    ("ai safety", 10),
    ("ai assurance", 9),
    ("trustworthy ai", 9),
    ("governance", 5),
    ("verification", 4),
    ("software", 2),
)


@dataclass(frozen=True)
class QueryProfile:
    profile_id: str
    label: str
    match_bonus: int
    title: str = ""
    organization_name: str = ""
    naics_code: str = ""

    def request_kwargs(self) -> dict[str, str]:
        values = {
            "query": self.title,
            "organization_name": self.organization_name,
            "naics_code": self.naics_code,
        }
        return {name: value for name, value in values.items() if value}


def default_profiles() -> list[QueryProfile]:
    title_terms = (
        "AI safety",
        "artificial intelligence governance",
        "post-quantum cryptography",
        "cybersecurity",
        "machine learning security",
        "AI assurance",
        "trustworthy AI",
        "adversarial machine learning",
        "autonomous systems",
        "swarm autonomy",
    )
    profiles = [
        QueryProfile(
            profile_id=f"title-{re.sub(r'[^a-z0-9]+', '-', term.lower()).strip('-')}",
            label=f'Title contains "{term}"',
            title=term,
            match_bonus=10,
        )
        for term in title_terms
    ]
    profiles.append(
        QueryProfile(
            profile_id="organization-darpa",
            label="DARPA organization",
            organization_name="Defense Advanced Research Projects Agency",
            match_bonus=12,
        )
    )
    for code, label in (
        ("541511", "Custom computer programming"),
        ("541512", "Computer systems design"),
        ("541519", "Other computer related services"),
        ("541715", "Engineering R&D"),
        ("513210", "Software publishers"),
    ):
        profiles.append(
            QueryProfile(
                profile_id=f"naics-{code}",
                label=f"NAICS {code} — {label}",
                naics_code=code,
                match_bonus=1,
            )
        )
    return profiles


def _text(value: Any) -> str:
    return str(value or "").strip()


def _safe_error(exc: Exception, *, api_key: str | None) -> str:
    message = f"{type(exc).__name__}: {exc}"
    if api_key:
        message = message.replace(api_key, "<redacted>")
    message = re.sub(r"(?i)api_key=[^&\s]+", "credential=<redacted>", message)
    return message[:500]


def _notice_id(row: dict[str, Any]) -> str:
    return _text(row.get("noticeId") or row.get("solicitationNumber"))


def _days_until(raw: Any, *, now: datetime) -> int | None:
    value = _text(raw)
    if not value:
        return None
    candidate = value.replace("Z", "+00:00")
    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        for pattern in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(value[:10], pattern).replace(tzinfo=UTC)
                break
            except ValueError:
                continue
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return (parsed.date() - now.date()).days


def normalize_public_opportunity(row: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    notice_id = _notice_id(row)
    link = _text(row.get("uiLink"))
    if not link and notice_id:
        link = f"https://sam.gov/opp/{notice_id}/view"
    deadline = _text(row.get("responseDeadLine") or row.get("responseDeadline"))
    return {
        "notice_id": notice_id,
        "title": _text(row.get("title")) or "Untitled opportunity",
        "solicitation_number": _text(row.get("solicitationNumber")),
        "organization": _text(row.get("fullParentPathName") or row.get("organizationName") or row.get("department")),
        "notice_type": _text(row.get("type") or row.get("noticeType")),
        "posted_date": _text(row.get("postedDate")),
        "response_deadline": deadline,
        "days_until_deadline": _days_until(deadline, now=now),
        "naics_code": _text(row.get("naicsCode")),
        "classification_code": _text(row.get("classificationCode")),
        "set_aside": _text(row.get("setAside")),
        "set_aside_code": _text(row.get("setAsideCode")),
        "active": _text(row.get("active")),
        "sam_url": link,
        "additional_info_url": _text(row.get("additionalInfoLink")),
    }


def _score(record: dict[str, Any], profiles: Iterable[QueryProfile]) -> tuple[int, list[str]]:
    title = record["title"].lower()
    organization = record["organization"].lower()
    searchable = f"{title} {organization} {record['naics_code']} {record['classification_code']}"
    matched_terms: list[str] = []
    score = sum(profile.match_bonus for profile in profiles)
    for term, weight in CAPABILITY_TERMS:
        if term in searchable:
            matched_terms.append(term)
            score += weight * (2 if term in title else 1)
    days_left = record.get("days_until_deadline")
    if isinstance(days_left, int):
        if days_left < 0:
            score -= 30
        elif days_left <= 7:
            score += 1
        elif days_left <= 45:
            score += 4
        else:
            score += 2
    return score, matched_terms


def run_scan(
    client: SamGovPublicClient,
    *,
    profiles: list[QueryProfile],
    days: int,
    per_profile: int,
    min_score: int,
    max_results: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    merged: dict[str, dict[str, Any]] = {}
    profile_by_id = {profile.profile_id: profile for profile in profiles}
    profile_reports: list[dict[str, Any]] = []
    query_errors: list[dict[str, str]] = []
    successful_profiles = 0

    for profile in profiles:
        request_kwargs = profile.request_kwargs()
        public_query = client.public_query(
            **request_kwargs,
            limit=per_profile,
            days_back=days,
            notice_types=NOTICE_TYPES,
        )
        try:
            rows = client.search_opportunities(
                **request_kwargs,
                limit=per_profile,
                active_only=True,
                days_back=days,
                notice_types=NOTICE_TYPES,
            )
            successful_profiles += 1
            profile_reports.append(
                {
                    "profile_id": profile.profile_id,
                    "label": profile.label,
                    "status": "ok",
                    "raw_count": len(rows),
                    "query": public_query,
                }
            )
        except Exception as exc:  # sanitized client exceptions plus configuration errors
            error = _safe_error(exc, api_key=client.api_key)
            query_errors.append({"profile_id": profile.profile_id, "label": profile.label, "error": error})
            profile_reports.append(
                {
                    "profile_id": profile.profile_id,
                    "label": profile.label,
                    "status": "error",
                    "raw_count": 0,
                    "query": public_query,
                    "error": error,
                }
            )
            continue

        for row in rows:
            record = normalize_public_opportunity(row, now=now)
            key = record["notice_id"] or "|".join((record["title"], record["organization"], record["posted_date"]))
            current = merged.get(key)
            if current is None:
                current = record
                current["matched_profile_ids"] = []
                merged[key] = current
            if profile.profile_id not in current["matched_profile_ids"]:
                current["matched_profile_ids"].append(profile.profile_id)

    ranked: list[dict[str, Any]] = []
    for record in merged.values():
        matched_profiles = [profile_by_id[profile_id] for profile_id in record["matched_profile_ids"]]
        score, matched_terms = _score(record, matched_profiles)
        record["matched_profiles"] = [profile.label for profile in matched_profiles]
        record["matched_terms"] = matched_terms
        record["relevance_score"] = score
        if score >= min_score:
            ranked.append(record)
    ranked.sort(
        key=lambda row: (
            -int(row["relevance_score"]),
            -(row["days_until_deadline"] if isinstance(row["days_until_deadline"], int) else -9999),
            row["title"].lower(),
        )
    )
    ranked = ranked[:max_results]

    return {
        "schema_version": "scbe_sam_opportunity_report_v2",
        "scan_date": now.date().isoformat(),
        "generated_at": now.isoformat(),
        "period_days": days,
        "total_opportunities": len(ranked),
        "raw_unique_opportunities": len(merged),
        "profile_count": len(profiles),
        "successful_profiles": successful_profiles,
        "scan_complete": not query_errors and successful_profiles == len(profiles),
        "profiles": profile_reports,
        "query_errors": query_errors,
        "opportunities": ranked,
        "policy": {
            "source": "SAM.gov Opportunities v2 public API",
            "metadata_only": True,
            "attachments_downloaded": False,
            "qualification_required": True,
        },
    }


def _write_github_outputs(report: dict[str, Any]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT", "").strip()
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as stream:
        stream.write(f"total={report['total_opportunities']}\n")
        stream.write(f"errors={len(report['query_errors'])}\n")
        stream.write(f"successful_profiles={report['successful_profiles']}\n")
        stream.write(f"profile_count={report['profile_count']}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=14, help="Posted-date lookback, from 0 through 365 days.")
    parser.add_argument("--per-profile", type=int, default=50, help="Maximum rows requested for each profile.")
    parser.add_argument("--min-score", type=int, default=6, help="Minimum deterministic relevance score.")
    parser.add_argument("--max-results", type=int, default=100, help="Maximum ranked rows in the report.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not 0 <= args.days <= 365:
        parser.error("--days must be between 0 and 365")
    if not 1 <= args.per_profile <= 1000:
        parser.error("--per-profile must be between 1 and 1000")
    if not 1 <= args.max_results <= 1000:
        parser.error("--max-results must be between 1 and 1000")

    client = SamGovPublicClient()
    report = run_scan(
        client,
        profiles=default_profiles(),
        days=args.days,
        per_profile=args.per_profile,
        min_score=args.min_score,
        max_results=args.max_results,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_github_outputs(report)
    print(
        json.dumps(
            {
                "ok": report["scan_complete"],
                "output": str(args.output),
                "opportunities": report["total_opportunities"],
                "successful_profiles": report["successful_profiles"],
                "profile_count": report["profile_count"],
                "errors": len(report["query_errors"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
