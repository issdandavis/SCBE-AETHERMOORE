#!/usr/bin/env python3
"""Collect SAM.gov coding/software opportunity metadata for training seeds.

Default mode is a dry-run query plan. Use --execute to call SAM.gov with
SAM_API_KEY or SAM_GOV_API_KEY. The output is opportunity metadata for task
shaping, not a training corpus of solicitation attachments.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from api.darpa_prep.sam_public import SamGovPublicClient, validate_official_endpoint

DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "training" / "sam_coding_opportunities"
DEFAULT_ENDPOINT = "https://api.sam.gov/opportunities/v2/search"
DEFAULT_KEYWORDS = [
    "software development",
    "application development",
    "code",
    "data pipeline",
    "API integration",
    "test automation",
    "machine learning",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_date_window(days: int = 30) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=days)
    return start.strftime("%m/%d/%Y"), end.strftime("%m/%d/%Y")


def resolve_api_key() -> str:
    return os.environ.get("SAM_API_KEY", "").strip() or os.environ.get("SAM_GOV_API_KEY", "").strip()


def build_query_params(
    *,
    api_key: str,
    posted_from: str,
    posted_to: str,
    limit: int,
    ptype: str,
    keyword: str,
) -> dict[str, str]:
    return {
        "api_key": api_key,
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "limit": str(limit),
        "ptype": ptype,
        "title": keyword,
    }


def redact_params(params: dict[str, str]) -> dict[str, str]:
    out = dict(params)
    if out.get("api_key"):
        out["api_key"] = "<redacted>"
    return out


def safe_plan_summary(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "sam_gov_opportunities_api",
        "query_count": len(plan.get("queries", [])),
        "api_key_present": bool(plan.get("api_key_present")),
    }


def public_plan_status(plan: dict[str, Any], *, ok: bool, dry_run: bool, error: str = "") -> dict[str, Any]:
    """CLI status without query parameters or API credentials."""
    return {
        "ok": ok,
        "dry_run": dry_run,
        "query_count": len(plan.get("queries", [])),
        "api_key_present": bool(plan.get("api_key_present")),
        "error": error,
    }


def normalize_opportunities(payload: dict[str, Any], *, keyword: str) -> list[dict[str, Any]]:
    rows = payload.get("opportunitiesData") or payload.get("data") or []
    normalized = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        normalized.append(
            {
                "notice_id": row.get("noticeId") or row.get("notice_id") or row.get("id"),
                "title": row.get("title", ""),
                "agency": row.get("fullParentPathName") or row.get("agency") or row.get("department", ""),
                "posted_date": row.get("postedDate", ""),
                "response_deadline": row.get("responseDeadLine") or row.get("responseDeadline") or "",
                "type": row.get("type", ""),
                "naics": row.get("naicsCode", ""),
                "classification_code": row.get("classificationCode", ""),
                "ui_link": row.get("uiLink", ""),
                "keyword": keyword,
                "training_use": "metadata_to_task_shape_only",
            }
        )
    return normalized


def write_report(report: dict[str, Any], output_root: Path) -> dict[str, str]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / stamp
    latest_dir = output_root / "latest"
    out_dir.mkdir(parents=True, exist_ok=True)
    latest_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "sam_coding_opportunities.json"
    latest_path = latest_dir / "sam_coding_opportunities.json"
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    report_path.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")
    return {"json": str(report_path), "latest_json": str(latest_path)}


def build_plan(args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    endpoint = validate_official_endpoint(args.endpoint)
    posted_from, posted_to = args.posted_from, args.posted_to
    if not posted_from or not posted_to:
        posted_from, posted_to = default_date_window(args.days)
    keywords = args.keyword or DEFAULT_KEYWORDS
    queries = [
        {
            "endpoint": endpoint,
            "params": redact_params(
                build_query_params(
                    api_key=api_key,
                    posted_from=posted_from,
                    posted_to=posted_to,
                    limit=args.limit,
                    ptype=args.ptype,
                    keyword=keyword,
                )
            ),
        }
        for keyword in keywords
    ]
    return {
        "schema_version": "scbe_sam_coding_opportunity_plan_v1",
        "created_at": _utc_now(),
        "execute": bool(args.execute),
        "api_key_present": bool(api_key),
        "policy": "metadata_to_task_shape_only; do not ingest restricted attachments",
        "queries": queries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--keyword", action="append", default=[])
    parser.add_argument("--posted-from", default="")
    parser.add_argument("--posted-to", default="")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--ptype", default="o", help="SAM opportunity type, default solicitations")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()

    api_key = resolve_api_key()
    plan = build_plan(args, api_key)
    if not args.execute:
        print(json.dumps(public_plan_status(plan, ok=True, dry_run=True), indent=2))
        return 0
    if not api_key:
        print(json.dumps(public_plan_status(plan, ok=False, dry_run=False, error="missing_api_key"), indent=2))
        return 2

    opportunities: list[dict[str, Any]] = []
    raw_counts: dict[str, int] = {}
    client = SamGovPublicClient(api_key=api_key, base_url=args.endpoint, timeout_seconds=60)
    for query in plan["queries"]:
        redacted = query["params"]
        keyword = str(redacted["title"])
        rows_raw = client.search_opportunities(
            query=keyword,
            limit=int(redacted["limit"]),
            active_only=False,
            posted_from=str(redacted["postedFrom"]),
            posted_to=str(redacted["postedTo"]),
            notice_types=str(redacted["ptype"]),
        )
        payload = {"opportunitiesData": rows_raw}
        rows = normalize_opportunities(payload, keyword=keyword)
        raw_counts[keyword] = len(rows)
        opportunities.extend(rows)

    report = {
        "schema_version": "scbe_sam_coding_opportunities_v1",
        "created_at": _utc_now(),
        "source": "sam_gov_opportunities_api",
        "policy": plan["policy"],
        "query_plan": plan,
        "counts": raw_counts,
        "opportunities": opportunities,
    }
    paths = write_report(report, args.output_root)
    print(json.dumps({"ok": True, **paths, "opportunity_count": len(opportunities)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
