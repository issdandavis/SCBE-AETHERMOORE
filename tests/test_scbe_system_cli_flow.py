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

    action_map = bundle["action_map"]
    assert action_map["enabled"] is True
    run_dir = packet_action_root / action_map["run_id"]
    assert (run_dir / "action_map.json").exists()
    assert (run_dir / "training_rows.jsonl").exists()
