#!/usr/bin/env python3
"""Auto-generated Kaggle kernel - SCBE Polly Training.
Config is injected via the KERNEL_CONFIG dict at the top."""

import subprocess, sys, json, os

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
            print(f"sm_{cap[0]}{cap[1]} not supported by current torch - reinstalling with cu118 (supports sm_60+)...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "torch==2.1.2", "torchvision", "torchaudio",
                "--index-url", "https://download.pytorch.org/whl/cu118"],
                check=True)
            print("Reinstalled torch 2.1.2+cu118 - P100 now supported")
        else:
            print(f"sm_{cap[0]}{cap[1]} should work - reinstalling latest cu121...")
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

import re
import torch
from datasets import Dataset, load_dataset
from huggingface_hub import login
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    EarlyStoppingCallback,
    TrainerCallback,
)
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
EVAL_FILE_LIST = CFG.get("eval_files", [])
OUTPUT_DIR = f"/kaggle/working/polly-{ROUND}"
EPOCHS = CFG["epochs"]
BATCH_SIZE = CFG["batch_size"]
GRAD_ACCUM = CFG["grad_accum"]
MAX_LEN = CFG["max_length"]
HF_DATASET_REPO = CFG.get("hf_dataset_repo", "issdandavis/scbe-aethermoore-training-data")
KAGGLE_DATASET_SLUG = CFG.get("kaggle_dataset", "issacizrealdavis/scbe-polly-training-data").split("/")[-1]
MAX_STEPS = int(CFG.get("max_steps", -1))
LEARNING_RATE = float(CFG.get("learning_rate", 2e-4))
MAX_RECORDS = int(CFG.get("max_records", 10000))
LORA_R = int(CFG.get("lora_r", 16))
LORA_ALPHA = int(CFG.get("lora_alpha", 32))
LORA_DROPOUT = float(CFG.get("lora_dropout", 0.05))
EARLY_STOPPING_PATIENCE = int(CFG.get("early_stopping_patience", 3))
EARLY_STOPPING_THRESHOLD = float(CFG.get("early_stopping_threshold", 0.0))
EVAL_STEPS = int(CFG.get("eval_steps", 30))
SAVE_STEPS = int(CFG.get("save_steps", EVAL_STEPS))

# ---- v5 contract-aware levers (Lever B-1 / B-3 / repair-lane sampler) ----
SELECTOR_TOKEN_WEIGHT = float(CFG.get("selector_token_weight", 1.0))
WEIGHTED_CE_TOKEN_IDS = list(CFG.get("weighted_ce_token_ids", []))
CONTRACT_EVAL_ENABLED = bool(CFG.get("contract_eval_enabled", False))
CONTRACT_EVAL_STEPS = int(CFG.get("contract_eval_steps", 50))
CONTRACT_EVAL_SLICE_N = int(CFG.get("contract_eval_slice_n", 25))
CONTRACT_PATIENCE = int(CFG.get("contract_patience", 2))
CONTRACT_MIN_DELTA = float(CFG.get("contract_min_delta", 0.005))
CONTRACT_EVAL_MAX_NEW_TOKENS = int(CFG.get("contract_eval_max_new_tokens", 128))
REPAIR_LANE_WEIGHT = float(CFG.get("repair_lane_weight", 1.0))
REPAIR_LANE_FILES = set(CFG.get("repair_lane_files", []))
REQUIRE_GPU = bool(CFG.get("require_gpu", False))

V5_WEIGHTED_CE_ACTIVE = bool(WEIGHTED_CE_TOKEN_IDS) and SELECTOR_TOKEN_WEIGHT != 1.0
V5_REPAIR_SAMPLER_ACTIVE = bool(REPAIR_LANE_FILES) and REPAIR_LANE_WEIGHT != 1.0
V5_FEATURES_ENABLED = V5_WEIGHTED_CE_ACTIVE or V5_REPAIR_SAMPLER_ACTIVE or CONTRACT_EVAL_ENABLED
print(
    f"v5 levers: weighted_ce={V5_WEIGHTED_CE_ACTIVE} (n_ids={len(WEIGHTED_CE_TOKEN_IDS)}, "
    f"w={SELECTOR_TOKEN_WEIGHT}) | repair_sampler={V5_REPAIR_SAMPLER_ACTIVE} "
    f"(n_files={len(REPAIR_LANE_FILES)}, w={REPAIR_LANE_WEIGHT}) | "
    f"contract_eval={CONTRACT_EVAL_ENABLED} (every={CONTRACT_EVAL_STEPS}, n={CONTRACT_EVAL_SLICE_N})"
)

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
        print("No HF auth - local save only")


# ---- Data Loading ----
def _normalize_records_from_files(files, split_name):
    records = []
    lane_weights = []  # parallel to records: REPAIR_LANE_WEIGHT for repair files, 1.0 otherwise
    kaggle_dir = Path("/kaggle/input") / KAGGLE_DATASET_SLUG

    if files == "__ALL__":
        if kaggle_dir.exists():
            files = sorted(f.name for f in kaggle_dir.glob("*.jsonl"))
        else:
            print("Cannot discover all files without Kaggle dataset input")
            sys.exit(1)

    for name in files:
        is_repair = name in REPAIR_LANE_FILES
        per_file_weight = REPAIR_LANE_WEIGHT if is_repair else 1.0
        path = kaggle_dir / name
        if not path.exists() and Path("/kaggle/input").exists():
            matches = list(Path("/kaggle/input").glob(f"**/{name}"))
            if matches:
                path = matches[0]
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
                lane_weights.append(per_file_weight)
                count += 1
        print(f"  LOAD {split_name} {name}: {count} records (lane_w={per_file_weight})")

    return records, lane_weights


def load_data():
    records, lane_weights = _normalize_records_from_files(FILE_LIST, "train")

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
        kept_idx = _random.sample(range(len(records)), _max_records)
        records = [records[i] for i in kept_idx]
        lane_weights = [lane_weights[i] for i in kept_idx]
        print(f"Sampled {_max_records} records ({'GPU' if _use_gpu else 'CPU-tiny'} mode)")

    repair_n = sum(1 for w in lane_weights if w != 1.0)
    if V5_REPAIR_SAMPLER_ACTIVE:
        print(f"Repair-lane records: {repair_n}/{len(records)} (weight={REPAIR_LANE_WEIGHT})")

    return Dataset.from_list(records), lane_weights


def load_eval_data():
    if not EVAL_FILE_LIST:
        return None
    records, _ = _normalize_records_from_files(EVAL_FILE_LIST, "eval")
    print(f"\nTotal: {len(records)} eval records")
    if not records:
        print("WARNING: Eval files configured but no eval records loaded")
        return None
    return Dataset.from_list(records)


# ---- v5 trainer subclass + contract-eval callback ----
_SELECTOR_RE = re.compile(r"well_select\(\s*([A-Z_]+)\s*\)")


class WeightedSFTTrainer(SFTTrainer):
    """SFTTrainer with optional B-1 weighted CE on selector tokens and repair-lane sampler."""

    def __init__(self, *args, upweight_token_ids=None, selector_weight=1.0,
                 sample_weights=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.upweight_token_ids = list(upweight_token_ids or [])
        self.selector_weight = float(selector_weight)
        self.sample_weights = list(sample_weights) if sample_weights else None
        self._upweight_cache = None  # (device, tensor)

    def _get_upweight_tensor(self, device):
        if self._upweight_cache is None or self._upweight_cache[0] != device:
            self._upweight_cache = (
                device,
                torch.tensor(self.upweight_token_ids, device=device, dtype=torch.long),
            )
        return self._upweight_cache[1]

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        if not self.upweight_token_ids or self.selector_weight == 1.0:
            return super().compute_loss(
                model, inputs, return_outputs=return_outputs,
                num_items_in_batch=num_items_in_batch,
            )

        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits

        # Causal LM shift: predict token i+1 from token i
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()

        flat_logits = shift_logits.view(-1, shift_logits.size(-1))
        flat_labels = shift_labels.view(-1)

        per_token_loss = torch.nn.functional.cross_entropy(
            flat_logits, flat_labels, reduction="none", ignore_index=-100,
        )

        upweight_tensor = self._get_upweight_tensor(flat_labels.device)
        upweight_mask = torch.isin(flat_labels, upweight_tensor)
        weights = torch.where(
            upweight_mask,
            torch.full_like(per_token_loss, self.selector_weight),
            torch.ones_like(per_token_loss),
        )
        weighted = per_token_loss * weights

        valid_mask = flat_labels.ne(-100)
        denom = valid_mask.sum().clamp(min=1).to(weighted.dtype)
        loss = (weighted * valid_mask.to(weighted.dtype)).sum() / denom

        return (loss, outputs) if return_outputs else loss

    def _get_train_sampler(self, *args, **kwargs):
        if not self.sample_weights:
            return super()._get_train_sampler(*args, **kwargs)
        weights = torch.tensor(self.sample_weights, dtype=torch.double)
        return torch.utils.data.WeightedRandomSampler(
            weights=weights,
            num_samples=len(weights),
            replacement=True,
        )


class ContractEvalCallback(TrainerCallback):
    """B-3: in-training executable-accuracy gate over a fixed eval slice."""

    def __init__(self, tokenizer, eval_dataset, eval_steps, slice_n,
                 patience, min_delta, max_new_tokens):
        self.tokenizer = tokenizer
        self.eval_steps = max(int(eval_steps), 1)
        self.patience = int(patience)
        self.min_delta = float(min_delta)
        self.max_new_tokens = int(max_new_tokens)
        self.best_acc = -1.0
        self.no_improve = 0
        self.slice = []
        if eval_dataset is None:
            return
        for rec in eval_dataset:
            if len(self.slice) >= slice_n:
                break
            msgs = rec.get("messages") or []
            user_msg = next(
                (m["content"] for m in msgs if m.get("role") == "user"), None,
            )
            asst_msg = next(
                (m["content"] for m in msgs if m.get("role") == "assistant"), None,
            )
            if not user_msg or not asst_msg:
                continue
            match = _SELECTOR_RE.search(asst_msg)
            if not match:
                continue
            self.slice.append({"user": user_msg, "expected": match.group(1)})
        print(
            f"[contract-eval] callback armed: slice_n={len(self.slice)} "
            f"every={self.eval_steps} patience={self.patience} "
            f"min_delta={self.min_delta} max_new_tokens={self.max_new_tokens}"
        )

    def on_step_end(self, args, state, control, model=None, **kwargs):
        if not self.slice or model is None:
            return control
        if state.global_step <= 0 or state.global_step % self.eval_steps != 0:
            return control

        n_total = 0
        n_correct = 0
        n_unparseable = 0
        n_wrong_well = 0
        was_training = model.training
        model.eval()
        try:
            with torch.no_grad():
                for item in self.slice:
                    n_total += 1
                    prompt = self.tokenizer.apply_chat_template(
                        [{"role": "user", "content": item["user"]}],
                        tokenize=False,
                        add_generation_prompt=True,
                    )
                    inputs = self.tokenizer(
                        prompt,
                        return_tensors="pt",
                        truncation=True,
                        max_length=1024,
                    )
                    inputs = {k: v.to(model.device) for k, v in inputs.items()}
                    out_ids = model.generate(
                        **inputs,
                        max_new_tokens=self.max_new_tokens,
                        do_sample=False,
                        pad_token_id=self.tokenizer.pad_token_id,
                    )
                    gen_ids = out_ids[0][inputs["input_ids"].shape[1]:]
                    text = self.tokenizer.decode(gen_ids, skip_special_tokens=True)
                    match = _SELECTOR_RE.search(text)
                    if not match:
                        n_unparseable += 1
                        continue
                    if match.group(1) == item["expected"]:
                        n_correct += 1
                    else:
                        n_wrong_well += 1
        finally:
            model.train(was_training)

        acc = n_correct / max(n_total, 1)
        log_entry = {
            "step": state.global_step,
            "contract_eval_accuracy": acc,
            "contract_eval_n_correct": n_correct,
            "contract_eval_n_total": n_total,
            "contract_eval_n_unparseable": n_unparseable,
            "contract_eval_n_wrong_well": n_wrong_well,
        }
        if hasattr(state, "log_history"):
            state.log_history.append(log_entry)
        print(
            f"[contract-eval] step={state.global_step} acc={acc:.3f} "
            f"correct={n_correct}/{n_total} unparseable={n_unparseable} "
            f"wrong_well={n_wrong_well}"
        )

        if acc > self.best_acc + self.min_delta:
            self.best_acc = acc
            self.no_improve = 0
        else:
            self.no_improve += 1
            if self.patience > 0 and self.no_improve >= self.patience:
                print(
                    f"[contract-eval] no improvement >= {self.min_delta} for "
                    f"{self.patience} checks - signaling stop"
                )
                control.should_training_stop = True
        return control


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
        print("WARNING: GPU compute < 7.0 - may have compatibility issues")
        print("Falling back to CPU-safe torch operations")
else:
    print("WARNING: No GPU")

write_status("loading_data")
dataset, train_lane_weights = load_data()
eval_dataset = load_eval_data()
write_status("data_loaded", {"num_records": len(dataset), "eval_records": len(eval_dataset) if eval_dataset is not None else 0})

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

has_bf16 = torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 8
compute_cap = torch.cuda.get_device_capability(0) if torch.cuda.is_available() else (0, 0)
compute_dtype = torch.bfloat16 if has_bf16 else torch.float16

# Kaggle randomly assigns P100 (sm_60) or T4 (sm_75).
# P100's PyTorch build lacks sm_60 kernels - CUDA ops segfault.
# For sm_60: fall back to CPU (0.5B model trains fine on CPU with small datasets).
# For sm_70+: use 4-bit NF4 quantization via bitsandbytes.
use_gpu = torch.cuda.is_available() and compute_cap[0] >= 7

# Hard-fail guard: when CFG.require_gpu is True, refuse to silently degrade to
# the CPU tiny-run path. Re-queueing the kernel is cheaper than wasting wall-clock
# on a 200-record / 30-step run that cannot accumulate enough gradient on the
# contract grammar (see bijective-tongue-coder-v2-format-repair RESULT 2026-04-27).
if REQUIRE_GPU and not use_gpu:
    _gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    raise RuntimeError(
        f"REQUIRE_GPU=True but assigned {_gpu_name} (sm_{compute_cap[0]}{compute_cap[1]}); "
        "need T4/A10G/L4 (sm_70+). Re-queue this kernel to retry the GPU lottery."
    )

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
        print(f"GPU sm_{compute_cap[0]}{compute_cap[1]} not supported - falling back to CPU tiny-run (200 records, 1 epoch)")
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        torch.cuda.is_available = lambda: False
    else:
        print("No GPU - CPU tiny-run (200 records, 1 epoch)")
    # CPU tiny-run: override epochs and steps so a bad GPU assignment cannot
    # consume the full Kaggle wall-clock limit.
    EPOCHS = 1
    if MAX_STEPS < 0:
        MAX_STEPS = 30
    else:
        MAX_STEPS = min(MAX_STEPS, 30)
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
    print(f"CPU mode: batch_size={effective_batch}, max_steps={MAX_STEPS}, fp32, no gradient checkpointing")
else:
    use_fp16 = not has_bf16
    use_bf16 = has_bf16

trainer_cls = WeightedSFTTrainer if V5_FEATURES_ENABLED else SFTTrainer
extra_trainer_kwargs = {}
if V5_FEATURES_ENABLED:
    extra_trainer_kwargs["upweight_token_ids"] = (
        WEIGHTED_CE_TOKEN_IDS if V5_WEIGHTED_CE_ACTIVE else []
    )
    extra_trainer_kwargs["selector_weight"] = (
        SELECTOR_TOKEN_WEIGHT if V5_WEIGHTED_CE_ACTIVE else 1.0
    )
    extra_trainer_kwargs["sample_weights"] = (
        train_lane_weights if V5_REPAIR_SAMPLER_ACTIVE else None
    )

trainer = trainer_cls(
    model=model, processing_class=tokenizer, train_dataset=dataset, eval_dataset=eval_dataset,
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
        eval_strategy="steps" if eval_dataset is not None else "no",
        eval_steps=EVAL_STEPS,
        save_strategy="steps" if eval_dataset is not None else "epoch",
        save_steps=SAVE_STEPS if eval_dataset is not None else 500,
        save_total_limit=3,
        load_best_model_at_end=eval_dataset is not None,
        metric_for_best_model="eval_loss" if eval_dataset is not None else None,
        greater_is_better=False if eval_dataset is not None else None,
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
    **extra_trainer_kwargs,
)

if eval_dataset is not None and EARLY_STOPPING_PATIENCE > 0:
    trainer.add_callback(
        EarlyStoppingCallback(
            early_stopping_patience=EARLY_STOPPING_PATIENCE,
            early_stopping_threshold=EARLY_STOPPING_THRESHOLD,
        )
    )
    print(
        f"EarlyStopping armed: patience={EARLY_STOPPING_PATIENCE}, "
        f"threshold={EARLY_STOPPING_THRESHOLD}, monitoring eval_loss"
    )

if CONTRACT_EVAL_ENABLED and eval_dataset is not None:
    trainer.add_callback(
        ContractEvalCallback(
            tokenizer=tokenizer,
            eval_dataset=eval_dataset,
            eval_steps=CONTRACT_EVAL_STEPS,
            slice_n=CONTRACT_EVAL_SLICE_N,
            patience=CONTRACT_PATIENCE,
            min_delta=CONTRACT_MIN_DELTA,
            max_new_tokens=CONTRACT_EVAL_MAX_NEW_TOKENS,
        )
    )
elif CONTRACT_EVAL_ENABLED:
    print("[contract-eval] requested but no eval_dataset - callback not registered")

write_status("training")
train_result = trainer.train()
write_status("saving")
trainer.save_model()
print(f"\nSaved to {OUTPUT_DIR}")

history_payload = {
    "round": ROUND,
    "base_model": BASE_MODEL,
    "hf_repo": HF_REPO,
    "train_records": len(dataset),
    "eval_records": len(eval_dataset) if eval_dataset is not None else 0,
    "best_model_checkpoint": getattr(trainer.state, "best_model_checkpoint", None),
    "best_metric": getattr(trainer.state, "best_metric", None),
    "global_step": getattr(trainer.state, "global_step", None),
    "train_metrics": getattr(train_result, "metrics", {}),
    "log_history": getattr(trainer.state, "log_history", []),
}
with open("/kaggle/working/TRAINING_HISTORY.json", "w", encoding="utf-8") as f:
    json.dump(history_payload, f, indent=2)
print("Wrote TRAINING_HISTORY.json")

if PUSH:
    trainer.push_to_hub()
    print(f"Pushed to {HF_REPO}")

with open("/kaggle/working/DONE.json", "w", encoding="utf-8") as f:
    json.dump(
        {
            "round": ROUND,
            "status": "complete",
            "hf_repo": HF_REPO,
            "push": PUSH,
            "best_model_checkpoint": history_payload["best_model_checkpoint"],
            "best_metric": history_payload["best_metric"],
            "global_step": history_payload["global_step"],
            "train_records": history_payload["train_records"],
            "eval_records": history_payload["eval_records"],
        },
        f,
    )

print("=== TRAINING COMPLETE ===")
