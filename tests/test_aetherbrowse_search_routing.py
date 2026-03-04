from aetherbrowse.runtime import server as runtime_server


def test_normalize_search_engine_aliases() -> None:
    assert runtime_server._normalize_search_engine("roundtable") == "roundtable"
    assert runtime_server._normalize_search_engine("AUTO") == "roundtable"
    assert runtime_server._normalize_search_engine("ddg") == "duckduckgo"
    assert runtime_server._normalize_search_engine("bing") == "bing"
    assert runtime_server._normalize_search_engine("unknown-engine") == "roundtable"


def test_extract_bing_results_parses_basic_card() -> None:
    html = """
    <li class="b_algo">
      <h2><a href="https://example.com/page">Example Result</a></h2>
      <div class="b_caption"><p>Useful snippet text</p></div>
    </li>
    """
    results = runtime_server._extract_bing_results(html, limit=5)
    assert len(results) == 1
    assert results[0]["url"] == "https://example.com/page"
    assert results[0]["title"] == "Example Result"
    assert results[0]["source"] == "bing"


def test_aether_search_roundtable_combines_sources(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_server,
        "_search_duckduckgo",
        lambda query, limit: [{"title": "DDG One", "url": "https://ddg.test/1", "snippet": "", "source": "duckduckgo"}],
    )
    monkeypatch.setattr(
        runtime_server,
        "_search_bing",
        lambda query, limit: [{"title": "Bing One", "url": "https://bing.test/1", "snippet": "", "source": "bing"}],
    )

    results = runtime_server._aether_search("agent browser", limit=4, engine="roundtable")
    urls = {item["url"] for item in results}
    assert "https://ddg.test/1" in urls
    assert "https://bing.test/1" in urls
    assert len(results) == 4


def test_aether_search_specific_engine_falls_back_when_empty(monkeypatch) -> None:
    monkeypatch.setattr(runtime_server, "_search_duckduckgo", lambda query, limit: [])
    results = runtime_server._aether_search("fallback test", limit=3, engine="duckduckgo")
    assert len(results) == 3
    assert any("duckduckgo.com" in item["url"] for item in results)
