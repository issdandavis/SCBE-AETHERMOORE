from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "training_data" / "build_geoshell_pair_agent_sft.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_geoshell_pair_agent_sft", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_dataset_emits_pair_records_and_geoshell_events() -> None:
    module = _load_module()

    dataset = module.build_dataset()

    assert dataset["schema_version"] == "geoshell_pair_agent_sft_v1"
    assert dataset["base_record_count"] == 15
    assert dataset["population_multiplier"] == 6
    assert dataset["eval_gold_count"] == 32
    assert len(dataset["train"]) == 110  # 13 train base * 6 + 32 eval_gold
    assert len(dataset["holdout"]) == 12  # 2 holdout base * 6
    assert len(dataset["events"]) == 122  # 90 multiplied + 32 eval_gold

    first = json.loads(dataset["train"][0]["messages"][-1]["content"])
    assert first["schema_version"] == "geoshell_pair_agent_answer_v1"
    assert first["mode"] == "paired_geoshell_coding"
    assert first["builder"]
    assert first["navigator"]
    assert first["geoseal_policy"]["apply_allowed"] is False
    assert first["switchboard"]["decision"] == "GRANT"
    assert first["switchboard"]["request"]["agent_id"] == "pair-agent-builder-navigator"
    assert first["verification"]["recommended_gate"] == "python scripts/benchmark/dual_agent_pair_benchmark.py validate"
    assert first["geoshell_event"]["task_type"] == "pair_coding"
    assert first["tokenizer_alignment"]["primary_tongue"] == "CA"
    assert {item["code"] for item in first["tokenizer_alignment"]["sacred_tongues"]} == {
        "KO",
        "AV",
        "RU",
        "CA",
        "UM",
        "DR",
    }
    assert "Kor'aelin" in dataset["train"][0]["meta"]["sacred_tongue_names"]
    assert dataset["train"][0]["meta"]["population_context"]
    assert dataset["train"][0]["meta"]["base_task_id"] == "ca_opcode_abs_add"

    switchboard = next(
        json.loads(row["messages"][-1]["content"])
        for row in dataset["train"]
        if row["meta"]["task_id"].startswith("switchboard_queue_equal_priority_ui_write")
    )
    assert switchboard["schema_version"] == "geoshell_switchboard_answer_v1"
    assert switchboard["decision"] == "QUEUE"
    assert switchboard["switchboard_event"]["task_type"] == "switchboard"

    gate_repair = next(
        json.loads(row["messages"][-1]["content"])
        for row in dataset["train"]
        if row["meta"]["task_id"].startswith("gate_repair_tokenizer_alignment_packet")
    )
    assert gate_repair["schema_version"] == "geoshell_pair_agent_gate_answer_v1"
    assert "Kor'aelin" in gate_repair["required_gate_evidence"]
    assert gate_repair["verification"]["apply_gate"] == "closed until tests pass"

    # Gate-repair user prompts must NOT leak the substring contract any more.
    gate_repair_row = next(
        row
        for row in dataset["train"]
        if row["meta"]["task_kind"] == "promotion_gate_repair"
    )
    user_content = gate_repair_row["messages"][1]["content"]
    assert "REQUIRED:" not in user_content, "gate-spec leakage in training prompt"
    assert "FORBIDDEN:" not in user_content, "gate-spec leakage in training prompt"
    assert "GATE_ID:" not in user_content, "gate-spec leakage in training prompt"

    # Eval-shape gold rows must be present and population-immune (no
    # POPULATION_CONTEXT trailer, mirroring the natural inference distribution).
    eval_gold_rows = [
        row for row in dataset["train"] if row["meta"]["task_kind"] == "eval_shape_gold"
    ]
    assert len(eval_gold_rows) == 32
    eval_gold_gate_ids = {row["meta"]["gate_id"] for row in eval_gold_rows}
    assert eval_gold_gate_ids == {
        "builder_navigator_packet",
        "ca_abs_add_pair_route",
        "geoshell_event_shape",
        "tokenizer_alignment_packet",
    }
    for row in eval_gold_rows:
        assert "POPULATION_CONTEXT:" not in row["messages"][1]["content"]
        # Source must not cite the failed bootstrap HF job.
        assert "hf_job:69f89eb798a8d679adfb8ef5" not in row["meta"]["source_script"]

    # Spot-check: builder_navigator_packet gold response must satisfy the contract
    # (every required substring present, no forbidden substring leaking).
    bnp_row = next(
        row for row in eval_gold_rows if row["meta"]["gate_id"] == "builder_navigator_packet"
    )
    bnp_assistant_text = bnp_row["messages"][-1]["content"]
    for required in ("Builder", "Navigator", "deterministic", "verification", "apply", "tests"):
        assert required in bnp_assistant_text, f"{required!r} missing from gold answer"
    for forbidden in ("apply immediately", "skip tests"):
        assert forbidden not in bnp_assistant_text, f"{forbidden!r} leaked into gold answer"


def test_records_do_not_embed_secret_material() -> None:
    module = _load_module()

    dataset = module.build_dataset()
    body = json.dumps(dataset, sort_keys=True)

    assert "HF_TOKEN" not in body
    assert "GEMINI_API_KEY" not in body
    assert "PROTONMAIL_BRIDGE_PASSWORD" not in body
    assert "config/connector_oauth/.env.connector.oauth" not in body


def test_write_outputs_creates_train_holdout_manifest_and_events(
    tmp_path: Path,
) -> None:
    module = _load_module()
    dataset = module.build_dataset()
    event_path = tmp_path / "events" / "latest_events.json"

    paths = module.write_outputs(dataset, tmp_path, event_path)

    train = Path(paths["train"])
    holdout = Path(paths["holdout"])
    manifest = json.loads(Path(paths["manifest"]).read_text(encoding="utf-8"))
    events = json.loads(Path(paths["events"]).read_text(encoding="utf-8"))

    assert train.exists()
    assert holdout.exists()
    assert manifest["profile_id"] == "geoshell-pair-agent-v1"
    assert manifest["base_record_count"] == 15
    assert manifest["population_multiplier"] == 6
    assert manifest["eval_gold_count"] == 32
    assert manifest["train_count"] == 110
    assert manifest["holdout_count"] == 12
    assert manifest["record_count"] == 122
    assert len(events) == 122
    assert events[0]["_agent_id"] == "pair-agent-builder-navigator"


def test_relative_output_paths_resolve_inside_repo() -> None:
    module = _load_module()

    resolved = module._resolve_repo_path(Path("training-data") / "sft")

    assert resolved.is_absolute()
    assert resolved == ROOT / "training-data" / "sft"


def test_geoseal_cli_builds_pair_agent_training_outputs(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "pair-agent-training",
            "--output-dir",
            str(tmp_path / "sft"),
            "--event-path",
            str(tmp_path / "events" / "latest_events.json"),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["base_record_count"] == 15
    assert payload["population_multiplier"] == 6
    assert payload["train_count"] == 110
    assert payload["holdout_count"] == 12
    assert Path(payload["paths"]["manifest"]).exists()
    assert Path(payload["geoshell_event_feed"]).exists()
