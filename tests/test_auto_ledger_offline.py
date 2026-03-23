from __future__ import annotations

from src.training import auto_ledger


def test_get_phdm_classifier_respects_disable_flag(monkeypatch) -> None:
    monkeypatch.setenv("SCBE_DISABLE_HF_CLASSIFIER", "1")
    monkeypatch.setattr(auto_ledger, "_phdm_classifier", None)
    assert auto_ledger.get_phdm_classifier() is None
