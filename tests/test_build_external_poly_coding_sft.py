from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_external_poly_coding_sft.py"
CATALOG_PATH = REPO_ROOT / "config" / "training" / "poly_coding_source_catalog.json"


def load_module():
    spec = importlib.util.spec_from_file_location("build_external_poly_coding_sft", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_catalog_declares_public_source_policy():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    assert catalog["schema_version"] == "scbe_poly_coding_source_catalog_v1"
    assert catalog["policy"]["default_mode"] == "metadata_first"
    assert catalog["policy"]["do_not_bulk_download_by_default"] is True
    source_ids = {source["source_id"] for source in catalog["sources"]}
    assert {
        "sam_gov_opportunities_api",
        "darpa_aixcc_public",
        "nasa_open_source_catalog",
        "kaggle_meta_kaggle_code",
        "bigcode_the_stack",
    } <= source_ids


def test_build_dataset_preserves_poly_lenses_and_transport():
    module = load_module()

    dataset = module.build_dataset(CATALOG_PATH)

    assert dataset["schema_version"] == "scbe_external_poly_coding_dataset_v1"
    assert len(dataset["train"]) == 4
    assert len(dataset["holdout"]) == 1
    first = json.loads(dataset["train"][0]["messages"][-1]["content"])
    assert first["schema_version"] == "scbe_external_poly_coding_answer_v1"
    languages = {lens["language"] for lens in first["language_lenses"]}
    assert {"python", "typescript", "rust", "c", "haskell", "java"} <= languages
    assert first["geoseal_tokenizer"]["bijective_checks"]["all_lens_utf8_round_trip"] is True
    assert first["canonical_python_transport"]["hex_prefix"]
    assert first["canonical_python_transport"]["binary_prefix"]
    assert first["source"]["license_or_terms"]


def test_ca_operation_hints_include_table_source():
    module = load_module()
    dataset = module.build_dataset(CATALOG_PATH)
    records = [json.loads(row["messages"][-1]["content"]) for row in [*dataset["train"], *dataset["holdout"]]]
    safe_divide = next(record for record in records if record["task_id"] == "external_safe_divide")

    assert safe_divide["ca_operation_hints"]["source"] == "python.scbe.ca_opcode_table.OP_TABLE"
    assert "0x20" in safe_divide["ca_operation_hints"]["hex_sequence"]
    assert "0x03" in safe_divide["ca_operation_hints"]["hex_sequence"]


def test_write_outputs_creates_jsonl_and_manifest(tmp_path):
    module = load_module()
    dataset = module.build_dataset(CATALOG_PATH)

    result = module.write_outputs(dataset, tmp_path)

    train = Path(result["train"])
    holdout = Path(result["holdout"])
    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    assert train.exists()
    assert holdout.exists()
    assert manifest["train_count"] == 4
    assert manifest["holdout_count"] == 1
    assert "sam_gov_opportunities_api" in manifest["source_ids"]
