import pytest
from fastapi.testclient import TestClient

from scripts.aetherbrowser import api_server


def test_ops_email_fails_closed_without_admin_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SCBE_OPS_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("SCBE_RUNTIME_GATE_ADMIN_TOKEN", raising=False)
    monkeypatch.setattr(
        api_server,
        "_run_subprocess",
        lambda *args, **kwargs: pytest.fail("operator subprocess must not run without an admin token"),
    )

    with TestClient(api_server.app) as client:
        response = client.post("/api/ops/check-email")

    assert response.status_code == 403
    assert response.json() == {"detail": "operator endpoints disabled (set SCBE_OPS_ADMIN_TOKEN to enable)"}


def test_ops_email_rejects_invalid_admin_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCBE_OPS_ADMIN_TOKEN", "expected-token")
    monkeypatch.delenv("SCBE_RUNTIME_GATE_ADMIN_TOKEN", raising=False)
    monkeypatch.setattr(
        api_server,
        "_run_subprocess",
        lambda *args, **kwargs: pytest.fail("operator subprocess must not run with an invalid admin token"),
    )

    with TestClient(api_server.app) as client:
        response = client.post("/api/ops/check-email", headers={"X-Admin-Token": "wrong-token"})

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid or missing X-Admin-Token"}


def test_ops_email_allows_matching_admin_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCBE_OPS_ADMIN_TOKEN", "expected-token")
    monkeypatch.delenv("SCBE_RUNTIME_GATE_ADMIN_TOKEN", raising=False)
    monkeypatch.setattr(
        api_server,
        "_run_subprocess",
        lambda *args, **kwargs: {"stdout": "digest", "stderr": "", "exit_code": 0},
    )

    with TestClient(api_server.app) as client:
        response = client.post("/api/ops/check-email", headers={"X-Admin-Token": "expected-token"})

    assert response.status_code == 200
    assert response.json() == {"output": "digest", "exit_code": 0, "errors": None}


def test_cli_email_alias_is_guarded_without_admin_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCBE_OPS_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("SCBE_RUNTIME_GATE_ADMIN_TOKEN", raising=False)
    monkeypatch.setattr(
        api_server,
        "_run_subprocess",
        lambda *args, **kwargs: pytest.fail("CLI operator subprocess must not run without an admin token"),
    )

    with TestClient(api_server.app) as client:
        response = client.post("/api/cli/run", json={"command": "ops email"})

    assert response.status_code == 403


def test_ops_preflight_does_not_authorize_following_post(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCBE_OPS_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("SCBE_RUNTIME_GATE_ADMIN_TOKEN", raising=False)
    monkeypatch.setattr(
        api_server,
        "_run_subprocess",
        lambda *args, **kwargs: pytest.fail("CORS preflight must not invoke or authorize the operator subprocess"),
    )

    with TestClient(api_server.app) as client:
        preflight = client.options(
            "/api/ops/check-email",
            headers={
                "Origin": "https://attacker.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "x-admin-token",
            },
        )
        response = client.post("/api/ops/check-email")

    assert preflight.status_code == 200
    assert response.status_code == 403


def test_ops_email_accepts_runtime_gate_token_as_documented_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCBE_OPS_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("SCBE_RUNTIME_GATE_ADMIN_TOKEN", "runtime-token")
    monkeypatch.setattr(
        api_server,
        "_run_subprocess",
        lambda *args, **kwargs: {"stdout": "digest", "stderr": "", "exit_code": 0},
    )

    with TestClient(api_server.app) as client:
        response = client.post("/api/ops/check-email", headers={"X-Admin-Token": "runtime-token"})

    assert response.status_code == 200


def test_arena_numeric_input_stays_local_command() -> None:
    response = api_server._arena_local_command_response("2")

    assert response is not None
    assert "No model deliberation is needed" in response
    assert "active numbered menu" in response


@pytest.mark.asyncio
async def test_cli_dispatch_compiles_coding_harness_plan() -> None:
    result = await api_server._cli_dispatch(["harness", "plan", "explain", "arena", "route"])

    assert result["ok"] is True
    assert result["lane"] == "coding-harness"
    plan = result["result"]
    assert plan["schema_version"] == "scbe_command_plan_v1"
    assert plan["intent"]["permission_mode"] == "observe"
    assert plan["policy"]["decision"] != "DENY"


@pytest.mark.asyncio
async def test_cli_dispatch_rejects_mutating_harness_mode() -> None:
    result = await api_server._cli_dispatch(["harness", "plan", "delete", "everything", "--permission-mode", "execute"])

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
async def test_cli_dispatch_does_not_allow_raw_shell_commands() -> None:
    result = await api_server._cli_dispatch(["powershell", "-Command", "Get-ChildItem"])

    assert result["ok"] is False
    assert "Unknown command" in result["error"]
