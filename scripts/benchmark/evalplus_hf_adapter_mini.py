"""Run HumanEval+ Mini against the pushed SCBE LoRA coding adapter on HF Jobs."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import torch
from evalplus.data import get_human_eval_plus
from evalplus.data.utils import write_jsonl
from evalplus.evaluate import evaluate
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


BASE_MODEL = os.environ.get("SCBE_EVAL_BASE_MODEL", "Qwen/Qwen2.5-Coder-0.5B-Instruct")
ADAPTER_REPO = os.environ.get(
    "SCBE_EVAL_ADAPTER_REPO",
    "issdandavis/scbe-coding-agent-qwen-full-coding-system-v8",
)


def _token() -> str | None:
    token = os.environ.get("HF_TOKEN", "").strip() or os.environ.get("HUGGING_FACE_HUB_TOKEN", "").strip()
    return token or None


def _trim_completion(text: str) -> str:
    # Keep generated code in the current function body. HumanEval prompts already
    # include imports/signature; extra top-level prose usually breaks execution.
    stop_patterns = [
        r"\n```",
        r"\nif __name__",
        r"\nclass ",
        r"\ndef ",
        r"\n# Test",
        r"\nThe ",
        r"\nExplanation",
    ]
    end = len(text)
    for pattern in stop_patterns:
        match = re.search(pattern, text)
        if match:
            end = min(end, match.start())
    return text[:end].rstrip() + "\n"


def _result_path_for(samples_path: Path) -> Path:
    candidates = [
        Path(str(samples_path).replace(".jsonl", ".eval_results.json")),
        Path(str(samples_path).replace(".jsonl", "_eval_results.json")),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    matches = sorted(samples_path.parent.glob("*.eval_results.json")) + sorted(
        samples_path.parent.glob("*_eval_results.json")
    )
    if not matches:
        raise FileNotFoundError(f"No EvalPlus result JSON found in {samples_path.parent}")
    return matches[0]


def _pass1(results: dict, plus: bool) -> float:
    rows = list((results.get("eval") or {}).values())
    if not rows:
        return 0.0
    passed = 0
    for task_rows in rows:
        row = task_rows[0]
        base_ok = row.get("base_status") == "pass"
        plus_ok = row.get("plus_status") == "pass"
        passed += int(base_ok and (plus_ok if plus else True))
    return passed / len(rows)


def main() -> None:
    os.environ.setdefault("EVALPLUS_MAX_MEMORY_BYTES", "-1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    workdir = Path(os.environ.get("SCBE_EVALPLUS_WORKDIR", "/tmp/scbe-evalplus-adapter-mini"))
    workdir.mkdir(parents=True, exist_ok=True)
    samples_path = workdir / "scbe_adapter_humaneval_plus_mini.jsonl"
    for old in workdir.glob("*eval_results.json"):
        old.unlink()

    token = _token()
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, token=token, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        token=token,
        torch_dtype=dtype,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(base, ADAPTER_REPO, token=token)
    model.eval()

    problems = get_human_eval_plus(mini=True)
    samples = []
    max_new_tokens = int(os.environ.get("SCBE_EVAL_MAX_NEW_TOKENS", "128"))
    started = time.time()
    for index, (task_id, problem) in enumerate(sorted(problems.items()), start=1):
        prompt = problem["prompt"]
        encoded = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            generated = model.generate(
                **encoded,
                do_sample=False,
                max_new_tokens=max_new_tokens,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        decoded = tokenizer.decode(generated[0], skip_special_tokens=True)
        completion = decoded[len(prompt) :] if decoded.startswith(prompt) else decoded
        samples.append({"task_id": task_id, "completion": _trim_completion(completion)})
        if index == 1 or index % 10 == 0 or index == len(problems):
            print(
                json.dumps(
                    {
                        "event": "generation_progress",
                        "done": index,
                        "total": len(problems),
                        "elapsed_s": round(time.time() - started, 2),
                        "task_id": task_id,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    write_jsonl(str(samples_path), samples, drop_builtin=False)
    evaluate(
        dataset="humaneval",
        samples=str(samples_path),
        parallel=2,
        mini=True,
        i_just_wanna_run=False,
    )

    results_path = _result_path_for(samples_path)
    with results_path.open("r", encoding="utf-8") as handle:
        results = json.load(handle)
    summary = {
        "event": "evalplus_hf_adapter_mini_complete",
        "adapter_repo": ADAPTER_REPO,
        "base_model": BASE_MODEL,
        "dataset": "humaneval_plus_mini",
        "sample_count": len(samples),
        "base_pass_at_1": _pass1(results, plus=False),
        "plus_pass_at_1": _pass1(results, plus=True),
        "results_path": str(results_path),
    }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
