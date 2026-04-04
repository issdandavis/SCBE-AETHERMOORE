#!/usr/bin/env python3
"""
SCBE Round 3 A/B Training — Balanced Layer Dataset
===================================================
Upload this to Colab, upload the two JSONL files, click Run All.

Files needed (upload when prompted):
  - round3_baseline_l3.jsonl     (1000 records, flat)
  - round3_multiview_l0l3.jsonl  (1000 records, tongue/null/layer tagged)

What it does:
  1. Installs deps (transformers, trl, peft, bitsandbytes)
  2. Loads Qwen2.5-0.5B-Instruct as base model
  3. Trains baseline (flat text) for 150 steps
  4. Trains multiview (with tongue/layer context) for 150 steps
  5. Compares final loss
  6. Saves chart to round3_loss.png

Expected result: multiview beats baseline by 15-20%
(Round 2 was 7.9% with 83% L0 data. Round 3 has perfect 25/25/25/25 balance.)
"""

# ── Cell 1: Install dependencies ──
import subprocess
import sys

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])

print("Installing dependencies...")
install("transformers>=4.45.0")
install("trl>=0.12.0")
install("peft>=0.13.0")
install("bitsandbytes>=0.44.0")
install("datasets")
install("accelerate")
install("matplotlib")
print("Done.")

# ── Cell 2: Upload data files ──
import os

# Check if running in Colab
IN_COLAB = "COLAB_GPU" in os.environ or os.path.exists("/content")

if IN_COLAB:
    from google.colab import files
    print("Upload round3_baseline_l3.jsonl and round3_multiview_l0l3.jsonl")
    uploaded = files.upload()
    BASELINE_FILE = "round3_baseline_l3.jsonl"
    MULTIVIEW_FILE = "round3_multiview_l0l3.jsonl"
else:
    # Local paths
    BASELINE_FILE = "training-data/sft/round3_baseline_l3.jsonl"
    MULTIVIEW_FILE = "training-data/sft/round3_multiview_l0l3.jsonl"

print(f"Baseline: {BASELINE_FILE}")
print(f"Multiview: {MULTIVIEW_FILE}")

# ── Cell 3: Load and format data ──
import json

def load_jsonl(path):
    records = []
    for line in open(path, encoding="utf-8"):
        try:
            r = json.loads(line)
            if r.get("instruction") and r.get("output"):
                text = f"<|im_start|>user\n{r['instruction']}<|im_end|>\n<|im_start|>assistant\n{r['output']}<|im_end|>"
                records.append({"text": text})
        except:
            continue
    return records

baseline_data = load_jsonl(BASELINE_FILE)
multiview_data = load_jsonl(MULTIVIEW_FILE)
print(f"Baseline: {len(baseline_data)} records")
print(f"Multiview: {len(multiview_data)} records")

# ── Cell 4: Setup model and training ──
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig
from datasets import Dataset
import matplotlib.pyplot as plt
import gc

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
STEPS = 150
BATCH = 2
GRAD_ACCUM = 8
LR = 2e-4
MAX_SEQ = 1024
SEED = 42

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
)

lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    task_type="CAUSAL_LM",
)


def train_run(name, data, output_dir):
    """Train one run and return loss history."""
    print(f"\n{'='*60}")
    print(f"  Training: {name}")
    print(f"  Records: {len(data)}, Steps: {STEPS}")
    print(f"{'='*60}")

    # Load fresh model each run
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
    )
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, lora_config)

    ds = Dataset.from_list(data)

    args = SFTConfig(
        output_dir=output_dir,
        max_steps=STEPS,
        per_device_train_batch_size=BATCH,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LR,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        fp16=True,
        logging_steps=5,
        save_steps=9999,  # don't save checkpoints
        optim="paged_adamw_8bit",
        max_seq_length=MAX_SEQ,
        report_to="none",
        seed=SEED,
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=ds,
        args=args,
    )

    result = trainer.train()

    # Extract loss history
    losses = [log["loss"] for log in trainer.state.log_history if "loss" in log]
    steps = [log["step"] for log in trainer.state.log_history if "loss" in log]
    final_loss = result.training_loss

    print(f"  Final loss: {final_loss:.4f}")

    # Cleanup
    del model, trainer, tokenizer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return {"losses": losses, "steps": steps, "final_loss": final_loss}


# ── Cell 5: Run both trainings ──
print("Starting A/B comparison...")
print(f"Model: {MODEL_NAME}")
print(f"Steps: {STEPS}, Batch: {BATCH}x{GRAD_ACCUM}, LR: {LR}")

baseline_result = train_run("Baseline (L3 only)", baseline_data, "/tmp/round3_baseline")
multiview_result = train_run("Multiview (L0-L3)", multiview_data, "/tmp/round3_multiview")

# ── Cell 6: Results ──
improvement = (baseline_result["final_loss"] - multiview_result["final_loss"]) / baseline_result["final_loss"] * 100

print(f"\n{'='*60}")
print(f"  SCBE ROUND 3 RESULTS")
print(f"{'='*60}")
print(f"  Baseline (L3 only):  {baseline_result['final_loss']:.4f}")
print(f"  Multiview (L0-L3):   {multiview_result['final_loss']:.4f}")
print(f"  Improvement:         {improvement:.1f}%")
print(f"{'='*60}")
print(f"  Previous results:")
print(f"    Chat:    14.0%")
print(f"    Code:    31.0%")
print(f"    Round 2: 7.9% (83% L0, unbalanced)")
print(f"    Round 3: {improvement:.1f}% (25% per layer, balanced)")
print(f"{'='*60}")

# ── Cell 7: Plot ──
plt.figure(figsize=(10, 5))
plt.plot(baseline_result["steps"], baseline_result["losses"],
         label=f"Baseline ({baseline_result['final_loss']:.4f})", color="blue", linewidth=2)
plt.plot(multiview_result["steps"], multiview_result["losses"],
         label=f"Multiview ({multiview_result['final_loss']:.4f})", color="orange", linewidth=2)
plt.xlabel("Step")
plt.ylabel("Loss")
plt.title(f"SCBE Round 3: {improvement:.1f}% improvement with balanced L0-L3 + tongue tags")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("round3_loss.png", dpi=150)
plt.show()
print(f"Chart saved to round3_loss.png")

# ── Cell 8: Save results ──
results = {
    "experiment": "SCBE Round 3 A/B Training",
    "baseline_loss": baseline_result["final_loss"],
    "multiview_loss": multiview_result["final_loss"],
    "improvement_pct": round(improvement, 1),
    "model": MODEL_NAME,
    "method": f"4-bit QLoRA, {STEPS} steps, T4 GPU",
    "dataset": {
        "records": len(baseline_data),
        "balance": "250 per layer (L0/L1/L2/L3)",
        "features": "tongue, tongues_null, layer, governance, tri-braid, trichromatic, HYDRA coordination, adversarial storms, ray tracing"
    },
    "previous": {
        "chat": 14.0,
        "code": 31.0,
        "round2_unbalanced": 7.9
    }
}

with open("round3_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"Results saved to round3_results.json")

# Download files if in Colab
if IN_COLAB:
    files.download("round3_loss.png")
    files.download("round3_results.json")
