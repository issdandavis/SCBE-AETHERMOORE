from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR_PATH = ROOT / "scripts" / "system" / "extract_specialist_training_records.py"
REVIEW_PATH = ROOT / "scripts" / "system" / "review_training_runs.py"
READINESS_PATH = ROOT / "scripts" / "benchmark" / "specialist_bucket_readiness.py"

# Operator records are extracted from local run artifacts that are not
# committed to the repo; the extractor yields zero operator records without
# them, so the source-faithful test only runs where they exist.
OPERATOR_ARTIFACT_ROOTS = [
    ROOT / "artifacts" / "ai2ai_bridge",
    ROOT / "artifacts" / "ai2ai_bridge_live",
    ROOT / "artifacts" / "benchmark" / "orchestrator_live",
    ROOT / "artifacts" / "benchmark" / "run_route_shell",
    ROOT / "artifacts" / "benchmark" / "project_scaffold_run_route",
]


def _load(path: Path, name: str):
    """Import a script file as a module under ``name``."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(
    not any(root.exists() for root in OPERATOR_ARTIFACT_ROOTS),
    reason="operator agent-bus run artifacts not present in this checkout",
)
def test_specialist_extractor_builds_source_faithful_records(tmp_path: Path) -> None:
    """Extractor builds manifests with operator/research records from artifacts."""
    extractor = _load(EXTRACTOR_PATH, "extract_specialist_training_records_test")

    manifest = extractor.build(tmp_path)

    assert manifest["counts"]["operator_train"] > 0
    assert manifest["counts"]["operator_eval"] > 0
    assert manifest["counts"]["research_train"] > 0
    assert manifest["counts"]["research_eval"] > 0
    assert manifest["counts"]["governance_eval"] > 0

    operator_train = tmp_path / "operator_agent_bus_extracted_v1_train.sft.jsonl"
    first = json.loads(operator_train.read_text(encoding="utf-8").splitlines()[0])

    assert first["messages"][0]["role"] == "user"
    assert first["messages"][1]["role"] == "assistant"
    assert first["metadata"]["purpose"] == "operator_agent_bus"
    assert first["metadata"]["source_path"]
    assert first["metadata"]["dedupe_key"]


def test_gain_board_marks_data_ready_buckets_as_needing_benchmark() -> None:
    """Buckets with data but no benchmark are marked as needing one."""
    review = _load(REVIEW_PATH, "review_training_runs_test")
    plan = {
        "specialists": [
            {
                "purpose": "operator_agent_bus",
                "train_records": 12,
                "eval_records": 3,
            }
        ]
    }

    board = review.build_gain_board([], plan)

    assert board["operator_agent_bus"]["status"] == "ready_needs_benchmark"
    assert "no measurable run artifacts" in board["operator_agent_bus"]["blockers"]


def test_gain_board_promotes_bucket_with_eval_and_metrics() -> None:
    """Buckets with eval coverage and metrics get promoted."""
    review = _load(REVIEW_PATH, "review_training_runs_promote_test")
    plan = {
        "specialists": [
            {
                "purpose": "coding_model",
                "train_records": 10,
                "eval_records": 2,
            }
        ]
    }
    reviews = [
        {
            "purpose": "coding_model",
            "path": "artifacts/benchmark/example.json",
            "promotion_score": 77.0,
            "quality_signal": 0.97,
            "loss_signal": None,
            "metric_count": 1,
            "decision": "PASS",
        }
    ]

    board = review.build_gain_board(reviews, plan)

    assert board["coding_model"]["status"] == "promote_candidate"
    assert board["coding_model"]["top_promotion_score"] == 77.0
    assert board["coding_model"]["diamond_counts"]["diamond_promotion_ready"] == 1


def test_gain_board_does_not_promote_metric_without_frozen_gate() -> None:
    """Metrics without a frozen gate must not trigger promotion."""
    review = _load(REVIEW_PATH, "review_training_runs_polished_test")
    plan = {
        "specialists": [
            {
                "purpose": "coding_model",
                "train_records": 10,
                "eval_records": 2,
            }
        ]
    }
    reviews = [
        {
            "purpose": "coding_model",
            "path": "artifacts/benchmark/example.json",
            "promotion_score": 99.0,
            "quality_signal": 0.99,
            "loss_signal": None,
            "metric_count": 1,
        }
    ]

    board = review.build_gain_board(reviews, plan)

    assert board["coding_model"]["status"] == "polished_needs_frozen_gate"
    assert "quality signal exists but no explicit frozen gate PASS" in board["coding_model"]["blockers"]
    assert board["coding_model"]["diamond_counts"]["polished_candidate"] == 1


def test_gain_board_blocks_explicit_hold_eval_artifact() -> None:
    """An explicit hold eval artifact blocks promotion."""
    review = _load(REVIEW_PATH, "review_training_runs_hold_test")
    plan = {
        "specialists": [
            {
                "purpose": "governance_security",
                "train_records": 10,
                "eval_records": 2,
            }
        ]
    }
    reviews = [
        {
            "purpose": "governance_security",
            "path": "artifacts/benchmarks/governance_security_eval/report.json",
            "promotion_score": 100.0,
            "quality_signal": 1.0,
            "loss_signal": None,
            "metric_count": 3,
            "decision": "HOLD",
        }
    ]

    board = review.build_gain_board(reviews, plan)

    assert board["governance_security"]["status"] == "needs_eval_gate"
    assert "explicit HOLD eval artifact" in board["governance_security"]["blockers"][0]
    assert "false-positive" in board["governance_security"]["recommended_action"]


def test_diamond_state_marks_loss_only_as_cut_not_promoted() -> None:
    """Loss-only runs are marked cut, not promoted."""
    review = _load(REVIEW_PATH, "review_training_runs_loss_only_test")

    state = review.diamond_state_for_run(
        {
            "promotion_score": 15.0,
            "quality_signal": None,
            "loss_signal": 0.9,
            "metric_count": 1,
        }
    )

    assert state["state"] == "cut_loss_only"
    assert state["promotion_ready"] is False


def test_score_run_rejects_huge_config_quality_counts() -> None:
    """score_run rejects implausibly huge config-quality counts."""
    review = _load(REVIEW_PATH, "review_training_runs_score_guard_test")

    scored = review.score_run(
        [
            review.MetricSignal(
                name="score",
                value=143548.0,
                kind="quality",
                json_path="model.vocab_score_like_config_count",
            )
        ]
    )

    assert scored["raw_quality_signal"] == 143548.0
    assert scored["quality_signal"] is None
    assert scored["promotion_score"] == 0.0


def test_iter_json_artifacts_skips_tokenizer_config_files(tmp_path: Path) -> None:
    """Tokenizer config JSONs are skipped when iterating artifacts."""
    review = _load(REVIEW_PATH, "review_training_runs_skip_tokenizer_test")
    root = tmp_path / "runs"
    root.mkdir()
    (root / "tokenizer.json").write_text('{"score": 143548}', encoding="utf-8")
    (root / "report.json").write_text('{"pass_rate": 1.0}', encoding="utf-8")

    files = review.iter_json_artifacts((str(root),))

    assert [path.name for path in files] == ["report.json"]


def test_specialist_bucket_readiness_scores_valid_bucket(tmp_path: Path) -> None:
    """Readiness scoring accepts a structurally valid bucket."""
    readiness = _load(READINESS_PATH, "specialist_bucket_readiness_test")
    train_path = tmp_path / "train.jsonl"
    eval_path = tmp_path / "eval.jsonl"
    manifest_path = tmp_path / "manifest.json"

    def row(idx: int, split: str) -> dict:
        """Build one synthetic SFT record row."""
        return {
            "messages": [
                {"role": "user", "content": f"request {idx}"},
                {"role": "assistant", "content": f"response {idx}"},
            ],
            "metadata": {
                "source_path": f"source/{split}/{idx}.json",
                "dedupe_key": f"{split}-{idx}",
            },
        }

    train_path.write_text("\n".join(json.dumps(row(i, "train")) for i in range(10)) + "\n", encoding="utf-8")
    eval_path.write_text("\n".join(json.dumps(row(i, "eval")) for i in range(3)) + "\n", encoding="utf-8")
    manifest = {"outputs": {"train": str(train_path), "eval": str(eval_path), "manifest": str(manifest_path)}}

    report = readiness.benchmark_bucket("operator_agent_bus", manifest)

    assert report["decision"] == "PASS"
    assert report["readiness_score"] == 1.0
    assert report["train_eval_overlap_count"] == 0
