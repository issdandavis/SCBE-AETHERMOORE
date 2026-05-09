from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_node(script: str) -> dict:
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_agent_search_endpoint_requires_commonjs_cleanly() -> None:
    payload = run_node("""
        const mod = require('./api/agent/search.js');
        console.log(JSON.stringify({
          handlerType: typeof mod,
          hasSearchAll: typeof mod._private.searchAll
        }));
        """)
    assert payload == {"handlerType": "function", "hasSearchAll": "function"}


def test_agent_search_zero_credit_fanout_with_mocked_fetch() -> None:
    payload = run_node("""
        global.fetch = async (url) => ({
          ok: true,
          json: async () => {
            if (String(url).includes('wikipedia')) {
              return { query: { search: [{ title: 'SCBE', snippet: 'governed <b>agent</b> overlay' }] } };
            }
            if (String(url).includes('openalex')) {
              return { results: [{ display_name: 'Low Resource Computing', id: 'https://openalex.org/W1', publication_year: 2026 }] };
            }
            return { AbstractURL: 'https://example.com/scbe', Heading: 'SCBE', Abstract: 'Local first agent bus' };
          },
          text: async () => '<feed><entry><title>Agent overlay</title><id>https://arxiv.org/abs/0000.00000</id><summary>test</summary></entry></feed>'
        });
        const { searchAll } = require('./api/agent/search.js')._private;
        searchAll('scbe low resource', { sources: ['duckduckgo', 'wikipedia', 'openalex', 'arxiv'], maxResults: 8 })
          .then((result) => console.log(JSON.stringify(result)))
          .catch((error) => {
            console.error(error);
            process.exit(1);
          });
        """)
    assert payload["cost"] == "zero-credit-public-sources"
    assert len(payload["results"]) >= 3
    assert {row["source"] for row in payload["results"]} >= {
        "duckduckgo",
        "wikipedia",
        "openalex",
    }
