from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_funnel_labels_count_tags_source_paths_and_chemistry_markers(tmp_path: Path) -> None:
    orchestrator = _load_module("self_improvement_orchestrator_test", "scripts/self_improvement_orchestrator.py")

    training_dir = tmp_path / "training-data"
    training_dir.mkdir()
    rows = [
        {"source": "docs/CODING_SYSTEMS_MASTER_REFERENCE.md", "text": "coding spine"},
        {"smiles": "CCO", "tags": ["organic"], "expected_family": "alcohol"},
        {"source": "docs/proposals/DARPA_MATHBAC/evidence.md", "text": "research"},
    ]
    (training_dir / "sample.jsonl").write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    config = {
        "fine_tune": {
            "streams": [
                {"name": "coding", "lane": "canonical", "required_min_records": 1, "categories": ["coding"]},
                {"name": "chemistry", "lane": "canonical", "required_min_records": 1, "categories": ["chemistry"]},
                {"name": "research", "lane": "research", "required_min_records": 1, "categories": ["darpa"]},
            ]
        }
    }

    tasks = orchestrator._fine_tune_funnel_tasks(training_dir, config)

    assert len(tasks) == 1
    assert tasks[0].title == "Fine-tune funnel remains healthy"


def test_gap_review_no_longer_flags_present_fine_tune_streams(tmp_path: Path) -> None:
    gap_review = _load_module("notion_pipeline_gap_review_test", "scripts/notion_pipeline_gap_review.py")

    training_dir = tmp_path / "training-data"
    training_dir.mkdir()
    (training_dir / "sample.jsonl").write_text(
        json.dumps({"smiles": "CCO", "tags": ["organic"], "expected_family": "alcohol"}) + "\n",
        encoding="utf-8",
    )
    (training_dir / "metadata.json").write_text(
        json.dumps({"exported_records": 1, "category_breakdown": {"chemistry": 1}}),
        encoding="utf-8",
    )
    sync_config = tmp_path / "sync-config.json"
    sync_config.write_text("{}", encoding="utf-8")
    pipeline_config = tmp_path / "vertex_pipeline_config.yaml"
    pipeline_config.write_text(
        "\n".join(
            [
                "fine_tune:",
                "  streams:",
                "    - name: chemistry",
                "      lane: canonical",
                "      required_min_records: 1",
                "      categories:",
                "        - chemistry",
            ]
        ),
        encoding="utf-8",
    )

    manifest = gap_review.run_gap_review(tmp_path, sync_config, pipeline_config, training_dir)
    titles = {task["title"] for task in manifest["tasks"]}

    assert "Missing fine_tune streams in vertex pipeline config" not in titles
    assert not any(title.startswith("Increase 'chemistry' training stream coverage") for title in titles)


def test_gap_review_local_export_mode_does_not_require_live_notion(tmp_path: Path) -> None:
    gap_review = _load_module("notion_pipeline_gap_review_local_mode_test", "scripts/notion_pipeline_gap_review.py")

    training_dir = tmp_path / "training-data"
    training_dir.mkdir()
    (training_dir / "sample.jsonl").write_text(
        json.dumps({"source": "docs/SCBE_SYSTEM_OVERVIEW.md", "text": "local export row"}) + "\n",
        encoding="utf-8",
    )
    (training_dir / "metadata.json").write_text(
        json.dumps({"exported_records": 0, "total_pages": 0, "category_breakdown": {}}),
        encoding="utf-8",
    )
    sync_config = tmp_path / "sync-config.json"
    sync_config.write_text(
        json.dumps({"missing": {"pageId": "local-disabled", "outputPath": "docs/MISSING_FROM_LIVE_NOTION.md"}}),
        encoding="utf-8",
    )
    pipeline_config = tmp_path / "vertex_pipeline_config.yaml"
    pipeline_config.write_text(
        "\n".join(
            [
                "notion:",
                "  source_mode: local_export_only",
                "  live_sync_required: false",
                "  live_export_required: false",
                "fine_tune:",
                "  streams:",
                "    - name: local_docs",
                "      lane: research",
                "      required_min_records: 1",
                "      categories:",
                "        - scbe",
            ]
        ),
        encoding="utf-8",
    )

    manifest = gap_review.run_gap_review(tmp_path, sync_config, pipeline_config, training_dir)
    titles = {task["title"] for task in manifest["tasks"]}

    assert "Notion export returned zero records" not in titles
    assert not any(title.startswith("Sync output path missing") for title in titles)
    assert manifest["summary"]["local_records"] == 1
