import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "system" / "free_compute_agent_array.py"


def load_module():
    spec = importlib.util.spec_from_file_location("free_compute_agent_array", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_builds_ten_worker_array_with_choice_markers():
    module = load_module()
    packets = module.build_packets("build agentic coding harness", 10)

    assert len(packets) == 10
    assert packets[0].task_id.startswith("array-build-agentic-coding-harness-01")
    assert all("QUEST_CREATED" in packet.achievements for packet in packets)
    assert any(packet.quest_state == "MERGED" for packet in packets)
    assert all(packet.training_signal["record_type"] == "agentic_quest_marker" for packet in packets)


def test_high_risk_and_sensitive_packets_stay_local():
    module = load_module()
    packets = module.build_packets("build agentic coding harness", 10)
    integration = next(packet for packet in packets if packet.lane == "integration_review")

    assert integration.compute_target == "local"
    assert integration.remote_ok is False


def test_plan_check_and_outputs(tmp_path):
    module = load_module()
    packets = module.build_packets("build agentic coding harness", 10)

    check = module.check_plan(packets)
    assert check["ok"], check

    outputs = module.write_outputs("build agentic coding harness", 10, tmp_path, packets)
    for path in outputs.values():
        assert Path(path).exists()

    plan_data = json.loads(Path(outputs["plan"]).read_text(encoding="utf-8"))
    assert plan_data["sacred_tongue_bijection"]["ok"] is True

    matrix = Path(outputs["matrix"]).read_text(encoding="utf-8")
    assert "matrix_query" in matrix
    markers = Path(outputs["training_markers"]).read_text(encoding="utf-8")
    assert "choicescript_agentic_loop" in markers
    commands = Path(outputs["enqueue_commands"]).read_text(encoding="utf-8")
    assert "advanced_ai_dispatch.py enqueue" in commands
