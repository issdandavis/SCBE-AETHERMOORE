from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.system import playwriter_lane_runner as runner


def test_extract_search_results_decodes_redirects_and_snippets() -> None:
    html = (
        "    <html>\n"
        "      <body>\n"
        '        <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Falpha">Alpha <b>Result</b></a>\n'  # noqa: E501
        "\n"
        '        <div class="result__snippet">First <b>snippet</b> for alpha.</div>\n'
        '        <a class="result__a" href="https://example.org/bravo">Bravo Result</a>\n'
        '        <div class="result__snippet">Second snippet for bravo.</div>\n'
        "      </body>\n"
        "    </html>\n"
    )

    results = runner._extract_search_results(html, max_results=5)

    assert results == [
        {
            "rank": 1,
            "title": "Alpha Result",
            "url": "https://example.com/alpha",
            "snippet": "First snippet for alpha.",
        },
        {
            "rank": 2,
            "title": "Bravo Result",
            "url": "https://example.org/bravo",
            "snippet": "Second snippet for bravo.",
        },
    ]


def test_search_evidence_fetches_selected_result_and_updates_state(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    search_html = """
    <html>
      <body>
        <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Falpha">Alpha Result</a>
        <div class="result__snippet">First snippet.</div>
        <a class="result__a" href="https://example.org/bravo">Bravo Result</a>
        <div class="result__snippet">Second snippet.</div>
      </body>
    </html>
    """
    page_html = """
    <html>
      <head><title>Bravo Evidence Page</title></head>
      <body>
        <main>Bravo evidence body with enough text to build an excerpt.</main>
      </body>
    </html>
    """

    def fake_fetch_html(url: str, timeout: int) -> tuple[str, str]:
        assert timeout == 11
        if url.startswith(runner.DEFAULT_SEARCH_URL):
            return search_html, "200"
        if url == "https://example.org/bravo":
            return page_html, "200"
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(runner, "_fetch_html", fake_fetch_html)
    monkeypatch.setattr(runner, "EVIDENCE_DIR", tmp_path)
    monkeypatch.setattr(runner, "_utc_iso", lambda: "2026-03-17T12:00:00+00:00")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "playwriter_lane_runner.py",
            "--session",
            "lane-5",
            "--task",
            "search-evidence",
            "--query",
            "scbe browser",
            "--result-index",
            "1",
            "--timeout",
            "11",
        ],
    )

    exit_code = runner.main()
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["query"] == "scbe browser"
    assert payload["selected_result_index"] == 1
    assert payload["selected_result"] == {
        "rank": 2,
        "title": "Bravo Result",
        "url": "https://example.org/bravo",
        "snippet": "Second snippet.",
    }
    assert payload["title"] == "Bravo Evidence Page"
    assert "Bravo evidence body" in payload["excerpt"]

    artifact_path = Path(payload["artifact_path"])
    assert artifact_path.exists()
    assert artifact_path.parent == tmp_path

    state = json.loads((tmp_path / "playwriter-session-lane-5.json").read_text(encoding="utf-8"))
    assert state == {
        "session_id": "lane-5",
        "url": "https://example.org/bravo",
        "last_search_query": "scbe browser",
        "last_search_url": "https://html.duckduckgo.com/html/?q=scbe+browser",
        "updated_at": "2026-03-17T12:00:00+00:00",
    }
