from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_swe_local_benchmark_dry_run_command_shape() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/benchmark/swe_local_benchmark.py", "--dry-run"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    cmd = payload["command"]
    assert "scripts/eval/functional_coding_agent_benchmark.py" in cmd
    assert "--replace-default-tasks" in cmd
    assert "--candidate-file" in cmd
    assert "--task-file" in cmd


def test_swe_verified_readiness_reports_without_secrets() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/benchmark/swe_verified_readiness.py"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=90,
    )
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "scbe_swe_bench_verified_readiness_v1"
    assert payload["claim_boundary"] == "readiness_only_no_official_score"
    assert "probes" in payload
    assert "sk-" not in proc.stdout
