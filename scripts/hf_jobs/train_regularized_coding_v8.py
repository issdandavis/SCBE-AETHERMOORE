# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "transformers>=4.49",
#   "peft>=0.14",
#   "trl>=0.19",
#   "bitsandbytes>=0.45",
#   "accelerate>=1.3",
#   "datasets>=3.3",
#   "huggingface_hub>=0.27",
#   "torch",
# ]
# ///
"""SCBE regularized coding-model v8 HF Jobs runner.

This run is intentionally narrower than the failed broad v7 attempts:
- it trains from the regularized coding bucket only;
- it uses the frozen coding eval bucket during training;
- it fails before model load if the remote dataset files are missing;
- it uses ASCII-safe logs to avoid Windows/charmap replay failures.
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import torch
from datasets import Dataset, load_dataset
from datasets.utils.logging import disable_progress_bar
from huggingface_hub import hf_hub_download, login
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

disable_progress_bar()

ROUND = "regularized-coding-v8-hfjobs"
BASE_MODEL = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
HF_REPO = "issdandavis/scbe-coding-agent-qwen-regularized-coding-v8-hfjobs"
HF_DATASET_REPO = "issdandavis/scbe-training-regularized-20260426"
TRAIN_FILE = "regularized/coding_model/coding_model_train.regularized.jsonl"
EVAL_FILE = "regularized/coding_model/coding_model_eval.regularized.jsonl"
OUTPUT_DIR = f"/tmp/polly-{ROUND}"

BATCH_SIZE = 2
GRAD_ACCUM = 16
MAX_LEN = 768
MAX_STEPS = 120
LEARNING_RATE = 5e-5
MAX_TRAIN_RECORDS = 2755
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05


def safe_text(value: object) -> str:
    return str(value).encode("ascii", errors="replace").decode("ascii")


def auth() -> str:
    tok = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not tok:
        print("ERROR: no HF_TOKEN in env", file=sys.stderr)
        sys.exit(2)
    login(token=tok)
    return tok


def normalize_row(row: dict, cols: list[str]) -> dict | None:
    if "messages" in cols and row.get("messages"):
        return {"messages": row["messages"]}
    if "instruction" in cols:
        user = row.get("instruction", "")
        assistant = row.get("response") or row.get("output") or row.get("positive", "")
        if user and assistant:
            return {"messages": [{"role": "user", "content": user}, {"role": "assistant", "content": assistant}]}
    if "prompt" in cols:
        user = row.get("prompt", "")
        assistant = row.get("ideal_contains") or row.get("response", "")
        if user and assistant:
            return {"messages": [{"role": "user", "content": user}, {"role": "assistant", "content": str(assistant)}]}
    return None


def load_split(token: str, filename: str, split_name: str, max_records: int | None = None) -> Dataset:
    try:
        path = Path(
            hf_hub_download(
                repo_id=HF_DATASET_REPO,
                filename=filename,
                repo_type="dataset",
                token=token,
            )
        )
    except Exception as exc:
        print(f"ERROR: missing {split_name} file {filename}: {safe_text(exc)}", file=sys.stderr)
        sys.exit(10)

    raw = path.read_text(encoding="utf-8").strip()
    if not raw or raw.startswith("version https://git-lfs"):
        print(f"ERROR: invalid {split_name} file {filename} (empty/LFS pointer)", file=sys.stderr)
        sys.exit(11)

    ds = load_dataset("json", data_files=str(path), split="train")
    cols = ds.column_names
    records = []
    for row in ds:
        rec = normalize_row(row, cols)
        if rec:
            records.append(rec)

    if not records:
        print(f"ERROR: no normalized records in {split_name} file {filename}", file=sys.stderr)
        sys.exit(12)

    if max_records and len(records) > max_records:
        random.seed(42)
        records = random.sample(records, max_records)

    print(f"LOAD {split_name}: {len(records)} records from {filename}")
    return Dataset.from_list(records)


def write_status(phase: str, extra: dict | None = None):
    payload = {
        "round": ROUND,
        "phase": phase,
        "elapsed_s": round(time.time() - _start_ts),
        "base_model": BASE_MODEL,
        "train_file": TRAIN_FILE,
        "eval_file": EVAL_FILE,
        **(extra or {}),
    }
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    with open(f"{OUTPUT_DIR}/STATUS.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"[status] {phase} elapsed={payload['elapsed_s']}s")


_start_ts = time.time()


def main():
    print(f"=== POLLY HF-JOBS: {ROUND} ===")
    if not torch.cuda.is_available():
        print("ERROR: no GPU detected - this script requires a GPU runner", file=sys.stderr)
        sys.exit(3)

    cap = torch.cuda.get_device_capability(0)
    gpu_name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"GPU: {safe_text(gpu_name)}, sm_{cap[0]}{cap[1]}, VRAM={vram:.1f} GB")
    if cap[0] < 7:
        print("ERROR: need sm_70+ for bnb 4-bit; refusing CPU fallback", file=sys.stderr)
        sys.exit(4)

    token = auth()
    write_status("loading_data")
    train_dataset = load_split(token, TRAIN_FILE, "train", MAX_TRAIN_RECORDS)
    eval_dataset = load_split(token, EVAL_FILE, "eval", None)
    write_status("data_loaded", {"train_records": len(train_dataset), "eval_records": len(eval_dataset)})

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True, token=token)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    has_bf16 = cap[0] >= 8
    compute_dtype = torch.bfloat16 if has_bf16 else torch.float16
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True,
    )

    write_status("loading_model")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=quant_config,
        torch_dtype=compute_dtype,
        device_map="auto",
        token=token,
    )
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model = get_peft_model(
        model,
        LoraConfig(
            r=LORA_R,
            lora_alpha=LORA_ALPHA,
            lora_dropout=LORA_DROPOUT,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        ),
    )
    model.print_trainable_parameters()

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        args=SFTConfig(
            output_dir=OUTPUT_DIR,
            hub_model_id=HF_REPO,
            push_to_hub=True,
            learning_rate=LEARNING_RATE,
            per_device_train_batch_size=BATCH_SIZE,
            gradient_accumulation_steps=GRAD_ACCUM,
            max_steps=MAX_STEPS,
            warmup_ratio=0.03,
            weight_decay=0.01,
            max_grad_norm=0.3,
            lr_scheduler_type="cosine",
            logging_steps=10,
            eval_strategy="steps",
            eval_steps=30,
            save_strategy="steps",
            save_steps=30,
            save_total_limit=2,
            max_length=MAX_LEN,
            packing=False,
            dataset_num_proc=1,
            report_to="none",
            fp16=not has_bf16,
            bf16=has_bf16,
            optim="adamw_torch",
            gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False},
        ),
    )

    write_status("training")
    trainer.train()
    write_status("evaluating")
    metrics = trainer.evaluate()
    print("FINAL_EVAL", json.dumps({k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))}, sort_keys=True))

    write_status("saving")
    trainer.save_model()
    pushed = False
    try:
        trainer.push_to_hub()
        pushed = True
    except Exception as exc:
        print(f"WARN push_to_hub failed: {safe_text(exc)}", file=sys.stderr)

    with open(f"{OUTPUT_DIR}/DONE.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "round": ROUND,
                "status": "complete",
                "hf_repo": HF_REPO,
                "push": pushed,
                "final_eval": {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))},
            },
            f,
            indent=2,
        )
    print("=== TRAINING COMPLETE ===")


if __name__ == "__main__":
    main()
