from scripts.eval.score_agentic_training_system import _grade, _sum_dataset_rows


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
