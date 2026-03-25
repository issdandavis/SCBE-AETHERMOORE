from __future__ import annotations

from typing import Any, Dict, List

from hydra.arxiv_retrieval import AI2AIRetrievalService, ArxivClient

SAMPLE_FEED = """<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom'
      xmlns:opensearch='http://a9.com/-/spec/opensearch/1.1/'
      xmlns:arxiv='http://arxiv.org/schemas/atom'>
  <title>arXiv Query Results</title>
  <opensearch:totalResults>2</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/2501.00001v1</id>
    <updated>2025-01-01T00:00:00Z</updated>
    <published>2025-01-01T00:00:00Z</published>
    <title>Dual Lattice Governance for AI Agents</title>
    <summary>We propose a dual lattice system for agent coordination.</summary>
    <author><name>Issac Davis</name></author>
    <author><name>A. Researcher</name></author>
    <link rel='alternate' type='text/html' href='https://arxiv.org/abs/2501.00001v1' />
    <link title='pdf' rel='related' type='application/pdf' href='https://arxiv.org/pdf/2501.00001v1.pdf' />
    <arxiv:comment>Accepted to Workshop X</arxiv:comment>
    <arxiv:primary_category term='cs.AI' scheme='http://arxiv.org/schemas/atom'/>
    <category term='cs.AI' scheme='http://arxiv.org/schemas/atom'/>
    <category term='cs.CR' scheme='http://arxiv.org/schemas/atom'/>
  </entry>
  <entry>
    <id>https://arxiv.org/abs/2501.00002</id>
    <updated>2025-01-03T00:00:00Z</updated>
    <published>2025-01-02T00:00:00Z</published>
    <title>Hyperbolic Retrieval Routing</title>
    <summary>Routing strategy for multi-agent retrieval systems.</summary>
    <author><name>R. Author</name></author>
    <link rel='alternate' type='text/html' href='https://arxiv.org/abs/2501.00002' />
    <category term='cs.AI' scheme='http://arxiv.org/schemas/atom'/>
  </entry>
</feed>
"""


class _FakeArxivClient(ArxivClient):
    def __init__(self, feed_text: str) -> None:
        super().__init__(min_delay_seconds=0.0)
        self.feed_text = feed_text
        self.last_params: Dict[str, str] = {}

    def _fetch_xml(self, params: Dict[str, str]) -> str:
        self.last_params = dict(params)
        return self.feed_text


class _MemoryStub:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def remember(self, key: str, value: Any, category: str, importance: float, keywords: List[str]) -> None:
        self.calls.append(
            {
                "key": key,
                "value": value,
                "category": category,
                "importance": importance,
                "keywords": keywords,
            }
        )


def test_arxiv_client_search_parses_atom_feed() -> None:
    client = _FakeArxivClient(SAMPLE_FEED)
    result = client.search("dual lattice", category="cs.AI", max_results=2)

    assert client.last_params["search_query"] == "all:dual lattice+AND+cat:cs.AI"
    assert result.total_results == 2
    assert len(result.papers) == 2

    first = result.papers[0]
    assert first.arxiv_id == "2501.00001v1"
    assert first.primary_category == "cs.AI"
    assert first.pdf_url == "https://arxiv.org/pdf/2501.00001v1.pdf"
    assert "Issac Davis" in first.authors


def test_arxiv_client_fetch_by_ids_normalizes_id_input() -> None:
    client = _FakeArxivClient(SAMPLE_FEED)
    papers = client.fetch_by_ids(
        [
            "2501.00001v1",
            "https://arxiv.org/abs/2501.00002",
        ]
    )

    assert client.last_params["id_list"] == "2501.00001v1,2501.00002"
    assert len(papers) == 2


def test_ai2ai_service_builds_packet_and_remembers() -> None:
    memory = _MemoryStub()
    client = _FakeArxivClient(SAMPLE_FEED)
    service = AI2AIRetrievalService(client=client, librarian=memory)

    packet = service.retrieve_arxiv_packet(
        requester="polly",
        query="hyperbolic agent retrieval",
        category="cs.AI",
        max_results=2,
        remember=True,
    )

    assert packet["source"] == "arxiv"
    assert packet["requester"] == "polly"
    assert packet["returned_results"] == 2
    assert packet["papers"][0]["arxiv_id"] == "2501.00001v1"
    assert memory.calls, "expected memory remember() call"

    outline = service.build_related_work_outline(packet)
    assert "# Related Work Outline" in outline
    assert "2501.00001v1" in outline
