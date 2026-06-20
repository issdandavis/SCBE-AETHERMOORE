"""Bijective Sacred Tongue round-trip gate for the SCBE coding model.

Real gate per user 2026-04-29: a "trained model" must be able to take a Python
function, translate it into another Sacred Tongue's spirit language (AV=JS,
RU=Rust, ...), translate it back into Python, and have the round-tripped
Python pass the original test assertions.

This script is the executable, reusable runner for that gate. It intentionally
reuses `tests/fixtures/code_eval_prompts.json` and the safe-exec sandbox from
`scripts/benchmark/scbe_code_eval.py` so the source-truth tasks and assertion
semantics stay aligned.

Usage:

    # Stub model (offline, fast, used by pytest)
    python scripts/benchmark/bijective_tongue_gate.py --stub --tongues AV --dry-run

    # Real model (HF transformers, slow on CPU)
    python scripts/benchmark/bijective_tongue_gate.py \\
        --model issdandavis/scbe-coding-agent-qwen-merged-coding-model-v1 \\
        --tongues AV RU \\
        --output artifacts/benchmarks/bijective_tongue_gate/coding_model_v1.json
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

TONGUE_TO_LANG = {
    "KO": ("Python", "python"),
    "AV": ("JavaScript", "javascript"),
    "RU": ("Rust", "rust"),
    "CA": ("Mathematica", "mathematica"),
    "UM": ("Haskell", "haskell"),
    "DR": ("Markdown", "markdown"),
}

CODEBLOCK_RE = re.compile(r"```(?:[a-zA-Z0-9_+-]*)\n(.*?)```", re.DOTALL)


def extract_first_codeblock(text: str) -> str:
    m = CODEBLOCK_RE.search(text or "")
    if m:
        return m.group(1).strip("\n")
    return (text or "").strip()


def build_forward_prompt(python_source: str, tongue: str) -> str:
    lang_name, _ = TONGUE_TO_LANG[tongue]
    return (
        f"Translate the following Python function into idiomatic {lang_name}. "
        "Preserve the function's name, parameters, return type, and behavior exactly. "
        f"Output only the {lang_name} code inside a single fenced code block. No prose.\n\n"
        f"```python\n{python_source}\n```\n"
    )


def build_back_prompt(other_source: str, tongue: str) -> str:
    lang_name, _ = TONGUE_TO_LANG[tongue]
    return (
        f"Translate the following {lang_name} function back into idiomatic Python. "
        "Preserve the function's name, parameters, return type, and behavior exactly. "
        "Output only the Python code inside a single fenced code block. No prose.\n\n"
        f"```{lang_name.lower()}\n{other_source}\n```\n"
    )


@dataclass
class RoundTripResult:
    case_id: str
    tongue: str
    forward_output: str
    intermediate_code: str
    back_output: str
    round_tripped_python: str
    syntax_ok: bool
    exec_ok: bool
    tests_passed: bool
    error: Optional[str] = None


@dataclass
class GateReport:
    schema: str = "scbe_bijective_tongue_gate_v1"
    model_id: str = ""
    tongues: List[str] = field(default_factory=list)
    n_cases: int = 0
    n_tests: int = 0
    pass_rate: float = 0.0
    by_tongue: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_case: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    results: List[Dict[str, Any]] = field(default_factory=list)


GenerateFn = Callable[[str], str]


def round_trip_case(case: PromptCase, tongue: str, generate: GenerateFn) -> RoundTripResult:
    """Single round-trip: python -> tongue -> python -> assertions."""
    if tongue == "KO":
        intermediate = case.prompt
        forward_output = case.prompt
    else:
        forward_prompt = build_forward_prompt(_python_seed_for_case(case), tongue)
        forward_output = generate(forward_prompt)
        intermediate = extract_first_codeblock(forward_output)
        if not intermediate:
            return RoundTripResult(
                case_id=case.id,
                tongue=tongue,
                forward_output=forward_output,
                intermediate_code="",
                back_output="",
                round_tripped_python="",
                syntax_ok=False,
                exec_ok=False,
                tests_passed=False,
                error="forward_extract_empty",
            )

    back_prompt = build_back_prompt(intermediate, tongue if tongue != "KO" else "AV")
    back_output = generate(back_prompt)
    round_tripped = extract_first_codeblock(back_output)
    if not round_tripped:
        return RoundTripResult(
            case_id=case.id,
            tongue=tongue,
            forward_output=forward_output,
            intermediate_code=intermediate,
            back_output=back_output,
            round_tripped_python="",
            syntax_ok=False,
            exec_ok=False,
            tests_passed=False,
            error="back_extract_empty",
        )

    check = run_code_checks(round_tripped, case.assertions)
    return RoundTripResult(
        case_id=case.id,
        tongue=tongue,
        forward_output=forward_output,
        intermediate_code=intermediate,
        back_output=back_output,
        round_tripped_python=round_tripped,
        syntax_ok=check.syntax_ok,
        exec_ok=check.exec_ok,
        tests_passed=check.tests_passed,
        error=check.error,
    )


def _python_seed_for_case(case: PromptCase) -> str:
    """Seed Python source the model is asked to translate.

    Prefer a known-good reference body so the gate isolates *translation* skill,
    not generation skill. Falls back to a name-only stub if no seed is mapped.
    """
    seeds = {
        "reverse_string": "def reverse_string(s: str) -> str:\n    return s[::-1]\n",
        "safe_divide": (
            "def safe_divide(a: float, b: float):\n" "    if b == 0:\n" "        return None\n" "    return a / b\n"
        ),
        "parse_json_name": (
            "import json\n"
            "def extract_name(payload: str):\n"
            "    try:\n"
            "        data = json.loads(payload)\n"
            "    except Exception:\n"
            "        return None\n"
            "    return data.get('name')\n"
        ),
        "bounded_factorial": (
            "def factorial(n: int) -> int:\n"
            "    if n < 0:\n"
            "        raise ValueError('n must be non-negative')\n"
            "    if n == 0:\n"
            "        return 1\n"
            "    return n * factorial(n - 1)\n"
        ),
        "eval_runner": (
            "def run_expr(expr: str) -> object:\n"
            "    _ALLOWED = {'__builtins__': {}}\n"
            "    return eval(expr, _ALLOWED)\n"
        ),
    }
    return seeds.get(case.id, f"def {case.entrypoint}():\n    return None\n")


def aggregate(results: List[RoundTripResult], model_id: str, tongues: List[str]) -> GateReport:
    report = GateReport(model_id=model_id, tongues=list(tongues))
    report.n_tests = len(results)
    report.n_cases = len({r.case_id for r in results})
    if results:
        passed = sum(1 for r in results if r.tests_passed)
        report.pass_rate = round(passed / len(results), 4)
    for tongue in tongues:
        subset = [r for r in results if r.tongue == tongue]
        if not subset:
            continue
        passed = sum(1 for r in subset if r.tests_passed)
        report.by_tongue[tongue] = {
            "n": len(subset),
            "pass": passed,
            "pass_rate": round(passed / len(subset), 4),
        }
    case_ids = sorted({r.case_id for r in results})
    for cid in case_ids:
        subset = [r for r in results if r.case_id == cid]
        passed = sum(1 for r in subset if r.tests_passed)
        report.by_case[cid] = {
            "n": len(subset),
            "pass": passed,
            "pass_rate": round(passed / len(subset), 4),
        }
    report.results = [asdict(r) for r in results]
    return report


class StubBackEcho:
    """Offline stub that simulates a perfect (or broken) translator.

    perfect_back=True: forward step pipes the seed Python through the JS block
    unchanged so the back step can echo it back as Python and the assertions
    pass — exercises the harness happy path without transformers.

    perfect_back=False: back step returns a stub `def broken(): return None`,
    which fails every assertion — exercises the harness failure path.
    """

    def __init__(self, perfect_back: bool = True) -> None:
        self.perfect_back = perfect_back

    def generate(self, prompt: str) -> str:
        if "back into idiomatic Python" in prompt:
            inner = CODEBLOCK_RE.search(prompt)
            if not self.perfect_back or not inner:
                return "```python\ndef broken():\n    return None\n```\n"
            return f"```python\n{inner.group(1)}\n```\n"
        inner = CODEBLOCK_RE.search(prompt)
        seed = inner.group(1) if inner else ""
        if self.perfect_back and seed:
            return f"```javascript\n{seed}\n```\n"
        return "```javascript\n// stub forward translation\nfunction noop(){}\n```\n"


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
    tongues: List[str],
    generate: GenerateFn,
    model_id: str,
) -> GateReport:
    results: List[RoundTripResult] = []
    for case in cases:
        for tongue in tongues:
            results.append(round_trip_case(case, tongue, generate))
    return aggregate(results, model_id=model_id, tongues=tongues)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bijective Sacred Tongue round-trip gate")
    parser.add_argument(
        "--prompts",
        default="tests/fixtures/code_eval_prompts.json",
        help="Path to prompt fixture JSON",
    )
    parser.add_argument(
        "--tongues",
        nargs="+",
        default=["AV"],
        choices=sorted(TONGUE_TO_LANG.keys()),
        help="Sacred Tongues to round-trip through",
    )
    parser.add_argument("--model", default="", help="HF model id to load (omit if using --stub)")
    parser.add_argument("--stub", action="store_true", help="Use offline echo stub")
    parser.add_argument(
        "--output",
        default="artifacts/benchmarks/bijective_tongue_gate/result.json",
        help="Path to write JSON report",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print summary, skip file write")
    args = parser.parse_args()

    if not args.stub and not args.model:
        print("error: must pass either --stub or --model <hf_id>", file=sys.stderr)
        return 2

    cases = load_prompt_cases(args.prompts)
    model_id = "stub" if args.stub else args.model
    generate = StubBackEcho().generate if args.stub else _hf_adapter(args.model)

    report = run_gate(cases, args.tongues, generate, model_id=model_id)

    summary = {
        "schema": report.schema,
        "model_id": report.model_id,
        "tongues": report.tongues,
        "n_cases": report.n_cases,
        "n_tests": report.n_tests,
        "pass_rate": report.pass_rate,
        "by_tongue": report.by_tongue,
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
