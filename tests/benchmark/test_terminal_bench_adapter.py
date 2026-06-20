from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "terminal_bench_adapter.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("terminal_bench_adapter", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_terminal_adapter_builds_answer_file_receipts(tmp_path: Path) -> None:
    module = _load_module()

    report = module.build_report(tmp_path, run_id="pytest-terminal-adapter")

    assert report["schema_version"] == "scbe_terminal_bench_adapter_v1"
    assert report["summary"]["decision"] == "PASS"
    assert report["summary"]["passed"] == report["summary"]["task_count"]
    assert report["summary"]["answer_contract"] == "answer.txt"
    assert report["summary"]["cross_test"] == "real-patch-tasks"
    assert (tmp_path / "pytest-terminal-adapter" / "report.json").exists()
    assert (tmp_path / "latest_report.json").exists()
    assert (tmp_path / "LATEST.md").exists()

    for receipt in report["receipts"]:
        assert receipt["ok"] is True
        assert receipt["answer_ok"] is True
        assert receipt["answer_path"] == "answer.txt"
        assert receipt["answer_sha256"]
        assert receipt["artifact_sha256"]


def test_terminal_adapter_rejects_wrong_answer(tmp_path: Path) -> None:
    module = _load_module()
    task = module.TerminalTask(
        task_id="wrong_answer",
        instruction="Write the expected answer.",
        files={},
        command=(sys.executable, "-c", "from pathlib import Path; Path('answer.txt').write_text('wrong')"),
        answer_path="answer.txt",
        expected_answer="right",
    )

    receipt = module.run_task(tmp_path, task)

    assert receipt.ok is False
    assert receipt.answer_ok is False
    assert "expected 'right', got 'wrong'" in receipt.verifier_note


def test_terminal_adapter_cli_smoke(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/benchmark/terminal_bench_adapter.py", "--out-dir", str(tmp_path), "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=False,
        timeout=60,
    )

    assert proc.returncode == 0, proc.stderr
    assert "scbe_terminal_bench_adapter_v1" in proc.stdout
    assert (tmp_path / "latest_report.json").exists()
