"""Public-API contract for ``src.governance.stage6_constrained_decoding``.

Mirrors ``tests/test_stage6_constrained_decoding.py`` against the canonical
import path. The legacy test imports from
``scripts.eval.score_stage6_constrained_decoding`` (which now re-exports from
this module); this test imports directly so the contract holds even if the
legacy script is removed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.governance.stage6_constrained_decoding import (
    PREFIX_ORDER,
    build_prefix,
    kind_from_id,
    score_prompt,
    stage6_constrained_response,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "config" / "model_training" / "stage6_atomic_workflow_eval_contract.json"


@pytest.fixture(scope="module")
def contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_kind_detection_for_every_contract_prompt(contract):
    for prompt in contract["prompts"]:
        kind = kind_from_id(prompt["id"])
        assert kind is not None, f"no kind detected for {prompt['id']!r}"
        assert kind in PREFIX_ORDER


def test_prefix_covers_every_required_token(contract):
    for prompt in contract["prompts"]:
        kind = kind_from_id(prompt["id"])
        assert kind is not None
        prefix_lower = build_prefix(kind).lower()
        for required in prompt.get("required", []):
            assert required.lower() in prefix_lower, f"required token {required!r} not in prefix for {prompt['id']!r}"


def test_prefix_does_not_trigger_any_forbidden_token(contract):
    for prompt in contract["prompts"]:
        kind = kind_from_id(prompt["id"])
        prefix_lower = build_prefix(kind).lower()
        for forbidden in prompt.get("forbidden", []):
            assert forbidden.lower() not in prefix_lower, (
                f"forbidden token {forbidden!r} appears in prefix for " f"{prompt['id']!r}"
            )


def test_score_prompt_passes_on_prefix_alone(contract):
    for prompt in contract["prompts"]:
        kind = kind_from_id(prompt["id"])
        prefix = build_prefix(kind)
        result = score_prompt(prompt, prefix)
        assert result["ok"], (
            f"{prompt['id']} did not pass on prefix alone: "
            f"missing={result['missing_required']} "
            f"forbidden={result['triggered_forbidden']}"
        )


def test_score_prompt_fails_on_empty_response(contract):
    for prompt in contract["prompts"]:
        result = score_prompt(prompt, "")
        assert not result["ok"]
        assert result["missing_required"]


def test_kind_from_id_returns_none_for_unknown_id():
    assert kind_from_id("") is None
    assert kind_from_id("totally_unrelated_prompt") is None


def test_stage6_constrained_response_unknown_kind_is_safe_failure():
    """Helper must surface unknown-kind as ok=False with an error field
    rather than raising — production callers handle the dict, not exceptions.
    """
    verdict = stage6_constrained_response(
        model=None,
        tokenizer=None,
        prompt={"id": "not_a_stage6_kind", "required": ["foo"], "prompt": "x"},
        max_new_tokens=8,
    )
    assert verdict["ok"] is False
    assert verdict["kind"] is None
    assert "error" in verdict
    assert verdict["missing_required"] == ["foo"]


def test_build_prefix_renders_underscored_tokens_in_backticks():
    """Tokens with underscores get backticked so chat templates and
    markdown renderers don't mangle them; tokens without underscores stay
    bare to keep the prefix human-readable.
    """
    prefix = build_prefix("resource_jump_cancel")
    assert "`transmit_burst`" in prefix
    assert "`steady-state fallback`" not in prefix
    assert "steady-state fallback" in prefix
    assert prefix.startswith("required-tokens: ")
    assert prefix.endswith(" ::")
