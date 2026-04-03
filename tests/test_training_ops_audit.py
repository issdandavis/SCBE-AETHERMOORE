from pathlib import Path

from scripts.system.training_ops_audit import build_training_ops_audit, summarize_registry


def test_build_training_ops_audit_reports_safe_scope_and_canonical_notebooks(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    payload = build_training_ops_audit(registry)

    assert payload["schema_version"] == "training_ops_audit_v1"
    assert "artifacts/research/**" in payload["safe_scope"]["excluded"]
    names = {item["name"] for item in payload["canonical_notebooks"]}
    assert "canonical-training-lane" in names
    assert "spiralverse-generator" in names
    assert payload["registry"]["exists"] is False
    assert payload["warnings"]


def test_summarize_registry_counts_runs_and_promotions(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text(
        """
        {
          "schema_version": "multi_host_training_registry_v1",
          "runs": [
            {"run_id": "colab-a", "status": "promoted"},
            {"run_id": "kaggle-b", "status": "candidate"}
          ],
          "promotions": {
            "textgen": {"run_id": "colab-a"}
          }
        }
        """,
        encoding="utf-8",
    )

    summary = summarize_registry(registry)
    assert summary["exists"] is True
    assert summary["run_count"] == 2
    assert summary["promotion_count"] == 1
    assert summary["promotions"]["textgen"]["run_id"] == "colab-a"
