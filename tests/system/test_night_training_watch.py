from scripts.system import night_training_watch as watch


def test_collect_once_records_remote_status_and_bijective_tests() -> None:
    commands: list[list[str]] = []

    def fake_runner(command: list[str], timeout: int) -> dict:
        commands.append(command)
        text = "ok"
        if command[:3] == ["hf", "jobs", "inspect"]:
            text = '"status": {"stage": "RUNNING"}'
        if command[:3] == ["kaggle", "kernels", "status"]:
            text = "KernelWorkerStatus.RUNNING"
        if any("score_agentic_training_system.py" in part for part in command):
            text = '{"overall_score": 68.7, "model_promotion_score": 32.5, "rank": "C"}'
        if command[:3] == ["python", "-m", "pytest"] or command[1:3] == ["-m", "pytest"]:
            text = "4 passed"
        return {
            "command": command,
            "returncode": 0,
            "duration_sec": 0.01,
            "stdout": text,
            "stderr": "",
            "timed_out": False,
        }

    report = watch.collect_once(runner=fake_runner)

    assert report["schema_version"] == "scbe_night_training_watch_v1"
    assert report["kaggle"]["status"] == "running"
    assert report["scorecard"]["overall_score"] == 68.7
    assert report["bijective_coding"]["status"] == "complete"
    assert any("test_bijective_reasoning_code_packet.py" in part for command in commands for part in command)


def test_completed_kaggle_triggers_pull() -> None:
    def fake_runner(command: list[str], timeout: int) -> dict:
        stdout = "ok"
        if command[:3] == ["hf", "jobs", "inspect"]:
            stdout = '"status": {"stage": "RUNNING"}'
        if command[:3] == ["kaggle", "kernels", "status"]:
            stdout = "KernelWorkerStatus.COMPLETE"
        if "--pull" in command:
            stdout = "pulled"
        return {
            "command": command,
            "returncode": 0,
            "duration_sec": 0.01,
            "stdout": stdout,
            "stderr": "",
            "timed_out": False,
        }

    report = watch.collect_once(runner=fake_runner, run_tests=False)

    assert report["kaggle"]["status"] == "complete"
    assert [action["name"] for action in report["actions"]] == ["kaggle_pull"]


def test_write_report_creates_latest_and_journal(tmp_path) -> None:
    paths = watch.write_report({"schema_version": "x", "ok": True}, tmp_path)

    assert paths["latest"].endswith("latest.json")
    assert paths["journal"].endswith("night_training_watch.jsonl")
    assert (tmp_path / "latest.json").exists()
    assert (tmp_path / "night_training_watch.jsonl").exists()
