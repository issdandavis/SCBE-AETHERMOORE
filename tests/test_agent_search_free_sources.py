from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

REPO_ROOT = Path(__file__).resolve().parents[1]
SEARCH_JS = REPO_ROOT / "api" / "agent" / "search.js"


def test_agent_search_declares_zero_credit_sources() -> None:
    source = SEARCH_JS.read_text(encoding="utf-8")

    for name in [
        "duckduckgo",
        "wikipedia",
        "openalex",
        "crossref",
        "arxiv",
        "pubmed",
        "github",
        "npm",
        "hackernews",
    ]:
        assert name in source

    assert "zero-credit-public-sources" in source
    assert "@google-cloud" not in source
    assert "BIGQUERY" not in source


def test_agent_search_commonjs_endpoint_with_mocked_free_sources() -> None:
    script = textwrap.dedent(r"""
        global.fetch = async (url) => {
          if (String(url).includes("wikipedia.org")) {
            return {
              ok: true,
              json: async () => ({
                query: {
                  search: [
                    { title: "Hyperbolic geometry", snippet: "non-Euclidean geometry" }
                  ]
                }
              })
            };
          }
          if (String(url).includes("registry.npmjs.org")) {
            return {
              ok: true,
              json: async () => ({
                objects: [
                  {
                    package: {
                      name: "scbe-aethermoore",
                      description: "SCBE package",
                      links: { npm: "https://www.npmjs.com/package/scbe-aethermoore" },
                      version: "4.0.3"
                    },
                    score: { final: 1 }
                  }
                ]
              })
            };
          }
          throw new Error(`unexpected URL ${url}`);
        };

        const handler = require("./api/agent/search.js");
        const req = {
          method: "POST",
          body: {
            query: "scbe hyperbolic",
            sources: ["wikipedia", "npm"],
            limit: 4
          }
        };
        const res = {
          headers: {},
          statusCode: 200,
          setHeader(k, v) { this.headers[k] = v; },
          status(code) { this.statusCode = code; return this; },
          json(payload) {
            console.log(JSON.stringify({ statusCode: this.statusCode, payload }));
          }
        };

        Promise.resolve(handler(req, res)).catch((error) => {
          console.error(error);
          process.exit(1);
        });
        """)

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

    output = json.loads(proc.stdout)
    assert output["statusCode"] == 200
    payload = output["payload"]
    assert payload["ok"] is True
    assert payload["cost"] == "zero-credit-public-sources"
    assert payload["source_count"] == 2
    assert payload["result_count"] == 2
    assert {result["source"] for result in payload["results"]} == {"wikipedia", "npm"}
