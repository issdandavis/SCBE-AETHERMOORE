import json

from scripts.eval import score_agentic_training_system as scorer
from scripts.eval.score_agentic_training_system import (
    _grade,
    _local_hf_gate_from_log,
    _model_lines,
    _packet_job_id,
    _sum_dataset_rows,
)


def test_sum_dataset_rows_handles_hf_job_packet_shape() -> None:
    datasets = [
        {"name": "train-a.jsonl", "row_count": 4},
        {"name": "train-b.jsonl", "row_count": 6},
        {"name": "missing-count.jsonl"},
    ]

    assert _sum_dataset_rows(datasets) == 10


def test_grade_keeps_smoke_runs_below_raid_ready() -> None:
    assert _grade(78.2)["rank"] == "Dungeon Clear"
    assert _grade(90.0)["rank"] == "Raid Ready"


def test_packet_job_id_reads_nested_dispatch() -> None:
    packet = {"dispatch": {"job_id": "abc123"}}

    assert _packet_job_id(packet) == "abc123"


def test_model_lines_scores_dpo_dataset_without_eval_floor() -> None:
    evidence = {
        "kaggle_done": {"status": "complete", "round": "r1", "global_step": 3, "push": False},
        "kaggle_history": {},
        "hf_packet": {
            "schema_version": "scbe_coding_agent_dpo_hf_job_packet_v1",
            "profile_id": "coding-agent-qwen-stage6-boss-dpo-v1",
            "dispatched": True,
            "dispatch": {"job_id": "job-1"},
            "train_datasets": [{"row_count": 168}],
            "eval_datasets": [],
        },
        "hf_gate": {
            "job_id": "job-1",
            "gate_overall_pass": True,
            "gate_pass_rate": 1.0,
            "pushed_adapter": True,
        },
    }

    lines = {item.name: item for item in _model_lines(evidence)}

    assert lines["hf_dataset_floor"].status == "PASS"
    assert "eval=n/a dpo" in lines["hf_dataset_floor"].evidence
    assert lines["adapter_promoted"].status == "PASS"


def test_local_hf_gate_from_log_reads_training_complete(monkeypatch, tmp_path) -> None:
    root = tmp_path
    log_dir = root / "artifacts" / "hf_coding_agent_jobs" / "profile" / "run"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "hf_job_job-1.log"
    log_path.write_text(
        json.dumps(
            {
                "event": "training_complete",
                "summary": {
                    "profile_id": "profile",
                    "adapter_repo": "owner/adapter",
                    "training_loss": 1.23,
                    "pushed_adapter": True,
                    "gate_overall_pass": True,
                    "gate_pass_rate": 1.0,
                    "gate_n_pass": 4,
                    "gate_n_total": 4,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(scorer, "PROJECT_ROOT", root)

    gate = _local_hf_gate_from_log("job-1")

    assert gate["source"] == "local_hf_log"
    assert gate["gate_overall_pass"] is True
    assert gate["pushed_adapter"] is True
    assert gate["train_loss"] == 1.23


def test_local_hf_gate_from_log_reads_pretty_training_complete(monkeypatch, tmp_path) -> None:
    root = tmp_path
    log_dir = root / "artifacts" / "hf_coding_agent_jobs" / "profile" / "run"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "hf_job_job-2.log"
    log_path.write_text(
        json.dumps(
            {
                "event": "training_complete",
                "summary": {
                    "profile_id": "profile",
                    "adapter_repo": "owner/adapter",
                    "training_loss": 0.9,
                    "pushed_adapter": True,
                    "gate_overall_pass": True,
                    "gate_pass_rate": 1.0,
                    "gate_n_pass": 4,
                    "gate_n_total": 4,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(scorer, "PROJECT_ROOT", root)

    gate = _local_hf_gate_from_log("job-2")

    assert gate["source"] == "local_hf_log"
    assert gate["gate_n_pass"] == 4
    assert gate["train_loss"] == 0.9


def test_local_hf_gate_from_log_reads_sibling_hf_job_logs(monkeypatch, tmp_path) -> None:
    root = tmp_path
    log_dir = root / "artifacts" / "hf_coding_agent_jobs" / "profile" / "run"
    log_dir.mkdir(parents=True)
    packet_path = log_dir / "job_packet.json"
    packet_path.write_text(json.dumps({"dispatch": {"job_id": "job-3"}}), encoding="utf-8")
    (log_dir / "hf_job_logs.txt").write_text(
        json.dumps(
            {
                "event": "training_complete",
                "summary": {
                    "profile_id": "profile",
                    "adapter_repo": "owner/adapter",
                    "training_loss": 0.7,
                    "pushed_adapter": True,
                    "gate_overall_pass": True,
                    "gate_pass_rate": 1.0,
                    "gate_n_pass": 5,
                    "gate_n_total": 5,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(scorer, "PROJECT_ROOT", root)

    gate = _local_hf_gate_from_log("job-3", packet_path)

    assert gate["source"] == "local_hf_log"
    assert gate["gate_n_pass"] == 5
    assert gate["pushed_adapter"] is True
