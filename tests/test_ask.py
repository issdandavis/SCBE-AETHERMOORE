"""ask: summon an AI in the terminal -- returns the model's TEXT (never executed here), logs an
audit receipt, and fails honestly (no fabricated answer) on a dead endpoint. Mocked transport;
no live model call."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm import ask as ask_mod  # noqa: E402
from python.helm.ask import ask, log_ask  # noqa: E402


def test_ask_returns_model_text(monkeypatch):
    monkeypatch.setattr(ask_mod.fg, "_chat", lambda messages, **kw: "a Poincare ball is a model of hyperbolic space")
    r = ask("what is a Poincare ball?", model="mock")
    assert r["ok"] is True
    assert isinstance(r["response"], str) and "hyperbolic" in r["response"]
    assert r["model"] == "mock"


def test_dead_endpoint_returns_no_answer_not_a_guess(monkeypatch):
    def boom(messages, **kw):
        raise ConnectionError("no model running")

    monkeypatch.setattr(ask_mod.fg, "_chat", boom)
    r = ask("anything")
    assert r["ok"] is False and r["response"] == ""  # honest: empty, never fabricated
    assert "ConnectionError" in r["error"]


def test_log_ask_writes_an_auditable_receipt_without_leaking_the_full_prompt(tmp_path, monkeypatch):
    monkeypatch.setattr(ask_mod, "RECEIPTS_DIR", tmp_path)
    secret = "SECRET-PROMPT-" + "x" * 500
    r = {"ok": True, "model": "mock", "response": "ok", "error": None, "started_at": "t0", "finished_at": "t1"}
    path = log_ask(r, secret)
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert rec["schema"] == "aetherdesk_ask_receipt_v1"
    assert len(rec["prompt_digest"]) == 64  # sha256 of the full prompt (audit), not the prompt itself
    assert rec["prompt_preview"] == secret[:200]
    assert ("x" * 500) not in json.dumps(rec)  # the full prompt body is not stored verbatim
    assert "not executed" in rec["note"]


def test_main_prints_response_and_exits(monkeypatch, tmp_path):
    monkeypatch.setattr(ask_mod, "RECEIPTS_DIR", tmp_path)
    monkeypatch.setattr(ask_mod.fg, "_chat", lambda messages, **kw: "42")
    assert ask_mod.main(["what is 6*7?", "--model", "mock"]) == 0


def test_main_fails_loudly_on_dead_endpoint(monkeypatch, tmp_path):
    monkeypatch.setattr(ask_mod, "RECEIPTS_DIR", tmp_path)

    def boom(messages, **kw):
        raise ConnectionError("down")

    monkeypatch.setattr(ask_mod.fg, "_chat", boom)
    assert ask_mod.main(["q"]) == 1  # non-zero, no answer printed
