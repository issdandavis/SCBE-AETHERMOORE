"""Regression tests for the bijective constrained-decoding failure catalog."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_runner():
    path = Path("scripts/eval/run_bijective_constrained_decoding_local.py")
    spec = importlib.util.spec_from_file_location("bijective_constrained_runner", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_eval_runner_prefix_includes_safe_return_line() -> None:
    runner = _load_runner()

    prefix = runner.BACK_PREFIX["eval_runner"]

    assert "_ALLOWED = {'__builtins__': {}}" in prefix
    assert "return eval(expr, _ALLOWED)" in prefix


def test_eval_runner_canonical_prefix_passes_local_assertions() -> None:
    runner = _load_runner()
    case = next(c for c in runner.CASES if c.case_id == "eval_runner")

    result = runner.run_code_checks(runner.BACK_PREFIX["eval_runner"], case.assertions)

    assert result.syntax_ok
    assert result.exec_ok
    assert result.tests_passed
    assert result.error is None
