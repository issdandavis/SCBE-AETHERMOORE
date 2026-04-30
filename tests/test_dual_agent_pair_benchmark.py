from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "benchmark" / "dual_agent_pair_benchmark.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dual_agent_pair_benchmark", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_pair_beats_solo_on_scbe_native_tasks():
    module = load_module()

    payload = module.run_benchmark()

    assert payload["schema_version"] == "scbe_dual_agent_pair_benchmark_v1"
    assert payload["summary"]["pair_passed"] > payload["summary"]["solo_passed"]
    assert payload["summary"]["cost_usd"] == 0.0
    assert payload["sacred_tongue_bijection"]["ok"] is True


def test_pair_routes_ca_opcode_through_deterministic_table():
    module = load_module()
    task = next(task for task in module.task_suite() if task.task_id == "ca_opcode_abs_add")

    result = module.run_pair(task)

    assert result["ok"] is True
    assert "0x09, 0x09, 0x00" in result["output"]
    assert any(packet["lane"] == "deterministic_tool" for packet in result["packets"])
    assert any("scbe_code.py ca-plan" in tool for packet in result["packets"] for tool in packet["tools"])


def test_solo_model_fails_exact_ca_sequence():
    module = load_module()
    task = next(task for task in module.task_suite() if task.task_id == "ca_opcode_abs_add")

    result = module.run_solo(task)

    assert result["ok"] is False
    assert "0x09, 0x09, 0x00" not in result["output"]


def test_write_report_creates_json_and_markdown(tmp_path):
    module = load_module()
    output = tmp_path / "pair_report.json"

    paths = module.write_report(module.run_benchmark(), output)

    assert Path(paths["json"]).exists()
    assert Path(paths["markdown"]).exists()
    assert "Dual Agent Pair Benchmark" in Path(paths["markdown"]).read_text(encoding="utf-8")


def test_validate_subcommand_outputs_summary():
    proc = subprocess.run(
        [sys.executable, "scripts/benchmark/dual_agent_pair_benchmark.py", "validate"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["summary"]["pair_passed"] > payload["summary"]["solo_passed"]
