from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "scbe-system-cli.py"


def _run_cli(*args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "--repo-root", str(ROOT), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def test_flow_plan_writes_packet_and_action_map(tmp_path: Path) -> None:
    output_path = tmp_path / "flow-plan.json"
    action_root = tmp_path / "action-maps"

    result = _run_cli(
        "flow",
        "plan",
        "--task",
        "improve CLI swarm planning",
        "--formation",
        "concentric",
        "--workflow-template",
        "architecture-enhancement",
        "--output",
        str(output_path),
        "--action-root",
        str(action_root),
    )

    assert result.returncode == 0, result.stderr
    assert output_path.exists()

    packet = json.loads(output_path.read_text(encoding="utf-8"))
    assert packet["schema_version"] == "scbe_flow_plan_v1"
    assert packet["formation"]["name"] == "concentric"
    assert packet["formation"]["fault_tolerance"]["byzantine_fault_tolerance"] == 1
    assert len(packet["agents"]) == 6
    assert packet["quasi_mesh"]["mode"] == "golden-weave"

    roles = {agent["role"] for agent in packet["agents"]}
    assert "Implementation Engineer" in roles
    assert "Security Auditor" in roles
    assert "Telemetry Archivist" in roles

    steps = packet["steps"]
    assert steps[0]["owner_role"] == "Architecture Curator"
    assert steps[-1]["owner_role"] == "Telemetry Archivist"

    action_map = packet["action_map"]
    assert action_map["enabled"] is True
    run_id = action_map["run_id"]
    run_dir = action_root / run_id
    assert (run_dir / "action_map.json").exists()
    assert (run_dir / "training_rows.jsonl").exists()

    compiled_summary = json.loads((run_dir / "run_summary.json").read_text(encoding="utf-8"))
    assert compiled_summary["run_id"] == run_id
    assert compiled_summary["training_rows"] >= 2


def test_flow_plan_accepts_skill_level_formation_aliases(tmp_path: Path) -> None:
    aliases = {
        "hexagonal-ring": "hexagonal",
        "ring": "concentric",
        "scatter": "adaptive-scatter",
    }

    for requested, canonical in aliases.items():
        output_path = tmp_path / f"{requested}-flow-plan.json"
        result = _run_cli(
            "flow",
            "plan",
            "--task",
            f"validate alias {requested}",
            "--formation",
            requested,
            "--workflow-template",
            "architecture-enhancement",
            "--output",
            str(output_path),
            "--no-action-map",
        )

        assert result.returncode == 0, result.stderr
        packet = json.loads(output_path.read_text(encoding="utf-8"))
        assert packet["formation"]["name"] == canonical
        assert packet["formation"]["requested_name"] == requested


def test_flow_packetize_builds_bounded_work_packets(tmp_path: Path) -> None:
    plan_path = tmp_path / "flow-plan.json"
    plan_action_root = tmp_path / "plan-action-maps"
    packet_path = tmp_path / "flow-packets.json"
    packet_action_root = tmp_path / "packet-action-maps"

    plan_result = _run_cli(
        "flow",
        "plan",
        "--task",
        "execute swarm packet loop",
        "--workflow-template",
        "implementation-loop",
        "--output",
        str(plan_path),
        "--action-root",
        str(plan_action_root),
    )
    assert plan_result.returncode == 0, plan_result.stderr

    packet_result = _run_cli(
        "flow",
        "packetize",
        "--plan",
        str(plan_path),
        "--support-units",
        "2",
        "--output",
        str(packet_path),
        "--action-root",
        str(packet_action_root),
    )
    assert packet_result.returncode == 0, packet_result.stderr
    assert packet_path.exists()

    bundle = json.loads(packet_path.read_text(encoding="utf-8"))
    assert bundle["schema_version"] == "scbe_work_packet_bundle_v1"
    assert bundle["packet_count"] == len(bundle["packets"])
    assert bundle["support_units_per_step"] == 2
    assert bundle["packet_count"] == 4

    first_packet = bundle["packets"][0]
    assert first_packet["schema_version"] == "scbe_work_packet_v1"
    assert first_packet["owner_role"] == "Integration Coordinator"
    assert "scripts" in first_packet["allowed_paths"]
    assert "node_modules" in first_packet["blocked_paths"]
    assert len(first_packet["support_cells"]) == 2
    assert first_packet["return_format"]["required"]
    assert first_packet["handoff_contract"]["who"] == first_packet["owner_agent_id"]
    assert first_packet["handoff_contract"]["what"].startswith(first_packet["step_name"])
    assert first_packet["workingness_gate"]["authority"] == "workingness_over_consensus"
    assert first_packet["workingness_gate"]["consensus_role"] == "advisory_signal_only"
    assert "commands_run" in first_packet["workingness_gate"]["evidence_required"]

    contract = bundle["coordination_contract"]
    assert contract["schema_version"] == "scbe_coordination_contract_v1"
    assert contract["packet_count"] == bundle["packet_count"]
    assert contract["proof_authority"].startswith("runnable checks")
    assert "node_modules" in contract["blocked_paths"]
    assert any("known failures" in item for item in contract["completion_checklist"])

    action_map = bundle["action_map"]
    assert action_map["enabled"] is True
    run_dir = packet_action_root / action_map["run_id"]
    assert (run_dir / "action_map.json").exists()
    assert (run_dir / "training_rows.jsonl").exists()


def test_flow_status_marks_ready_and_waiting_packets(tmp_path: Path) -> None:
    plan_path = tmp_path / "flow-plan.json"
    packet_path = tmp_path / "flow-packets.json"
    status_path = tmp_path / "status.json"
    markdown_path = tmp_path / "status.md"

    plan_result = _run_cli(
        "flow",
        "plan",
        "--task",
        "ship actual multi agent work",
        "--workflow-template",
        "implementation-loop",
        "--output",
        str(plan_path),
        "--no-action-map",
    )
    assert plan_result.returncode == 0, plan_result.stderr

    packet_result = _run_cli(
        "flow",
        "packetize",
        "--plan",
        str(plan_path),
        "--output",
        str(packet_path),
        "--no-action-map",
    )
    assert packet_result.returncode == 0, packet_result.stderr

    status_result = _run_cli(
        "flow",
        "status",
        "--packets",
        str(packet_path),
        "--output",
        str(status_path),
        "--markdown-output",
        str(markdown_path),
    )
    assert status_result.returncode == 0, status_result.stderr

    board = json.loads(status_path.read_text(encoding="utf-8"))
    assert board["schema_version"] == "scbe_flow_status_board_v1"
    assert board["ready_count"] == 1
    assert board["next_packets"][0]["step_id"] == "scope"
    assert board["counts"]["waiting"] == 3
    assert board["next_packets"][0]["dispatch_command"][:3] == [
        "python",
        "scripts/scbe-system-cli.py",
        "--repo-root",
    ]
    assert "SCBE Flow Status Board" in markdown_path.read_text(encoding="utf-8")

    status_after_scope = tmp_path / "status-after-scope.json"
    completed_result = _run_cli(
        "flow",
        "status",
        "--packets",
        str(packet_path),
        "--completed",
        "scope",
        "--output",
        str(status_after_scope),
    )
    assert completed_result.returncode == 0, completed_result.stderr
    board_after_scope = json.loads(status_after_scope.read_text(encoding="utf-8"))
    assert board_after_scope["ready_count"] == 1
    assert board_after_scope["next_packets"][0]["step_id"] == "build"


def test_flow_run_next_dry_run_selects_first_ready_packet(tmp_path: Path) -> None:
    plan_path = tmp_path / "flow-plan.json"
    packet_path = tmp_path / "flow-packets.json"
    status_path = tmp_path / "run-next-status.json"
    run_output = tmp_path / "run-next.json"

    plan_result = _run_cli(
        "flow",
        "plan",
        "--task",
        "run next packet",
        "--workflow-template",
        "implementation-loop",
        "--output",
        str(plan_path),
        "--no-action-map",
    )
    assert plan_result.returncode == 0, plan_result.stderr

    packet_result = _run_cli(
        "flow",
        "packetize",
        "--plan",
        str(plan_path),
        "--output",
        str(packet_path),
        "--no-action-map",
    )
    assert packet_result.returncode == 0, packet_result.stderr

    run_result = _run_cli(
        "--json",
        "flow",
        "run-next",
        "--packets",
        str(packet_path),
        "--output",
        str(status_path),
        "--run-output",
        str(run_output),
        "--dry-run",
    )
    assert run_result.returncode == 0, run_result.stderr

    run_packet = json.loads(run_output.read_text(encoding="utf-8"))
    assert run_packet["schema_version"] == "scbe_flow_run_next_result_v1"
    assert run_packet["executed"] is False
    assert run_packet["dry_run"] is True
    assert run_packet["step_id"] == "scope"
    assert run_packet["ready_count"] == 1
    assert run_packet["completed_steps"] == []
    assert run_packet["command"][:3] == ["python", "scripts/scbe-system-cli.py", "--repo-root"]
    board = json.loads(status_path.read_text(encoding="utf-8"))
    assert board["run_next"]["dry_run"] is True
    assert board["next_packets"][0]["step_id"] == "scope"
