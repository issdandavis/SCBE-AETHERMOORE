from __future__ import annotations

import pytest

from scripts.eval import corridor_ranker_baseline as harness


def test_heldout_synonym_split_rejects_alias_table_self_certification(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harness, "_SEMANTIC_ALIASES", {"shipping": {"parcel"}})

    audit = harness._audit_heldout_alias_isolation()

    assert audit["isolated"] is False
    assert audit["violations"]
    with pytest.raises(ValueError, match="heldout_synonym split is no longer isolated"):
        harness.build_dataset()


def test_heldout_synonym_split_is_isolated_for_token_overlap_router() -> None:
    audit = harness._audit_heldout_alias_isolation()

    assert audit["isolated"] is True
    assert audit["violations"] == []
