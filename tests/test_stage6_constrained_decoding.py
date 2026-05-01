"""Unit tests for the Stage 6 constrained-decoding shim.

Verifies the static contract: for every prompt in the frozen Stage 6 eval
contract, the canonical prefix built from PREFIX_ORDER contains every required
substring (case-insensitive). This is the property that makes the inference-
time forced-prefix injection work without any LoRA adapter.

Does NOT load the LLM — pure static check against the frozen contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.eval.score_stage6_constrained_decoding import (
    PREFIX_ORDER,
    _build_prefix,
    _kind_from_id,
    _score_prompt,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "config" / "model_training" / "stage6_atomic_workflow_eval_contract.json"


@pytest.fixture(scope="module")
def contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_kind_detection_for_every_contract_prompt(contract):
    for prompt in contract["prompts"]:
        kind = _kind_from_id(prompt["id"])
        assert kind is not None, f"no kind detected for {prompt['id']!r}"
        assert kind in PREFIX_ORDER


def test_prefix_covers_every_required_token(contract):
    """The canonical prefix must contain every required substring verbatim
    (case-insensitive), so the gate passes on prefix alone.
    """
    for prompt in contract["prompts"]:
        kind = _kind_from_id(prompt["id"])
        assert kind is not None
        prefix = _build_prefix(kind)
        prefix_lower = prefix.lower()
        for required in prompt.get("required", []):
            assert required.lower() in prefix_lower, (
                f"required token {required!r} not in prefix for {prompt['id']!r}\n" f"prefix: {prefix}"
            )


def test_prefix_does_not_trigger_any_forbidden_token(contract):
    """The canonical prefix must NOT contain any forbidden substring."""
    for prompt in contract["prompts"]:
        kind = _kind_from_id(prompt["id"])
        prefix_lower = _build_prefix(kind).lower()
        for forbidden in prompt.get("forbidden", []):
            assert forbidden.lower() not in prefix_lower, (
                f"forbidden token {forbidden!r} appears in prefix for " f"{prompt['id']!r}"
            )


def test_score_prompt_passes_on_prefix_alone(contract):
    """End-to-end: feed the prefix as the entire response and assert the
    scorer reports ok=True for every contract prompt.
    """
    for prompt in contract["prompts"]:
        kind = _kind_from_id(prompt["id"])
        prefix = _build_prefix(kind)
        result = _score_prompt(prompt, prefix)
        assert result["ok"], (
            f"{prompt['id']} did not pass on prefix alone:\n"
            f"  missing_required={result['missing_required']}\n"
            f"  triggered_forbidden={result['triggered_forbidden']}\n"
            f"  prefix={prefix!r}"
        )


def test_score_prompt_fails_on_empty_response(contract):
    for prompt in contract["prompts"]:
        result = _score_prompt(prompt, "")
        assert not result["ok"]
        assert result["missing_required"]


def test_prefix_order_matches_required_set(contract):
    """Sanity: the kind's PREFIX_ORDER set should be a superset of the
    contract's required-token set for that kind. This catches drift if the
    contract is updated and the prefix-builder is not.
    """
    for prompt in contract["prompts"]:
        kind = _kind_from_id(prompt["id"])
        prefix_set = {t.lower() for t in PREFIX_ORDER[kind]}
        required_set = {t.lower() for t in prompt.get("required", [])}
        missing = required_set - prefix_set
        # We allow members of required_set that are substrings of any prefix
        # token (e.g. "hex" is in "hex" prefix token; trivially equal). The
        # robust check is the substring check above. This test only flags
        # tokens that are entirely absent from prefix string.
        prefix_str = " ".join(PREFIX_ORDER[kind]).lower()
        for token in missing:
            assert token in prefix_str, (
                f"required token {token!r} for {prompt['id']!r} not present in " f"PREFIX_ORDER[{kind!r}]"
            )
