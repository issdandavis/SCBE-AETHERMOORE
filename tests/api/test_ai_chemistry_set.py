from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_node_json(source: str) -> dict:
    completed = subprocess.run(
        ["node", "-e", source],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_ai_chemistry_set_balances_equation_with_receipt() -> None:
    result = run_node_json("""
        const handler = require('./api/agent/ai-chemistry-set');
        const req = {
          method: 'POST',
          body: { input: 'C3H8 + O2 -> CO2 + H2O', level: 'learner' },
          headers: {}
        };
        const res = {
          code: 200,
          headers: {},
          setHeader(name, value) { this.headers[name] = value; },
          status(code) { this.code = code; return this; },
          json(payload) { this.payload = payload; return this; },
          end() { return this; }
        };
        Promise.resolve(handler(req, res)).then(() => {
          console.log(JSON.stringify({code: res.code, payload: res.payload}));
        }).catch((error) => {
          console.error(error);
          process.exit(1);
        });
        """)

    assert result["code"] == 200
    payload = result["payload"]
    assert payload["schema_version"] == "aethermoore_ai_chemistry_set_v1"
    assert payload["product"] == "AI Chemistry Set"
    assert payload["balance"]["balanced_equation"] == "C3H8 + 5O2 -> 3CO2 + 4H2O"
    assert payload["balance"]["math"] == "exact rational nullspace over the element conservation matrix"
    assert payload["receipt_id"].startswith("chemset_")
    assert "visual" in payload["sellable_output"]["offer"].lower()


def test_ai_chemistry_set_page_contains_visual_bench() -> None:
    page = (REPO_ROOT / "docs" / "ai-chemistry-set.html").read_text(encoding="utf-8")

    assert "Visual chemistry with real balancing math" in page
    assert "<canvas" in page
    assert "drawFlask" in page
    assert "/api/agent/ai-chemistry-set" in page
