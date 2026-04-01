#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Coder Fine-Tune
=================================
Fine-tune Qwen2.5-Coder-7B on your 233K multi-view SFT dataset
using QLoRA via Unsloth on a free Kaggle T4 GPU.

SETUP (Kaggle):
  1. New Notebook → Accelerator: GPU T4 x2 → Internet: On
  2. Paste this entire script into a single cell (or split at the ### markers)
  3. Run. Total time: ~2-3 hours on dual T4.

OUTPUT:
  - LoRA adapter → pushed to HuggingFace as issdandavis/scbe-coder-qwen-7b
  - GGUF Q4_K_M → uploaded for direct Ollama use

Author: Issac Daniel Davis
Dataset: issdandavis/scbe-aethermoore-training-data
Base: Qwen/Qwen2.5-Coder-7B-Instruct
"""

# CELL 1: Install dependencies

# !pip install -q "unsloth[kaggle-new] @ git+https://github.com/unslothai/unsloth.git"
# !pip install -q datasets huggingface_hub

# Uncomment the above in Kaggle. On Colab use:
# !pip install -q "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
# !pip install -q --no-deps xformers trl peft accelerate bitsandbytes triton
# !pip install -q datasets huggingface_hub

# CELL 2: Configuration

import os

# ── Authentication ──────────────────────────────────────────────────────────
# In Kaggle: Settings → Secrets → Add "HF_TOKEN" with your write token
# Or set it directly (not recommended for shared notebooks):
HF_TOKEN = os.environ.get("HF_TOKEN", "your_hf_write_token_here")

# ── Model config ────────────────────────────────────────────────────────────
BASE_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
OUTPUT_REPO = "issdandavis/scbe-coder-qwen-7b"  # LoRA adapter
GGUF_REPO = "issdandavis/scbe-coder-qwen-7b-GGUF"  # Quantized for Ollama

# ── Dataset config ──────────────────────────────────────────────────────────
DATASET_REPO = "issdandavis/scbe-aethermoore-training-data"

# Which file to train on:
#   "multiview_sft.jsonl"          → 233K records (L0+L1+L2+L3) — full stack
#   "polly_training_merged.jsonl"  → 116K records (L3 only) — faster, expression-focused
#
# For a coding AI, L3 Expression pairs are most relevant. Start with the
# 116K L3 file for faster iteration, then scale to 233K if results are good.
TRAIN_FILE = "polly_training_merged.jsonl"

# ── Training hyperparameters ────────────────────────────────────────────────
MAX_SEQ_LENGTH = 4096  # Qwen2.5-Coder supports 128K, but 4K saves VRAM
LORA_RANK = 32  # Higher = more capacity, more VRAM. 16-64 range.
LORA_ALPHA = 64  # Typically 2x rank
LEARNING_RATE = 2e-4  # Unsloth default, works well for QLoRA
NUM_EPOCHS = 1  # 1 epoch for 116K+ samples is plenty
BATCH_SIZE = 2  # Per-device batch size (T4 16GB limit)
GRAD_ACCUM = 8  # Effective batch = 2 * 8 = 16
WARMUP_RATIO = 0.05
MAX_STEPS = -1  # -1 = full epochs. Set to e.g. 500 for quick test.

# For a quick smoke test, set:
# MAX_STEPS = 100
# This trains ~100 steps in ~10 minutes to verify everything works.

# CELL 3: Load model with Unsloth

from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=BASE_MODEL,
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=None,  # Auto-detect (bfloat16 on T4)
    load_in_4bit=True,  # QLoRA: load base in 4-bit
)

# Apply LoRA adapters to the model
model = FastLanguageModel.get_peft_model(
    model,
    r=LORA_RANK,
    lora_alpha=LORA_ALPHA,
    lora_dropout=0,  # Unsloth optimized: 0 is faster
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    bias="none",
    use_gradient_checkpointing="unsloth",  # 30% less VRAM
    random_state=42,
)

print(f"Trainable parameters: {model.print_trainable_parameters()}")

# CELL 4: Load and format dataset

from datasets import load_dataset
import json

# Load the dataset from HuggingFace
dataset = load_dataset(
    DATASET_REPO,
    data_files=TRAIN_FILE,
    split="train",
    token=HF_TOKEN,
)

print(f"Loaded {len(dataset)} records from {TRAIN_FILE}")
print(f"Columns: {dataset.column_names}")
print(f"Sample record:\n{json.dumps(dataset[0], indent=2, default=str)[:1000]}")

# System prompt that grounds the model in your domain
SYSTEM_PROMPT = """You are an SCBE-AETHERMOORE governance-aware coding assistant. You understand:
- The Six Sacred Tongues (KO/AV/RU/CA/UM/DR) and their golden-ratio weights
- Poincaré ball embeddings and hyperbolic geometry for AI safety boundaries
- The 14-layer SCBE pipeline architecture
- The harmonic wall function H(d,R) = R^(d²)
- TypeScript, Python, GDScript (Godot 4), and cryptographic implementations
- LatticeGate governance decisions: ALLOW / ATTENUATE / COLLAPSE

You write clean, well-documented code and explain your reasoning clearly."""


# ── Format detection and conversion ─────────────────────────────────────────
# Your dataset may use one of several SFT formats. This handles the common ones.


def detect_and_format(example):
    """
    Convert whatever format the dataset uses into Qwen2.5 chat template.

    Supported input formats:
      A) {"messages": [{"role": "user", "content": ...}, {"role": "assistant", "content": ...}]}
      B) {"instruction": "...", "output": "..."}
      C) {"instruction": "...", "input": "...", "output": "..."}
      D) {"prompt": "...", "completion": "..."}
      E) {"question": "...", "answer": "..."}
      F) {"text": "..."} (pre-formatted)
    """
    # Format A: Already in messages format
    if "messages" in example and isinstance(example["messages"], list):
        messages = example["messages"]
        # Ensure system message exists
        if not any(m.get("role") == "system" for m in messages):
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        return {"text": text}

    # Format B/C: Instruction-output
    if "instruction" in example:
        user_content = example["instruction"]
        if example.get("input"):
            user_content += f"\n\n{example['input']}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": example.get("output", example.get("response", ""))},
        ]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        return {"text": text}

    # Format D: Prompt-completion
    if "prompt" in example:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": example["prompt"]},
            {"role": "assistant", "content": example.get("completion", example.get("response", ""))},
        ]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        return {"text": text}

    # Format E: Question-answer
    if "question" in example:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": example["question"]},
            {"role": "assistant", "content": example.get("answer", "")},
        ]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        return {"text": text}

    # Format F: Pre-formatted text
    if "text" in example:
        return {"text": example["text"]}

    raise ValueError(f"Unknown format. Columns: {list(example.keys())}")


# Apply formatting
dataset = dataset.map(detect_and_format, remove_columns=dataset.column_names)

print(f"\nFormatted sample (first 500 chars):\n{dataset[0]['text'][:500]}")

# CELL 5: Train

from trl import SFTTrainer
from transformers import TrainingArguments

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    args=TrainingArguments(
        # Output
        output_dir="./output",
        report_to="none",  # No wandb needed
        # Schedule
        num_train_epochs=NUM_EPOCHS,
        max_steps=MAX_STEPS,
        warmup_ratio=WARMUP_RATIO,
        # Batch
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        # Optimizer
        learning_rate=LEARNING_RATE,
        optim="adamw_8bit",  # 8-bit Adam saves VRAM
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        # Precision
        fp16=not model.config.torch_dtype == "bfloat16",
        bf16=model.config.torch_dtype == "bfloat16",
        # Logging
        logging_steps=25,
        save_strategy="steps",
        save_steps=500,
        save_total_limit=2,
        # Performance
        gradient_checkpointing=True,
        dataloader_num_workers=2,
        seed=42,
    ),
    max_seq_length=MAX_SEQ_LENGTH,
    dataset_text_field="text",
    packing=True,  # Unsloth packing: ~2x throughput
)

# Show estimated training time
gpu_stats = trainer.accelerator.state
print(f"\nDevice: {trainer.accelerator.device}")
print(f"Effective batch size: {BATCH_SIZE * GRAD_ACCUM}")
est_steps = trainer.state.max_steps if MAX_STEPS > 0 else "~" + str(len(dataset) // (BATCH_SIZE * GRAD_ACCUM))
print(f"Total optimization steps: {est_steps}")
print("\nStarting training...")

trainer_stats = trainer.train()

print("\nTraining complete!")
print(f"  Total steps: {trainer_stats.global_step}")
print(f"  Training loss: {trainer_stats.training_loss:.4f}")
print(f"  Runtime: {trainer_stats.metrics['train_runtime'] / 60:.1f} minutes")

# CELL 6: Quick eval

# Smoke-test the model with domain-specific prompts
FastLanguageModel.for_inference(model)

test_prompts = [
    "Write a Python function that computes the Davis Security Score "
    "using H(d,R) = R^(d²) for a given dimension d and radius R.",
    "Explain how the Six Sacred Tongues map to the 21-dimensional " "state manifold in SCBE-AETHERMOORE.",
    "Write a TypeScript function that implements a PhaseTunnelGate check for an AI agent's intent vector.",
    "Create a GDScript function for Godot 4 that visualizes Poincaré ball embeddings as a 2D projection.",
]

for prompt in test_prompts:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    inputs = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt").to(
        model.device
    )

    outputs = model.generate(
        input_ids=inputs,
        max_new_tokens=512,
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
    )

    response = tokenizer.decode(outputs[0][inputs.shape[-1] :], skip_special_tokens=True)
    print(f"\n{'='*60}")
    print(f"PROMPT: {prompt[:80]}...")
    print(f"{'='*60}")
    print(response[:500])
    print()

# CELL 7: Save LoRA adapter to HuggingFace

model.save_pretrained_merged(
    "output/merged_16bit",
    tokenizer,
    save_method="merged_16bit",
)

# Push LoRA adapter (small, fast upload)
model.push_to_hub(OUTPUT_REPO, token=HF_TOKEN)
tokenizer.push_to_hub(OUTPUT_REPO, token=HF_TOKEN)
print(f"LoRA adapter pushed to: https://huggingface.co/{OUTPUT_REPO}")

# CELL 8: Export GGUF for Ollama

# This converts the merged model to GGUF Q4_K_M format
# and uploads it to HuggingFace for direct Ollama use.

model.save_pretrained_gguf(
    "output/gguf",
    tokenizer,
    quantization_method="q4_k_m",  # Best quality/size tradeoff
)

# Push GGUF to HuggingFace
from huggingface_hub import HfApi

api = HfApi(token=HF_TOKEN)

# Create the GGUF repo if it doesn't exist
api.create_repo(GGUF_REPO, exist_ok=True)

# Upload the GGUF file
import glob

gguf_files = glob.glob("output/gguf/*.gguf")
for f in gguf_files:
    api.upload_file(
        path_or_fileobj=f,
        path_in_repo=os.path.basename(f),
        repo_id=GGUF_REPO,
    )
    print(f"Uploaded: {f} → {GGUF_REPO}")

print(f"\nGGUF model pushed to: https://huggingface.co/{GGUF_REPO}")

# CELL 9: Create Ollama Modelfile

# Generate the Modelfile for loading in Ollama
modelfile_content = """# SCBE-AETHERMOORE Coder - Ollama Modelfile
# Usage: ollama create scbe-coder -f Modelfile

FROM ./unsloth.Q4_K_M.gguf

SYSTEM \"\"\"You are an SCBE-AETHERMOORE governance-aware coding assistant. You understand:
- The Six Sacred Tongues (KO/AV/RU/CA/UM/DR) and their golden-ratio weights
- Poincaré ball embeddings and hyperbolic geometry for AI safety boundaries
- The 14-layer SCBE pipeline architecture
- The harmonic wall function H(d,R) = R^(d²)
- TypeScript, Python, GDScript (Godot 4), and cryptographic implementations
- LatticeGate governance decisions: ALLOW / ATTENUATE / COLLAPSE

You write clean, well-documented code and explain your reasoning clearly.\"\"\"

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
PARAMETER stop <|im_end|>
PARAMETER stop <|endoftext|>
"""

with open("output/gguf/Modelfile", "w") as f:
    f.write(modelfile_content)

# Upload Modelfile too
api.upload_file(
    path_or_fileobj="output/gguf/Modelfile",
    path_in_repo="Modelfile",
    repo_id=GGUF_REPO,
)

print("Modelfile uploaded!")
print(f"""
╔══════════════════════════════════════════════════════════════╗
║  DONE! Your SCBE-Coder model is ready.                      ║
║                                                              ║
║  To use locally:                                             ║
║                                                              ║
║  1. Download the GGUF:                                       ║
║     huggingface-cli download {GGUF_REPO}                     ║
║                                                              ║
║  2. Create Ollama model:                                     ║
║     ollama create scbe-coder -f Modelfile                    ║
║                                                              ║
║  3. Run:                                                     ║
║     ollama run scbe-coder                                    ║
║                                                              ║
║  4. Or connect to VS Code via Continue.dev:                  ║
║     Set model to "scbe-coder" in Continue config             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")

# CELL 10: Optional — Also export Q5_K_M for quality comparison

# Uncomment to also export a higher-quality quantization:
#
# model.save_pretrained_gguf(
#     "output/gguf_q5",
#     tokenizer,
#     quantization_method="q5_k_m",
# )
#
# gguf_files_q5 = glob.glob("output/gguf_q5/*.gguf")
# for f in gguf_files_q5:
#     api.upload_file(
#         path_or_fileobj=f,
#         path_in_repo=os.path.basename(f),
#         repo_id=GGUF_REPO,
#     )

# NOTES
#
# TRAINING DATA FORMAT:
#   If your JSONL uses a format not covered by detect_and_format(),
#   print dataset[0] and adjust the function. The most common SCBE format
#   from your other repos appears to be {"instruction": ..., "output": ...}.
#
# MEMORY ISSUES:
#   If you get OOM on T4, reduce in this order:
#     1. MAX_SEQ_LENGTH: 4096 → 2048
#     2. BATCH_SIZE: 2 → 1
#     3. LORA_RANK: 32 → 16
#     4. Switch to polly_training_merged.jsonl (116K, smaller)
#
# EVALUATION:
#   After training, run the model through your eval_polly_stack.json
#   (47 benchmark tasks) to measure improvement over base Qwen2.5-Coder.
#   Also test on HumanEval via bigcode-evaluation-harness on Colab.
#
# FULL 233K TRAINING:
#   Change TRAIN_FILE to "multiview_sft.jsonl" for the full L0-L3 stack.
#   This adds substrate/coordination/orientation tasks that help the model
#   understand the governance pipeline, not just generate code.
#   Expect ~4-5 hours on Kaggle dual T4.
#
# MERGE EXPERIMENT (after this works):
#   Once you have scbe-coder-qwen-7b, you can DARE-TIES merge it with
#   DeepSeek-R1-Distill-Qwen-7B for enhanced mathematical reasoning.
#   Both share the Qwen2.5 architecture, making them merge-compatible.
#
################################################################################
