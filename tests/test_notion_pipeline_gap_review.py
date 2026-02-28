from __future__ import annotations

import json
import importlib.util
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List


def _load_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "notion_pipeline_gap_review.py"
    spec = importlib.util.spec_from_file_location("notion_pipeline_gap_review", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalize_string_list_filters_and_downcases():
    mod = _load_module()
    assert mod._normalize_string_list([" Notion ", "", "ALL", 3]) == ["notion", "all", "3"]


def test_filter_records_for_quality_checks_uses_source_filter():
    mod = _load_module()
    records = [
        {"source": "notion"},
        {"source": "notion"},
        {"source": "github"},
        {"source": ""},
    ]
    quality = {"imbalance_source_filter": ["notion"]}
    filtered = mod._filter_records_for_quality_checks(records, quality)
    assert [r["source"] for r in filtered] == ["notion", "notion"]


def test_evaluate_funnel_config_uses_quality_scope_filter_before_counts():
    mod = _load_module()
    records = [
        {"source": "notion", "categories": ["technical"]},
        {"source": "notion", "categories": ["technical"]},
        {"source": "github", "categories": ["technical"]},
    ]
    pipeline_config: Dict[str, Any] = {
        "fine_tune": {
            "streams": [
                {
                    "name": "technical_system_stream",
                    "categories": ["technical"],
                    "required_min_records": 3,
                }
            ],
            "quality_checks": {"imbalance_source_filter": ["notion"]},
        }
    }
    tasks: List[Dict[str, Any]] = []
    mod._evaluate_funnel_config(pipeline_config, records, tasks)

    assert len(tasks) == 1
    assert tasks[0]["title"] == "Increase 'technical_system_stream' training stream coverage"
    assert tasks[0]["evidence"]["matched_records"] == 2
    assert tasks[0]["evidence"]["total_records"] == 2


def test_evaluate_funnel_config_respects_category_imbalance_exclusions():
    mod = _load_module()
    records = [
        {"source": "notion", "categories": ["general"]},
        {"source": "notion", "categories": ["general"]},
        {"source": "notion", "categories": ["general"]},
        {"source": "notion", "categories": ["technical"]},
    ]
    pipeline_config: Dict[str, Any] = {
        "fine_tune": {
            "streams": [
                {
                    "name": "technical_system_stream",
                    "categories": ["technical"],
                    "required_min_records": 1,
                }
            ],
            "quality_checks": {
                "max_category_imbalance": 1.5,
                "max_category_imbalance_exclude": ["general"],
            },
        }
    }
    tasks: List[Dict[str, Any]] = []
    mod._evaluate_funnel_config(pipeline_config, records, tasks)

    # technical coverage passes and excluded category should prevent imbalance failure.
    assert len(tasks) == 0


def test_evaluate_funnel_config_reports_missing_streams():
    mod = _load_module()
    tasks: List[Dict[str, Any]] = []
    mod._evaluate_funnel_config({"fine_tune": {}}, [], tasks)
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Missing fine_tune streams in vertex pipeline config"
    assert tasks[0]["priority"] == "critical"


def test_evaluate_metadata_identifies_zero_and_stale_exports():
    mod = _load_module()

    zero: List[Dict[str, Any]] = []
    mod._evaluate_metadata({"exported_records": 0, "export_date": "2026-02-27T00:00:00Z"}, zero)
    assert len(zero) == 1
    assert zero[0]["title"] == "Notion export returned zero records"

    stale: List[Dict[str, Any]] = []
    stale_date = datetime.now(timezone.utc).date() - timedelta(days=20)
    mod._evaluate_metadata({"exported_records": 10, "export_date": stale_date.isoformat() + "T00:00:00Z"}, stale)
    assert len(stale) == 1
    assert stale[0]["title"] == "Notion export metadata is stale"


def test_run_gap_review_covers_notion_to_dataset_and_funnel_layers(tmp_path: Path):
    mod = _load_module()
    sync_path = tmp_path / "scripts" / "sync-config.json"
    sync_path.parent.mkdir(parents=True, exist_ok=True)
    sync_path.write_text(
        json.dumps(
            {
                "doc_sync": {
                    "pageId": "REPLACE_WITH_PAGE_ID",
                    "outputPath": "does_not_exist.md",
                }
            }
        ),
        encoding="utf-8",
    )

    pipeline_path = tmp_path / "training" / "vertex_pipeline_config.yaml"
    pipeline_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline_path.write_text("fine_tune: {}\n", encoding="utf-8")

    training_data = tmp_path / "training-data"
    training_data.mkdir()
    repo_root = tmp_path

    manifest = mod.run_gap_review(
        repo_root=repo_root,
        sync_config_path=sync_path,
        pipeline_config_path=pipeline_path,
        training_data_path=training_data,
    )

    titles = {task["title"] for task in manifest["tasks"]}
    assert "Resolve Notion placeholder for sync key 'doc_sync'" in titles
    assert "Missing fine_tune streams in vertex pipeline config" in titles
    assert "Rebuild training-data metadata file" in titles

    assert manifest["summary"]["total_tasks"] == 3


def test_run_gap_review_reports_healthy_when_all_layers_aligned(tmp_path: Path):
    mod = _load_module()
    sync_path = tmp_path / "scripts" / "sync-config.json"
    sync_path.parent.mkdir(parents=True, exist_ok=True)
    sync_path.write_text(
        (
            '{"doc_sync": {'
            '"pageId": "12345678-1234-1234-1234-123456789abc", '
            '"outputPath": "training-data"}'
            "}"
        ),
        encoding="utf-8",
    )

    pipeline_path = tmp_path / "training" / "vertex_pipeline_config.yaml"
    pipeline_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline_path.write_text(
        """
fine_tune:
  streams:
    - name: technical_system_stream
      categories:
        - technical
      required_min_records: 1
      lane: canonical
""",
        encoding="utf-8",
    )

    training_data = tmp_path / "training-data"
    training_data.mkdir()
    dataset_path = training_data / "notion_export_all.jsonl"
    dataset_path.write_text(
        '{"source":"notion","categories":["technical"],"title":"doc1"}\n',
        encoding="utf-8",
    )
    metadata = {
        "exported_records": 1,
        "export_date": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    (training_data / "metadata.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    manifest = mod.run_gap_review(
        repo_root=tmp_path,
        sync_config_path=sync_path,
        pipeline_config_path=pipeline_path,
        training_data_path=training_data,
    )

    assert manifest["summary"]["status"] == "healthy"
    assert manifest["summary"]["total_tasks"] == 0
