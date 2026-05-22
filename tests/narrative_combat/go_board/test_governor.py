"""The study move is governed: allowlist gates it, every call is audited, results are cached."""

from __future__ import annotations

from src.narrative_combat.go_board.governor import SearchGovernor, StubSearchBackend


def test_stub_backend_returns_nothing_and_audits_allow():
    gov = SearchGovernor()
    results = gov.study("xianxia footwork", seed=1337, turn_index=3)
    assert results == ()
    assert len(gov.audit) == 1
    assert gov.audit[0].decision == "allow"
    assert gov.audit[0].backend == "stub"


def test_allowlist_denies_off_topic_queries():
    gov = SearchGovernor(allow_terms=["lawful", "shrine"])
    assert gov.study("how to pick a lock", seed=1, turn_index=1) == ()
    assert gov.audit[-1].decision == "deny"
    # an on-topic query is allowed
    gov.study("shrine wards", seed=1, turn_index=2)
    assert gov.audit[-1].decision == "allow"


def test_results_are_cached_by_seed_turn_query():
    class CountingBackend(StubSearchBackend):
        name = "counting"

        def __init__(self):
            self.calls = 0

        def search(self, query):
            self.calls += 1
            return ("a fact",)

    backend = CountingBackend()
    gov = SearchGovernor(backend=backend)
    first = gov.study("ash law", seed=42, turn_index=5)
    second = gov.study("ash law", seed=42, turn_index=5)
    assert first == second == ("a fact",)
    assert backend.calls == 1  # second call served from cache
    assert gov.audit[-1].decision == "cached"


def test_backend_failure_degrades_to_empty():
    class BrokenBackend(StubSearchBackend):
        name = "broken"

        def search(self, query):
            raise RuntimeError("network down")

    gov = SearchGovernor(backend=BrokenBackend())
    assert gov.study("anything", seed=7, turn_index=1) == ()
    assert gov.audit[-1].decision == "allow"  # it was permitted; the backend just yielded nothing
