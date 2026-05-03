from scripts.eval.score_agentic_training_system import _grade, _model_lines, _packet_job_id, _sum_dataset_rows


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
