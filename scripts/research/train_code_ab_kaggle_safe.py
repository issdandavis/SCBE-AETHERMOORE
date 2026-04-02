#!/usr/bin/env python3
"""Run the matched-budget code A/B benchmark safely on Kaggle.

This script fixes the dead notebook pattern that compared mismatched corpora on
CPU and then sat until Kaggle killed the session. It always prepares the
matched-budget corpora first, detects the available accelerator, and does one
of two things:

1. GPU present (`T4`, `P100`, or similar): run a real matched-budget QLoRA A/B.
2. CPU only: fail fast by default, or run a tiny smoke lane only when
   `--allow-cpu-smoke` is set explicitly.

Outputs a single JSON summary packet that can be pulled from `/kaggle/working`
or a local artifacts directory.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
KAGGLE_WORKING = Path("/kaggle/working")
LOCAL_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "research" / "code_ab_kaggle"
TRAIN_CODE_AB_FAST_PATH = Path(__file__).with_name("train_code_ab_fast.py")


def _load_prepare_module() -> Any:
    spec = importlib.util.spec_from_file_location("train_code_ab_fast", TRAIN_CODE_AB_FAST_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_PREPARE_MODULE = _load_prepare_module()
DEFAULT_BASELINE = _PREPARE_MODULE.DEFAULT_BASELINE
DEFAULT_TRIANGULATED = _PREPARE_MODULE.DEFAULT_TRIANGULATED
extract_text = _PREPARE_MODULE.extract_text
prepare_benchmark = _PREPARE_MODULE.prepare_benchmark


def detect_accelerator() -> str:
    """Return the current accelerator name in a stable string form."""
    try:
        import torch

        if torch.cuda.is_available():
            return str(torch.cuda.get_device_name(0))
    except Exception:
        pass
    return "CPU"


def is_kaggle_runtime() -> bool:
    return KAGGLE_WORKING.exists() or bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE"))


def resolve_output_root(output_root: Path | None = None) -> Path:
    if output_root is not None:
        return output_root
    return KAGGLE_WORKING if is_kaggle_runtime() else LOCAL_OUTPUT_ROOT


def build_runtime_plan(accelerator: str, *, allow_cpu_smoke: bool = False) -> dict[str, Any]:
    """Pick a training plan that matches the actual hardware."""
    name = accelerator.strip().lower()

    if "t4" in name:
        return {
            "mode": "gpu_full",
            "accelerator": accelerator,
            "max_steps": 75,
            "max_seq_length": 512,
            "lora_rank": 8,
            "lora_alpha": 16,
            "batch_size": 2,
            "gradient_accumulation_steps": 8,
            "quantized": True,
        }

    if "p100" in name:
        return {
            "mode": "gpu_full",
            "accelerator": accelerator,
            "max_steps": 60,
            "max_seq_length": 384,
            "lora_rank": 8,
            "lora_alpha": 16,
            "batch_size": 2,
            "gradient_accumulation_steps": 8,
            "quantized": True,
        }

    if "gpu" in name or "cuda" in name:
        return {
            "mode": "gpu_full",
            "accelerator": accelerator,
            "max_steps": 50,
            "max_seq_length": 384,
            "lora_rank": 8,
            "lora_alpha": 16,
            "batch_size": 2,
            "gradient_accumulation_steps": 8,
            "quantized": True,
        }

    if allow_cpu_smoke:
        return {
            "mode": "cpu_smoke",
            "accelerator": accelerator,
            "max_steps": 4,
            "max_seq_length": 128,
            "lora_rank": 4,
            "lora_alpha": 8,
            "batch_size": 1,
            "gradient_accumulation_steps": 4,
            "quantized": False,
        }

    raise RuntimeError(
        "GPU required for the fair Kaggle code A/B lane. "
        "This runtime is CPU-only, so the script stopped instead of wasting hours. "
        "Enable a Kaggle GPU session or rerun with --allow-cpu-smoke for a tiny contract check."
    )


def load_jsonl_text_rows(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            text = extract_text(record) if "text" not in record else str(record["text"]).strip()
            if len(text) < 32:
                continue
            rows.append({"text": text})
    return rows


def summarize_delta(baseline_loss: float | None, triangulated_loss: float | None) -> dict[str, Any]:
    if baseline_loss is None or triangulated_loss is None:
        return {"delta_loss": None, "relative_improvement_pct": None, "winner": "unknown"}

    delta = triangulated_loss - baseline_loss
    relative = abs(delta) / baseline_loss * 100 if baseline_loss else None
    winner = "triangulated" if delta < 0 else "baseline" if delta > 0 else "tie"
    return {
        "delta_loss": round(delta, 4),
        "relative_improvement_pct": round(relative, 2) if relative is not None else None,
        "winner": winner,
    }


def train_condition(
    *,
    data_path: Path,
    model_name: str,
    output_dir: Path,
    plan: dict[str, Any],
) -> dict[str, Any]:
    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        Trainer,
        TrainingArguments,
    )

    rows = load_jsonl_text_rows(data_path)
    dataset = Dataset.from_list(rows)

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    load_mode = "full_precision"
    if plan["quantized"]:
        try:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
                bnb_4bit_use_double_quant=True,
            )
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
            )
            model = prepare_model_for_kbit_training(model)
            load_mode = "4bit_qlora"
        except Exception:
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True,
            )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float32,
            trust_remote_code=True,
        )

    lora = LoraConfig(
        r=plan["lora_rank"],
        lora_alpha=plan["lora_alpha"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "v_proj"] if plan["mode"] == "cpu_smoke" else ["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    model = get_peft_model(model, lora)

    def tokenize_fn(batch: dict[str, list[str]]) -> dict[str, list[list[int]]]:
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=plan["max_seq_length"],
            padding="max_length",
        )

    tokenized = dataset.map(tokenize_fn, batched=True, remove_columns=["text"])
    tokenized = tokenized.map(lambda batch: {"labels": batch["input_ids"]}, batched=True)

    bf16 = False
    fp16 = False
    if torch.cuda.is_available():
        capability = torch.cuda.get_device_capability(0)[0]
        bf16 = capability >= 8
        fp16 = capability < 8

    args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=1,
        max_steps=plan["max_steps"],
        per_device_train_batch_size=plan["batch_size"],
        gradient_accumulation_steps=plan["gradient_accumulation_steps"],
        learning_rate=2e-4,
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        logging_steps=10,
        save_strategy="no",
        gradient_checkpointing=plan["mode"] != "cpu_smoke",
        report_to="none",
        bf16=bf16,
        fp16=fp16,
    )

    trainer = Trainer(model=model, args=args, train_dataset=tokenized)
    start = time.time()
    trainer.train()
    elapsed = time.time() - start

    final_loss = None
    for entry in reversed(trainer.state.log_history):
        if "loss" in entry:
            final_loss = float(entry["loss"])
            break

    del trainer, model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return {
        "rows": len(dataset),
        "elapsed_seconds": round(elapsed, 2),
        "final_loss": round(final_loss, 4) if final_loss is not None else None,
        "load_mode": load_mode,
    }


def run_benchmark(
    *,
    baseline_path: Path,
    triangulated_path: Path,
    artifact_dir: Path,
    output_root: Path,
    model_name: str,
    max_baseline_rows: int,
    seed: int,
    allow_cpu_smoke: bool,
) -> dict[str, Any]:
    accelerator = detect_accelerator()
    plan = build_runtime_plan(accelerator, allow_cpu_smoke=allow_cpu_smoke)
    manifest = prepare_benchmark(
        baseline_path=baseline_path,
        triangulated_path=triangulated_path,
        artifact_dir=artifact_dir,
        max_baseline_rows=max_baseline_rows,
        seed=seed,
    )

    run_root = output_root / "code_ab_matched_budget"
    run_root.mkdir(parents=True, exist_ok=True)

    baseline_result = train_condition(
        data_path=artifact_dir / "baseline_matched.jsonl",
        model_name=model_name,
        output_dir=run_root / "baseline",
        plan=plan,
    )
    triangulated_result = train_condition(
        data_path=artifact_dir / "triangulated_matched.jsonl",
        model_name=model_name,
        output_dir=run_root / "triangulated",
        plan=plan,
    )

    summary = {
        "model": model_name,
        "runtime_plan": plan,
        "manifest": manifest,
        "baseline": baseline_result,
        "triangulated": triangulated_result,
    }
    summary.update(
        summarize_delta(
            baseline_result.get("final_loss"),
            triangulated_result.get("final_loss"),
        )
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--triangulated", type=Path, default=DEFAULT_TRIANGULATED)
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=REPO_ROOT / "artifacts" / "research" / "code_ab_fast",
    )
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-baseline-rows", type=int, default=5000)
    parser.add_argument("--allow-cpu-smoke", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = resolve_output_root(args.output_root)
    summary = run_benchmark(
        baseline_path=args.baseline,
        triangulated_path=args.triangulated,
        artifact_dir=args.artifact_dir,
        output_root=output_root,
        model_name=args.model,
        max_baseline_rows=args.max_baseline_rows,
        seed=args.seed,
        allow_cpu_smoke=args.allow_cpu_smoke,
    )

    summary_path = output_root / "code_ab_matched_budget_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"\nSummary written to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
