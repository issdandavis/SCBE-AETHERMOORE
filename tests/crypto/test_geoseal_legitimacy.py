from __future__ import annotations

from pathlib import Path

from src.crypto.geoseal_legitimacy import CoarseLocation, run_legitimacy_trial


def test_legitimacy_trial_allows_scoped_user_cli_probe_shape() -> None:
    payload = run_legitimacy_trial(
        goal="run focused tests before commit",
        expected_tool="terminal.command.request",
        origin="user",
        command="python --version",
        workspace=Path.cwd(),
        location=CoarseLocation(source="user_confirmed", label="local dev workstation", confidence=0.95),
        network_state="local",
    )

    decision = payload["decision"]
    assert decision["decision"] == "ALLOW_CLI"
    assert decision["allowed_cli"] is True
    assert decision["packet_sha256"]


def test_legitimacy_trial_demotes_unscoped_execution_to_probe_only() -> None:
    payload = run_legitimacy_trial(
        goal="inspect project state",
        expected_tool="terminal.command.request",
        origin="user",
        command="python --version",
        location=CoarseLocation(source="unknown", label="unknown", confidence=0.0),
    )

    decision = payload["decision"]
    assert decision["decision"] == "PROBE_ONLY"
    assert decision["allowed_cli"] is False
    assert {finding["rule"] for finding in decision["findings"]} >= {
        "workspace-unscoped",
        "weak-location-context",
    }


def test_legitimacy_trial_denies_destructive_command_shape() -> None:
    payload = run_legitimacy_trial(
        goal="cleanup generated files",
        expected_tool="terminal.command.request",
        origin="user",
        command="powershell Remove-Item .env -Recurse",
        workspace=Path.cwd(),
        location=CoarseLocation(source="user_confirmed", label="local dev workstation", confidence=0.9),
        network_state="local",
    )

    decision = payload["decision"]
    assert decision["decision"] == "DENY"
    assert decision["allowed_cli"] is False
    assert any(finding["rule"].startswith("exec-gate:") for finding in decision["findings"])


def test_legitimacy_trial_escalates_agent_high_risk_authority() -> None:
    payload = run_legitimacy_trial(
        goal="publish deployment",
        expected_tool="deploy.publish",
        origin="agent",
        workspace=Path.cwd(),
        location=CoarseLocation(source="user_confirmed", label="local dev workstation", confidence=0.95),
        network_state="online",
    )

    decision = payload["decision"]
    assert decision["decision"] == "ESCALATE"
    assert any(finding["rule"] == "non-user-high-risk" for finding in decision["findings"])
