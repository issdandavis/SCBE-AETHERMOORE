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

    assert len(rows) == 5
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
    assert result["row_count"] == 5
    assert len(rows) == 5
    assert manifest["row_count"] == 5
    assert manifest["source_smoke_jobs"] == [
        "69f89eb798a8d679adfb8ef5",
        "69f8a39798a8d679adfb8f09",
        "69f90ef29d85bec4d76f268d",
    ]
    assert manifest["training_boundary"]["not_for_blind_positive_sft"] is True
