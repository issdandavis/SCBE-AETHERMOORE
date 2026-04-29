from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_benchmark_exits_nonzero_when_below_min_pass_rate(tmp_path: Path):
    candidate_file = tmp_path / "candidates.json"
    candidate_file.write_text(
        json.dumps(
            [
                {
                    "name": "always_bad",
                    "tasks": {
                        "score_add": "function evaluate(input, state) { return 0; }",
                        "heal_clamp": "function evaluate(input, state) { return 0; }",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/eval/functional_coding_agent_benchmark.py",
            "--candidate-file",
            str(candidate_file),
            "--task-limit",
            "2",
            "--min-pass-rate",
            "1.0",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 1
    assert "below threshold" in proc.stderr
