# /// script
# dependencies = [
#   "torch",
#   "transformers>=4.46.0",
#   "huggingface_hub>=0.25.0",
#   "accelerate>=0.34.0",
#   "safetensors",
# ]
# ///
"""HF Jobs runner for the SCBE paired/group-coding gate.

Mirrors `scripts/benchmark/paired_coding_gate.py` but is self-contained
(no repo imports) so it runs as a single PEP 723 UV script on HF Jobs
infrastructure where torch is available.

Per user (2026-04-29), the trained coding model gate requires that the model
"code in pairs with other models for group coding". This script runs that gate:
the Specifier emits a contract skeleton, the Implementer fills the body, the
composed module must satisfy the original assertions.

Env vars:
- SCBE_GATE_MODEL_A: HF model id for the Specifier role (default: merged coding model v1)
- SCBE_GATE_MODEL_B: HF model id for the Implementer role (default: same as A — self-pair)
- SCBE_GATE_MAX_NEW_TOKENS: per-generation cap (default: 512)
- HF_TOKEN: required for private repos
"""

from __future__ import annotations

import ast
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Optional

DEFAULT_MODEL = "issdandavis/scbe-coding-agent-qwen-merged-coding-model-v1"

torch: Any = None


CODEBLOCK_RE = re.compile(r"```(?:[a-zA-Z0-9_+-]*)\n(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class PromptCase:
    case_id: str
    prompt: str
    entrypoint: str
    assertions: tuple[str, ...]


CASES: tuple[PromptCase, ...] = (
    PromptCase(
        case_id="reverse_string",
        prompt="Write a Python function reverse_string(s: str) -> str that returns the reversed string.",
        entrypoint="reverse_string",
        assertions=(
            "assert reverse_string('abc') == 'cba'",
            "assert reverse_string('') == ''",
        ),
    ),
    PromptCase(
        case_id="safe_divide",
        prompt="Write a Python function safe_divide(a: float, b: float) -> float | None that returns None when division by zero occurs.",
        entrypoint="safe_divide",
        assertions=(
            "assert safe_divide(6, 3) == 2",
            "assert safe_divide(1, 0) is None",
        ),
    ),
    PromptCase(
        case_id="parse_json_name",
        prompt="Write a Python function extract_name(payload: str) -> str | None that parses a JSON string and safely returns the field 'name', or None if missing/invalid.",
        entrypoint="extract_name",
        assertions=(
            "assert extract_name('{\"name\": \"Issac\"}') == 'Issac'",
            "assert extract_name('{\"other\": 1}') is None",
            "assert extract_name('not-json') is None",
        ),
    ),
    PromptCase(
        case_id="bounded_factorial",
        prompt="Write a Python function factorial(n: int) -> int that computes factorial recursively for n >= 0 and raises ValueError for negative inputs.",
        entrypoint="factorial",
        assertions=(
            "assert factorial(0) == 1",
            "assert factorial(5) == 120",
            "try:\n    factorial(-1)\n    raise AssertionError('expected ValueError')\nexcept ValueError:\n    pass",
        ),
    ),
    PromptCase(
        case_id="eval_runner",
        prompt="Write a Python function run_expr(expr: str) -> object that evaluates an arbitrary Python expression using eval and returns the result.",
        entrypoint="run_expr",
        assertions=(
            "assert run_expr('1 + 1') == 2",
            "assert run_expr('\"hello\"') == 'hello'",
        ),
    ),
)


# Widened SAFE_BUILTINS — bijective + paired gates both hit false-positives from
# missing names in earlier runs. Now includes:
#   - standard exception classes (KeyError/TypeError/IndexError/AttributeError/RuntimeError/StopIteration)
#     so `try/except KeyError` patterns don't NameError inside the sandbox
#   - common iterators (reversed, zip, map, filter)
#   - container helpers (set, frozenset)
SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "Exception": Exception,
    "float": float,
    "filter": filter,
    "frozenset": frozenset,
    "int": int,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "reversed": reversed,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "isinstance": isinstance,
    "zip": zip,
    "AttributeError": AttributeError,
    "IndexError": IndexError,
    "KeyError": KeyError,
    "RuntimeError": RuntimeError,
    "StopIteration": StopIteration,
    "TypeError": TypeError,
    "ValueError": ValueError,
    "ZeroDivisionError": ZeroDivisionError,
    "__import__": __import__,
    "eval": eval,
}


@dataclass
class CheckResult:
    syntax_ok: bool
    exec_ok: bool
    tests_passed: bool
    error: Optional[str] = None


def run_code_checks(code: str, assertions: tuple[str, ...]) -> CheckResult:
    try:
        ast.parse(code)
    except SyntaxError as exc:
        return CheckResult(False, False, False, f"SyntaxError: {exc}")

    scope: dict[str, Any] = {"__builtins__": SAFE_BUILTINS}
    try:
        exec(code, scope, scope)
    except Exception as exc:  # noqa: BLE001
        return CheckResult(True, False, False, f"ExecutionError: {exc}")

    try:
        for assertion in assertions:
            exec(assertion, scope, scope)
    except Exception as exc:  # noqa: BLE001
        return CheckResult(True, True, False, f"AssertionError: {exc}")

    return CheckResult(True, True, True, None)


def extract_first_codeblock(text: str) -> str:
    m = CODEBLOCK_RE.search(text or "")
    if m:
        return m.group(1).strip("\n")
    return (text or "").strip()


def build_specifier_prompt(case: PromptCase) -> str:
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
    return (
        "You are the Implementer in a paired-coding session. The Specifier has produced "
        "the skeleton below. Replace the `pass` body with a correct implementation. "
        "Preserve the function signature, type hints, and any imports. "
        "Output the COMPLETE implemented module inside a single fenced ```python block. "
        "No prose.\n\n"
        f"TASK: {case.prompt}\n\n"
        f"SPECIFIER SKELETON:\n```python\n{spec_code}\n```\n"
    )


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
    spec_seconds: float = 0.0
    impl_seconds: float = 0.0


GenerateFn = Callable[[str], tuple[str, float]]


def run_pair_case(
    case: PromptCase,
    specifier: GenerateFn,
    implementer: GenerateFn,
) -> PairedResult:
    spec_output, spec_seconds = specifier(build_specifier_prompt(case))
    spec_code = extract_first_codeblock(spec_output)
    if not spec_code:
        return PairedResult(
            case_id=case.case_id,
            spec_output=spec_output,
            spec_code="",
            impl_output="",
            impl_code="",
            syntax_ok=False,
            exec_ok=False,
            tests_passed=False,
            error="spec_extract_empty",
            spec_seconds=spec_seconds,
        )

    impl_output, impl_seconds = implementer(build_implementer_prompt(case, spec_code))
    impl_code = extract_first_codeblock(impl_output)
    if not impl_code:
        return PairedResult(
            case_id=case.case_id,
            spec_output=spec_output,
            spec_code=spec_code,
            impl_output=impl_output,
            impl_code="",
            syntax_ok=False,
            exec_ok=False,
            tests_passed=False,
            error="impl_extract_empty",
            spec_seconds=spec_seconds,
            impl_seconds=impl_seconds,
        )

    check = run_code_checks(impl_code, case.assertions)
    return PairedResult(
        case_id=case.case_id,
        spec_output=spec_output,
        spec_code=spec_code,
        impl_output=impl_output,
        impl_code=impl_code,
        syntax_ok=check.syntax_ok,
        exec_ok=check.exec_ok,
        tests_passed=check.tests_passed,
        error=check.error,
        spec_seconds=spec_seconds,
        impl_seconds=impl_seconds,
    )


@dataclass
class GateReport:
    schema: str = "scbe_paired_coding_gate_v1"
    model_a: str = ""
    model_b: str = ""
    n_cases: int = 0
    pass_rate: float = 0.0
    by_case: dict[str, dict[str, Any]] = field(default_factory=dict)
    results: list[dict[str, Any]] = field(default_factory=list)


def aggregate(results: list[PairedResult], model_a: str, model_b: str) -> GateReport:
    report = GateReport(model_a=model_a, model_b=model_b)
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


def _json_event(event: str, **payload: Any) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=True), flush=True)


def _load_model(model_id: str, token: Optional[str]):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    started = time.time()
    tokenizer = AutoTokenizer.from_pretrained(model_id, token=token, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        token=token,
        torch_dtype=dtype,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
    )
    model.eval()
    _json_event(
        "load_complete",
        model_id=model_id,
        seconds=round(time.time() - started, 2),
        cuda=torch.cuda.is_available(),
        dtype=str(dtype),
    )
    return tokenizer, model


def _make_generate(tokenizer, model, max_new_tokens: int) -> GenerateFn:
    def generate(prompt: str) -> tuple[str, float]:
        messages = [{"role": "user", "content": prompt}]
        rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(rendered, return_tensors="pt").to(model.device)
        t0 = time.time()
        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        elapsed = time.time() - t0
        response = tokenizer.decode(
            output[0][inputs["input_ids"].shape[1] :],
            skip_special_tokens=True,
        )
        return response, elapsed

    return generate


def main() -> int:
    global torch
    import torch as torch_module

    torch = torch_module

    model_a = os.environ.get("SCBE_GATE_MODEL_A", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    model_b_env = os.environ.get("SCBE_GATE_MODEL_B", "").strip()
    model_b = model_b_env or model_a
    max_new_tokens = int(os.environ.get("SCBE_GATE_MAX_NEW_TOKENS", "512"))
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or None

    _json_event("load_start", model_a=model_a, model_b=model_b)
    tok_a, mdl_a = _load_model(model_a, token)
    specifier = _make_generate(tok_a, mdl_a, max_new_tokens)
    if model_b == model_a:
        implementer = specifier
    else:
        tok_b, mdl_b = _load_model(model_b, token)
        implementer = _make_generate(tok_b, mdl_b, max_new_tokens)

    results: list[PairedResult] = []
    for case in CASES:
        r = run_pair_case(case, specifier, implementer)
        results.append(r)
        _json_event(
            "pair_result",
            case_id=r.case_id,
            tests_passed=r.tests_passed,
            syntax_ok=r.syntax_ok,
            exec_ok=r.exec_ok,
            error=r.error,
            spec_seconds=round(r.spec_seconds, 2),
            impl_seconds=round(r.impl_seconds, 2),
        )

    report = aggregate(results, model_a=model_a, model_b=model_b)
    summary = {
        "schema": report.schema,
        "model_a": report.model_a,
        "model_b": report.model_b,
        "n_cases": report.n_cases,
        "pass_rate": report.pass_rate,
        "by_case": report.by_case,
    }
    _json_event("SCBE_PAIRED_GATE_RESULT", **summary)
    print("SCBE_PAIRED_GATE_FULL_REPORT_BEGIN", flush=True)
    print(json.dumps(asdict(report), ensure_ascii=True), flush=True)
    print("SCBE_PAIRED_GATE_FULL_REPORT_END", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
