from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "system" / "agentic_transit_station.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("agentic_transit_station", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_aws_demo_packet_is_small_and_repo_referenced() -> None:
    module = _load_module()

    packet = module.build_aws_demo_agent_packet(
        ticket_id="ats-test-ticket",
        execute_demo=False,
        latest_packet=None,
    )

    assert packet.task_id == "ats-test-ticket"
    assert packet.route.domain == "aws-free-tier-demo"
    assert packet.route.tongue == "RU"
    assert packet.expected_output == "verdict"
    assert module.packet_input_tokens(packet) < 200
    assert packet.context_refs[0].value == "scripts/system/aws_free_tier_demo_stack.py"


def test_station_platforms_include_cost_and_telemetry_gates() -> None:
    module = _load_module()

    platforms = {platform.platform_id: platform for platform in module.station_platforms()}

    assert "security_gate" in platforms
    assert "telemetry_archive" in platforms
    assert "grant broad EC2/IAM/admin permissions" in platforms["security_gate"].blocked_action
    assert "store raw credentials" in platforms["telemetry_archive"].blocked_action
