"""Lock in the paired/group-coding gate harness.

Guards the third leg of the user's executable promotion gate (2026-04-29):
a "trained" coding model must be able to code in pairs with other models —
Specifier emits a contract skeleton, Implementer fills the body, the
composed module must satisfy the original assertions.

These tests use stub adapters (CPU-only, fast). The real gate runs against
HF models via `scripts/benchmark/paired_coding_gate.py`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = REPO_ROOT / "scripts" / "benchmark" / "paired_coding_gate.py"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "code_eval_prompts.json"


def _load_gate_module():
    import sys

    name = "paired_coding_gate"
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


def test_codeblock_extractor_pulls_first_block(gate):
    text = "preamble\n```python\nprint(1)\n```\nmore\n```js\nx=2\n```"
    assert gate.extract_first_codeblock(text) == "print(1)"


def test_codeblock_extractor_falls_back_to_raw(gate):
    text = "no fences here"
    assert gate.extract_first_codeblock(text) == "no fences here"


def test_specifier_prompt_includes_function_name(gate):
    cases = gate.load_prompt_cases(str(FIXTURE_PATH))
    case = next(c for c in cases if c.id == "reverse_string")
    p = gate.build_specifier_prompt(case)
    assert "Specifier" in p
    assert f"REQUIRED FUNCTION NAME: {case.entrypoint}" in p
    assert "```python" in p


def test_implementer_prompt_embeds_spec_skeleton(gate):
    cases = gate.load_prompt_cases(str(FIXTURE_PATH))
    case = next(c for c in cases if c.id == "safe_divide")
    spec_code = "def safe_divide(a: float, b: float):\n    pass\n"
    p = gate.build_implementer_prompt(case, spec_code)
    assert "Implementer" in p
    assert spec_code in p
    assert case.prompt in p


def test_perfect_stub_pair_passes_all_cases(gate):
    cases = gate.load_prompt_cases(str(FIXTURE_PATH))
    spec = gate.StubSpecifier().generate
    impl = gate.StubImplementer(perfect=True).generate
    report = gate.run_gate(cases, specifier=spec, implementer=impl, model_a="stub_a", model_b="stub_b")
    assert report.n_cases == len(cases)
    assert report.pass_rate == pytest.approx(1.0)
    for cid, stats in report.by_case.items():
        assert stats["tests_passed"] is True, f"{cid} failed: {stats}"


def test_broken_implementer_fails_all_cases(gate):
    cases = gate.load_prompt_cases(str(FIXTURE_PATH))
    spec = gate.StubSpecifier().generate
    impl = gate.StubImplementer(perfect=False).generate
    report = gate.run_gate(cases, specifier=spec, implementer=impl, model_a="stub_a", model_b="stub_broken")
    assert report.pass_rate == pytest.approx(0.0)


def test_aggregation_records_each_case(gate):
    cases = gate.load_prompt_cases(str(FIXTURE_PATH))
    spec = gate.StubSpecifier().generate
    impl = gate.StubImplementer(perfect=True).generate
    report = gate.run_gate(cases, specifier=spec, implementer=impl, model_a="stub_a", model_b="stub_b")
    assert set(report.by_case.keys()) == {c.id for c in cases}
    assert len(report.results) == len(cases)


def test_seed_spec_skeleton_has_pass_body(gate):
    for cid, spec in gate._SEED_SPECS.items():
        assert "pass" in spec, f"seed spec for {cid} missing pass placeholder"
        assert gate._has_pass_only_body(spec), f"seed spec for {cid} has no pass-only function body"


def test_self_pair_uses_single_adapter(gate):
    cases = gate.load_prompt_cases(str(FIXTURE_PATH))
    calls: list[str] = []

    def specifier(prompt: str) -> str:
        calls.append("S")
        return gate.StubSpecifier().generate(prompt)

    report = gate.run_gate(
        cases,
        specifier=specifier,
        implementer=specifier,
        model_a="self",
        model_b="self",
    )
    assert report.model_a == report.model_b == "self"
    assert len(calls) == 2 * len(cases)


def test_schema_constant(gate):
    report = gate.PairedReport()
    assert report.schema == "scbe_paired_coding_gate_v1"
