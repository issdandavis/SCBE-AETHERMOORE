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
"""SCBE Polly geoseal-stage6-repair-v7 - HF Jobs runner.

Pulls all v7 SFT files from issdandavis/scbe-aethermoore-training-data,
trains a LoRA adapter on Qwen/Qwen2.5-Coder-0.5B-Instruct using bnb 4-bit
NF4 quantization, and pushes the adapter to
issdandavis/scbe-coding-agent-qwen-stage6-repair-v7-hfjobs on completion.

Designed for HF Jobs t4-small (1x T4 16GB, sm_75) - no CPU fallback.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("HF_DATASETS_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TQDM_DISABLE", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import torch
from datasets import Dataset, disable_progress_bar, load_dataset
from huggingface_hub import hf_hub_download, login
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

disable_progress_bar()

ROUND = "geoseal-stage6-repair-v7-hfjobs"
BASE_MODEL = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
HF_REPO = "issdandavis/scbe-coding-agent-qwen-stage6-repair-v7-hfjobs"
HF_DATASET_REPO = "issdandavis/scbe-coding-agent-sft-stage6-repair-v7"
OUTPUT_DIR = f"/tmp/polly-{ROUND}"

FILES = [
    # --- coding systems (agentic codeflow over all primaries) ---
    "coding_system_full_v1_train.sft.jsonl",
    "bijective_codeflow_v1_train.sft.jsonl",
    "cross_tongue_dialogue_bijective_v1_train.sft.jsonl",
    "drill_langues_full_train.sft.jsonl",
    "tongue_name_pairing_sft.jsonl",
    # --- binary / hexadecimal lanes ---
    "binary_interpretation_matrix_v1.sft.jsonl",
    "binary_matrix_v2_full.sft.jsonl",
    "binary_pillars_v1.sft.jsonl",
    "blc_time_placement_v1.sft.jsonl",
    "typescript_debug_harness_v1.sft.jsonl",
    # --- agentic operators (true agentic coding) ---
    "t_operator_v1.sft.jsonl",
    "eml_operator_v1.sft.jsonl",
    "operator_agent_bus_extracted_v1_train.sft.jsonl",
    "colab_run_evidence_v1.sft.jsonl",
    "aligned_foundations_train.sft.jsonl",
    # --- command lattice + geoseal commands ---
    "command_lattice_seed_train.sft.jsonl",
    "geoseal_command_recall_v1.sft.jsonl",
    "geoseal_command_harmony_v1.sft.jsonl",
    # --- atomic workflow (stage 6) ---
    "atomic_workflow_stage6_train.sft.jsonl",
    "atomic_workflow_stage6_repair_train.sft.jsonl",
]

EPOCHS = 1
BATCH_SIZE = 2
GRAD_ACCUM = 16
MAX_LEN = 768
MAX_STEPS = 360
LEARNING_RATE = 8e-5
MAX_RECORDS = 3950
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05


def safe_text(value: object) -> str:
    """Keep remote HF job logs ASCII-safe even if the runner falls back to cp1252."""
    return str(value).encode("ascii", errors="replace").decode("ascii")


def auth():
    tok = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not tok:
        print("ERROR: no HF_TOKEN in env", file=sys.stderr)
        sys.exit(2)
    login(token=tok)
    return tok


def load_records(token: str) -> Dataset:
    records = []
    for name in FILES:
        path = None
        last_exc = None
        try:
            for candidate in (name, f"sft/{name}", f"training-data/sft/{name}"):
                try:
                    path = Path(
                        hf_hub_download(
                            repo_id=HF_DATASET_REPO,
                            filename=candidate,
                            repo_type="dataset",
                            token=token,
                        )
                    )
                    break
                except Exception as exc:
                    last_exc = exc
            if path is None:
                raise RuntimeError(last_exc)
        except Exception as exc:
            print(f"  SKIP {name}: {safe_text(exc)}", file=sys.stderr)
            continue

        raw = path.read_text(encoding="utf-8").strip()
        if not raw or raw.startswith("version https://git-lfs"):
            print(f"  SKIP {name} (empty/LFS)")
            continue

        ds = load_dataset("json", data_files=str(path), split="train")
        cols = ds.column_names
        count = 0
        for row in ds:
            rec = None
            if "messages" in cols and row.get("messages"):
                rec = {"messages": row["messages"]}
            elif "instruction" in cols:
                u = row.get("instruction", "")
                a = row.get("response") or row.get("output") or row.get("positive", "")
                if u and a:
                    rec = {"messages": [{"role": "user", "content": u}, {"role": "assistant", "content": a}]}
            elif "prompt" in cols:
                u = row.get("prompt", "")
                a = row.get("ideal_contains") or row.get("response", "")
                if u and a:
                    rec = {"messages": [{"role": "user", "content": u}, {"role": "assistant", "content": str(a)}]}
            if rec:
                records.append(rec)
                count += 1
        print(f"  LOAD {name}: {count} records")

    print(f"\nTotal: {len(records)} training records")
    if not records:
        print("ERROR: no data loaded", file=sys.stderr)
        sys.exit(1)

    if len(records) > MAX_RECORDS:
        import random as _random
        _random.seed(42)
        records = _random.sample(records, MAX_RECORDS)
        print(f"Sampled {MAX_RECORDS} records")

    return Dataset.from_list(records)


def write_status(phase: str, extra: dict | None = None):
    payload = {
        "round": ROUND,
        "phase": phase,
        "elapsed_s": round(time.time() - _start_ts),
        "base_model": BASE_MODEL,
        **(extra or {}),
    }
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    with open(f"{OUTPUT_DIR}/STATUS.json", "w", encoding="utf-8") as f:
        json.dump(payload, f)
    print(f"[status] {phase} elapsed={payload['elapsed_s']}s")


_start_ts = time.time()


def main():
    print(f"=== POLLY HF-JOBS: {ROUND} ===")
    if not torch.cuda.is_available():
        print("ERROR: no GPU detected - this script requires a GPU runner", file=sys.stderr)
        sys.exit(3)

    cap = torch.cuda.get_device_capability(0)
    name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"GPU: {name}, sm_{cap[0]}{cap[1]}, VRAM={vram:.1f} GB")
    if cap[0] < 7:
        print("ERROR: need sm_70+ for bnb 4-bit; this runner refuses to fall back to CPU", file=sys.stderr)
        sys.exit(4)

    token = auth()
    write_status("loading_data")
    dataset = load_records(token)
    write_status("data_loaded", {"num_records": len(dataset)})

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
        train_dataset=dataset,
        args=SFTConfig(
            output_dir=OUTPUT_DIR,
            hub_model_id=HF_REPO,
            push_to_hub=True,
            learning_rate=LEARNING_RATE,
            per_device_train_batch_size=BATCH_SIZE,
            gradient_accumulation_steps=GRAD_ACCUM,
            num_train_epochs=EPOCHS,
            max_steps=MAX_STEPS,
            warmup_ratio=0.03,
            weight_decay=0.01,
            max_grad_norm=0.3,
            lr_scheduler_type="cosine",
            logging_steps=10,
            save_strategy="steps",
            save_steps=60,
            save_total_limit=3,
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
    write_status("saving")
    trainer.save_model()

    try:
        trainer.push_to_hub()
        pushed = True
    except Exception as exc:
        print(f"WARN push_to_hub failed: {safe_text(exc)}", file=sys.stderr)
        pushed = False

    with open(f"{OUTPUT_DIR}/DONE.json", "w", encoding="utf-8") as f:
        json.dump(
            {"round": ROUND, "status": "complete", "hf_repo": HF_REPO, "push": pushed},
            f,
        )
    print("=== TRAINING COMPLETE ===")


if __name__ == "__main__":
    main()
