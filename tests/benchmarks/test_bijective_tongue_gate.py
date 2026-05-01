"""Lock in the bijective Sacred Tongue round-trip gate harness.

Guards the executable promotion gate the user defined 2026-04-29:
a "trained" coding model must round-trip code through another Sacred Tongue
and have the result still pass the original assertions.

These tests use the stub adapter, so they're CPU-only and fast. The gate
itself is exercised against real models via `scripts/benchmark/bijective_tongue_gate.py`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = REPO_ROOT / "scripts" / "benchmark" / "bijective_tongue_gate.py"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "code_eval_prompts.json"


def _load_gate_module():
    import sys

    name = "bijective_tongue_gate"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, GATE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gate():
    return _load_gate_module()


def test_tongue_map_covers_all_six(gate):
    assert set(gate.TONGUE_TO_LANG.keys()) == {"KO", "AV", "RU", "CA", "UM", "DR"}


def test_codeblock_extractor_pulls_first_block(gate):
    text = "preamble\n```python\nprint(1)\n```\nmore\n```js\nx=2\n```"
    assert gate.extract_first_codeblock(text) == "print(1)"


def test_codeblock_extractor_falls_back_to_raw(gate):
    text = "no fences here"
    assert gate.extract_first_codeblock(text) == "no fences here"


def test_forward_prompt_names_target_language(gate):
    p = gate.build_forward_prompt("def f(): pass\n", "AV")
    assert "JavaScript" in p
    assert "```python" in p


def test_back_prompt_names_target_language(gate):
    p = gate.build_back_prompt("function f(){}", "AV")
    assert "JavaScript" in p
    assert "```javascript" in p


def test_perfect_stub_passes_all_cases(gate):
    cases = gate.load_prompt_cases(str(FIXTURE_PATH))
    stub = gate.StubBackEcho(perfect_back=True)
    report = gate.run_gate(cases, tongues=["AV"], generate=stub.generate, model_id="stub")
    assert report.n_cases == len(cases)
    assert report.n_tests == len(cases)
    assert report.pass_rate == pytest.approx(1.0)
    assert report.by_tongue["AV"]["pass_rate"] == pytest.approx(1.0)


def test_broken_stub_fails_all_cases(gate):
    cases = gate.load_prompt_cases(str(FIXTURE_PATH))
    stub = gate.StubBackEcho(perfect_back=False)
    report = gate.run_gate(cases, tongues=["AV"], generate=stub.generate, model_id="stub_broken")
    assert report.pass_rate == pytest.approx(0.0)


def test_aggregation_handles_mixed_tongues(gate):
    cases = gate.load_prompt_cases(str(FIXTURE_PATH))
    stub = gate.StubBackEcho(perfect_back=True)
    report = gate.run_gate(cases, tongues=["AV", "RU"], generate=stub.generate, model_id="stub")
    assert report.n_tests == len(cases) * 2
    assert set(report.by_tongue.keys()) == {"AV", "RU"}
    for _cid, stats in report.by_case.items():
        assert stats["n"] == 2


def test_seed_python_is_correct_for_reverse_string(gate):
    cases = gate.load_prompt_cases(str(FIXTURE_PATH))
    case = next(c for c in cases if c.id == "reverse_string")
    seed = gate._python_seed_for_case(case)
    scope = {}
    exec(seed, scope)
    assert scope["reverse_string"]("abc") == "cba"


def test_schema_constant(gate):
    report = gate.GateReport()
    assert report.schema == "scbe_bijective_tongue_gate_v1"
