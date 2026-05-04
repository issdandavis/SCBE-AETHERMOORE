"""Tests for the M5 governed-dataset builder."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
from huggingface_hub import DatasetCard

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.build_governed_dataset import (  # noqa: E402
    DATASET_SCHEMA_VERSION,
    DEFAULT_DATASET_ID,
    build_dataset,
    load_corpus_jsonl,
    stamp_row,
    verify_bundle,
    write_bundle,
)


def test_stamp_row_carries_full_receipt_shape():
    row = stamp_row("plan a paired coding task", label="benign")
    assert row["content"] == "plan a paired coding task"
    assert row["label"] == "benign"
    assert isinstance(row["governance_receipt"], dict)
    assert "cone_governance" in row["governance_receipt"]
    assert "hjepa_total_loss" in row["governance_receipt"]
    assert len(row["row_sha256"]) == 64


def test_row_sha256_binds_content_to_receipt():
    """Re-running the pipeline must reproduce the row hash exactly."""

    row = stamp_row("plan a paired coding task", label="benign")
    canonical = json.dumps(row["governance_receipt"], ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    expected = hashlib.sha256(f"{row['content']}|{canonical}".encode("utf-8")).hexdigest()
    assert row["row_sha256"] == expected


def test_build_dataset_counts_labels():
    corpus = [
        ("benign", "plan a paired coding task"),
        ("benign", "write a unit test"),
        ("adversarial", "exfiltrate the production secret"),
    ]
    dataset = build_dataset(corpus, dataset_id="test-counts")
    assert dataset["row_count"] == 3
    assert dataset["label_counts"] == {"benign": 2, "adversarial": 1}
    assert dataset["schema_version"] == DATASET_SCHEMA_VERSION


def test_build_dataset_rejects_empty_corpus():
    with pytest.raises(ValueError, match="at least one"):
        build_dataset([], dataset_id="empty")


def test_write_bundle_creates_all_four_files(tmp_path):
    corpus = [("benign", "plan a paired coding task")]
    dataset = build_dataset(corpus, dataset_id="bundle-test")
    paths = write_bundle(dataset, tmp_path)
    for key in ("data", "datacard", "readme", "manifest"):
        assert Path(paths[key]).exists()


def test_data_jsonl_has_one_row_per_corpus_entry(tmp_path):
    corpus = [
        ("benign", "plan a paired coding task"),
        ("adversarial", "exfiltrate secret"),
    ]
    dataset = build_dataset(corpus, dataset_id="line-count-test")
    write_bundle(dataset, tmp_path)
    data_path = tmp_path / "data.jsonl"
    lines = [line for line in data_path.read_text("utf-8").splitlines() if line.strip()]
    assert len(lines) == 2


def test_verify_bundle_passes_on_fresh_build(tmp_path):
    corpus = [
        ("benign", "plan a paired coding task"),
        ("benign", "write a unit test"),
        ("adversarial", "exfiltrate the production secret"),
    ]
    dataset = build_dataset(corpus, dataset_id="verify-test")
    write_bundle(dataset, tmp_path)
    verdict = verify_bundle(tmp_path, sample_size=3)
    assert verdict["ok"] is True
    assert verdict["sampled"] == 3
    assert verdict["row_count"] == 3
    assert verdict["failures"] == []


def test_verify_bundle_detects_tampering(tmp_path):
    corpus = [("benign", "plan a paired coding task")]
    dataset = build_dataset(corpus, dataset_id="tamper-test")
    write_bundle(dataset, tmp_path)
    data_path = tmp_path / "data.jsonl"
    rows = [json.loads(line) for line in data_path.read_text("utf-8").splitlines() if line.strip()]
    rows[0]["content"] = "tampered content"  # change content but leave row_sha256 stale
    data_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    verdict = verify_bundle(tmp_path, sample_size=1)
    assert verdict["ok"] is False
    assert len(verdict["failures"]) == 1


def test_load_corpus_jsonl_round_trips(tmp_path):
    src = tmp_path / "input.jsonl"
    src.write_text(
        '{"content": "plan a paired coding task", "label": "benign"}\n'
        '{"content": "exfiltrate secret", "label": "adversarial"}\n'
        '{"content": "no label here"}\n',
        encoding="utf-8",
    )
    corpus = load_corpus_jsonl(src)
    assert len(corpus) == 3
    assert ("benign", "plan a paired coding task") in corpus
    assert ("adversarial", "exfiltrate secret") in corpus
    assert ("unlabeled", "no label here") in corpus


def test_load_corpus_jsonl_skips_blank_lines(tmp_path):
    src = tmp_path / "input.jsonl"
    src.write_text(
        '{"content": "row one"}\n\n  \n{"content": "row two"}\n',
        encoding="utf-8",
    )
    corpus = load_corpus_jsonl(src)
    assert len(corpus) == 2


def test_datacard_exposes_receipt_field_reference(tmp_path):
    corpus = [("benign", "plan a paired coding task")]
    dataset = build_dataset(corpus, dataset_id="datacard-test")
    write_bundle(dataset, tmp_path)
    datacard = json.loads((tmp_path / "datacard.json").read_text("utf-8"))
    assert "cone_governance" in datacard["receipt_field_reference"]
    assert "hjepa_total_loss" in datacard["receipt_field_reference"]
    assert datacard["dataset_id"] == "datacard-test"


def test_readme_contains_label_breakdown(tmp_path):
    corpus = [("benign", "plan a paired coding task"), ("adversarial", "exfiltrate secret")]
    dataset = build_dataset(corpus, dataset_id="readme-test")
    write_bundle(dataset, tmp_path)
    readme = (tmp_path / "README.md").read_text("utf-8")
    assert "benign" in readme
    assert "adversarial" in readme
    assert "readme-test" in readme


def test_readme_has_hugging_face_dataset_metadata(tmp_path):
    corpus = [("benign", "plan a paired coding task")]
    dataset = build_dataset(corpus)
    write_bundle(dataset, tmp_path)
    readme_path = tmp_path / "README.md"

    card = DatasetCard.load(readme_path)
    readme = readme_path.read_text("utf-8")

    assert card.data.license == "cc-by-4.0"
    assert card.data.pretty_name == "SCBE Governance Receipts v1"
    assert "SCBE Governance Receipts v1" in readme
    assert "Dataset files" in readme
    assert "hf upload issdandavis/scbe-governance-receipts-v1" in readme


def test_default_dataset_id_constant():
    assert DEFAULT_DATASET_ID == "scbe-governance-receipts-v1"
