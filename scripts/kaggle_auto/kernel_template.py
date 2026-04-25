#!/usr/bin/env python3
"""Auto-generated Kaggle kernel — SCBE Polly Training.
Config is injected via the KERNEL_CONFIG dict at the top."""

import subprocess, sys, json, os

# Detect GPU compute capability and install matching PyTorch
# P100 = sm_60, T4 = sm_75, A100 = sm_80
def ensure_cuda_compat():
    try:
        import torch
        if not torch.cuda.is_available():
            return
        cap = torch.cuda.get_device_capability(0)
        name = torch.cuda.get_device_name(0)
        print(f"GPU: {name}, sm_{cap[0]}{cap[1]}")

        # Test if CUDA ops actually work
        try:
            torch.zeros(1).cuda()
            print("CUDA ops OK - no reinstall needed")
            return
        except RuntimeError as exc:
            print(f"CUDA ops probe failed: {exc}")

        # sm_60 (P100): needs PyTorch with cu118 (last version supporting sm_60)
        if cap[0] < 7:
            print(f"sm_{cap[0]}{cap[1]} not supported by current torch — reinstalling with cu118 (supports sm_60+)...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "torch==2.1.2", "torchvision", "torchaudio",
                "--index-url", "https://download.pytorch.org/whl/cu118"],
                check=True)
            print("Reinstalled torch 2.1.2+cu118 — P100 now supported")
        else:
            print(f"sm_{cap[0]}{cap[1]} should work — reinstalling latest cu121...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "torch", "--index-url", "https://download.pytorch.org/whl/cu121"],
                check=True)
    except ImportError as exc:
        print(f"torch import unavailable during CUDA compatibility check: {exc}")

ensure_cuda_compat()

subprocess.run([sys.executable, "-m", "pip", "install", "-q",
    "transformers>=4.49", "peft>=0.14", "trl>=0.19",
    "bitsandbytes>=0.45", "accelerate>=1.3", "datasets>=3.3",
    "huggingface_hub"], check=True)

import torch
from datasets import Dataset, load_dataset
from huggingface_hub import login
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer
from pathlib import Path

# ==== INJECTED CONFIG (replaced by launch.py) ====
KERNEL_CONFIG = "__INJECT_CONFIG_HERE__"
# ==================================================

CFG = json.loads(KERNEL_CONFIG) if isinstance(KERNEL_CONFIG, str) else KERNEL_CONFIG
BASE_MODEL = CFG["base_model"]
HF_REPO = CFG["hf_repo"]
ROUND = CFG["round"]
FILE_LIST = CFG["files"]
OUTPUT_DIR = f"/kaggle/working/polly-{ROUND}"
EPOCHS = CFG["epochs"]
BATCH_SIZE = CFG["batch_size"]
GRAD_ACCUM = CFG["grad_accum"]
MAX_LEN = CFG["max_length"]
HF_DATASET_REPO = CFG.get("hf_dataset_repo", "issdandavis/scbe-aethermoore-training-data")
MAX_STEPS = int(CFG.get("max_steps", -1))
LEARNING_RATE = float(CFG.get("learning_rate", 2e-4))
MAX_RECORDS = int(CFG.get("max_records", 10000))
LORA_R = int(CFG.get("lora_r", 16))
LORA_ALPHA = int(CFG.get("lora_alpha", 32))
LORA_DROPOUT = float(CFG.get("lora_dropout", 0.05))

# ---- Auth ----
PUSH = False
try:
    from kaggle_secrets import UserSecretsClient
    hf_token = UserSecretsClient().get_secret("hugging face")
    login(token=hf_token)
    print("HF authenticated via Kaggle secrets")
    PUSH = True
except ImportError:
    pass  # Not on Kaggle
except (KeyError, Exception) as e:
    print(f"Kaggle secret lookup failed: {e}")

if not PUSH:
    hf_token = os.environ.get("HF_TOKEN", "")
    if hf_token:
        login(token=hf_token)
        print("HF authenticated via env var")
        PUSH = True
    else:
        print("No HF auth -- local save only")


# ---- Data Loading ----
def load_data():
    records = []
    kaggle_dir = Path("/kaggle/input/scbe-polly-training-data")

    files = FILE_LIST
    if files == "__ALL__":
        if kaggle_dir.exists():
            files = sorted(f.name for f in kaggle_dir.glob("*.jsonl"))
        else:
            print("Cannot discover all files without Kaggle dataset input")
            sys.exit(1)

    for name in files:
        path = kaggle_dir / name
        if not path.exists():
            try:
                from huggingface_hub import hf_hub_download
                last_hf_error = None
                for prefix in [f"sft/{name}", name, f"training-data/sft/{name}"]:
                    try:
                        path = Path(hf_hub_download(
                            repo_id=HF_DATASET_REPO,
                            filename=prefix,
                            repo_type="dataset",
                        ))
                        break
                    except (OSError, RuntimeError, ValueError) as exc:
                        last_hf_error = exc
                        continue
                else:
                    print(f"  SKIP {name} (not found locally or on HF: {last_hf_error})")
                    continue
            except (ImportError, OSError, RuntimeError, ValueError) as exc:
                print(f"  SKIP {name} ({exc})")
                continue

        if not path.exists():
            continue

        raw = path.read_text(encoding="utf-8").strip()
        if not raw or raw.startswith("version https://git-lfs"):
            print(f"  SKIP {name} (empty/LFS)")
            continue

        try:
            ds = load_dataset("json", data_files=str(path), split="train")
        except Exception as e:
            print(f"  SKIP {name} ({e})")
            continue

        count = 0
        cols = ds.column_names
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
        print("ERROR: No data loaded!")
        sys.exit(1)

    # Cap dataset size to prevent OOM and timeout on CPU fallback
    import random as _random
    _use_gpu = torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 7
    _max_records = MAX_RECORDS if _use_gpu else min(MAX_RECORDS, 200)  # CPU: tiny run, finishes in ~30min
    if len(records) > _max_records:
        _random.seed(42)
        records = _random.sample(records, _max_records)
        print(f"Sampled {_max_records} records ({'GPU' if _use_gpu else 'CPU-tiny'} mode)")

    return Dataset.from_list(records)


# ---- Heartbeat helper ----
import time as _time
_start_ts = _time.time()

def write_status(phase: str, extra: dict | None = None):
    """Write /kaggle/working/STATUS.json so `kaggle kernels output` can see progress."""
    import json as _json
    payload = {
        "round": ROUND,
        "phase": phase,
        "elapsed_s": round(_time.time() - _start_ts),
        "base_model": BASE_MODEL,
        **(extra or {}),
    }
    with open("/kaggle/working/STATUS.json", "w") as _f:
        _json.dump(payload, _f)

# ---- Train ----
print(f"=== POLLY KAGGLE: {ROUND} ===")
write_status("starting")
if torch.cuda.is_available():
    props = torch.cuda.get_device_properties(0)
    vram = getattr(props, 'total_memory', getattr(props, 'total_mem', 0)) / 1024**3
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {vram:.1f} GB")
    print(f"Compute: {props.major}.{props.minor}")
    if props.major < 7:
        print("WARNING: GPU compute < 7.0 — may have compatibility issues")
        print("Falling back to CPU-safe torch operations")
else:
    print("WARNING: No GPU")

write_status("loading_data")
dataset = load_data()
write_status("data_loaded", {"num_records": len(dataset)})

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

has_bf16 = torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 8
compute_cap = torch.cuda.get_device_capability(0) if torch.cuda.is_available() else (0, 0)
compute_dtype = torch.bfloat16 if has_bf16 else torch.float16

# Kaggle randomly assigns P100 (sm_60) or T4 (sm_75).
# P100's PyTorch build lacks sm_60 kernels — CUDA ops segfault.
# For sm_60: fall back to CPU (0.5B model trains fine on CPU with small datasets).
# For sm_70+: use 4-bit NF4 quantization via bitsandbytes.
use_gpu = torch.cuda.is_available() and compute_cap[0] >= 7

if use_gpu:
    print("Using 4-bit NF4 quantization on GPU (sm_70+)")
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True,
    )
    load_kwargs = {"quantization_config": quant_config, "torch_dtype": compute_dtype, "device_map": "auto"}
else:
    if torch.cuda.is_available():
        print(f"GPU sm_{compute_cap[0]}{compute_cap[1]} not supported — falling back to CPU tiny-run (200 records, 1 epoch)")
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        torch.cuda.is_available = lambda: False
    else:
        print("No GPU — CPU tiny-run (200 records, 1 epoch)")
    # CPU tiny-run: override epochs to 1, dataset already capped at 200
    EPOCHS = 1
    quant_config = None
    compute_dtype = torch.float32
    load_kwargs = {"torch_dtype": torch.float32, "device_map": "cpu"}

write_status("loading_model")
model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, **load_kwargs)

if quant_config is not None:
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

model = get_peft_model(model, LoraConfig(
    r=LORA_R, lora_alpha=LORA_ALPHA, lora_dropout=LORA_DROPOUT, bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
))
model.print_trainable_parameters()

# Adjust training params based on device
effective_batch = BATCH_SIZE
use_fp16 = False
use_bf16 = False
use_grad_ckpt = True

if not use_gpu:
    # CPU mode: smaller batch, no mixed precision, no gradient checkpointing
    effective_batch = 2
    use_grad_ckpt = False
    print(f"CPU mode: batch_size={effective_batch}, fp32, no gradient checkpointing")
else:
    use_fp16 = not has_bf16
    use_bf16 = has_bf16

trainer = SFTTrainer(
    model=model, processing_class=tokenizer, train_dataset=dataset,
    args=SFTConfig(
        output_dir=OUTPUT_DIR,
        hub_model_id=HF_REPO,
        push_to_hub=PUSH,
        learning_rate=LEARNING_RATE,
        per_device_train_batch_size=effective_batch,
        gradient_accumulation_steps=GRAD_ACCUM,
        num_train_epochs=EPOCHS,
        max_steps=MAX_STEPS,
        warmup_ratio=0.03,
        weight_decay=0.01,
        max_grad_norm=0.3,
        lr_scheduler_type="cosine",
        logging_steps=10,
        save_strategy="epoch",
        save_total_limit=2,
        max_length=MAX_LEN,
        packing=False,
        dataset_num_proc=1,
        report_to="none",
        fp16=use_fp16,
        bf16=use_bf16,
        optim="adamw_torch",
        gradient_checkpointing=use_grad_ckpt,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    ),
)

write_status("training")
trainer.train()
write_status("saving")
trainer.save_model()
print(f"\nSaved to {OUTPUT_DIR}")

if PUSH:
    trainer.push_to_hub()
    print(f"Pushed to {HF_REPO}")

with open("/kaggle/working/DONE.json", "w") as f:
    json.dump({"round": ROUND, "status": "complete", "hf_repo": HF_REPO, "push": PUSH}, f)

print("=== TRAINING COMPLETE ===")
