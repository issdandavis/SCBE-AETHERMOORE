from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "system" / "agent_context_vault.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("agent_context_vault", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_append_event_writes_agent_and_channel_streams(tmp_path: Path) -> None:
    module = _load_module()

    event = module.append_event(
        root=tmp_path,
        agent_id="agent.codex",
        channel_id="build-vault",
        task_id="CTX-1",
        summary="Codex creates the vault contract.",
        proof=["scripts/system/agent_context_vault.py"],
        next_action="Claude tails the channel.",
    )

    assert event["event_id"].startswith("ctx-")
    assert (tmp_path / "agents" / "agent.codex" / "rolling.jsonl").exists()
    assert (tmp_path / "channels" / "build-vault.jsonl").exists()


def test_digest_agent_creates_small_state_with_source_hash(tmp_path: Path) -> None:
    module = _load_module()
    module.append_event(
        root=tmp_path,
        agent_id="agent.kimi",
        channel_id="scale-test",
        task_id="CTX-2",
        summary="Kimi reviews compact context.",
        next_action="Return ACK and patch suggestion.",
    )

    state = module.digest_agent(root=tmp_path, agent_id="agent.kimi", max_chars=120)

    assert state["schema_version"] == "scbe_agent_context_state_v1"
    assert state["agent_id"] == "agent.kimi"
    assert state["state_hash"]
    assert state["source_event_count"] == 1
    assert len(state["compact_context"]) <= 120
    assert (tmp_path / "agents" / "agent.kimi" / "state.json").exists()


def test_simulate_team_builds_channel_states_and_scoreboard(tmp_path: Path) -> None:
    module = _load_module()

    result = module.simulate_team(
        root=tmp_path,
        task_id="ai-context-vault-smoke",
        agents=["agent.codex", "agent.claude", "agent.kimi"],
    )

    assert len(result["events"]) == 3
    assert len(result["states"]) == 3
    assert result["scoreboard"]["ready_for_scale_test"] is True
    assert set(result["scoreboard"]["state_hashes"]) == {"agent.codex", "agent.claude", "agent.kimi"}
    assert (tmp_path / "scoreboards" / "ai-context-vault-smoke.json").exists()


def test_likely_secret_text_is_rejected(tmp_path: Path) -> None:
    module = _load_module()

    try:
        module.append_event(
            root=tmp_path,
            agent_id="agent.codex",
            channel_id="secrets",
            task_id="CTX-3",
            summary="sk-test_abcdefghijklmnopqrstuvwxyz",
        )
    except ValueError as exc:
        assert "secret" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("secret-like context should be rejected")


def test_cli_simulate_outputs_json(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/system/agent_context_vault.py",
            "--root",
            str(tmp_path),
            "simulate",
            "--task-id",
            "cli-smoke",
            "--agents",
            "agent.codex,agent.claude",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["scoreboard"]["task_id"] == "cli-smoke"
    assert len(payload["events"]) == 2
