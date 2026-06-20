"""Atomic-style tokenizer lookup rows."""

from __future__ import annotations

from python.scbe.token_lookup import lookup_token, lookup_tokens


def test_lookup_token_exposes_semantic_periodic_row_and_bytes():
    row = lookup_token("build", language="en")

    assert row["schema_version"] == "scbe_token_lookup_v1"
    assert row["byte_signature"]["hex"] == ["0x62", "0x75", "0x69", "0x6C", "0x64"]
    assert row["semantic"]["semantic_class"] == "ACTION"
    assert row["semantic"]["semantic_element"]["symbol"] == "Na"
    assert set(row["semantic"]["tau"]) == {"KO", "AV", "RU", "CA", "UM", "DR"}
    assert row["workflow_unit"]["semantic_lane"]["role"] == "compute"
    assert row["workflow_unit"]["chemistry_lane"]["mode"] == "structural_template"
    assert row["material"] is None


def test_lookup_token_adds_material_dimensions_for_formula():
    row = lookup_token("C6H12O6")

    assert row["material"]["kind"] == "formula"
    assert row["material"]["dimensions"]["totals"]["atoms"] == 24
    assert row["material"]["dimensions"]["totals"]["protons"] == 96
    assert row["material"]["dimensions"]["totals"]["neutrons_common_isotope"] == 84
    assert row["material"]["dimensions"]["totals"]["electrons"] == 96


def test_lookup_token_adds_material_dimensions_for_element_symbol():
    row = lookup_token("Fe")

    assert row["material"]["kind"] == "element"
    assert row["material"]["symbol"] == "Fe"
    assert row["material"]["atomic_number"] == 26
    assert row["workflow_unit"]["chemistry_lane"]["mode"] == "material"
    assert row["workflow_unit"]["chemistry_lane"]["material_elements"] == ["Fe"]
    assert row["material"]["dimensions"]["totals"]["protons"] == 26
    assert row["material"]["dimensions"]["totals"]["electrons"] == 26


def test_lookup_tokens_batches_rows():
    batch = lookup_tokens(["not", "H2O"])

    assert batch["schema_version"] == "scbe_token_lookup_batch_v1"
    assert [row["token"] for row in batch["rows"]] == ["not", "H2O"]
    assert batch["rows"][0]["semantic"]["negative_state"] is True
    assert batch["rows"][1]["material"]["dimensions"]["totals"]["atoms"] == 3
