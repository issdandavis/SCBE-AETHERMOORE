from pathlib import Path

from hydra.ledger import Ledger


def test_ledger_falls_back_to_repo_runtime_when_requested_path_is_unwritable(monkeypatch, tmp_path):
    requested = tmp_path / "readonly-home" / "ledger.db"
    fallback = tmp_path / "runtime-fallback" / "ledger.db"

    monkeypatch.setattr(Ledger, "_repo_fallback_db", classmethod(lambda cls: fallback))
    monkeypatch.setattr(
        Ledger,
        "_can_write_path",
        staticmethod(lambda path: Path(path) == fallback),
    )

    ledger = Ledger(db_path=str(requested))
    ledger.remember("hello", {"ok": True}, category="test", importance=0.9)

    assert Path(ledger.db_path) == fallback
    assert ledger.recall("hello") == {"ok": True}
