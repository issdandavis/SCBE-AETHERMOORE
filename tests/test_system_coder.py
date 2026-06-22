import json

from python.helm.system_coder import load_spec, run_tasks


def test_system_coder_runs_all_rungs_with_zero_false_success(tmp_path):
    out_dir = tmp_path / "checkpoints"
    spec = load_spec(None)
    spec["checkpoint_dir"] = str(out_dir)

    report = run_tasks("tests/fixtures/system_coder_tasks.jsonl", spec, run_id="unit")
    summary = report["summary"]

    assert summary["attempted"] == 5
    assert summary["solved"] == 5
    assert summary["false_success_count"] == 0
    assert summary["contract_passed"] is True
    assert summary["by_solver"]["deterministic"] == 1
    assert summary["by_solver"]["reference"] == 1
    assert summary["by_solver"]["repair"] == 1
    assert summary["by_solver"]["known_logic"] == 1
    assert summary["by_solver"]["answer_stage"] == 1
    assert (out_dir / "unit" / "repair_add.json").exists()


def test_system_coder_receipts_include_reference_and_repair_paths(tmp_path):
    spec = load_spec(None)
    spec["checkpoint_dir"] = str(tmp_path / "checkpoints")

    report = run_tasks("tests/fixtures/system_coder_tasks.jsonl", spec, run_id="paths")
    receipts = {r["id"]: r for r in report["receipts"]}

    assert receipts["median_bank"]["via"] == "fallback:reference_bank"
    assert receipts["repair_add"]["solver"] == "repair"
    assert receipts["repair_add"]["tries"] == 2
    assert receipts["known_prime_gate"]["result"]["decision"]["answer"] == "ALLOW"
    assert receipts["physics_speed"]["result"]["arrow"]["kind"] == "finish"


def test_system_coder_cli_shape_is_json_serializable(tmp_path):
    spec = load_spec(None)
    spec["checkpoint_dir"] = str(tmp_path / "checkpoints")

    report = run_tasks("tests/fixtures/system_coder_tasks.jsonl", spec, run_id="json")

    encoded = json.dumps(report, sort_keys=True)
    assert "system_coder" in encoded
    assert len(report["sft"]) == 5
