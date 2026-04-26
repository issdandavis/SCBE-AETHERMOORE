from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_metric():
    path = ROOT / "scripts" / "eval" / "public_method_resilience_score.py"
    spec = importlib.util.spec_from_file_location("public_method_resilience_score_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_method_resilience_passes_known_method_secure_state() -> None:
    metric = load_metric()

    result = metric.score_public_method_resilience(
        {
            "controls": {
                "method_public": True,
                "keys_private": True,
                "authority_checked": True,
                "tamper_evident_ledger": True,
                "dual_tokenizer_verification": True,
                "ack_or_receipt_required": True,
                "replay_or_duplicate_protection": True,
                "red_team_method_exposed_tested": True,
            }
        }
    )

    assert result["verdict"] == "pass"
    assert result["score"] == 1.0


def test_public_method_resilience_fails_security_by_obscurity_and_direct_execution() -> None:
    metric = load_metric()

    result = metric.score_public_method_resilience(
        {
            "controls": {
                "method_public": False,
                "keys_private": False,
            },
            "risks": {
                "depends_on_hidden_algorithm": True,
                "direct_execution_from_message": True,
            },
        }
    )

    assert result["verdict"] == "fail"
    assert result["score"] == 0.0
    assert "direct_execution_from_message" in result["penalties"]
