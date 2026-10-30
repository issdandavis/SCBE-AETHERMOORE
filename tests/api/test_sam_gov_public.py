from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from api.darpa_prep import sam_public
from api.darpa_prep.sam_public import SamGovPublicClient, SamGovRequestError

TEST_API_KEY = "-".join(("unit", "fixture", "key"))
REDACTION_API_KEY = "-".join(("redaction", "fixture", "key"))


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_public_query_uses_documented_names_and_omits_key() -> None:
    client = SamGovPublicClient(api_key=TEST_API_KEY)

    query = client.public_query(
        query="AI safety",
        posted_from="10/01/2026",
        posted_to="10/30/2026",
        limit=25,
        notice_types=("p", "r"),
        naics_code="541511",
        organization_name="DARPA",
    )

    assert query["title"] == "AI safety"
    assert query["ptype"] == ["p", "r"]
    assert query["ncode"] == "541511"
    assert query["organizationName"] == "DARPA"
    assert "q" not in query
    assert "keywords" not in query
    assert "api_key" not in query
    assert TEST_API_KEY not in json.dumps(query)


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://api.sam.gov/opportunities/v2/search",
        "https://example.com/opportunities/v2/search",
        "https://api.sam.gov:444/opportunities/v2/search",
        "https://api.sam.gov/prod/opportunities/v2/search",
        "https://api.sam.gov/opportunities/v2/search?forward=1",
    ],
)
def test_endpoint_validation_prevents_key_exfiltration(endpoint: str) -> None:
    with pytest.raises(ValueError, match="official HTTPS"):
        SamGovPublicClient(api_key=TEST_API_KEY, base_url=endpoint)


def test_http_404_is_a_successful_empty_query(monkeypatch) -> None:
    seen_urls: list[str] = []

    def fake_urlopen(request, timeout):
        del timeout
        seen_urls.append(request.full_url)
        raise HTTPError(request.full_url, 404, "No Data", hdrs=None, fp=None)

    monkeypatch.setattr(sam_public, "urlopen", fake_urlopen)
    client = SamGovPublicClient(api_key=TEST_API_KEY)

    assert client.search_opportunities(query="no such title", limit=5) == []
    assert len(seen_urls) == 1


def test_overlong_title_is_rejected_before_network_call() -> None:
    client = SamGovPublicClient(api_key=TEST_API_KEY)

    with pytest.raises(ValueError, match="500 characters"):
        client.search_opportunities(query="x" * 501, limit=5)


def test_auth_error_never_echoes_key(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        del timeout
        raise HTTPError(request.full_url, 401, "Unauthorized", hdrs=None, fp=None)

    monkeypatch.setattr(sam_public, "urlopen", fake_urlopen)
    client = SamGovPublicClient(api_key=REDACTION_API_KEY)

    with pytest.raises(SamGovRequestError) as caught:
        client.search_opportunities(query="autonomy", limit=5)

    assert caught.value.status_code == 401
    assert REDACTION_API_KEY not in str(caught.value)
    assert "api_key" not in str(caught.value)


def test_pagination_uses_page_index_and_deduplicates(monkeypatch) -> None:
    monkeypatch.setattr(sam_public, "MAX_PAGE_SIZE", 2)
    calls: list[dict[str, list[str]]] = []
    pages = [
        {
            "totalRecords": 3,
            "opportunitiesData": [
                {"noticeId": "N1", "title": "AI safety", "active": "Yes"},
                {"noticeId": "N2", "title": "Cybersecurity", "active": "Yes"},
            ],
        },
        {
            "totalRecords": 3,
            "opportunitiesData": [
                {"noticeId": "N3", "title": "Autonomy", "active": "Yes"},
            ],
        },
    ]

    def fake_urlopen(request, timeout):
        del timeout
        calls.append(parse_qs(urlsplit(request.full_url).query))
        return _Response(pages[len(calls) - 1])

    monkeypatch.setattr(sam_public, "urlopen", fake_urlopen)
    client = SamGovPublicClient(api_key=TEST_API_KEY)

    rows = client.search_opportunities(query="AI", limit=3)

    assert [row["noticeId"] for row in rows] == ["N1", "N2", "N3"]
    assert [call["offset"] for call in calls] == [["0"], ["1"]]
    assert all(call["title"] == ["AI"] for call in calls)


def test_active_filter_keeps_missing_flag_but_rejects_explicit_inactive(monkeypatch) -> None:
    payload = {
        "totalRecords": 2,
        "opportunitiesData": [
            {"noticeId": "N1", "title": "No active field"},
            {"noticeId": "N2", "title": "Archived", "active": "No"},
        ],
    }
    monkeypatch.setattr(sam_public, "urlopen", lambda request, timeout: _Response(payload))

    rows = SamGovPublicClient(api_key=TEST_API_KEY).search_opportunities(query="AI", limit=2)

    assert [row["noticeId"] for row in rows] == ["N1"]
