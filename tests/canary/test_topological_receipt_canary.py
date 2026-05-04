"""Pytest wrapper for the topological-receipt canary smoke suite.

Runs the same logic as ``scripts/smoke_topological_receipt.py`` but
reports per-canary failures via standard pytest assertions so CI sees
the regression directly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from python.scbe.tri_braid_embedding import governance_receipt

CANARY_FILE = Path(__file__).parent / "topological_receipt_canaries.json"


@pytest.fixture(scope="module")
def canary_payload() -> dict:
    assert CANARY_FILE.exists(), "canary file missing — run scripts/build_topological_canaries.py to regenerate"
    return json.loads(CANARY_FILE.read_text(encoding="utf-8"))


def test_canary_schema_is_current(canary_payload: dict) -> None:
    assert canary_payload["schema_version"] == "scbe_topological_canary_v1"
    assert canary_payload["n"] == len(canary_payload["canaries"])
    assert canary_payload["n"] >= 25, "smoke suite below minimum canary count"


def test_canary_set_covers_all_six_tongues(canary_payload: dict) -> None:
    tongues = {c["expected"]["tongue"] for c in canary_payload["canaries"]}
    assert tongues == {"KO", "AV", "RU", "CA", "UM", "DR"}, f"tongues covered: {tongues}"


def test_canary_set_covers_multiple_decisions(canary_payload: dict) -> None:
    decisions = {c["expected"]["decision"] for c in canary_payload["canaries"]}
    assert len(decisions) >= 2, f"decisions covered: {decisions}"
    assert decisions <= {"ALLOW", "QUARANTINE", "DENY"}


def test_canary_set_covers_multiple_governance_states(canary_payload: dict) -> None:
    states = {c["expected"]["governance_state"] for c in canary_payload["canaries"]}
    assert len(states) >= 2, f"governance states covered: {states}"


def test_every_canary_matches_ground_truth(canary_payload: dict) -> None:
    failures = []
    for canary in canary_payload["canaries"]:
        params = canary.get("params") or {}
        actual = governance_receipt(
            canary["prompt"],
            masked_row=int(params.get("masked_row", 0)),
            masked_col=int(params.get("masked_col", 0)),
        )
        for key, want in canary["expected"].items():
            got = actual[key]
            if got != want:
                failures.append(
                    {
                        "category": canary.get("category", "?"),
                        "prompt": canary["prompt"][:60],
                        "key": key,
                        "expected": want,
                        "actual": got,
                    }
                )

    assert not failures, f"{len(failures)} canary mismatches detected; first three: {failures[:3]}"


def test_ordered_hashes_are_unique_across_canaries(canary_payload: dict) -> None:
    """Distinct (prompt, params) pairs must produce distinct ordered hashes.

    If two prompts collide on ordered_hash the smoke suite is too weak to
    detect a regression in either branch.
    """
    seen: dict[str, str] = {}
    for canary in canary_payload["canaries"]:
        ordered_hash = canary["expected"]["ordered_hash"]
        signature_key = f"{canary['prompt']}|{canary.get('params')}"
        if ordered_hash in seen and seen[ordered_hash] != signature_key:
            pytest.fail(
                f"hash collision: {ordered_hash[:16]} shared by " f"{seen[ordered_hash]!r} and {signature_key!r}"
            )
        seen[ordered_hash] = signature_key
