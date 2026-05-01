# /// script
# dependencies = [
#   "accelerate>=0.34.0",
#   "datasets>=2.20.0",
#   "peft>=0.12.0",
#   "torch",
#   "transformers>=4.46.0",
#   "huggingface_hub>=0.25.0",
#   "safetensors",
# ]
# ///
"""HF Jobs: v4 body-fidelity LoRA SFT + inline bijective Sacred Tongue gate.

End-to-end: load v4 SFT JSONL from issdandavis/scbe-coding-agent-sft,
train LoRA on the merged-coding-model-v1 base, then run the same bijective
round-trip gate as run_bijective_tongue_gate_hf.py (5 cases x 5 tongues).
Push adapter to HF only if repaired_pass_rate >= 0.80 AND no per-case below 0.60.
"""

from __future__ import annotations

import ast
import gc
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


BASE_MODEL = os.environ.get(
    "SCBE_V4_BASE_MODEL",
    "issdandavis/scbe-coding-agent-qwen-merged-coding-model-v1",
).strip()
ADAPTER_REPO = os.environ.get(
    "SCBE_V4_ADAPTER_REPO",
    "issdandavis/scbe-bijective-tongue-coder-v4-body-fidelity",
).strip()
DATASET_REPO = os.environ.get(
    "SCBE_V4_DATASET_REPO",
    "issdandavis/scbe-coding-agent-sft",
).strip()
DATASET_FILENAME = os.environ.get(
    "SCBE_V4_DATASET_FILENAME",
    "bijective_v4_body_fidelity.sft.jsonl",
).strip()
GATE_TONGUES = tuple(
    t.strip()
    for t in os.environ.get("SCBE_V4_GATE_TONGUES", "AV,RU,CA,UM,DR").split(",")
    if t.strip()
)
GATE_PASS_RATE_MIN = float(os.environ.get("SCBE_V4_GATE_PASS_RATE_MIN", "0.80"))
GATE_PER_CASE_MIN = float(os.environ.get("SCBE_V4_GATE_PER_CASE_MIN", "0.60"))
MAX_NEW_TOKENS = int(os.environ.get("SCBE_V4_MAX_NEW_TOKENS", "384"))
WORKDIR = Path("/tmp/scbe-bijective-v4")
WORKDIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")


def _json_event(event: str, **payload: Any) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=True), flush=True)


def _token() -> str:
    token = os.environ.get("HF_TOKEN", "").strip() or os.environ.get(
        "HUGGING_FACE_HUB_TOKEN", ""
    ).strip()
    if not token:
        raise RuntimeError("Missing HF_TOKEN secret")
    os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", token)
    return token


# === Bijective gate primitives (mirror run_bijective_tongue_gate_hf.py) ===

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


GenerateFn = Callable[[str], tuple]


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
                case_id=case.case_id, tongue=tongue, forward_output=forward_output,
                intermediate_code="", back_output="", round_tripped_python="",
                syntax_ok=False, exec_ok=False, tests_passed=False,
                error="forward_extract_empty", forward_seconds=forward_seconds,
            )
    back_prompt = build_back_prompt(intermediate, tongue if tongue != "KO" else "AV", seed)
    back_output, back_seconds = generate(back_prompt)
    round_tripped = extract_first_codeblock(back_output)
    if not round_tripped:
        return RoundTripResult(
            case_id=case.case_id, tongue=tongue, forward_output=forward_output,
            intermediate_code=intermediate, back_output=back_output,
            round_tripped_python="", syntax_ok=False, exec_ok=False, tests_passed=False,
            error="back_extract_empty", forward_seconds=forward_seconds, back_seconds=back_seconds,
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
    )


@dataclass
class GateReport:
    schema: str = "scbe_bijective_tongue_gate_v2_compiler_repair"
    model_id: str = ""
    tongues: list = field(default_factory=list)
    n_cases: int = 0
    n_tests: int = 0
    pass_rate: float = 0.0
    repaired_pass_rate: float = 0.0
    repair_lift: float = 0.0
    n_repaired: int = 0
    by_tongue: dict = field(default_factory=dict)
    by_case: dict = field(default_factory=dict)
    results: list = field(default_factory=list)


def aggregate(results, model_id, tongues):
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
        report.by_case[cid] = {
            "n": len(subset), "pass": passed,
            "pass_rate": round(passed / len(subset), 4),
            "repaired_pass": repaired,
            "repaired_pass_rate": round(repaired / len(subset), 4),
        }
    report.results = [asdict(r) for r in results]
    return report


# === Training + gate driver ===

def main() -> int:
    import torch
    from datasets import Dataset
    from huggingface_hub import hf_hub_download, whoami
    from peft import LoraConfig, PeftModel, get_peft_model
    from transformers import (
        AutoModelForCausalLM, AutoTokenizer,
        DataCollatorForLanguageModeling, Trainer, TrainingArguments,
    )

    token = _token()
    _json_event("auth", whoami=whoami(token=token).get("name", "unknown"),
                base_model=BASE_MODEL, adapter_repo=ADAPTER_REPO,
                dataset_repo=DATASET_REPO, dataset_filename=DATASET_FILENAME)

    # === 1) Load v4 SFT dataset ===
    local_path = hf_hub_download(
        repo_id=DATASET_REPO, filename=DATASET_FILENAME,
        repo_type="dataset", token=token,
        local_dir=str(WORKDIR / "hub-data"),
    )
    raw_rows: List[dict] = []
    with open(local_path, "r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                raw_rows.append(json.loads(stripped))
    _json_event("dataset_loaded", n_rows=len(raw_rows), local_path=local_path)

    # === 2) Tokenizer + base model ===
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, token=token, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
    train_dtype = dtype if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, token=token, torch_dtype=train_dtype,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
    )
    model.config.use_cache = False
    model = get_peft_model(
        model,
        LoraConfig(
            r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
            task_type="CAUSAL_LM",
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        ),
    )
    model.print_trainable_parameters()

    # === 3) Render messages -> chat template text ===
    def to_text(row):
        msgs = row.get("messages") or []
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
    texts = [to_text(r) for r in raw_rows]
    train_ds = Dataset.from_dict({"text": texts})

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=1024)
    train_tok = train_ds.map(tokenize, batched=True, remove_columns=["text"])
    _json_event("tokenize_complete", n_train=len(train_tok))

    # === 4) Train ===
    out_dir = WORKDIR / "adapter"
    args = TrainingArguments(
        output_dir=str(WORKDIR / "checkpoints"),
        num_train_epochs=3.0,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        warmup_ratio=0.05,
        logging_steps=5,
        save_strategy="no",
        fp16=torch.cuda.is_available() and dtype == torch.float16,
        bf16=torch.cuda.is_available() and dtype == torch.bfloat16,
        report_to=[],
        remove_unused_columns=False,
        seed=42,
    )
    trainer = Trainer(
        model=model, args=args, train_dataset=train_tok,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )
    train_stats = trainer.train()
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    _json_event("training_complete",
                global_step=int(getattr(train_stats, "global_step", 0)),
                training_loss=float(getattr(train_stats, "training_loss", 0.0)))

    # === 5) Free training state, reload for gate ===
    del trainer, model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    gate_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    gate_base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, token=token, torch_dtype=gate_dtype,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
    )
    gate_model = PeftModel.from_pretrained(gate_base, str(out_dir))
    gate_model.eval()
    gate_model.config.use_cache = True

    def generate(prompt: str):
        messages = [{"role": "user", "content": prompt}]
        rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(rendered, return_tensors="pt").to(gate_model.device)
        t0 = time.time()
        with torch.no_grad():
            output = gate_model.generate(
                **inputs, max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False, pad_token_id=tokenizer.eos_token_id,
            )
        elapsed = time.time() - t0
        response = tokenizer.decode(
            output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True,
        )
        return response, elapsed

    # === 6) Run bijective gate ===
    _json_event("gate_start", tongues=list(GATE_TONGUES), n_cases=len(CASES))
    results: List[RoundTripResult] = []
    for case in CASES:
        for tongue in GATE_TONGUES:
            r = round_trip_case(case, tongue, generate)
            results.append(r)
            _json_event(
                "round_trip_result",
                case_id=r.case_id, tongue=r.tongue,
                tests_passed=r.tests_passed,
                repaired_tests_passed=r.repaired_tests_passed,
                repair_actions=r.repair_actions,
                syntax_ok=r.syntax_ok, exec_ok=r.exec_ok,
                error=r.error, repaired_error=r.repaired_error,
                forward_seconds=round(r.forward_seconds, 2),
                back_seconds=round(r.back_seconds, 2),
            )

    report = aggregate(results, model_id=ADAPTER_REPO, tongues=list(GATE_TONGUES))
    summary = {
        "schema": report.schema, "model_id": report.model_id,
        "tongues": report.tongues, "n_cases": report.n_cases,
        "n_tests": report.n_tests, "pass_rate": report.pass_rate,
        "repaired_pass_rate": report.repaired_pass_rate,
        "repair_lift": report.repair_lift, "n_repaired": report.n_repaired,
        "by_tongue": report.by_tongue, "by_case": report.by_case,
    }
    _json_event("SCBE_BIJECTIVE_GATE_RESULT", **summary)
    print("SCBE_BIJECTIVE_GATE_FULL_REPORT_BEGIN", flush=True)
    print(json.dumps(asdict(report), ensure_ascii=True), flush=True)
    print("SCBE_BIJECTIVE_GATE_FULL_REPORT_END", flush=True)

    # === 7) Promotion gate ===
    per_case_min = min(
        (entry["repaired_pass_rate"] for entry in report.by_case.values()),
        default=0.0,
    )
    overall_pass = (
        report.repaired_pass_rate >= GATE_PASS_RATE_MIN
        and per_case_min >= GATE_PER_CASE_MIN
    )
    _json_event(
        "gate_decision",
        repaired_pass_rate=report.repaired_pass_rate,
        threshold=GATE_PASS_RATE_MIN,
        per_case_min=per_case_min,
        per_case_threshold=GATE_PER_CASE_MIN,
        overall_pass=overall_pass,
    )

    if overall_pass:
        _json_event("push_attempt", adapter_repo=ADAPTER_REPO)
        gate_model.push_to_hub(ADAPTER_REPO, token=token)
        tokenizer.push_to_hub(ADAPTER_REPO, token=token)
        _json_event("push_complete", adapter_repo=ADAPTER_REPO)
    else:
        _json_event(
            "push_skipped", reason="gate_failed",
            repaired_pass_rate=report.repaired_pass_rate,
            per_case_min=per_case_min,
        )

    return 0 if overall_pass else 0  # don't fail the job; gate decision is in logs


if __name__ == "__main__":
    raise SystemExit(main())
