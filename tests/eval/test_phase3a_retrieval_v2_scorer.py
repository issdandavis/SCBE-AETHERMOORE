"""Regression tests for the Phase 3a-3 retrieval-v2 scorer."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("torch")


def _load_phase3a_3_module():
    path = Path("scripts/eval/hf_job_v8_pre_phase3a_3_retrieval_v2.py")
    spec = importlib.util.spec_from_file_location("phase3a_3_retrieval_v2", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_score_requires_canonical_helper_arity() -> None:
    module = _load_phase3a_3_module()
    response = "def safety(d, p):\n    return xR_compute(d)"

    ok, missing, triggered = module.score(
        response,
        ["xR_compute(", "safety", "return", "d", "p"],
        ["def xR_compute"],
        "xR_compute(d, p)  # 2-arg helper",
    )

    assert not ok
    assert missing == ["canonical_call:xR_compute(d, p)  # 2-arg helper"]
    assert triggered == []


def test_score_accepts_canonical_helper_call() -> None:
    module = _load_phase3a_3_module()
    response = "def safety(d, p):\n    return xR_compute(d, p)"

    ok, missing, triggered = module.score(
        response,
        ["xR_compute(", "safety", "return", "d", "p"],
        ["def xR_compute"],
        "xR_compute(d, p)  # 2-arg helper",
    )

    assert ok
    assert missing == []
    assert triggered == []
