import pytest

from scripts.aetherbrowser import api_server


def test_arena_numeric_input_stays_local_command() -> None:
    response = api_server._arena_local_command_response("2")

    assert response is not None
    assert "No model deliberation is needed" in response
    assert "active numbered menu" in response


@pytest.mark.asyncio
async def test_cli_dispatch_compiles_coding_harness_plan() -> None:
    result = await api_server._cli_dispatch(
        ["harness", "plan", "explain", "arena", "route"]
    )

    assert result["ok"] is True
    assert result["lane"] == "coding-harness"
    plan = result["result"]
    assert plan["schema_version"] == "scbe_command_plan_v1"
    assert plan["intent"]["permission_mode"] == "observe"
    assert plan["policy"]["decision"] != "DENY"


@pytest.mark.asyncio
async def test_cli_dispatch_rejects_mutating_harness_mode() -> None:
    result = await api_server._cli_dispatch(
        ["harness", "plan", "delete", "everything", "--permission-mode", "execute"]
    )

    assert result["ok"] is False
    assert "observe, assist" in result["error"]


@pytest.mark.asyncio
async def test_cli_dispatch_agent_bus_uses_allowlisted_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def fake_run_subprocess(cmd: list[str], timeout: int = 60) -> dict[str, object]:
        seen["cmd"] = cmd
        seen["timeout"] = timeout
        return {
            "stdout": '{"perf": null, "reason": "no_events"}',
            "stderr": "",
            "exit_code": 0,
        }

    monkeypatch.setattr(api_server, "_run_subprocess", fake_run_subprocess)

    result = await api_server._cli_dispatch(["bus", "perf"])

    assert result["ok"] is True
    assert result["lane"] == "agent-bus"
    assert seen["cmd"] == [
        api_server.sys.executable,
        "-m",
        "agents.agent_bus_cli",
        "perf",
    ]
    assert seen["timeout"] == 30


@pytest.mark.asyncio
async def test_cli_dispatch_game_smoke_writes_narrative_packet(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api_server, "ROOT", tmp_path)

    result = await api_server._cli_dispatch(
        ["game", "smoke", "narrative-combat", "--seed", "1337"]
    )

    assert result["ok"] is True
    assert result["lane"] == "game-production"
    payload = result["result"]
    assert payload["schema"] == "scbe.narrative_combat.fight.v1"
    assert payload["encounter_id"] == "boss_duel_demo"
    assert payload["seed"] == 1337
    assert payload["beat_count"] >= 1
    assert payload["winner"] == "Wu Jin"
    assert (tmp_path / payload["artifact"]).exists()


@pytest.mark.asyncio
async def test_cli_dispatch_game_smoke_rejects_unknown_target() -> None:
    result = await api_server._cli_dispatch(["game", "smoke", "unbounded-autonomy"])

    assert result["ok"] is False
    assert "Unknown game smoke target" in result["error"]


@pytest.mark.asyncio
async def test_cli_dispatch_does_not_allow_raw_shell_commands() -> None:
    result = await api_server._cli_dispatch(["powershell", "-Command", "Get-ChildItem"])

    assert result["ok"] is False
    assert "Unknown command" in result["error"]
