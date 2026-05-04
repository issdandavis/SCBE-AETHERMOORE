from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "training_data" / "build_geoshell_pair_agent_preference_dpo.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_geoshell_pair_agent_preference_dpo", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_rows_emits_failure_pack_preference_records() -> None:
    module = _load_module()

    rows = module.build_rows()

    assert len(rows) == 21
    assert {row["meta"]["schema_version"] for row in rows} == {"geoshell_pair_agent_preference_v1"}
    assert {row["meta"]["training_boundary"] for row in rows} == {"preference_rows_not_positive_sft"}
    assert all(row["chosen"] != row["rejected"] for row in rows)
    assert all(row["id"].startswith("geoshell_pair_agent_preference_v1_") for row in rows)


def test_preference_rows_pin_observed_smoke_failures() -> None:
    module = _load_module()

    rows = {row["meta"]["case_id"]: row for row in module.build_rows()}

    builder = rows["builder_navigator_packet_missing_verification_tests"]
    assert "verification=" in builder["chosen"]
    assert "tests=" in builder["chosen"]
    assert "verification=" not in builder["rejected"]

    tests_literal = rows["builder_navigator_packet_tests_literal_first_field"]
    assert "00_required_items=Builder | Navigator | deterministic | verification | tests | apply" in tests_literal["chosen"]
    assert "01_tests_literal=tests" in tests_literal["chosen"]
    assert "test passes" in tests_literal["rejected"]
    assert "verification | tests | apply" not in tests_literal["rejected"]

    ca_route = rows["ca_abs_add_pair_route_lost_exact_markers"]
    assert "Builder=" in ca_route["chosen"]
    assert "Navigator=" in ca_route["chosen"]
    assert "add=0x00" in ca_route["chosen"]
    assert "deterministic=required" in ca_route["chosen"]

    tokenizer = rows["tokenizer_alignment_forbidden_secret_query"]
    assert "Runethic RU" in tokenizer["chosen"]
    assert "Draumric DR" in tokenizer["chosen"]
    assert "secret_query" not in tokenizer["chosen"]
    assert "secret_query" in tokenizer["rejected"]

    apply_repair = rows["expanded_gate_tests_before_apply_missing_ownership_rollback"]
    assert "ownership=" in apply_repair["chosen"]
    assert "rollback=" in apply_repair["chosen"]
    assert "ownership" not in apply_repair["rejected"]
    assert "rollback" not in apply_repair["rejected"]

    lookup = rows["expanded_gate_deterministic_lookup_repo_memory_verify"]
    assert "repo=" in lookup["chosen"]
    assert "memory=" in lookup["chosen"]
    assert "verify=" in lookup["chosen"]

    recovery = rows["expanded_gate_failure_recovery_hold_packet"]
    assert "HOLD=" in recovery["chosen"]
    assert "diagnostics=" in recovery["chosen"]
    assert "re-advance=" in recovery["chosen"]

    roundtable = rows["expanded_gate_roundtable_handoff_recorder_success_timestamp"]
    assert "Recorder=" in roundtable["chosen"]
    assert "success=true" in roundtable["chosen"]
    assert "timestamp=" in roundtable["chosen"]

    roundtable_tail = rows["expanded_gate_roundtable_handoff_no_forbidden_token_tail"]
    assert "Recorder=" in roundtable_tail["chosen"]
    assert "success=true" in roundtable_tail["chosen"]
    assert "timestamp=" in roundtable_tail["chosen"]
    assert "tokenizer=" not in roundtable_tail["chosen"]
    assert "tokenizer=" in roundtable_tail["rejected"]

    event_tail = rows["expanded_gate_event_shape_no_forbidden_token_fields"]
    assert "_agent_id=" in event_tail["chosen"]
    assert "task_type=" in event_tail["chosen"]
    assert "apply_gate=closed" in event_tail["chosen"]
    assert "tokenizer_pair" not in event_tail["chosen"]
    assert "tokenizer_pair" in event_tail["rejected"]

    lookup_phrase = rows["expanded_gate_deterministic_lookup_avoid_from_memory_phrase"]
    assert "memory=model memory is advisory only" in lookup_phrase["chosen"]
    assert "from memory" not in lookup_phrase["chosen"]
    assert "from memory" in lookup_phrase["rejected"]

    independent_event = rows["independent_smoke_event_shape_first_fields"]
    assert "task_type=" in independent_event["chosen"]
    assert "success=true" in independent_event["chosen"]
    assert "timestamp=" in independent_event["chosen"]
    assert "task_type" not in independent_event["rejected"]

    independent_apply = rows["independent_smoke_apply_repair_ownership_literal"]
    assert "ownership=" in independent_apply["chosen"]
    assert "ownership" not in independent_apply["rejected"]

    independent_lookup = rows["independent_smoke_lookup_memory_verify_literals"]
    assert "memory=model memory" in independent_lookup["chosen"]
    assert "verify=" in independent_lookup["chosen"]
    assert "from memory" not in independent_lookup["chosen"]

    independent_recovery = rows["independent_smoke_recovery_diagnostics_rollback_readvance"]
    assert "diagnostics=" in independent_recovery["chosen"]
    assert "rollback=" in independent_recovery["chosen"]
    assert "re-advance=" in independent_recovery["chosen"]

    independent_roundtable = rows["independent_smoke_roundtable_success_timestamp_first_fields"]
    assert "success=true" in independent_roundtable["chosen"]
    assert "timestamp=" in independent_roundtable["chosen"]
    assert "success" not in independent_roundtable["rejected"]

    builder_v4 = rows["independent_smoke_builder_apply_tests_first_line"]
    assert "apply" in builder_v4["chosen"].splitlines()[0]
    assert "tests" in builder_v4["chosen"].splitlines()[0]
    assert "apply" not in builder_v4["rejected"].splitlines()[0]

    apply_v4 = rows["independent_smoke_apply_ownership_first_line_v2"]
    assert "ownership" in apply_v4["chosen"].splitlines()[0]
    assert "ownership" not in apply_v4["rejected"].splitlines()[0]

    lookup_v4 = rows["independent_smoke_lookup_all_literals_v2"]
    assert "Navigator" in lookup_v4["chosen"].splitlines()[0]
    assert "lookup" in lookup_v4["chosen"].splitlines()[0]
    assert "memory" in lookup_v4["chosen"].splitlines()[0]
    assert "verify" in lookup_v4["chosen"].splitlines()[0]

    roundtable_v4 = rows["independent_smoke_roundtable_timestamp_first_line_v2"]
    assert "timestamp" in roundtable_v4["chosen"].splitlines()[0]
    assert "timestamp" not in roundtable_v4["rejected"].splitlines()[0]


def test_rows_do_not_contain_real_secret_names() -> None:
    module = _load_module()

    body = json.dumps(module.build_rows(), sort_keys=True)

    assert "HF_TOKEN" not in body
    assert "GEMINI_API_KEY" not in body
    assert "PROTONMAIL_BRIDGE_PASSWORD" not in body
    assert "sk-" not in body


def test_write_outputs_creates_jsonl_and_manifest(tmp_path: Path) -> None:
    module = _load_module()

    result = module.write_outputs(tmp_path)

    train_path = Path(result["train_path"])
    manifest_path = Path(result["manifest_path"])
    rows = [json.loads(line) for line in train_path.read_text(encoding="utf-8").splitlines()]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["row_count"] == 21
    assert len(rows) == 21
    assert manifest["row_count"] == 21
    assert manifest["source_smoke_jobs"] == [
        "69f89eb798a8d679adfb8ef5",
        "69f8a39798a8d679adfb8f09",
        "69f90ef29d85bec4d76f268d",
        "69f9144798a8d679adfb9148",
        "69f9159d98a8d679adfb914c",
        "69f91f249d85bec4d76f272c",
        "69f922c598a8d679adfb91ad",
    ]
    assert manifest["training_boundary"]["not_for_blind_positive_sft"] is True
