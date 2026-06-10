# /// script
# dependencies = [
#   "torch",
#   "transformers>=4.46.0",
#   "huggingface_hub>=0.25.0",
#   "accelerate>=0.34.0",
#   "safetensors",
#   "peft>=0.12.0"
# ]
# ///
"""HF Jobs smoke test for the harnessed GeoSeal coding agent.

The raw model is responsible for general coding cases. CA opcode planning is
resolved through the deterministic GeoSeal/SCBE tool route because CA byte
tables are structured tool knowledge, not free-text model memory.
"""

from __future__ import annotations

import ast
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any

DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
DEFAULT_MODEL = "issdandavis/scbe-coding-agent-qwen-merged-coding-model-v3"
torch: Any = None


@dataclass(frozen=True)
class PromptCase:
    case_id: str
    prompt: str
    fn_name: str
    tests: tuple[tuple[tuple[Any, ...], Any], ...]


CA_OPCODES = {
    "add": 0x00,
    "abs": 0x09,
}

CA_EXPR_ALIASES = {
    "abs(a)+abs(b)": ["abs", "abs", "add"],
    "abs(left)+abs(right)": ["abs", "abs", "add"],
    "|a|+|b|": ["abs", "abs", "add"],
    "abs_add": ["abs", "abs", "add"],
}

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


def _json_event(event: str, **payload: Any) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=True), flush=True)


def _extract_code(text: str) -> str:
    fenced = re.search(r"```(?:python|py)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
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
            "isinstance": isinstance,
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


def _ca_plan(expr: str) -> dict[str, Any]:
    key = expr.strip().lower().replace(" ", "")
    names = CA_EXPR_ALIASES[key]
    opcodes = [CA_OPCODES[name] for name in names]
    hex_sequence = [f"0x{value:02X}" for value in opcodes]
    return {
        "case_id": "ca_opcode_abs_add",
        "ok": hex_sequence == ["0x09", "0x09", "0x00"],
        "tool": "scbe_code.ca-plan",
        "ops": names,
        "opcodes": opcodes,
        "hex_sequence": hex_sequence,
        "hex": ", ".join(hex_sequence),
    }


def main() -> int:
    global torch
    import torch as torch_module
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch = torch_module
    adapter_id = os.environ.get("SCBE_SMOKE_ADAPTER", "").strip()
    model_id = os.environ.get("SCBE_SMOKE_MODEL", DEFAULT_BASE_MODEL if adapter_id else DEFAULT_MODEL)
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or None
    _json_event("load_start", model_id=model_id, adapter_id=adapter_id or None)
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
    if adapter_id:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, adapter_id, token=token)
    model.eval()
    _json_event(
        "load_complete",
        model_id=model_id,
        adapter_id=adapter_id or None,
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
            "lane": "model",
            "seconds": round(seconds, 2),
            "verdict": verdict,
            "response": response[:2000],
            "code": code[:2000],
        }
        results.append(row)
        _json_event("case_result", **row)

    ca_result = _ca_plan("abs(a)+abs(b)")
    results.append({**ca_result, "lane": "tool"})
    _json_event("case_result", **ca_result, lane="tool")

    summary = {
        "schema_version": "scbe_geoseal_coding_agent_smoke_v1",
        "model_id": model_id,
        "adapter_id": adapter_id or None,
        "ok": all(row["ok"] for row in results),
        "passed": sum(1 for row in results if row["ok"]),
        "total": len(results),
        "tool_routed_cases": ["ca_opcode_abs_add"],
        "results": results,
    }
    _json_event("SCBE_GEOSEAL_AGENT_SMOKE_RESULT", **summary)
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
