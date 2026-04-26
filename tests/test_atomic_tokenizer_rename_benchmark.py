import pytest

from scripts.experiments.atomic_tokenizer_rename_benchmark import (
    DEFAULT_INPUT,
    run,
)


@pytest.fixture(scope="module")
def rename_report(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run(
        DEFAULT_INPUT,
        tmp_path_factory.mktemp("rename-benchmark"),
        "hex",
        shuffle_runs=8,
    )


def test_atomic_tokenizer_rename_benchmark_outputs_report(
    rename_report: dict, tmp_path_factory: pytest.TempPathFactory
) -> None:
    output_dir = tmp_path_factory.mktemp("rename-benchmark-output")
    report = run(DEFAULT_INPUT, output_dir, "hex", shuffle_runs=8)

    assert report["sample_count"] == 84
    assert report["concept_count"] == 14
    assert report["primary_count"] == 6
    assert report["atomic_collapse"]["top_states"][0]["state"].startswith("ENTITY/Fe/")
    assert report["chemical_distance"]["feature_count"] > 50
    assert report["binary_hex_lookup"]["row_count"] >= 126
    assert report["token_atom_traces"]
    assert (output_dir / "rename_benchmark_report.json").exists()
    assert (output_dir / "comparison.md").exists()
    assert (output_dir / "renamed_manifest.json").exists()
    assert (output_dir / "semantic_chemistry_workflows.jsonl").exists()
    assert report["workflow_training_records"]["record_count"] == 84


def test_byte_periodic_chemical_analysis_separates_same_concept_from_inter_concept(
    rename_report: dict,
) -> None:
    chemical = rename_report["chemical_distance"]
    assert chemical["intra_inter_ratio"] < 1.0
    assert chemical["intra_concept_mean"] < chemical["inter_concept_mean"]


def test_token_atom_trace_records_byte_and_element_sequences(rename_report: dict) -> None:
    traces = rename_report["token_atom_traces"]
    palindrome = next(trace for trace in traces if trace["concept"] == "palindrome")
    first_token = palindrome["tokens"][0]
    assert first_token["token"] == "def"
    assert first_token["hex"] == ["0x64", "0x65", "0x66"]
    assert first_token["binary"] == ["0b01100100", "0b01100101", "0b01100110"]
    assert first_token["hex_source_sheets"] == ["ASCII Table", "ASCII Table", "ASCII Table"]
    assert len(first_token["elements"]) == 3


def test_semantic_chemistry_workflow_export_has_dual_lanes(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    output_dir = tmp_path_factory.mktemp("workflow-export")
    run(DEFAULT_INPUT, output_dir, "hex", shuffle_runs=8)

    first = (output_dir / "semantic_chemistry_workflows.jsonl").read_text(encoding="utf-8").splitlines()[0]
    assert '"schema_version": "semantic_chemistry_workflow_v1"' in first
    assert '"chemistry_actual"' in first
    assert '"semantic_overlay"' in first
    assert '"layered_geometry_semantic"' in first
    assert '"workflow_chain"' in first


def test_label_shuffle_control_gates_training_export(rename_report: dict) -> None:
    controls = rename_report["label_shuffle_control"]
    dual = controls["dual_lane_chemistry_semantic_hex"]
    geometry = controls["layered_geometry_semantic"]

    assert dual["shuffle_runs"] == 8
    assert len(dual["distribution"]) == 8
    assert len(dual["iteration_seeds"]) == 8
    assert geometry["shuffle_runs"] == 8
    assert len(geometry["distribution"]) == 8
    assert dual["marginal_counts_preserved"] is True
    assert 0.0 <= dual["empirical_p"] <= 1.0
    assert dual["histogram"]
    assert rename_report["workflow_training_records"]["status"] in {"candidate", "hold"}


def test_layered_geometry_lane_is_reported_with_zero_loss_probe(rename_report: dict) -> None:
    assert "layered_geometry_semantic" in rename_report["evaluations"]
    assert "reinforced_chemistry_semantic_flow_geometry_hex" in rename_report["evaluations"]
    assert rename_report["lane_model"]["layered_geometry_semantic"].startswith("stable outer token hull")

    probe = rename_report["layered_geometry_probe"]
    assert probe["passed"] is True
    assert probe["aggregate"]["avg_semantic_loss"] == 0.0
    assert probe["aggregate"]["fit_score_lift"] > 0.0


def test_situational_lane_selection_uses_formula_by_need(rename_report: dict) -> None:
    selection = rename_report["situational_lane_selection"]
    profiles = selection["profiles"]

    assert selection["version"] == "situational-lane-selection-v1"
    assert profiles["recovery_default"]["primary_lane"] == "dual_lane_chemistry_semantic_hex"
    assert profiles["geometry_context"]["primary_lane"] == "reinforced_chemistry_semantic_flow_geometry_hex"
    assert profiles["low_resource_route"]["primary_lane"] in {
        "reinforced_chemistry_semantic_flow_hex",
        "reinforced_chemistry_semantic_flow_geometry_hex",
    }
    geometry_top = profiles["geometry_context"]["ranked_lanes"][0]
    assert geometry_top["geometry_bonus_applied"] is True
    assert geometry_top["has_shuffle_control"] is True


def test_within_primary_diagnostic_is_explicit_for_singleton_corpus(
    rename_report: dict,
) -> None:
    diagnostic = rename_report["within_primary_diagnostic"]
    chemistry = diagnostic["feature_heads"]["chemistry_actual_hex"]

    assert chemistry["status"] == "not_applicable_single_sample_per_concept_per_primary"
    assert "at least two samples" in chemistry["reason"]
