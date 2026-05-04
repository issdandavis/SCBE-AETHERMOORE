from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOOP_PATH = ROOT / "scripts" / "system" / "hydra_challenge_loop.py"
EVAL_PATH = ROOT / "scripts" / "system" / "hydra_challenge_eval.py"
RELOOP_PATH = ROOT / "scripts" / "system" / "hydra_challenge_reloop.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_eval_report_turns_pass_into_complete_factor() -> None:
    module = _load(EVAL_PATH, "hydra_challenge_eval")
    report = {
        "ok": True,
        "challenge": {"challenge_id": "repo_ladder_validate"},
        "attempts": [
            {
                "result": {"ok": True, "elapsed_sec": 0.2},
                "classification": {"class": "none"},
                "parsed_stdout": {"ok": True},
            }
        ],
    }

    payload = module.evaluate_report(report)

    assert payload["completion_factor"] == 1.0
    assert payload["residual"] == 0.0
    assert payload["next_mode"] == "compact_and_archive"


def test_eval_report_keeps_residual_for_failure() -> None:
    module = _load(EVAL_PATH, "hydra_challenge_eval")
    report = {
        "ok": False,
        "challenge": {"challenge_id": "repo_ladder_level1"},
        "attempts": [
            {
                "result": {"ok": False, "elapsed_sec": 1.0},
                "classification": {"class": "manifest_or_schema"},
                "parsed_stdout": {"ok": False},
            }
        ],
    }

    payload = module.evaluate_report(report)

    assert 0.0 < payload["completion_factor"] < 1.0
    assert payload["residual"] > 0.0
    assert payload["next_mode"] == "reloop_with_compacted_state"


def test_reloop_plan_uses_temp_branch_not_real_git_branch(tmp_path: Path) -> None:
    module = _load(RELOOP_PATH, "hydra_challenge_reloop")
    eval_path = tmp_path / "eval.json"
    eval_path.write_text(
        json.dumps(
            {
                "eval_hash": "abcdef123456",
                "source_challenge": {"challenge_id": "repo_ladder_validate"},
                "completion_factor": 1.0,
                "residual": 0.0,
                "step_completion": {"verify": 1.0},
            }
        ),
        encoding="utf-8",
    )

    result = module.build_reloop_plan(eval_path=eval_path, output_root=tmp_path / "loops")

    assert result["plan"]["uses_real_git_branch"] is False
    assert result["plan"]["next_challenge"] == "repo_ladder_level1"
    assert Path(result["plan"]["temp_dir"]).exists()
    assert result["compact"]["completion_factor"] == 1.0


def test_loop_runs_challenge_eval_and_reloop(tmp_path: Path) -> None:
    module = _load(LOOP_PATH, "hydra_challenge_loop")

    report = module.run_challenge_loop(challenge_id="repo_ladder_validate", output_root=tmp_path, max_attempts=1)

    assert report["ok"] is True
    assert report["pipeline"]["completion_factor"] == 1.0
    assert report["pipeline"]["next_challenge"] == "repo_ladder_level1"
    assert Path(report["pipeline"]["eval_artifact"]).exists()
    assert Path(report["pipeline"]["reloop_temp_dir"]).exists()


def test_loop_runs_continuous_rounds_with_quorum(tmp_path: Path) -> None:
    module = _load(LOOP_PATH, "hydra_challenge_loop")

    report = module.run_challenge_loop(
        challenge_id="repo_ladder_validate",
        output_root=tmp_path,
        rounds=2,
        attempts_per_round=2,
        continue_after_pass=True,
    )

    assert report["ok"] is True
    assert report["round_count"] == 2
    assert report["time_packets_per_round"] == 2
    assert report["attempt_count"] == 4
    assert len(report["round_summaries"]) == 2
    assert report["improvement_quorum"]["leader_vote_is_decisive"] is True
    assert report["improvement_quorum"]["votes"]["leader_context_vote"] is True
    assert "continuous rounds" in report["improvement_quorum"]["agreed_test_additions"][0]


def test_eval_cli_writes_artifact(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "ok": True,
                "challenge": {"challenge_id": "cli_eval"},
                "attempts": [{"result": {"ok": True, "elapsed_sec": 0.1}, "parsed_stdout": {}}],
            }
        ),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/system/hydra_challenge_eval.py",
            "--report",
            str(report_path),
            "--output-root",
            str(tmp_path / "eval"),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["completion_factor"] == 1.0
    assert Path(payload["artifact_path"]).exists()
