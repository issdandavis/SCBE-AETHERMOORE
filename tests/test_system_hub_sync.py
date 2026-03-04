from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    repo_root = Path(__file__).resolve().parents[1]
    mod_path = repo_root / "scripts" / "system" / "system_hub_sync.py"
    spec = importlib.util.spec_from_file_location("system_hub_sync", mod_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_should_emit_with_missing_state_file(tmp_path: Path) -> None:
    mod = _load_module()
    state_file = tmp_path / "zapier_state.json"

    assert mod.should_emit_with_cooldown(state_file, "sync_completed", 900) is True


def test_mark_then_cooldown_blocks_emit(tmp_path: Path) -> None:
    mod = _load_module()
    state_file = tmp_path / "zapier_state.json"

    mod.mark_emitted(state_file, "sync_completed")

    assert mod.should_emit_with_cooldown(state_file, "sync_completed", 3600) is False


def test_maybe_emit_skips_when_cooldown_active(tmp_path: Path, monkeypatch, capsys) -> None:
    mod = _load_module()
    state_file = tmp_path / "zapier_state.json"
    mod.mark_emitted(state_file, "sync_completed")

    called = {"value": False}

    def _fake_post(_url: str, _payload: dict, _dry_run: bool) -> None:
        called["value"] = True

    monkeypatch.setattr(mod, "post_zapier_event", _fake_post)

    emitted = mod.maybe_emit_zapier_event(
        state_file=state_file,
        webhook_url="https://hooks.zapier.com/hooks/catch/test/test/",
        payload={"event": "sync_completed"},
        dry_run=False,
        cooldown_seconds=3600,
    )

    assert emitted is False
    assert called["value"] is False
    out = capsys.readouterr().out
    assert "[zapier] skipped sync_completed" in out


def test_maybe_emit_posts_and_marks_state(tmp_path: Path, monkeypatch, capsys) -> None:
    mod = _load_module()
    state_file = tmp_path / "zapier_state.json"

    calls: list[dict] = []

    def _fake_post(_url: str, payload: dict, _dry_run: bool) -> None:
        calls.append(payload)

    monkeypatch.setattr(mod, "post_zapier_event", _fake_post)

    emitted = mod.maybe_emit_zapier_event(
        state_file=state_file,
        webhook_url="https://hooks.zapier.com/hooks/catch/test/test/",
        payload={"event": "sync_completed", "ok": True},
        dry_run=False,
        cooldown_seconds=0,
    )

    assert emitted is True
    assert len(calls) == 1

    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert "sync_completed" in state

    out = capsys.readouterr().out
    assert "[zapier] emitted sync_completed" in out
