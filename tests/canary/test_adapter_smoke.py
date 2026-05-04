"""Tests for the adapter-aware smoke runner.

Exercises the comparison logic and the dry-run path so the smoke
machinery is regression-tested even without HF inference access.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.smoke_adapter_topological_receipt import (
    DECISION_LEVEL,
    compare_decisions,
    echo_adapter,
    run_smoke,
)

CANARY_FILE = Path(__file__).parent / "topological_receipt_canaries.json"


def test_decision_levels_are_canonical_order():
    assert DECISION_LEVEL["DENY"] < DECISION_LEVEL["QUARANTINE"] < DECISION_LEVEL["ALLOW"]


@pytest.mark.parametrize(
    "prompt,response,status",
    [
        ("ALLOW", "ALLOW", "match"),
        ("QUARANTINE", "QUARANTINE", "match"),
        ("DENY", "DENY", "match"),
        ("ALLOW", "QUARANTINE", "drift"),
        ("QUARANTINE", "ALLOW", "drift"),
        ("QUARANTINE", "DENY", "drift"),
        ("DENY", "QUARANTINE", "drift"),
        ("ALLOW", "DENY", "regression"),
        ("DENY", "ALLOW", "regression"),
    ],
)
def test_compare_decisions_classifies_each_pair(prompt, response, status):
    result = compare_decisions(prompt, response)
    assert result["status"] == status
    assert result["delta"] == DECISION_LEVEL[response] - DECISION_LEVEL[prompt]


def test_dry_run_smoke_passes_against_canaries():
    """Echo adapter returns the prompt verbatim so every comparison must match."""
    if not CANARY_FILE.exists():
        pytest.skip("canary file not generated yet")

    result = run_smoke(
        CANARY_FILE,
        adapter=echo_adapter,
        model="<dry-run>",
        token="<dry-run>",
    )
    assert result["matches"] == result["n"]
    assert result["drifts"] == 0
    assert result["regressions"] == 0
    assert result["errors"] == 0


def test_dry_run_respects_max_canaries():
    if not CANARY_FILE.exists():
        pytest.skip("canary file not generated yet")

    result = run_smoke(
        CANARY_FILE,
        adapter=echo_adapter,
        model="<dry-run>",
        token="<dry-run>",
        max_canaries=3,
    )
    assert result["n"] == 3
    assert result["matches"] == 3


def test_failing_adapter_records_errors_without_crashing():
    if not CANARY_FILE.exists():
        pytest.skip("canary file not generated yet")

    def broken_adapter(prompt, **_):
        raise RuntimeError("simulated adapter outage")

    result = run_smoke(
        CANARY_FILE,
        adapter=broken_adapter,
        model="<broken>",
        token="<broken>",
        max_canaries=4,
    )
    assert result["errors"] == 4
    assert result["matches"] == 0


def test_smoke_output_is_json_serializable():
    if not CANARY_FILE.exists():
        pytest.skip("canary file not generated yet")

    result = run_smoke(
        CANARY_FILE,
        adapter=echo_adapter,
        model="<dry-run>",
        token="<dry-run>",
        max_canaries=5,
    )
    payload = json.dumps(result)
    restored = json.loads(payload)
    assert restored["n"] == 5
    assert restored["schema_version"] == "scbe_adapter_smoke_v1"
