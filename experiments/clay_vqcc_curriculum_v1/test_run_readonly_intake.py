from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import run_readonly_intake as intake
from test_pipeline_integration import _make_corpus


ROOT = Path(__file__).resolve().parent


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_test_spec(path: Path, *, manifest_sha256: str, counts: dict[str, int]) -> str:
    spec = json.loads((ROOT / "CAMPAIGN_SPEC.json").read_text(encoding="utf-8"))
    spec["dataset"]["manifest_sha256"] = manifest_sha256
    spec["dataset"]["counts"] = counts
    spec["campaign_split"]["holdout_fraction"] = 0.5
    for role in intake.ROLES:
        spec["sampling"][role] = {
            "seed": 739 if role == "train" else 740,
            "lane_caps": {
                "public.experimental_findings": 100,
                "public.gate_count": 100,
            },
            "max_chars_per_record": 1_000,
            "max_tokens_per_record": 1_000,
            "total_token_budget": 100_000,
        }
    path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    return _sha256(path)


def _fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    corpus = tmp_path / "corpus"
    manifest_sha256, counts = _make_corpus(corpus)
    spec_path = tmp_path / "CAMPAIGN_SPEC.test.json"
    spec_sha256 = _write_test_spec(
        spec_path, manifest_sha256=manifest_sha256, counts=counts
    )
    return corpus, spec_path, spec_sha256


def test_readonly_intake_builds_sealed_tasks_without_mutating_corpus(tmp_path: Path) -> None:
    corpus, spec_path, spec_sha256 = _fixture(tmp_path)
    before = {
        path.relative_to(corpus).as_posix(): _sha256(path)
        for path in sorted(corpus.rglob("*"))
        if path.is_file()
    }
    output = tmp_path / "intake"

    receipt = intake.run_readonly_intake(
        corpus,
        output,
        spec_path=spec_path,
        expected_spec_sha256=spec_sha256,
    )

    after = {
        path.relative_to(corpus).as_posix(): _sha256(path)
        for path in sorted(corpus.rglob("*"))
        if path.is_file()
    }
    assert after == before
    assert receipt["status"] == "PASS_PREPARED_ONLY"
    assert receipt["mode"] == {
        "training": False,
        "cloud_or_kaggle_execution": False,
        "dataset_mutation": False,
        "competition_submission": False,
    }
    assert receipt["invariants"] == {
        "source_family_overlap": 0,
        "record_id_overlap": 0,
        "gate_task_family_and_record_overlap": 0,
        "finding_task_family_and_record_overlap": 0,
        "required_finding_task_coverage": True,
        "manifest_and_consumed_files_verified": True,
        "failure_atomic_output": True,
    }
    for role in intake.ROLES:
        assert (output / "samples" / f"{role}.jsonl").is_file()
        assert (output / "samples" / f"{role}.receipt.json").is_file()
        assert receipt["tasks"][role]["gate_count"]["balanced"]["label_counts"] == {
            "A": 2,
            "B": 2,
            "T": 2,
        }
        assert set(
            receipt["tasks"][role]["finding_binding"]["comparisons"]["task_counts"]
        ) == {"all", "chemistry", "dqi", "invsqrt"}
    assert receipt["tasks"]["train"]["finding_binding"]["aligned_training_arms"][
        "retained_records"
    ] == 8
    assert json.loads((output / "INTAKE_RECEIPT.json").read_text(encoding="utf-8")) == receipt
    assert sorted(path.name for path in output.iterdir()) == [
        "INTAKE_RECEIPT.json",
        "campaign-split",
        "samples",
    ]


def test_mid_pipeline_failure_removes_all_staged_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus, spec_path, spec_sha256 = _fixture(tmp_path)
    output = tmp_path / "failed-intake"

    def fail_build(*_args, **_kwargs):
        raise RuntimeError("injected task-builder failure")

    monkeypatch.setattr(intake.findings_task, "build_finding_comparisons", fail_build)
    with pytest.raises(RuntimeError, match="injected task-builder failure"):
        intake.run_readonly_intake(
            corpus,
            output,
            spec_path=spec_path,
            expected_spec_sha256=spec_sha256,
        )

    assert not output.exists()
    assert list(tmp_path.glob(f".{output.name}.tmp-*")) == []


def test_spec_pin_and_prepared_only_authority_fail_closed(tmp_path: Path) -> None:
    corpus, spec_path, spec_sha256 = _fixture(tmp_path)
    output = tmp_path / "intake"
    with pytest.raises(ValueError, match="Campaign spec hash differs"):
        intake.run_readonly_intake(
            corpus,
            output,
            spec_path=spec_path,
            expected_spec_sha256="0" * 64,
        )
    assert not output.exists()

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["training_authorized"] = True
    spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="authority-bearing"):
        intake.run_readonly_intake(
            corpus,
            output,
            spec_path=spec_path,
            expected_spec_sha256=_sha256(spec_path),
        )
    assert not output.exists()
    assert spec_sha256 != _sha256(spec_path)


def test_existing_output_and_corpus_descendant_output_are_rejected(tmp_path: Path) -> None:
    corpus, spec_path, spec_sha256 = _fixture(tmp_path)
    existing = tmp_path / "existing"
    existing.mkdir()
    marker = existing / "marker.txt"
    marker.write_text("preserve", encoding="utf-8")
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        intake.run_readonly_intake(
            corpus,
            existing,
            spec_path=spec_path,
            expected_spec_sha256=spec_sha256,
        )
    assert marker.read_text(encoding="utf-8") == "preserve"

    with pytest.raises(ValueError, match="must not be the corpus root"):
        intake.run_readonly_intake(
            corpus,
            corpus / "forbidden-output",
            spec_path=spec_path,
            expected_spec_sha256=spec_sha256,
        )
    assert not (corpus / "forbidden-output").exists()
