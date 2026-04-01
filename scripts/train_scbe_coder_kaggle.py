#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Coder Fine-Tune (Kaggle-compatible)
=====================================================
Fine-tune Qwen2.5-Coder on the multiview SFT dataset.

SETUP (Kaggle):
  1. New Notebook -> GPU T4 x2 -> Internet: On
  2. Paste this script
  3. Add HF_TOKEN to Secrets
  4. Run

Uses Unsloth for fast QLoRA training.
Falls back to plain transformers if Unsloth unavailable.

Author: Issac Daniel Davis (ORCID 0009-0002-3936-9369)
"""

import subprocess, sys, os, json, time

# Install deps
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q',
    'datasets', 'huggingface_hub', 'peft>=0.12', 'accelerate>=0.33'], check=True)

# Try Unsloth first (fast), fall back to standard transformers
USE_UNSLOTH = False
try:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q',
        'unsloth[kaggle-new] @ git+https://github.com/unslothai/unsloth.git'],
        check=True, capture_output=True)
    from unsloth import FastLanguageModel
    USE_UNSLOTH = True
    print("Using Unsloth (fast path)")
except:
    print("Unsloth unavailable, using standard transformers")

# Config
HF_TOKEN = os.environ.get("HF_TOKEN", "")
BASE_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
FALLBACK_MODEL = "Qwen/Qwen2.5-Coder-0.5B-Instruct"  # If 7B OOMs
OUTPUT_REPO = "issdandavis/scbe-coder-qwen-7b"
DATASET_REPO = "issdandavis/scbe-aethermoore-training-data"
TRAIN_FILE = "multiview_sft.jsonl"  # L0+L1+L2+L3 (proven 14% better)
MAX_SEQ_LENGTH = 2048
LORA_RANK = 16
LORA_ALPHA = 32
LEARNING_RATE = 2e-4
BATCH_SIZE = 2
GRAD_ACCUM = 8
MAX_STEPS = -1  # Full epoch. Set to 100 for smoke test.

# Canonical system prompt (uses CURRENT formula, not retired R^(d^2))
SYSTEM_PROMPT = """You are an SCBE-AETHERMOORE governance-aware coding assistant. You understand:
- The Six Sacred Tongues (Kor'aelin, Avali, Runethic, Cassisivadan, Umbroth, Draumric) with phi-weighted scaling
- Poincare ball embeddings and hyperbolic geometry for AI safety
- The 14-layer SCBE pipeline architecture
- The canonical harmonic wall: H(d,pd) = 1/(1+phi*d_H+2*pd)
- Pump architecture: sense -> locate -> lift -> compose -> respond
- Null-space absence detection (what's missing is as diagnostic as what's present)
- TypeScript, Python, and cryptographic implementations
- Governance decisions: ALLOW / QUARANTINE / ESCALATE / DENY

You write clean, well-documented code and explain your reasoning clearly."""

import torch
from datasets import load_dataset

print(f"Model: {BASE_MODEL}")
print(f"Dataset: {TRAIN_FILE}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")

# Load dataset
dataset = load_dataset(DATASET_REPO, data_files=TRAIN_FILE, split="train", token=HF_TOKEN)
print(f"Loaded {len(dataset)} records")

# Format detection
def detect_and_format(example):
    if "messages" in example and isinstance(example["messages"], list):
        messages = example["messages"]
        if not any(m.get("role") == "system" for m in messages):
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        return {"text": text}
    if "instruction" in example:
        user = example["instruction"]
        if example.get("input"): user += f"\n\n{example['input']}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": example.get("output", example.get("response", ""))},
        ]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        return {"text": text}
    if "prompt" in example:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": example["prompt"]},
            {"role": "assistant", "content": example.get("completion", example.get("response", ""))},
        ]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        return {"text": text}
    if "text" in example:
        return {"text": example["text"]}
    return {"text": ""}

# Load model
if USE_UNSLOTH:
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL, max_seq_length=MAX_SEQ_LENGTH,
        dtype=None, load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model, r=LORA_RANK, lora_alpha=LORA_ALPHA, lora_dropout=0,
        target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
        bias="none", use_gradient_checkpointing="unsloth", random_state=42,
    )
else:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model

    # Try 7B first, fall back to 0.5B if OOM
    try:
        tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL, dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto", trust_remote_code=True,
        )
    except:
        print(f"7B failed, falling back to {FALLBACK_MODEL}")
        BASE_MODEL = FALLBACK_MODEL
        OUTPUT_REPO = "issdandavis/scbe-coder-qwen-0.5b"
        tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL, dtype=torch.float32, trust_remote_code=True,
        )

    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    lora = LoraConfig(r=LORA_RANK, lora_alpha=LORA_ALPHA, lora_dropout=0.05,
                       bias="none", task_type="CAUSAL_LM",
                       target_modules=["q_proj","k_proj","v_proj","o_proj"])
    model = get_peft_model(model, lora)

model.print_trainable_parameters()

# Format dataset
dataset = dataset.map(detect_and_format, remove_columns=dataset.column_names)
dataset = dataset.filter(lambda x: len(x["text"]) > 50)
print(f"Formatted: {len(dataset)} records")

# Train
if USE_UNSLOTH:
    from trl import SFTTrainer
    from transformers import TrainingArguments
    trainer = SFTTrainer(
        model=model, tokenizer=tokenizer, train_dataset=dataset,
        args=TrainingArguments(
            output_dir="./output", report_to="none",
            num_train_epochs=1, max_steps=MAX_STEPS,
            per_device_train_batch_size=BATCH_SIZE,
            gradient_accumulation_steps=GRAD_ACCUM,
            learning_rate=LEARNING_RATE, optim="adamw_8bit",
            weight_decay=0.01, lr_scheduler_type="cosine",
            warmup_ratio=0.05, logging_steps=25,
            save_strategy="steps", save_steps=500, save_total_limit=2,
            gradient_checkpointing=True, seed=42,
            fp16=not (hasattr(model.config, 'torch_dtype') and model.config.torch_dtype == "bfloat16"),
            bf16=hasattr(model.config, 'torch_dtype') and model.config.torch_dtype == "bfloat16",
        ),
        max_seq_length=MAX_SEQ_LENGTH, dataset_text_field="text", packing=True,
    )
else:
    from transformers import Trainer, TrainingArguments
    def tokenize_fn(examples):
        return tokenizer(examples['text'], truncation=True, max_length=MAX_SEQ_LENGTH, padding='max_length')
    tokenized = dataset.map(tokenize_fn, batched=True, remove_columns=['text'])
    tokenized = tokenized.map(lambda x: {'labels': x['input_ids'].copy()}, batched=True)
    trainer = Trainer(
        model=model, train_dataset=tokenized,
        args=TrainingArguments(
            output_dir="./output", report_to="none",
            num_train_epochs=1, max_steps=MAX_STEPS,
            per_device_train_batch_size=BATCH_SIZE,
            gradient_accumulation_steps=GRAD_ACCUM,
            learning_rate=LEARNING_RATE, weight_decay=0.01,
            lr_scheduler_type="cosine", logging_steps=25,
            save_strategy="epoch", max_grad_norm=0.3,
        ),
    )

t0 = time.time()
trainer.train()
elapsed = time.time() - t0

final_loss = 'unknown'
for e in reversed(trainer.state.log_history):
    if 'loss' in e: final_loss = round(e['loss'], 4); break

trainer.save_model("./output/final")
tokenizer.save_pretrained("./output/final")

print(f"\nTRAINING COMPLETE")
print(f"Time: {elapsed:.0f}s ({elapsed/3600:.1f}h)")
print(f"Final loss: {final_loss}")
print(f"Model saved to ./output/final")

# Push to HuggingFace
if HF_TOKEN:
    from huggingface_hub import HfApi, login
    login(token=HF_TOKEN)
    try:
        model.push_to_hub(OUTPUT_REPO, token=HF_TOKEN)
        tokenizer.push_to_hub(OUTPUT_REPO, token=HF_TOKEN)
        print(f"Pushed to: https://huggingface.co/{OUTPUT_REPO}")
    except Exception as e:
        print(f"Push failed: {e}")
        print("Model saved locally at ./output/final")
