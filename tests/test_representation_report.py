"""Combined chemistry/tokenizer representation reports."""

from __future__ import annotations

from python.scbe.representation_report import build_representation_report, representation_tokens


def test_representation_tokens_preserve_formula_charge_markers():
    assert representation_tokens("NH4^+ build H2O") == ["NH4^+", "build", "H2O"]


def test_representation_report_summarizes_semantic_and_material_axes():
    report = build_representation_report("Fe build H2O")
    summary = report["summary"]

    assert report["schema_version"] == "scbe_representation_report_v1"
    assert report["tokens"] == ["Fe", "build", "H2O"]
    assert summary["semantic_class_counts"] == {"ACTION": 1, "ENTITY": 2}
    assert summary["semantic_element_counts"] == {"Fe": 2, "Na": 1}
    assert summary["material_hit_count"] == 2
    assert [hit["token"] for hit in summary["material_hits"]] == ["Fe", "H2O"]
    assert summary["material_totals"]["atoms"] == 4
    assert summary["material_totals"]["protons"] == 36
    assert summary["material_totals"]["neutrons_common_isotope"] == 38
    assert summary["material_totals"]["electrons"] == 36
    assert summary["workflow_resource_totals"]["compute"] > 0


def test_representation_report_handles_no_material_hits():
    report = build_representation_report("build not compare")
    summary = report["summary"]

    assert summary["material_hit_count"] == 0
    assert summary["material_totals"]["atoms"] == 0
    assert summary["semantic_class_counts"]["NEGATION"] == 1
