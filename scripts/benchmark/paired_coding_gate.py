"""Paired/group-coding gate for the SCBE coding model.

Real gate per user 2026-04-29: a "trained model" must be able to code
"in pairs with other models for group coding" — so this harness drives a
two-role collaborative loop (Specifier + Implementer) and verifies the
composed artifact still passes the original assertions.

Roles:
    A (Specifier)   — Given the natural-language prompt, produces a Python
                      function signature, docstring, and embedded test
                      assertions (the contract).
    B (Implementer) — Given A's spec contract, fills in the function body.

The harness then concatenates B's body into A's signature and runs the
fixture's `assertions` against the composed module.

Reuses `tests/fixtures/code_eval_prompts.json` and the safe-exec sandbox in
`scripts/benchmark/scbe_code_eval.py` so the source-truth tasks stay aligned
with the bijective gate.

Usage:

    # Stub run (offline, fast — used by pytest)
    python scripts/benchmark/paired_coding_gate.py --stub --dry-run

    # Single-model self-pair (model plays both roles)
    python scripts/benchmark/paired_coding_gate.py \\
        --model-a issdandavis/scbe-coding-agent-qwen-merged-coding-model-v1 \\
        --output artifacts/benchmarks/paired_coding_gate/self_pair.json

    # Two distinct models
    python scripts/benchmark/paired_coding_gate.py \\
        --model-a issdandavis/scbe-coding-agent-qwen-merged-coding-model-v1 \\
        --model-b Qwen/Qwen2.5-Coder-0.5B-Instruct \\
        --output artifacts/benchmarks/paired_coding_gate/cross_pair.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_eval_module():
    name = "scbe_code_eval"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / "benchmark" / "scbe_code_eval.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_EVAL = _load_eval_module()
load_prompt_cases = _EVAL.load_prompt_cases
run_code_checks = _EVAL.run_code_checks
PromptCase = _EVAL.PromptCase

CODEBLOCK_RE = re.compile(r"```(?:[a-zA-Z0-9_+-]*)\n(.*?)```", re.DOTALL)


def extract_first_codeblock(text: str) -> str:
    m = CODEBLOCK_RE.search(text or "")
    if m:
        return m.group(1).strip("\n")
    return (text or "").strip()


def build_specifier_prompt(case: PromptCase) -> str:
    """A's role: produce a Python signature + docstring + embedded test calls.

    The contract A returns becomes the spec B must implement against.
    """
    return (
        "You are the Specifier in a paired-coding session. Given the task below, "
        "output ONLY a Python skeleton consisting of:\n"
        "  - the import lines you expect the implementer to need,\n"
        "  - the function signature with type hints,\n"
        "  - a triple-quoted docstring describing inputs/outputs/edge cases,\n"
        "  - a `pass` placeholder body.\n"
        "Do NOT implement the function. Output a single fenced ```python block.\n\n"
        f"TASK: {case.prompt}\n"
        f"REQUIRED FUNCTION NAME: {case.entrypoint}\n"
    )


def build_implementer_prompt(case: PromptCase, spec_code: str) -> str:
    """B's role: replace the `pass` body with a real implementation."""
    return (
        "You are the Implementer in a paired-coding session. The Specifier has produced "
        "the skeleton below. Replace the `pass` body with a correct implementation. "
        "Preserve the function signature, type hints, and any imports. "
        "Output the COMPLETE implemented module inside a single fenced ```python block. "
        "No prose.\n\n"
        f"TASK: {case.prompt}\n\n"
        f"SPECIFIER SKELETON:\n```python\n{spec_code}\n```\n"
    )


def _has_pass_only_body(code: str) -> bool:
    """Heuristic: spec is acceptable if any function body is just `pass`."""
    return bool(re.search(r"def\s+\w+\s*\([^)]*\)\s*(?:->\s*[^:]+)?:\s*(?:\"\"\".*?\"\"\"\s*)?pass\b", code, re.DOTALL))


@dataclass
class PairedResult:
    case_id: str
    spec_output: str
    spec_code: str
    impl_output: str
    impl_code: str
    syntax_ok: bool
    exec_ok: bool
    tests_passed: bool
    error: Optional[str] = None


@dataclass
class PairedReport:
    schema: str = "scbe_paired_coding_gate_v1"
    model_a: str = ""
    model_b: str = ""
    n_cases: int = 0
    pass_rate: float = 0.0
    by_case: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    results: List[Dict[str, Any]] = field(default_factory=list)


GenerateFn = Callable[[str], str]


def run_pair_case(
    case: PromptCase,
    specifier: GenerateFn,
    implementer: GenerateFn,
) -> PairedResult:
    spec_output = specifier(build_specifier_prompt(case))
    spec_code = extract_first_codeblock(spec_output)
    if not spec_code:
        return PairedResult(
            case_id=case.id,
            spec_output=spec_output,
            spec_code="",
            impl_output="",
            impl_code="",
            syntax_ok=False,
            exec_ok=False,
            tests_passed=False,
            error="spec_extract_empty",
        )

    impl_output = implementer(build_implementer_prompt(case, spec_code))
    impl_code = extract_first_codeblock(impl_output)
    if not impl_code:
        return PairedResult(
            case_id=case.id,
            spec_output=spec_output,
            spec_code=spec_code,
            impl_output=impl_output,
            impl_code="",
            syntax_ok=False,
            exec_ok=False,
            tests_passed=False,
            error="impl_extract_empty",
        )

    check = run_code_checks(impl_code, case.assertions)
    return PairedResult(
        case_id=case.id,
        spec_output=spec_output,
        spec_code=spec_code,
        impl_output=impl_output,
        impl_code=impl_code,
        syntax_ok=check.syntax_ok,
        exec_ok=check.exec_ok,
        tests_passed=check.tests_passed,
        error=check.error,
    )


def aggregate(results: List[PairedResult], model_a: str, model_b: str) -> PairedReport:
    report = PairedReport(model_a=model_a, model_b=model_b)
    report.n_cases = len(results)
    if results:
        passed = sum(1 for r in results if r.tests_passed)
        report.pass_rate = round(passed / len(results), 4)
    for r in results:
        report.by_case[r.case_id] = {
            "tests_passed": r.tests_passed,
            "syntax_ok": r.syntax_ok,
            "exec_ok": r.exec_ok,
            "error": r.error,
        }
    report.results = [asdict(r) for r in results]
    return report


_SEED_BODIES: Dict[str, str] = {
    "reverse_string": "    return s[::-1]\n",
    "safe_divide": "    if b == 0:\n        return None\n    return a / b\n",
    "parse_json_name": (
        "    try:\n"
        "        data = json.loads(payload)\n"
        "    except Exception:\n"
        "        return None\n"
        "    return data.get('name')\n"
    ),
    "bounded_factorial": (
        "    if n < 0:\n"
        "        raise ValueError('n must be non-negative')\n"
        "    if n == 0:\n"
        "        return 1\n"
        "    return n * factorial(n - 1)\n"
    ),
    "eval_runner": ("    _ALLOWED = {'__builtins__': {}}\n" "    return eval(expr, _ALLOWED)\n"),
}


_SEED_SPECS: Dict[str, str] = {
    "reverse_string": ("def reverse_string(s: str) -> str:\n" '    """Return s reversed."""\n' "    pass\n"),
    "safe_divide": (
        "def safe_divide(a: float, b: float):\n" '    """Return a/b, or None if b is zero."""\n' "    pass\n"
    ),
    "parse_json_name": (
        "import json\n"
        "def extract_name(payload: str):\n"
        '    """Parse JSON and return the \'name\' field, else None."""\n'
        "    pass\n"
    ),
    "bounded_factorial": (
        "def factorial(n: int) -> int:\n" '    """Return n!, raise ValueError for negative n."""\n' "    pass\n"
    ),
    "eval_runner": (
        "def run_expr(expr: str) -> object:\n"
        '    """Evaluate expr in a sandboxed scope and return the result."""\n'
        "    pass\n"
    ),
}


class StubSpecifier:
    """Offline specifier: emits a known-good skeleton for fixture cases."""

    def generate(self, prompt: str) -> str:
        for cid, spec in _SEED_SPECS.items():
            marker = f"REQUIRED FUNCTION NAME: {_entry_for(cid)}"
            if marker in prompt:
                return f"```python\n{spec}\n```\n"
        return "```python\ndef placeholder():\n    pass\n```\n"


class StubImplementer:
    """Offline implementer: replaces `pass` with a known-good body."""

    def __init__(self, perfect: bool = True) -> None:
        self.perfect = perfect

    def generate(self, prompt: str) -> str:
        if not self.perfect:
            return "```python\ndef broken():\n    return None\n```\n"
        for cid, body in _SEED_BODIES.items():
            spec = _SEED_SPECS[cid]
            if spec.strip() in prompt:
                composed = spec.replace("    pass\n", body)
                return f"```python\n{composed}\n```\n"
        return "```python\ndef placeholder():\n    return None\n```\n"


def _entry_for(case_id: str) -> str:
    return {
        "reverse_string": "reverse_string",
        "safe_divide": "safe_divide",
        "parse_json_name": "extract_name",
        "bounded_factorial": "factorial",
        "eval_runner": "run_expr",
    }[case_id]


def _hf_adapter(model_id: str) -> GenerateFn:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch

    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.float32)
    model.eval()

    def generate(prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        templated = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tok(templated, return_tensors="pt")
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=False,
                pad_token_id=tok.eos_token_id,
            )
        new_tokens = out[0, inputs["input_ids"].shape[1] :]
        return tok.decode(new_tokens, skip_special_tokens=True)

    return generate


def run_gate(
    cases: List[PromptCase],
    specifier: GenerateFn,
    implementer: GenerateFn,
    model_a: str,
    model_b: str,
) -> PairedReport:
    results = [run_pair_case(c, specifier, implementer) for c in cases]
    return aggregate(results, model_a=model_a, model_b=model_b)


def main() -> int:
    parser = argparse.ArgumentParser(description="Paired/group-coding gate")
    parser.add_argument(
        "--prompts",
        default="tests/fixtures/code_eval_prompts.json",
        help="Path to prompt fixture JSON",
    )
    parser.add_argument("--model-a", default="", help="HF model id for the Specifier role")
    parser.add_argument(
        "--model-b",
        default="",
        help="HF model id for the Implementer role (defaults to model-a if omitted)",
    )
    parser.add_argument("--stub", action="store_true", help="Use offline stub adapters")
    parser.add_argument(
        "--output",
        default="artifacts/benchmarks/paired_coding_gate/result.json",
        help="Path to write JSON report",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print summary, skip file write")
    args = parser.parse_args()

    if not args.stub and not args.model_a:
        print("error: must pass either --stub or --model-a <hf_id>", file=sys.stderr)
        return 2

    cases = load_prompt_cases(args.prompts)
    if args.stub:
        specifier = StubSpecifier().generate
        implementer = StubImplementer(perfect=True).generate
        model_a, model_b = "stub_specifier", "stub_implementer"
    else:
        model_a = args.model_a
        model_b = args.model_b or args.model_a
        specifier = _hf_adapter(model_a)
        implementer = _hf_adapter(model_b) if model_b != model_a else specifier

    report = run_gate(cases, specifier, implementer, model_a=model_a, model_b=model_b)

    summary = {
        "schema": report.schema,
        "model_a": report.model_a,
        "model_b": report.model_b,
        "n_cases": report.n_cases,
        "pass_rate": report.pass_rate,
        "by_case": report.by_case,
    }
    print(json.dumps(summary, indent=2))

    if not args.dry_run:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
        print(f"\nWrote full report to {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
