from __future__ import annotations

from pathlib import Path

from scripts.eval.catalog_token_steering_results import (
    build_decision_matrix,
    summarize_artifacts,
)


def test_catalog_routes_missing_required_to_constrained_decoding(tmp_path: Path) -> None:
    artifact = tmp_path / "constrained.json"
    artifact.write_text(
        """
        {
          "schema_version": "scbe_multi_seed_gate_eval_v1",
          "trials": [
            {
              "passed": false,
              "checker_meta": {
                "missing_required": ["def foo"],
                "triggered_forbidden": []
              }
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    matrix = build_decision_matrix(summarize_artifacts([artifact]))

    assert matrix["recommendation"]["primary_next_action"] == "constrained_decoding_or_contract_prefix"


def test_catalog_routes_green_artifacts_to_coverage_hardening(tmp_path: Path) -> None:
    artifact = tmp_path / "local_constrained.json"
    artifact.write_text(
        """
        {
          "schema": "scbe_bijective_tongue_gate_v3_constrained_decoding",
          "results": [
            {
              "tests_passed": true,
              "repaired_tests_passed": true,
              "syntax_ok": true,
              "exec_ok": true
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    matrix = build_decision_matrix(summarize_artifacts([artifact]))

    assert matrix["recommendation"]["primary_next_action"] == "harden_ci_and_expand_coverage"
