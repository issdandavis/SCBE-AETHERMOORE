from __future__ import annotations

import json
from pathlib import Path

from scripts.system import publish_training_dataset_repo as publisher


def test_prepare_dataset_repo_combines_training_data_and_generated_inputs(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    training_data = repo_root / "training-data" / "sft"
    training_data.mkdir(parents=True)
    (training_data / "base.jsonl").write_text('{"instruction":"a","response":"b"}\n', encoding="utf-8")

    draft_root = tmp_path / "drafts"
    draft_root.mkdir()
    (draft_root / "draft.txt").write_text(
        (
            "The Spiral of Avalon follows Izack, Polly, Aria, and Clay through Avalon Academy. "
            "The World Tree and Sacred Tongues shape collaborative magic across the realm.\n\n"
        )
        * 50,
        encoding="utf-8",
    )

    monkeypatch.setattr(publisher, "REPO_ROOT", repo_root)
    build_root = tmp_path / "build"
    output_repo = tmp_path / "dataset-repo"
    result = publisher.prepare_dataset_repo(
        include_training_data=True,
        claude_export_zips=[],
        draft_roots=[str(draft_root)],
        extra_inputs=[],
        build_root=build_root,
        output_repo=output_repo,
        dataset_repo="issdandavis/scbe-aethermoore-training-data",
        max_bytes=1024,
        exclude_globs=[],
    )

    manifest = result["manifest"]
    assert manifest["counts"]["source_files"] == 2
    summary_path = Path(result["build_summary_path"])
    assert summary_path.exists()
    build_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert build_summary["generated"][0]["kind"] == "draft_corpus"
    assert (output_repo / "manifests" / "training_dataset_manifest.json").exists()
