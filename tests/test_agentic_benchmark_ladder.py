from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_ladder_module():
    path = REPO_ROOT / "scripts" / "benchmark" / "agentic_benchmark_ladder.py"
    name = "_agentic_benchmark_ladder_test_mod"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_parse_max_level() -> None:
    m = _load_ladder_module()
    assert m._parse_max_level("") == 1
    assert m._parse_max_level("0") == 0
    assert m._parse_max_level("3") == 3
    assert m._parse_max_level("6") == 6
    assert m._parse_max_level("max_level=2") == 2
    assert m._parse_max_level('{"max_level": 4}') == 4
    assert m._parse_max_level('{"max_level": 6}') == 6


def test_level6_cli_block_skipped_when_max_below_6() -> None:
    m = _load_ladder_module()
    block = m.run_level6_cli_readiness(5)
    assert block.get("skipped") is True
    assert block.get("subtasks") == []


def test_level6_cli_block_not_skipped_at_6() -> None:
    m = _load_ladder_module()
    block = m.run_level6_cli_readiness(6)
    assert block.get("skipped") is not True
    assert len(block.get("subtasks") or []) == 1


def test_secret_leak_count_heuristic() -> None:
    m = _load_ladder_module()
    assert m._secret_leak_count("no secrets here") == 0
    assert m._secret_leak_count("token sk-live-abcdefghijklmnopqrstuvwxyz1234567890abcd") >= 1


def test_agentic_ladder_validate_subcommand() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/benchmark/agentic_benchmark_ladder.py", "validate"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload.get("ok") is True


def test_agentic_ladder_list_subcommand() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/benchmark/agentic_benchmark_ladder.py", "list"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert len(payload.get("tasks", [])) >= 1
