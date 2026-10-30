from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from api.darpa_prep.sam_public import SamGovRequestError

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "system" / "scan_sam_opportunities.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("scan_sam_opportunities", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _Client:
    def public_query(self, **kwargs):
        return {key: value for key, value in kwargs.items() if value not in (None, "")}

    def search_opportunities(self, **kwargs):
        if kwargs.get("query") == "AI safety":
            return [
                {
                    "noticeId": "N1",
                    "title": "AI Safety and Cybersecurity Platform",
                    "fullParentPathName": "Agency",
                    "postedDate": "2026-10-29",
                    "responseDeadLine": "2026-11-20T17:00:00Z",
                    "naicsCode": "541511",
                    "active": "Yes",
                }
            ]
        return [
            {
                "noticeId": "N1",
                "title": "AI Safety and Cybersecurity Platform",
                "fullParentPathName": "Agency",
                "postedDate": "2026-10-29",
                "responseDeadLine": "2026-11-20T17:00:00Z",
                "naicsCode": "541511",
                "active": "Yes",
            },
            {
                "noticeId": "N2",
                "title": "Office chairs",
                "fullParentPathName": "Agency",
                "postedDate": "2026-10-29",
                "naicsCode": "541511",
                "active": "Yes",
            },
        ]


def test_ranked_scan_deduplicates_and_records_match_provenance() -> None:
    module = _load_module()
    profiles = [
        module.QueryProfile("title-ai-safety", "AI safety title", 10, title="AI safety"),
        module.QueryProfile("naics-541511", "NAICS 541511", 1, naics_code="541511"),
    ]

    report = module.run_scan(
        _Client(),
        profiles=profiles,
        days=14,
        per_profile=20,
        min_score=6,
        max_results=10,
        now=datetime(2026, 10, 30, tzinfo=UTC),
    )

    assert report["scan_complete"] is True
    assert report["successful_profiles"] == 2
    assert report["raw_unique_opportunities"] == 2
    assert report["total_opportunities"] == 1
    opportunity = report["opportunities"][0]
    assert opportunity["notice_id"] == "N1"
    assert opportunity["matched_profile_ids"] == ["title-ai-safety", "naics-541511"]
    assert {"ai safety", "cybersecurity"} <= set(opportunity["matched_terms"])
    assert opportunity["sam_url"] == "https://sam.gov/opp/N1/view"


def test_partial_failure_is_not_reported_as_clean_and_contains_no_key() -> None:
    module = _load_module()
    redaction_key = "-".join(("redaction", "fixture", "key"))

    class FailingClient(_Client):
        api_key = redaction_key

        def search_opportunities(self, **kwargs):
            raise SamGovRequestError(
                "SAM.gov request failed with HTTP 401: "
                f"https://api.sam.gov/opportunities/v2/search?api_key={redaction_key}",
                status_code=401,
            )

    report = module.run_scan(
        FailingClient(),
        profiles=[module.QueryProfile("title-ai", "AI title", 10, title="AI")],
        days=14,
        per_profile=20,
        min_score=1,
        max_results=10,
        now=datetime(2026, 10, 30, tzinfo=UTC),
    )

    encoded = json.dumps(report)
    assert report["scan_complete"] is False
    assert report["successful_profiles"] == 0
    assert len(report["query_errors"]) == 1
    assert "api_key" not in encoded
    assert redaction_key not in encoded
