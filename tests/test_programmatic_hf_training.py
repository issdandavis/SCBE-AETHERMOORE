from __future__ import annotations

import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "programmatic_hf_training.py"
SPEC = importlib.util.spec_from_file_location("programmatic_hf_training", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _sample_rows(count: int = 12) -> list[dict[str, object]]:
    labels = ["governance", "crypto", "browser", "lore"]
    rows: list[dict[str, object]] = []
    for index in range(count):
        rows.append(
            {
                "instruction": f"Instruction {index}: explain bounded agent step {index}",
                "output": (
                    f"Output {index}: this is a sufficiently long response about "
                    f"SCBE governed training lane behavior and audit trace {index}."
                ),
                "label": labels[index % len(labels)],
                "tongue": "KO",
                "curriculum": "foundation",
                "content_hash": f"hash-{index}",
            }
        )
    return rows


def test_build_dataset_package_emits_splits_and_pairs(tmp_path: Path) -> None:
    source_path = tmp_path / "clean.jsonl"
    MODULE.write_jsonl(source_path, _sample_rows(10))

    audit_report = {"status": "ALLOW", "hashchain_root": "abc123"}
    package_dir = tmp_path / "package"
    manifest = MODULE.build_dataset_package(
        source_path=source_path,
        output_dir=package_dir,
        dataset_repo="issdandavis/scbe-aethermoore-knowledge-base",
        audit_report=audit_report,
        seed=42,
        train_ratio=0.8,
        val_ratio=0.1,
    )

    assert manifest["total_rows"] == 10
    assert manifest["split_counts"]["train"] >= 1
    assert manifest["split_counts"]["validation"] >= 0
    assert manifest["split_counts"]["test"] >= 1
    assert manifest["embedding_pair_count"] == 10
    assert (package_dir / "data" / "all.jsonl").exists()
    assert (package_dir / "data" / "train.jsonl").exists()
    assert (package_dir / "data" / "validation.jsonl").exists()
    assert (package_dir / "data" / "test.jsonl").exists()
    assert (package_dir / "data" / "embedding_pairs.jsonl").exists()
    assert (package_dir / "README.md").exists()


def test_publish_dataset_package_dry_run(tmp_path: Path) -> None:
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    result = MODULE.publish_dataset_package(
        package_dir=package_dir,
        repo_id="issdandavis/scbe-aethermoore-knowledge-base",
        token="",
        private=False,
        dry_run=True,
    )
    assert result["status"] == "dry_run"
    assert result["repo_id"] == "issdandavis/scbe-aethermoore-knowledge-base"


def test_run_local_placeholder_training_smoke(tmp_path: Path) -> None:
    source_path = tmp_path / "clean.jsonl"
    MODULE.write_jsonl(source_path, _sample_rows(16))

    report = MODULE.run_local_placeholder_training(
        source_path=source_path,
        run_dir=tmp_path / "model_run",
        dataset_repo="issdandavis/scbe-aethermoore-knowledge-base",
        model_repo="issdandavis/phdm-21d-embedding-next",
        epochs=2,
        embedding_dim=32,
        learning_rate=0.2,
        val_ratio=0.2,
        seed=42,
        max_samples=64,
        push_to_hub=False,
        token="",
    )

    assert report["status"] == "completed"
    assert report["data"]["sample_count"] >= 16
    assert "growth" in report
    assert (tmp_path / "model_run" / "label_map.json").exists()
    assert (tmp_path / "model_run" / "model_weights.npz").exists()
    metrics = json.loads((tmp_path / "model_run" / "hf_training_metrics.json").read_text(encoding="utf-8"))
    assert metrics["model_repo"] == "issdandavis/phdm-21d-embedding-next"
