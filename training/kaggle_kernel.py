"""
SCBE-AETHERMOORE QLoRA Fine-Tuning — Kaggle Kernel Script

Runs on Kaggle with P100/T4 GPU (free tier: 30 hrs/week).
Pulls training data from HuggingFace, fine-tunes TinyLlama,
pushes adapter back to HuggingFace.

Usage:
  - Push to Kaggle via: python scripts/kaggle_remote_train.py push
  - Or upload manually at kaggle.com/kernels
"""

import os
import gc
import json
import subprocess
import sys
from pathlib import Path

# ── Install dependencies (Kaggle pre-installs torch + transformers) ──────────
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "-q",
    "peft>=0.10.0", "bitsandbytes>=0.43.0", "trl>=0.8.0",
    "accelerate>=0.30.0", "datasets>=2.19.0",
])

import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer
from huggingface_hub import HfApi, login

# ── Configuration ────────────────────────────────────────────────────────────

# HF token from Kaggle secrets (set in kernel settings)
HF_TOKEN = os.environ.get("HF_TOKEN", "")
if not HF_TOKEN:
    # Try Kaggle userdata API
    try:
        from kaggle_secrets import UserSecretsClient
        HF_TOKEN = UserSecretsClient().get_secret("HF_TOKEN")
    except Exception:
        pass

if HF_TOKEN:
    login(token=HF_TOKEN)
    print("Logged in to HuggingFace Hub.")
else:
    print("WARNING: No HF_TOKEN found. Push will fail.")

# Base model
BASE_MODEL = os.environ.get("BASE_MODEL", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")

# Dataset
DATASET_ID = os.environ.get("DATASET_ID", "issdandavis/scbe-aethermoore-training-data")

# Output
OUTPUT_MODEL = os.environ.get("OUTPUT_MODEL", "issdandavis/scbe-aethermoore-sft-v1")

# Training hyperparameters
EPOCHS = int(os.environ.get("EPOCHS", "3"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "4"))
LEARNING_RATE = float(os.environ.get("LEARNING_RATE", "2e-4"))
MAX_SEQ_LENGTH = int(os.environ.get("MAX_SEQ_LENGTH", "1024"))
LORA_R = int(os.environ.get("LORA_R", "16"))
LORA_ALPHA = int(os.environ.get("LORA_ALPHA", "32"))
GRADIENT_ACCUMULATION = int(os.environ.get("GRADIENT_ACCUMULATION", "4"))

# Output directory
OUTPUT_DIR = "/kaggle/working/scbe-sft-output"

print("=" * 60)
print("SCBE-AETHERMOORE QLoRA Fine-Tuning")
print("=" * 60)
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
if torch.cuda.is_available():
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")
print(f"Base model: {BASE_MODEL}")
print(f"Dataset: {DATASET_ID}")
print(f"Output: {OUTPUT_MODEL}")
print(f"Config: epochs={EPOCHS}, batch={BATCH_SIZE}, lr={LEARNING_RATE}")
print(f"LoRA: r={LORA_R}, alpha={LORA_ALPHA}")
print()

# ── Load & Format Dataset ────────────────────────────────────────────────────

dataset = load_dataset(DATASET_ID, split="train")
print(f"Dataset size: {len(dataset)} examples")
print(f"Columns: {dataset.column_names}")


def format_for_sft(example):
    """Convert SCBE training pair to chat format."""
    # Handle multiple column name conventions
    if "input" in example and "output" in example:
        user_text = example["input"]
        assistant_text = example["output"]
    elif "prompt" in example and "response" in example:
        user_text = example["prompt"]
        assistant_text = example["response"]
    elif "question" in example and "answer" in example:
        user_text = example["question"]
        assistant_text = example["answer"]
    elif "text" in example:
        return {"text": example["text"]}
    else:
        user_text = str(example.get("input", ""))
        assistant_text = str(example.get("output", ""))

    text = (
        f"<|system|>\n"
        f"You are an AI assistant powered by SCBE-AETHERMOORE governance. "
        f"You are helpful, safe, and technically competent.</s>\n"
        f"<|user|>\n{user_text}</s>\n"
        f"<|assistant|>\n{assistant_text}</s>"
    )
    return {"text": text}


formatted = dataset.map(format_for_sft, remove_columns=dataset.column_names)
split = formatted.train_test_split(test_size=0.05, seed=42)
train_dataset = split["train"]
eval_dataset = split["test"]
print(f"Train: {len(train_dataset)}, Eval: {len(eval_dataset)}")

# ── Load Model (4-bit quantized) ─────────────────────────────────────────────

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)
model.config.use_cache = False

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

model = prepare_model_for_kbit_training(model)
print(f"Model loaded: {model.num_parameters():,} params")
print(f"GPU memory: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

# ── Apply LoRA ────────────────────────────────────────────────────────────────

lora_config = LoraConfig(
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                     "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, lora_config)
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total = sum(p.numel() for p in model.parameters())
print(f"Trainable: {trainable:,} / {total:,} ({100 * trainable / total:.2f}%)")

# ── Train ─────────────────────────────────────────────────────────────────────

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRADIENT_ACCUMULATION,
    learning_rate=LEARNING_RATE,
    weight_decay=0.01,
    warmup_ratio=0.03,
    lr_scheduler_type="cosine",
    logging_steps=25,
    save_steps=200,
    save_total_limit=2,
    eval_strategy="steps",
    eval_steps=200,
    fp16=True,
    optim="paged_adamw_8bit",
    gradient_checkpointing=True,
    group_by_length=True,
    report_to="none",
)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    args=training_args,
    max_seq_length=MAX_SEQ_LENGTH,
    dataset_text_field="text",
    packing=True,
)

est_steps = len(train_dataset) * EPOCHS // (BATCH_SIZE * GRADIENT_ACCUMULATION)
print(f"\nStarting training: ~{est_steps} steps")
trainer.train()
print("Training complete!")

# Save locally
trainer.save_model(f"{OUTPUT_DIR}/final")
tokenizer.save_pretrained(f"{OUTPUT_DIR}/final")

# ── Push to HuggingFace ──────────────────────────────────────────────────────

if HF_TOKEN:
    api = HfApi()
    api.create_repo(repo_id=OUTPUT_MODEL, repo_type="model", exist_ok=True, private=True)
    model.push_to_hub(OUTPUT_MODEL, private=True)
    tokenizer.push_to_hub(OUTPUT_MODEL, private=True)

    # Model card
    model_card = f"""---
base_model: {BASE_MODEL}
library_name: peft
license: apache-2.0
tags:
  - scbe-aethermoore
  - qlora
  - sacred-tongues
  - governance
---

# SCBE-AETHERMOORE SFT Model v1

QLoRA fine-tuned on {len(train_dataset)} SCBE training pairs.

- **Base**: `{BASE_MODEL}`
- **LoRA**: r={LORA_R}, alpha={LORA_ALPHA}
- **Training**: {EPOCHS} epochs, lr={LEARNING_RATE}
- **Governance**: All data passed SCBE 14-layer pipeline

USPTO #63/961,403
"""
    api.upload_file(
        path_or_fileobj=model_card.encode(),
        path_in_repo="README.md",
        repo_id=OUTPUT_MODEL,
        repo_type="model",
    )
    print(f"Model pushed to: https://huggingface.co/{OUTPUT_MODEL}")
else:
    print("No HF_TOKEN — model saved locally only.")

# ── Quick Test ────────────────────────────────────────────────────────────────

model.eval()
test_prompts = [
    "What is SCBE?",
    "Explain the 14-layer pipeline.",
    "What are Sacred Tongues?",
]

print("\n" + "=" * 60)
print("INFERENCE TEST")
print("=" * 60)

for prompt in test_prompts:
    formatted_prompt = (
        f"<|system|>\nYou are an AI assistant powered by SCBE-AETHERMOORE governance.</s>\n"
        f"<|user|>\n{prompt}</s>\n"
        f"<|assistant|>\n"
    )
    inputs = tokenizer(formatted_prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs, max_new_tokens=150, temperature=0.7,
            top_p=0.9, do_sample=True, repetition_penalty=1.1,
        )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    generated = response[len(tokenizer.decode(inputs["input_ids"][0], skip_special_tokens=True)):]
    print(f"\nQ: {prompt}")
    print(f"A: {generated.strip()[:250]}")

# ── Training Summary ─────────────────────────────────────────────────────────

summary = {
    "base_model": BASE_MODEL,
    "output_model": OUTPUT_MODEL,
    "dataset": DATASET_ID,
    "train_size": len(train_dataset),
    "eval_size": len(eval_dataset),
    "epochs": EPOCHS,
    "lora_r": LORA_R,
    "lora_alpha": LORA_ALPHA,
    "learning_rate": LEARNING_RATE,
    "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None",
    "max_gpu_memory_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2) if torch.cuda.is_available() else 0,
}

summary_path = f"{OUTPUT_DIR}/training_summary.json"
with open(summary_path, "w") as f:
    json.dump(summary, f, indent=2)
print(f"\nSummary saved: {summary_path}")
print(json.dumps(summary, indent=2))

# Cleanup
del model, trainer
gc.collect()
if torch.cuda.is_available():
    torch.cuda.empty_cache()
print("\nDone. GPU memory freed.")
