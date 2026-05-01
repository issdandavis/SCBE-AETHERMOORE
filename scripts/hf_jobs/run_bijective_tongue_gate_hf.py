# /// script
# dependencies = [
#   "torch",
#   "transformers>=4.46.0",
#   "huggingface_hub>=0.25.0",
#   "accelerate>=0.34.0",
#   "safetensors",
# ]
# ///
"""HF Jobs runner for the bijective Sacred Tongue round-trip gate.

Mirrors `scripts/benchmark/bijective_tongue_gate.py` but is self-contained
(no repo imports) so it runs as a single PEP 723 UV script on HF Jobs
infrastructure where torch is available.

Per user (2026-04-29), the trained coding model gate requires that a Python
function survive translation into another Sacred Tongue's spirit language and
back. This script runs that gate against a published HF model and prints a
single SCBE_BIJECTIVE_GATE_RESULT JSON line for log scraping.

Env vars:
- SCBE_GATE_MODEL: HF model id (default: merged coding model v1)
- SCBE_GATE_TONGUES: comma-separated tongues (default: AV)
- SCBE_GATE_MAX_NEW_TOKENS: per-generation cap (default: 384)
- HF_TOKEN: required for private repos
"""

from __future__ import annotations

import ast
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional


DEFAULT_MODEL = "issdandavis/scbe-coding-agent-qwen-merged-coding-model-v1"
DEFAULT_TONGUES = ("AV",)

torch: Any = None


TONGUE_TO_LANG = {
    "KO": ("Python", "python"),
    "AV": ("JavaScript", "javascript"),
    "RU": ("Rust", "rust"),
    "CA": ("Mathematica", "mathematica"),
    "UM": ("Haskell", "haskell"),
    "DR": ("Markdown", "markdown"),
}

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


SEEDS: dict[str, str] = {
    "reverse_string": "def reverse_string(s: str) -> str:\n    return s[::-1]\n",
    "safe_divide": (
        "def safe_divide(a: float, b: float):\n"
        "    if b == 0:\n"
        "        return None\n"
        "    return a / b\n"
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
    "iter": iter,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "next": next,
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


def build_forward_prompt(python_source: str, tongue: str) -> str:
    lang_name, _ = TONGUE_TO_LANG[tongue]
    return (
        f"Translate the following Python function into idiomatic {lang_name}. "
        f"Preserve the function's name, parameters, return type, and behavior exactly. "
        f"Output only the {lang_name} code inside a single fenced code block. No prose.\n\n"
        f"```python\n{python_source}\n```\n"
    )


def extract_contract(seed: str) -> tuple[list[str], str]:
    """Extract canonical (imports, signature_line) from a seed snippet.

    The bijective key is the contract — name, signature, imports — not the body.
    Six Tongues Compiler primitive: cross-tongue translation must preserve this
    contract regardless of which intermediate language is used.
    """
    imports: list[str] = []
    signature = ""
    for line in seed.splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            imports.append(stripped)
        elif stripped.startswith("def ") and not signature:
            signature = stripped if stripped.endswith(":") else stripped + ":"
    return imports, signature


def build_back_prompt(other_source: str, tongue: str, seed: str = "") -> str:
    lang_name, _ = TONGUE_TO_LANG[tongue]
    imports, signature = extract_contract(seed)
    contract_lines: list[str] = []
    if signature:
        contract_lines.append(f"  Signature (must match exactly): {signature}")
    if imports:
        joined = "\n".join(f"    {i}" for i in imports)
        contract_lines.append(f"  Required imports (must appear at top of code block):\n{joined}")
    contract_block = (
        "\nThe Python output MUST satisfy this canonical contract:\n"
        + "\n".join(contract_lines)
        + "\n"
        if contract_lines
        else ""
    )
    return (
        f"Translate the following {lang_name} function back into idiomatic Python. "
        f"Preserve the function's name, parameters, return type, and behavior exactly."
        f"{contract_block}"
        f"Output only the Python code inside a single fenced code block. No prose. "
        f"Include all required imports inside the code block.\n\n"
        f"```{lang_name.lower()}\n{other_source}\n```\n"
    )


def compiler_repair(round_tripped: str, entrypoint: str, seed: str) -> tuple[str, list[str]]:
    """Six Tongues Compiler contract-enforcement pass.

    The bijection is a property of (model output + compiler) rather than the raw
    model output alone. The compiler enforces the canonical contract by:
      1. Renaming the (first) top-level function to the canonical entrypoint
         (also rewriting recursive self-calls so factorial-style bodies survive).
      2. Prepending any required imports from the seed contract that are missing.

    Returns (repaired_code, repair_actions). Body and behavior are not modified —
    only the contract surface (name + imports) is canonicalized.
    """
    actions: list[str] = []
    code = round_tripped

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code, actions

    fn_name: Optional[str] = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            fn_name = node.name
            break
    if fn_name is None:
        return code, actions

    if fn_name != entrypoint:
        code = re.sub(
            rf"\bdef\s+{re.escape(fn_name)}\s*\(",
            f"def {entrypoint}(",
            code,
            count=1,
        )
        code = re.sub(
            rf"\b{re.escape(fn_name)}\s*\(",
            f"{entrypoint}(",
            code,
        )
        actions.append(f"rename:{fn_name}->{entrypoint}")

    required_imports, _ = extract_contract(seed)
    for imp in required_imports:
        if imp not in code:
            code = imp + "\n" + code
            actions.append(f"add_import:{imp}")

    return code, actions


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
    repaired_python: str = ""
    repair_actions: list[str] = field(default_factory=list)
    repaired_tests_passed: bool = False
    repaired_error: Optional[str] = None
    error: Optional[str] = None
    forward_seconds: float = 0.0
    back_seconds: float = 0.0


GenerateFn = Callable[[str], tuple[str, float]]


def round_trip_case(case: PromptCase, tongue: str, generate: GenerateFn) -> RoundTripResult:
    seed = SEEDS.get(case.case_id, f"def {case.entrypoint}():\n    return None\n")

    if tongue == "KO":
        intermediate = seed
        forward_output = seed
        forward_seconds = 0.0
    else:
        forward_prompt = build_forward_prompt(seed, tongue)
        forward_output, forward_seconds = generate(forward_prompt)
        intermediate = extract_first_codeblock(forward_output)
        if not intermediate:
            return RoundTripResult(
                case_id=case.case_id,
                tongue=tongue,
                forward_output=forward_output,
                intermediate_code="",
                back_output="",
                round_tripped_python="",
                syntax_ok=False,
                exec_ok=False,
                tests_passed=False,
                error="forward_extract_empty",
                forward_seconds=forward_seconds,
            )

    back_prompt = build_back_prompt(intermediate, tongue if tongue != "KO" else "AV", seed)
    back_output, back_seconds = generate(back_prompt)
    round_tripped = extract_first_codeblock(back_output)
    if not round_tripped:
        return RoundTripResult(
            case_id=case.case_id,
            tongue=tongue,
            forward_output=forward_output,
            intermediate_code=intermediate,
            back_output=back_output,
            round_tripped_python="",
            syntax_ok=False,
            exec_ok=False,
            tests_passed=False,
            error="back_extract_empty",
            forward_seconds=forward_seconds,
            back_seconds=back_seconds,
        )

    check = run_code_checks(round_tripped, case.assertions)

    repaired_python, repair_actions = compiler_repair(round_tripped, case.entrypoint, seed)
    if check.tests_passed:
        repaired_tests_passed = True
        repaired_error: Optional[str] = None
    elif repair_actions:
        repaired_check = run_code_checks(repaired_python, case.assertions)
        repaired_tests_passed = repaired_check.tests_passed
        repaired_error = repaired_check.error
    else:
        repaired_tests_passed = False
        repaired_error = check.error

    return RoundTripResult(
        case_id=case.case_id,
        tongue=tongue,
        forward_output=forward_output,
        intermediate_code=intermediate,
        back_output=back_output,
        round_tripped_python=round_tripped,
        syntax_ok=check.syntax_ok,
        exec_ok=check.exec_ok,
        tests_passed=check.tests_passed,
        repaired_python=repaired_python,
        repair_actions=repair_actions,
        repaired_tests_passed=repaired_tests_passed,
        repaired_error=repaired_error,
        error=check.error,
        forward_seconds=forward_seconds,
        back_seconds=back_seconds,
    )


@dataclass
class GateReport:
    schema: str = "scbe_bijective_tongue_gate_v2_compiler_repair"
    model_id: str = ""
    tongues: list[str] = field(default_factory=list)
    n_cases: int = 0
    n_tests: int = 0
    pass_rate: float = 0.0
    repaired_pass_rate: float = 0.0
    repair_lift: float = 0.0
    n_repaired: int = 0
    by_tongue: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_case: dict[str, dict[str, Any]] = field(default_factory=dict)
    results: list[dict[str, Any]] = field(default_factory=list)


def aggregate(results: list[RoundTripResult], model_id: str, tongues: list[str]) -> GateReport:
    report = GateReport(model_id=model_id, tongues=list(tongues))
    report.n_tests = len(results)
    report.n_cases = len({r.case_id for r in results})
    if results:
        passed = sum(1 for r in results if r.tests_passed)
        repaired = sum(1 for r in results if r.repaired_tests_passed)
        report.pass_rate = round(passed / len(results), 4)
        report.repaired_pass_rate = round(repaired / len(results), 4)
        report.repair_lift = round(report.repaired_pass_rate - report.pass_rate, 4)
        report.n_repaired = sum(1 for r in results if r.repair_actions)
    for tongue in tongues:
        subset = [r for r in results if r.tongue == tongue]
        if not subset:
            continue
        passed = sum(1 for r in subset if r.tests_passed)
        repaired = sum(1 for r in subset if r.repaired_tests_passed)
        report.by_tongue[tongue] = {
            "n": len(subset),
            "pass": passed,
            "pass_rate": round(passed / len(subset), 4),
            "repaired_pass": repaired,
            "repaired_pass_rate": round(repaired / len(subset), 4),
        }
    case_ids = sorted({r.case_id for r in results})
    for cid in case_ids:
        subset = [r for r in results if r.case_id == cid]
        passed = sum(1 for r in subset if r.tests_passed)
        repaired = sum(1 for r in subset if r.repaired_tests_passed)
        report.by_case[cid] = {
            "n": len(subset),
            "pass": passed,
            "pass_rate": round(passed / len(subset), 4),
            "repaired_pass": repaired,
            "repaired_pass_rate": round(repaired / len(subset), 4),
        }
    report.results = [asdict(r) for r in results]
    return report


def _json_event(event: str, **payload: Any) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=True), flush=True)


def main() -> int:
    global torch
    import torch as torch_module
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch = torch_module

    model_id = os.environ.get("SCBE_GATE_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    tongue_csv = os.environ.get("SCBE_GATE_TONGUES", ",".join(DEFAULT_TONGUES))
    tongues = [t.strip() for t in tongue_csv.split(",") if t.strip()]
    bad = [t for t in tongues if t not in TONGUE_TO_LANG]
    if bad:
        _json_event("config_error", bad_tongues=bad, valid=list(TONGUE_TO_LANG.keys()))
        return 2

    max_new_tokens = int(os.environ.get("SCBE_GATE_MAX_NEW_TOKENS", "384"))
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or None

    _json_event("load_start", model_id=model_id, tongues=tongues)
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
            output[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )
        return response, elapsed

    results: list[RoundTripResult] = []
    for case in CASES:
        for tongue in tongues:
            r = round_trip_case(case, tongue, generate)
            results.append(r)
            _json_event(
                "round_trip_result",
                case_id=r.case_id,
                tongue=r.tongue,
                tests_passed=r.tests_passed,
                repaired_tests_passed=r.repaired_tests_passed,
                repair_actions=r.repair_actions,
                syntax_ok=r.syntax_ok,
                exec_ok=r.exec_ok,
                error=r.error,
                repaired_error=r.repaired_error,
                forward_seconds=round(r.forward_seconds, 2),
                back_seconds=round(r.back_seconds, 2),
            )

    report = aggregate(results, model_id=model_id, tongues=tongues)
    summary = {
        "schema": report.schema,
        "model_id": report.model_id,
        "tongues": report.tongues,
        "n_cases": report.n_cases,
        "n_tests": report.n_tests,
        "pass_rate": report.pass_rate,
        "repaired_pass_rate": report.repaired_pass_rate,
        "repair_lift": report.repair_lift,
        "n_repaired": report.n_repaired,
        "by_tongue": report.by_tongue,
        "by_case": report.by_case,
    }
    _json_event("SCBE_BIJECTIVE_GATE_RESULT", **summary)
    print("SCBE_BIJECTIVE_GATE_FULL_REPORT_BEGIN", flush=True)
    print(json.dumps(asdict(report), ensure_ascii=True), flush=True)
    print("SCBE_BIJECTIVE_GATE_FULL_REPORT_END", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
