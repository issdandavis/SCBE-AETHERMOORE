#!/usr/bin/env python3
from __future__ import annotations

import faulthandler
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

faulthandler.enable()

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from scripts.eval_legacy_hf_model import build_prompt, load_eval_records, score_response, summarize_results

ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "models" / "hf" / "Qwen2.5-0.5B-Instruct"
ADAPTER_DIR = ROOT / "models" / "hf" / "scbe-pivot-qwen-0.5b"
OUTPUT_DIR = ROOT / "artifacts" / "model_evals" / "local_qwen_benchmark_20260324"
SUITES = {
    "compliance": ROOT / "training-data" / "evals" / "compliance_evals.jsonl",
    "story": ROOT / "training-data" / "evals" / "story_evals.jsonl",
}


def log(*parts: object) -> None:
    print(*parts, flush=True)


def pick_device() -> tuple[str, torch.dtype]:
    if torch.cuda.is_available():
        return "cuda", torch.float16
    return "cpu", torch.float32


def load_tokenizer(local_dir: Path):
    tokenizer = AutoTokenizer.from_pretrained(local_dir, local_files_only=True)
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    return tokenizer


def load_base_model(local_dir: Path, device: str, dtype: torch.dtype):
    model = AutoModelForCausalLM.from_pretrained(
        local_dir,
        local_files_only=True,
        dtype=dtype,
        low_cpu_mem_usage=True,
    )
    model.to(device)
    model.eval()
    return model


def load_adapter_model(base_dir: Path, adapter_dir: Path, device: str, dtype: torch.dtype):
    base = AutoModelForCausalLM.from_pretrained(
        base_dir,
        local_files_only=True,
        dtype=dtype,
        low_cpu_mem_usage=True,
    )
    model = PeftModel.from_pretrained(base, adapter_dir, local_files_only=True)
    model.to(device)
    model.eval()
    return model


def generate(tokenizer, model, prompt: str, max_new_tokens: int = 180) -> str:
    if getattr(tokenizer, "chat_template", None):
        input_ids = tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
        )
    else:
        input_ids = tokenizer(prompt, return_tensors="pt")["input_ids"]
    input_ids = input_ids.to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            input_ids,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    generated = outputs[0][input_ids.shape[-1] :]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()


def run_suite(model_name: str, tokenizer, model, suite_name: str, suite_path: Path):
    records = load_eval_records(suite_path)
    results = []
    for index, record in enumerate(records, start=1):
        log(f"[{model_name}] {suite_name} {index}/{len(records)} {record.id}")
        response = generate(tokenizer, model, build_prompt(record))
        results.append(score_response(record, response))
    return results


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    device, dtype = pick_device()
    log("device", device, "dtype", dtype)
    log("base_dir", BASE_DIR)
    log("adapter_dir", ADAPTER_DIR)

    tokenizer = load_tokenizer(BASE_DIR)

    log("loading base model")
    base_model = load_base_model(BASE_DIR, device, dtype)
    log("loading adapter model")
    adapter_model = load_adapter_model(BASE_DIR, ADAPTER_DIR, device, dtype)

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "device": device,
        "dtype": str(dtype),
        "models": {},
    }

    model_map = {
        "qwen_base_0.5b": base_model,
        "scbe_pivot_qwen_0.5b": adapter_model,
    }

    for model_name, model in model_map.items():
        report["models"][model_name] = {}
        combined = []
        for suite_name, suite_path in SUITES.items():
            results = run_suite(model_name, tokenizer, model, suite_name, suite_path)
            summary = summarize_results(results)
            report["models"][model_name][suite_name] = summary
            combined.extend(results)
            out_path = OUTPUT_DIR / f"{model_name}_{suite_name}_results.json"
            out_path.write_text(
                json.dumps(
                    {
                        "model": model_name,
                        "suite": suite_name,
                        "summary": summary,
                        "results": [
                            {
                                "id": item.record.id,
                                "category": item.record.category,
                                "instruction": item.record.instruction,
                                "response": item.response,
                                "matched_terms": item.matched_terms,
                                "missing_terms": item.missing_terms,
                                "term_match_ratio": item.term_match_ratio,
                                "passed": item.passed,
                            }
                            for item in results
                        ],
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        report["models"][model_name]["combined"] = summarize_results(combined)

    summary_path = OUTPUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = [
        "# Local Qwen Benchmark 2026-03-24",
        "",
        f"- device: `{device}`",
        f"- dtype: `{dtype}`",
        "",
        "| Model | Compliance Pass | Story Pass | Combined Pass | Combined Coverage |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for model_name, data in report["models"].items():
        compliance = data["compliance"]
        story = data["story"]
        combined = data["combined"]
        md_lines.append(
            f"| {model_name} | {compliance['passed']}/{compliance['total']} ({compliance['pass_rate']:.2%}) | "
            f"{story['passed']}/{story['total']} ({story['pass_rate']:.2%}) | "
            f"{combined['passed']}/{combined['total']} ({combined['pass_rate']:.2%}) | "
            f"{combined['global_term_coverage']:.2%} |"
        )
    (OUTPUT_DIR / "summary.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    log(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException:
        traceback.print_exc()
        raise
