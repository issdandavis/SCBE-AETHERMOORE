from scripts.system.remote_training_lane_status import collect_status


def test_remote_training_lane_status_shape() -> None:
    report = collect_status()

    assert report["schema_version"] == "scbe_remote_training_lane_status_v1"
    assert report["hf"]["job_id"]
    assert "status_command" in report["hf"]
    assert "inspect_command" in report["hf"]
    assert "pull_command" in report["kaggle"]
    assert "kernel_status_command" in report["kaggle"]
    assert "scorecard" in report
