# /// script
# dependencies = [
#   "torch",
#   "transformers>=4.46.0",
#   "huggingface_hub>=0.25.0",
#   "accelerate>=0.34.0",
#   "safetensors"
# ]
# ///
"""HF Jobs smoke test for the merged SCBE coding model.

This is intentionally small and executable: generate code for canonical tasks,
run that code against deterministic checks, then probe CA opcode recall.
"""

from __future__ import annotations

import ast
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


DEFAULT_MODEL = "issdandavis/scbe-coding-agent-qwen-merged-coding-model-v1"


@dataclass(frozen=True)
class PromptCase:
    case_id: str
    prompt: str
    fn_name: str
    tests: tuple[tuple[tuple[Any, ...], Any], ...]


CASES: tuple[PromptCase, ...] = (
    PromptCase(
        case_id="fib_iterative",
        prompt=(
            "Return only Python code in one fenced code block. "
            "Write a Python function fib(n: int) -> int that returns the nth Fibonacci number. "
            "Use iteration."
        ),
        fn_name="fib",
        tests=(((0,), 0), ((1,), 1), ((2,), 1), ((10,), 55), ((20,), 6765)),
    ),
    PromptCase(
        case_id="is_prime",
        prompt=(
            "Return only Python code in one fenced code block. "
            "Write a Python function is_prime(n: int) -> bool that returns True if n is prime."
        ),
        fn_name="is_prime",
        tests=(((0,), False), ((1,), False), ((2,), True), ((17,), True), ((21,), False)),
    ),
    PromptCase(
        case_id="depth2_json_keys",
        prompt=(
            "Return only Python code in one fenced code block. "
            "Write a Python function depth2_keys(obj: dict) -> list[str] that returns sorted keys "
            "found exactly at depth 2 in nested dictionaries. Top-level keys are depth 1."
        ),
        fn_name="depth2_keys",
        tests=(
            (({"a": {"x": 1, "y": {"z": 2}}, "b": 3, "c": {"m": 4}},), ["m", "x", "y"]),
            (({},), []),
        ),
    ),
)

STISA_PROMPT = (
    "In the SCBE CA opcode table, generate a CA opcode sequence for abs(a) + abs(b). "
    "Return the relevant hex opcodes and operation names only."
)


def _json_event(event: str, **payload: Any) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=True), flush=True)


def _extract_code(text: str) -> str:
    fenced = re.search(r"```(?:python)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    start = text.find("def ")
    if start >= 0:
        return text[start:].strip()
    return text.strip()


def _compile_and_run(code: str, fn_name: str, tests: tuple[tuple[tuple[Any, ...], Any], ...]) -> dict[str, Any]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {"ok": False, "error": f"syntax_error: {exc}"}

    if not any(isinstance(node, ast.FunctionDef) and node.name == fn_name for node in tree.body):
        return {"ok": False, "error": f"missing_function: {fn_name}"}

    namespace: dict[str, Any] = {
        "__builtins__": {
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "int": int,
            "len": len,
            "list": list,
            "max": max,
            "min": min,
            "range": range,
            "sorted": sorted,
            "str": str,
            "sum": sum,
        }
    }
    try:
        exec(compile(tree, "<generated>", "exec"), namespace, namespace)
        fn = namespace[fn_name]
        failures: list[dict[str, Any]] = []
        for args, expected in tests:
            actual = fn(*args)
            if actual != expected:
                failures.append({"args": args, "expected": expected, "actual": actual})
        return {"ok": not failures, "failures": failures}
    except Exception as exc:  # noqa: BLE001 - generated code is the target under test
        return {"ok": False, "error": f"runtime_error: {type(exc).__name__}: {exc}"}


def _generate(model: Any, tokenizer: Any, prompt: str, max_new_tokens: int) -> tuple[str, float]:
    messages = [{"role": "user", "content": prompt}]
    rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(rendered, return_tensors="pt").to(model.device)
    started = time.time()
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    elapsed = time.time() - started
    response = tokenizer.decode(output[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)
    return response, elapsed


def main() -> int:
    model_id = os.environ.get("SCBE_SMOKE_MODEL", DEFAULT_MODEL)
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or None
    _json_event("load_start", model_id=model_id)
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

    results: list[dict[str, Any]] = []
    for case in CASES:
        response, seconds = _generate(model, tokenizer, case.prompt, max_new_tokens=220)
        code = _extract_code(response)
        verdict = _compile_and_run(code, case.fn_name, case.tests)
        row = {
            "case_id": case.case_id,
            "ok": bool(verdict.get("ok")),
            "seconds": round(seconds, 2),
            "verdict": verdict,
            "response": response[:2000],
            "code": code[:2000],
        }
        results.append(row)
        _json_event("case_result", **row)

    stisa_response, stisa_seconds = _generate(model, tokenizer, STISA_PROMPT, max_new_tokens=120)
    normalized = stisa_response.lower()
    stisa_checks = {
        "mentions_ca": "ca" in normalized or "cassisivadan" in normalized,
        "mentions_abs": "abs" in normalized,
        "mentions_add": "add" in normalized,
        "mentions_abs_hex": "0x09" in normalized or "09" in normalized,
        "mentions_add_hex": "0x00" in normalized or "00" in normalized,
    }
    stisa_ok = all(stisa_checks.values())
    stisa = {
        "case_id": "ca_opcode_abs_add",
        "ok": stisa_ok,
        "seconds": round(stisa_seconds, 2),
        "checks": stisa_checks,
        "response": stisa_response[:2000],
    }
    _json_event("case_result", **stisa)

    all_rows = [*results, stisa]
    summary = {
        "schema_version": "scbe_merged_coding_model_smoke_v1",
        "model_id": model_id,
        "ok": all(row["ok"] for row in all_rows),
        "passed": sum(1 for row in all_rows if row["ok"]),
        "total": len(all_rows),
        "results": all_rows,
    }
    _json_event("SCBE_SMOKE_RESULT", **summary)
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
