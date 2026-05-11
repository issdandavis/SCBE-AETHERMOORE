from __future__ import annotations

from scripts.eval.geoseal_functional_receipts import build_receipts


def test_build_receipts_summarizes_geoseal_packets(monkeypatch):
    def fake_packet(source: str, source_name: str, language: str, timeout: int):
        return (
            {
                "transport": {
                    "source_sha256": "source",
                    "token_sha256": "token",
                    "tongue": "AV",
                },
                "tokenizer": {"token_count": 4},
                "lexical_tokens": ["function", "evaluate"],
                "stisa": {
                    "version": "scbe-stisa-surface-v1",
                    "field_definitions": [{"name": "Z_proxy"}],
                    "token_rows": [{"token": "function"}],
                },
                "atomic_states": [{"token": "function", "tau": 0}],
                "semantic_expression": {"label": "generic_program_bin", "quarks": ["function_shape"]},
                "route_ir": {"route": {"signature": "op:add"}, "hashes": {"plan_sha256": "plan"}},
            },
            "",
        )

    monkeypatch.setattr("scripts.eval.geoseal_functional_receipts._run_code_packet", fake_packet)
    report = {
        "benchmark": "typescript_game_debug_functional_v1",
        "results": [
            {
                "adapter": "ollama:test",
                "summary": {"tasks": 1, "passed": 1},
                "tasks": [
                    {
                        "task_id": "score_add",
                        "passed": True,
                        "initial_passed": True,
                        "extracted_code": "function evaluate(input, state) { return 1; }",
                        "checks": [],
                    }
                ],
            }
        ],
    }

    payload = build_receipts(report, timeout=1)
    result = payload["results"][0]
    task = result["tasks"][0]

    assert payload["schema"] == "scbe_geoseal_functional_receipts_v1"
    assert result["receipt_summary"]["geoseal_ok"] == 1
    assert task["geoseal_ok"] is True
    assert task["stisa_version"] == "scbe-stisa-surface-v1"
    assert task["stisa_row_count"] == 1
    assert task["semantic_quarks"] == ["function_shape"]
