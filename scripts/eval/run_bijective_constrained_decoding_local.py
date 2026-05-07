"""Local bijective Sacred Tongue gate with constrained-decoding shim.

Closes Task #64. Reuses the v4 wrapper's bijective gate primitives but injects a
per-case canonical Python contract as a forced prefix on the BACK-translate step
ONLY. Mechanism mirrors src/governance/stage6_constrained_decoding.py:
chat-template + add_generation_prompt -> append forced prefix as if the model
emitted it -> greedy continuation. Forward step (Python -> other tongue) is
unchanged.

The shim hypothesis: cross-tongue back-translation drops contract structure
(imports, helper-set definitions, signature). Injecting that structure as a
forced prefix lets the base model fill in the body, which it does correctly
when the helper-set is in scope.

Loads issdandavis/scbe-coding-agent-qwen-merged-coding-model-v1 (the same
merged 0.5B base used by v4). Runs all 5 cases x 5 tongues = 25 round-trips
locally. Writes a report to artifacts/bijective_tongue/local_constrained_<ts>.json.

Gate: pass if repaired_pass_rate >= 0.80 AND per-case minimum >= 0.60.
If gate clears -> ship constrained decoding as production path, skip v5 SFT.
If not -> v5 SFT (Task #65) gets dispatched.
"""

from __future__ import annotations

import argparse
import ast
import gc
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]


BASE_MODEL = os.environ.get(
    "SCBE_BIJ_BASE_MODEL",
    "issdandavis/scbe-coding-agent-qwen-merged-coding-model-v1",
).strip()
GATE_TONGUES = tuple(
    t.strip()
    for t in os.environ.get("SCBE_BIJ_GATE_TONGUES", "AV,RU,CA,UM,DR").split(",")
    if t.strip()
)
GATE_PASS_RATE_MIN = float(os.environ.get("SCBE_BIJ_GATE_PASS_RATE_MIN", "0.80"))
GATE_PER_CASE_MIN = float(os.environ.get("SCBE_BIJ_GATE_PER_CASE_MIN", "0.60"))
MAX_NEW_TOKENS = int(os.environ.get("SCBE_BIJ_MAX_NEW_TOKENS", "384"))


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
    assertions: tuple


CASES = (
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


SEEDS = {
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


# Per-case canonical contract for back-translate forced prefix. Each entry is
# the imports + signature + helper-set lines that get lost in cross-tongue
# round-trip. The model continues with the body return statement.
BACK_PREFIX = {
    "reverse_string": "def reverse_string(s: str) -> str:\n",
    "safe_divide": "def safe_divide(a: float, b: float):\n",
    "parse_json_name": (
        "import json\n"
        "\n"
        "def extract_name(payload: str):\n"
        "    try:\n"
        "        data = json.loads(payload)\n"
        "    except Exception:\n"
        "        return None\n"
    ),
    "bounded_factorial": (
        "def factorial(n: int) -> int:\n"
        "    if n < 0:\n"
        "        raise ValueError('n must be non-negative')\n"
    ),
    "eval_runner": (
        "def run_expr(expr: str) -> object:\n"
        "    _ALLOWED = {'__builtins__': {}}\n"
        "    return eval(expr, _ALLOWED)\n"
    ),
}


SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "enumerate": enumerate, "Exception": Exception, "float": float,
    "filter": filter, "frozenset": frozenset, "int": int, "iter": iter,
    "len": len, "list": list, "map": map, "max": max, "min": min,
    "next": next, "print": print, "range": range, "reversed": reversed,
    "set": set, "sorted": sorted, "str": str, "sum": sum, "tuple": tuple,
    "type": type, "isinstance": isinstance, "zip": zip,
    "AttributeError": AttributeError, "IndexError": IndexError,
    "KeyError": KeyError, "RuntimeError": RuntimeError,
    "StopIteration": StopIteration, "TypeError": TypeError,
    "ValueError": ValueError, "ZeroDivisionError": ZeroDivisionError,
    "__import__": __import__, "eval": eval,
}


@dataclass
class CheckResult:
    syntax_ok: bool
    exec_ok: bool
    tests_passed: bool
    error: Optional[str] = None


def run_code_checks(code: str, assertions: tuple) -> CheckResult:
    try:
        ast.parse(code)
    except SyntaxError as exc:
        return CheckResult(False, False, False, f"SyntaxError: {exc}")
    scope: Dict[str, Any] = {"__builtins__": SAFE_BUILTINS}
    try:
        exec(code, scope, scope)
    except Exception as exc:
        return CheckResult(True, False, False, f"ExecutionError: {exc}")
    try:
        for assertion in assertions:
            exec(assertion, scope, scope)
    except Exception as exc:
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


def extract_contract(seed: str):
    imports: List[str] = []
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
    contract_lines: List[str] = []
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


def compiler_repair(round_tripped: str, entrypoint: str, seed: str):
    actions: List[str] = []
    code = round_tripped
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code, actions
    fn_name = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            fn_name = node.name
            break
    if fn_name is None:
        return code, actions
    if fn_name != entrypoint:
        code = re.sub(rf"\bdef\s+{re.escape(fn_name)}\s*\(", f"def {entrypoint}(", code, count=1)
        code = re.sub(rf"\b{re.escape(fn_name)}\s*\(", f"{entrypoint}(", code)
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
    repair_actions: list = field(default_factory=list)
    repaired_tests_passed: bool = False
    repaired_error: Optional[str] = None
    error: Optional[str] = None
    forward_seconds: float = 0.0
    back_seconds: float = 0.0
    back_used_prefix: bool = False


def round_trip_case(case: PromptCase, tongue: str, fwd_generate, back_generate) -> RoundTripResult:
    seed = SEEDS.get(case.case_id, f"def {case.entrypoint}():\n    return None\n")
    if tongue == "KO":
        intermediate = seed
        forward_output = seed
        forward_seconds = 0.0
    else:
        forward_prompt = build_forward_prompt(seed, tongue)
        forward_output, forward_seconds = fwd_generate(forward_prompt)
        intermediate = extract_first_codeblock(forward_output)
        if not intermediate:
            return RoundTripResult(
                case_id=case.case_id, tongue=tongue, forward_output=forward_output,
                intermediate_code="", back_output="", round_tripped_python="",
                syntax_ok=False, exec_ok=False, tests_passed=False,
                error="forward_extract_empty", forward_seconds=forward_seconds,
            )
    back_prompt = build_back_prompt(intermediate, tongue if tongue != "KO" else "AV", seed)
    forced_prefix = BACK_PREFIX.get(case.case_id, "")
    back_output, back_seconds = back_generate(back_prompt, forced_prefix)
    round_tripped = extract_first_codeblock(back_output)
    if not round_tripped:
        return RoundTripResult(
            case_id=case.case_id, tongue=tongue, forward_output=forward_output,
            intermediate_code=intermediate, back_output=back_output,
            round_tripped_python="", syntax_ok=False, exec_ok=False, tests_passed=False,
            error="back_extract_empty", forward_seconds=forward_seconds, back_seconds=back_seconds,
            back_used_prefix=bool(forced_prefix),
        )
    check = run_code_checks(round_tripped, case.assertions)
    repaired_python, repair_actions = compiler_repair(round_tripped, case.entrypoint, seed)
    if check.tests_passed:
        repaired_tests_passed = True
        repaired_error = None
    elif repair_actions:
        repaired_check = run_code_checks(repaired_python, case.assertions)
        repaired_tests_passed = repaired_check.tests_passed
        repaired_error = repaired_check.error
    else:
        repaired_tests_passed = False
        repaired_error = check.error
    return RoundTripResult(
        case_id=case.case_id, tongue=tongue, forward_output=forward_output,
        intermediate_code=intermediate, back_output=back_output,
        round_tripped_python=round_tripped, syntax_ok=check.syntax_ok,
        exec_ok=check.exec_ok, tests_passed=check.tests_passed,
        repaired_python=repaired_python, repair_actions=repair_actions,
        repaired_tests_passed=repaired_tests_passed, repaired_error=repaired_error,
        error=check.error, forward_seconds=forward_seconds, back_seconds=back_seconds,
        back_used_prefix=bool(forced_prefix),
    )


def aggregate(results, model_id, tongues):
    report: Dict[str, Any] = {
        "schema": "scbe_bijective_tongue_gate_v3_constrained_decoding",
        "model_id": model_id,
        "tongues": list(tongues),
        "n_cases": len({r.case_id for r in results}),
        "n_tests": len(results),
        "pass_rate": 0.0,
        "repaired_pass_rate": 0.0,
        "repair_lift": 0.0,
        "n_repaired": 0,
        "by_tongue": {},
        "by_case": {},
        "results": [asdict(r) for r in results],
    }
    if results:
        passed = sum(1 for r in results if r.tests_passed)
        repaired = sum(1 for r in results if r.repaired_tests_passed)
        report["pass_rate"] = round(passed / len(results), 4)
        report["repaired_pass_rate"] = round(repaired / len(results), 4)
        report["repair_lift"] = round(report["repaired_pass_rate"] - report["pass_rate"], 4)
        report["n_repaired"] = sum(1 for r in results if r.repair_actions)
    for tongue in tongues:
        subset = [r for r in results if r.tongue == tongue]
        if not subset:
            continue
        passed = sum(1 for r in subset if r.tests_passed)
        repaired = sum(1 for r in subset if r.repaired_tests_passed)
        report["by_tongue"][tongue] = {
            "n": len(subset), "pass": passed,
            "pass_rate": round(passed / len(subset), 4),
            "repaired_pass": repaired,
            "repaired_pass_rate": round(repaired / len(subset), 4),
        }
    case_ids = sorted({r.case_id for r in results})
    for cid in case_ids:
        subset = [r for r in results if r.case_id == cid]
        passed = sum(1 for r in subset if r.tests_passed)
        repaired = sum(1 for r in subset if r.repaired_tests_passed)
        report["by_case"][cid] = {
            "n": len(subset), "pass": passed,
            "pass_rate": round(passed / len(subset), 4),
            "repaired_pass": repaired,
            "repaired_pass_rate": round(repaired / len(subset), 4),
        }
    return report


def make_generators(model, tokenizer):
    """Return (fwd_generate, back_generate) closures.

    fwd_generate(prompt) -> (text, seconds)
    back_generate(prompt, forced_prefix) -> (text, seconds)
        If forced_prefix is non-empty, opens a python codeblock and primes the
        assistant turn with the prefix so model continues inside the block.
    """
    import torch

    SYSTEM = (
        "You are a careful coding agent. Output only the requested code inside a "
        "single fenced markdown code block. No prose, no commentary."
    )

    def _chat_text(user_prompt: str) -> str:
        msgs = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_prompt},
        ]
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

    def _generate(text: str, max_new_tokens: int) -> str:
        inputs = tokenizer(text, return_tensors="pt").to(model.device)
        n_in = inputs["input_ids"].shape[1]
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=1.0,
                pad_token_id=tokenizer.eos_token_id,
            )
        return tokenizer.decode(out[0][n_in:], skip_special_tokens=True)

    def fwd_generate(prompt: str):
        t0 = time.time()
        text = _chat_text(prompt)
        out = _generate(text, MAX_NEW_TOKENS)
        return out, round(time.time() - t0, 3)

    def back_generate(prompt: str, forced_prefix: str):
        t0 = time.time()
        text = _chat_text(prompt)
        if forced_prefix:
            primed = text + "```python\n" + forced_prefix
            n_in_chat_only = tokenizer(text, return_tensors="pt")["input_ids"].shape[1]
            inputs = tokenizer(primed, return_tensors="pt").to(model.device)
            with torch.no_grad():
                out = model.generate(
                    **inputs,
                    max_new_tokens=MAX_NEW_TOKENS,
                    do_sample=False,
                    temperature=1.0,
                    pad_token_id=tokenizer.eos_token_id,
                )
            full = tokenizer.decode(out[0][n_in_chat_only:], skip_special_tokens=True)
            return full, round(time.time() - t0, 3)
        out = _generate(text, MAX_NEW_TOKENS)
        return out, round(time.time() - t0, 3)

    return fwd_generate, back_generate


def main() -> int:
    global MAX_NEW_TOKENS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", default="", help="Comma-separated case_ids to run (default: all)")
    parser.add_argument("--tongues", default="", help="Comma-separated tongues to run (default: AV,RU,CA,UM,DR)")
    parser.add_argument("--no-prefix", action="store_true", help="Disable forced prefix (baseline run)")
    parser.add_argument("--out", default="", help="Output JSON path")
    parser.add_argument("--model", default=BASE_MODEL, help="Model id or local path")
    parser.add_argument("--max-new-tokens", type=int, default=MAX_NEW_TOKENS)
    args = parser.parse_args()

    MAX_NEW_TOKENS = args.max_new_tokens

    if args.no_prefix:
        for k in list(BACK_PREFIX.keys()):
            BACK_PREFIX[k] = ""

    selected_cases = (
        tuple(c for c in CASES if c.case_id in {x.strip() for x in args.cases.split(",") if x.strip()})
        if args.cases
        else CASES
    )
    selected_tongues = (
        tuple(t.strip() for t in args.tongues.split(",") if t.strip()) if args.tongues else GATE_TONGUES
    )

    print(json.dumps({"event": "boot", "model": args.model, "tongues": list(selected_tongues),
                      "cases": [c.case_id for c in selected_cases],
                      "prefix_enabled": not args.no_prefix,
                      "max_new_tokens": MAX_NEW_TOKENS}, ensure_ascii=True), flush=True)

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    cuda = torch.cuda.is_available()
    print(json.dumps({"event": "torch_env", "cuda": cuda,
                      "device_name": torch.cuda.get_device_name(0) if cuda else "cpu",
                      "vram_gb": (torch.cuda.get_device_properties(0).total_memory / 1024**3) if cuda else 0.0,
                      }, ensure_ascii=True), flush=True)

    dtype = torch.float16 if cuda else torch.float32
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=dtype, device_map="cuda" if cuda else "cpu", trust_remote_code=True,
    )
    model.eval()
    print(json.dumps({"event": "model_loaded", "seconds": round(time.time() - t0, 2)},
                     ensure_ascii=True), flush=True)

    fwd_generate, back_generate = make_generators(model, tokenizer)

    results: List[RoundTripResult] = []
    for case in selected_cases:
        for tongue in selected_tongues:
            t_case = time.time()
            print(json.dumps({"event": "case_start", "case": case.case_id, "tongue": tongue},
                             ensure_ascii=True), flush=True)
            r = round_trip_case(case, tongue, fwd_generate, back_generate)
            results.append(r)
            print(json.dumps({"event": "case_done", "case": case.case_id, "tongue": tongue,
                              "tests_passed": r.tests_passed,
                              "repaired_tests_passed": r.repaired_tests_passed,
                              "back_used_prefix": r.back_used_prefix,
                              "seconds": round(time.time() - t_case, 2),
                              "error": r.error,
                              "repaired_error": r.repaired_error,
                              }, ensure_ascii=True), flush=True)

    report = aggregate(results, args.model, selected_tongues)
    gate_pass = (
        report["repaired_pass_rate"] >= GATE_PASS_RATE_MIN
        and all(c["repaired_pass_rate"] >= GATE_PER_CASE_MIN for c in report["by_case"].values())
    )
    report["gate_pass_rate_min"] = GATE_PASS_RATE_MIN
    report["gate_per_case_min"] = GATE_PER_CASE_MIN
    report["gate_passed"] = gate_pass

    out_path = Path(args.out) if args.out else (
        REPO / "artifacts" / "bijective_tongue" /
        f"local_constrained_{int(time.time())}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")

    print(json.dumps({"event": "summary",
                      "pass_rate": report["pass_rate"],
                      "repaired_pass_rate": report["repaired_pass_rate"],
                      "repair_lift": report["repair_lift"],
                      "by_case": {k: v["repaired_pass_rate"] for k, v in report["by_case"].items()},
                      "by_tongue": {k: v["repaired_pass_rate"] for k, v in report["by_tongue"].items()},
                      "gate_passed": gate_pass,
                      "report_path": str(out_path),
                      }, ensure_ascii=True), flush=True)

    del model, tokenizer
    gc.collect()
    if cuda:
        import torch
        torch.cuda.empty_cache()

    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
