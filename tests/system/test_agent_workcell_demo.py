from pathlib import Path

import scripts.system.agent_workcell_demo as demo
from agents.agent_bus_schema import validate_log


def test_workcell_writes_packets_report_and_markdown(tmp_path: Path, monkeypatch) -> None:
    def fake_run(
        command: str,
        cwd: Path,
        *,
        max_attempts: int = 1,
        claimed_paths: list[str] | None = None,
    ) -> demo.CommandResult:
        return demo.CommandResult(
            command=command,
            returncode=0,
            duration_ms=7,
            stdout_tail="ok",
            stderr_tail="",
            geoseal_gate={"allowed": True, "tier": "ALLOW"},
            attempts=1,
        )

    monkeypatch.setattr(demo, "run_command", fake_run)
    monkeypatch.setattr(demo, "git_value", lambda args, cwd: "test-value")
    monkeypatch.setattr(demo, "DEFAULT_BUS_LOG", tmp_path / "events.jsonl")

    report = demo.run_workcell("prove cross-talk", tmp_path)

    assert report["decision"] == "SHIP_READY"
    assert report["scenario"] == "launch"
    assert report["crosstalk"]["packet_count"] == 4
    assert report["collision_report"]["agent_slots"] == 100
    assert report["collision_report"]["collision_count"] == 0
    assert report["coding_operating_system"]["agent_bus_policy"].startswith("all products")
    assert "workflow_snapshot_starter" in report["coding_operating_system"]["product_routes"]
    assert {agent["agent_id"] for agent in report["agents"]} == {
        "planner",
        "builder",
        "reviewer",
        "verifier",
        "shipper",
    }
    assert (tmp_path / "workcell-report.json").exists()
    assert (tmp_path / "leases.json").exists()
    assert (tmp_path / "crosstalk.jsonl").read_text(encoding="utf-8").count("\n") == 4
    assert "Decision: **SHIP_READY**" in (tmp_path / "ship-report.md").read_text(encoding="utf-8")
    ship_report = (tmp_path / "ship-report.md").read_text(encoding="utf-8")
    assert "Bus event:" in ship_report
    assert report["artifacts"]["agent_bus_event_log"] in ship_report

    bus_report = validate_log(tmp_path / "events.jsonl")
    assert bus_report.total == 1
    assert bus_report.accepted == 1
    assert bus_report.rejected == 0


def test_deploy_scenario_runs_deploy_gates_and_bus_event(tmp_path: Path, monkeypatch) -> None:
    def fake_run(
        command: str,
        cwd: Path,
        *,
        max_attempts: int = 1,
        claimed_paths: list[str] | None = None,
    ) -> demo.CommandResult:
        return demo.CommandResult(
            command=command,
            returncode=0,
            duration_ms=9,
            stdout_tail="ok",
            stderr_tail="",
            geoseal_gate={"allowed": True, "tier": "ALLOW"},
            attempts=1,
        )

    monkeypatch.setattr(demo, "run_command", fake_run)
    monkeypatch.setattr(demo, "git_value", lambda args, cwd: "test-value")
    monkeypatch.setattr(demo, "DEFAULT_BUS_LOG", tmp_path / "events.jsonl")

    report = demo.run_workcell("test multi agent deploy", tmp_path, scenario="deploy")

    assert report["decision"] == "SHIP_READY"
    assert report["scenario"] == "deploy"
    assert report["collision_report"]["agent_slots"] == 100
    assert report["collision_report"]["collision_count"] == 0
    assert "deployer" in {agent["agent_id"] for agent in report["agents"]}
    assert any("smoke:remote-app-config" in item["command"] for item in report["verification"]["checks"])
    assert report["deploy_policy"]["rollback"].startswith("failed gate")
    assert (tmp_path / "leases.json").exists()
    assert "Scenario: `deploy`" in (tmp_path / "ship-report.md").read_text(encoding="utf-8")

    bus_report = validate_log(tmp_path / "events.jsonl")
    assert bus_report.total == 1
    assert bus_report.accepted == 1
    assert bus_report.rejected == 0


def test_collision_report_detects_duplicate_write_scope() -> None:
    leases = demo.build_lease_plan(2)
    leases[1]["write_scope"] = leases[0]["write_scope"]

    report = demo.collision_report(leases)

    assert report["agent_slots"] == 2
    assert report["collision_count"] == 1
    assert leases[0]["write_scope"][0] in report["collisions"]


def test_command_argv_preserves_windows_style_repo_paths() -> None:
    argv = demo.command_argv(
        "python -m py_compile scripts\\system\\agent_workcell_demo.py " "scripts\\system\\product_launch_readiness.py"
    )

    assert argv[:3] == ["python", "-m", "py_compile"]
    assert argv[3:] == [
        "scripts/system/agent_workcell_demo.py",
        "scripts/system/product_launch_readiness.py",
    ]


def test_workcell_blocks_when_any_verification_fails(tmp_path: Path, monkeypatch) -> None:
    def fake_run(
        command: str,
        cwd: Path,
        *,
        max_attempts: int = 1,
        claimed_paths: list[str] | None = None,
    ) -> demo.CommandResult:
        return demo.CommandResult(
            command=command,
            returncode=1 if "pytest" in command else 0,
            duration_ms=7,
            stdout_tail="",
            stderr_tail="failed",
            geoseal_gate={"allowed": True, "tier": "ALLOW"},
            attempts=1,
        )

    monkeypatch.setattr(demo, "run_command", fake_run)
    monkeypatch.setattr(demo, "git_value", lambda args, cwd: "test-value")
    monkeypatch.setattr(demo, "DEFAULT_BUS_LOG", tmp_path / "events.jsonl")

    report = demo.run_workcell("prove blocking behavior", tmp_path)

    assert report["decision"] == "BLOCKED"
    assert any(item["returncode"] == 1 for item in report["verification"]["checks"])
    bus_report = validate_log(tmp_path / "events.jsonl")
    assert bus_report.accepted == 1
