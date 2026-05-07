"""Tests for dispatch_executable_holdout_inference_hf_job (plan-only).

Dispatch is gated to live HF Jobs and not exercised here. We verify:
- packet shape contains all 10 problems and 10 holdout prompts
- generated job script is valid Python
- adapter_repo and base_model are threaded through
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "eval" / "dispatch_executable_holdout_inference_hf_job.py"


@pytest.fixture(scope="module")
def dispatcher():
    spec = importlib.util.spec_from_file_location("dispatch_executable_holdout_inference_hf_job", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_packet_shape(dispatcher, tmp_path):
    packet = dispatcher.build_packet(
        adapter_repo="issdandavis/example-adapter",
        base_model="Qwen/Qwen2.5-Coder-7B-Instruct",
        holdout_path=dispatcher.DEFAULT_HOLDOUT_JSONL,
        artifact_root=tmp_path,
        flavor="l4x1",
        timeout="30m",
        result_dataset="issdandavis/scbe-eval-results",
        max_new_tokens=192,
        eval_id="example",
    )
    assert packet["schema_version"] == "scbe_executable_holdout_inference_packet_v1"
    assert packet["adapter_repo"] == "issdandavis/example-adapter"
    assert packet["base_model"] == "Qwen/Qwen2.5-Coder-7B-Instruct"
    assert packet["execution"] == {"flavor": "l4x1", "timeout": "30m"}
    assert len(packet["holdout"]) == 10
    assert len(packet["problems"]) == 10
    holdout_pids = {row["problem_id"] for row in packet["holdout"]}
    problem_pids = {p["id"] for p in packet["problems"]}
    assert holdout_pids == problem_pids


def test_generated_script_is_valid_python(dispatcher, tmp_path):
    packet = dispatcher.build_packet(
        adapter_repo="",
        base_model="Qwen/Qwen2.5-Coder-7B-Instruct",
        holdout_path=dispatcher.DEFAULT_HOLDOUT_JSONL,
        artifact_root=tmp_path,
        flavor="l4x1",
        timeout="30m",
        result_dataset="issdandavis/scbe-eval-results",
        max_new_tokens=192,
        eval_id="base-only",
    )
    script_text = Path(packet["script_path"]).read_text(encoding="utf-8")
    ast.parse(script_text)
    assert "def run_problem" in script_text
    assert "===EXECUTABLE_HOLDOUT_REPORT===" in script_text
    assert "max_new_tokens" in script_text


def test_total_tests_matches_46(dispatcher, tmp_path):
    packet = dispatcher.build_packet(
        adapter_repo="x/y",
        base_model="b/m",
        holdout_path=dispatcher.DEFAULT_HOLDOUT_JSONL,
        artifact_root=tmp_path,
        flavor="l4x1",
        timeout="30m",
        result_dataset="ds/r",
        max_new_tokens=64,
        eval_id="t",
    )
    total = sum(len(p["tests"]) for p in packet["problems"])
    assert total == 46
