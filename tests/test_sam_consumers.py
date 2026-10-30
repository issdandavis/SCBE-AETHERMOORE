from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from api.darpa_prep import client as darpa_client
from scripts import research_api_bus
from scripts.system import generate_research_feed

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_research_feed_uses_documented_darpa_organization_filter(monkeypatch) -> None:
    captured: dict = {}

    class FakeClient:
        def __init__(self, *, api_key: str, timeout_seconds: int) -> None:
            assert api_key == "test-key"
            assert timeout_seconds == generate_research_feed.TIMEOUT

        def search_opportunities(self, **kwargs):
            captured.update(kwargs)
            return [
                {
                    "noticeId": "N1",
                    "title": "DARPA trustworthy AI",
                    "postedDate": "2026-10-29",
                }
            ]

    monkeypatch.setenv("SAM_GOV_API_KEY", "test-key")
    monkeypatch.setattr(generate_research_feed, "SamGovPublicClient", FakeClient)

    items = generate_research_feed.darpa_opportunities(1)

    assert captured["organization_name"] == "Defense Advanced Research Projects Agency"
    assert captured["notice_types"] == ("p", "r", "o", "k", "s")
    assert items == [
        {
            "title": "DARPA trustworthy AI",
            "url": "https://sam.gov/opp/N1/view",
            "source": "darpa",
            "region": "us",
        }
    ]


def test_research_api_bus_maps_current_opportunity_record_fields(monkeypatch) -> None:
    class FakeSamGovClient:
        def search_opportunities(self, **kwargs):
            assert kwargs == {"query": "autonomy", "limit": 2, "active_only": True}
            return [
                {
                    "noticeId": "N1",
                    "title": "Autonomy",
                    "fullParentPathName": "Agency",
                    "type": "Sources Sought",
                    "naicsCode": "541715",
                    "setAside": "Small Business",
                    "responseDeadLine": "2026-11-30",
                }
            ]

        def normalize_opportunity(self, payload):
            assert payload["noticeId"] == "N1"
            return SimpleNamespace(
                model_dump=lambda: {
                    "title": "Autonomy",
                    "agency": "Agency",
                    "instrument_type": "contract",
                    "deadline": "2026-11-30",
                    "submission_path": "https://sam.gov/opp/N1/view",
                }
            )

    monkeypatch.setattr(darpa_client, "SamGovClient", FakeSamGovClient)

    result = research_api_bus._search_sam_gov("autonomy", 2)

    assert result["ok"] is True
    assert result["results"][0] == {
        "title": "Autonomy",
        "agency": "Agency",
        "type": "Sources Sought",
        "naics": "541715",
        "set_aside": "Small Business",
        "close_date": "2026-11-30",
        "notice_id": "N1",
        "url": "https://sam.gov/opp/N1/view",
    }


def test_known_sam_consumers_do_not_reintroduce_undocumented_filters() -> None:
    files = (
        REPO_ROOT / "scripts" / "system" / "collect_sam_coding_opportunities.py",
        REPO_ROOT / "scripts" / "system" / "generate_research_feed.py",
        REPO_ROOT / "scripts" / "system" / "research_triangle.py",
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)

    for stale_token in (
        "/prod/opportunities/v2/search",
        '"orgName"',
        '"sortBy"',
        '"naicscode"',
        '"organizationId"',
        '"q": keyword',
        '"q": keywords',
    ):
        assert stale_token not in combined
