from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.benchmark.terminus_training_runner import TerminusTrainingSession, run_benchmark, run_scripted

ROOT = Path(__file__).resolve().parents[2]


def test_terminus_session_solves_math_enemy() -> None:
    session = TerminusTrainingSession(agent_id="unit")
    for command in [
        "cd GuildDistrict",
        "cd AdvancedMathematicsGuild",
        "cd MathArena",
        "less LinearEquationEnemy",
        "solve LinearEquationEnemy 4",
    ]:
        response = session.run(command)
    assert "defeated" in response
    summary = session.summary()
    assert summary["score"] > 0
    assert "LinearEquationEnemy" in summary["solved"]


def test_scripted_run_writes_checkpoint_sft(tmp_path: Path) -> None:
    payload = run_scripted(
        [
            "ls",
            "cd GuildDistrict",
            "less GuildDirectory",
            "cd AdvancedMathematicsGuild",
            "cd MathArena",
            "solve LinearEquationEnemy 4",
        ],
        agent_id="unit-agent",
        scenario="unit",
        out_dir=tmp_path,
    )
    sft_path = Path(payload["sft_path"])
    events_path = Path(payload["events_path"])
    assert sft_path.exists()
    assert events_path.exists()
    rows = [json.loads(line) for line in sft_path.read_text(encoding="utf-8").splitlines()]
    assert rows
    assert rows[-1]["metadata"]["track"] == "terminus_guild_agent_training"
    assert rows[-1]["metadata"]["event_type"] == "solve_enemy"


def test_benchmark_passes_and_covers_representation_enemies(tmp_path: Path) -> None:
    report = run_benchmark(tmp_path, agent_id="unit-benchmark")
    assert report["pass"] is True
    assert {"LinearEquationEnemy", "BinaryMaskEnemy", "HexCarryEnemy"}.issubset(report["solved"])
    assert Path(report["report_path"]).exists()


def test_geoseal_terminus_training_cli(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "terminus-training",
            "--mode",
            "benchmark",
            "--out-dir",
            str(tmp_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "terminus_training_benchmark_v1"
    assert payload["pass"] is True
