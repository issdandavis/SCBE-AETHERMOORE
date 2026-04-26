#!/usr/bin/env python3
"""
Kaggle Notebook — SmolLM2-360M SCBE Twin Training
====================================================
Copy-paste this into a Kaggle notebook with GPU T4 enabled.

SETUP:
1. Create a Kaggle dataset called "scbe-training-data"
2. Upload these JSONL files to it:
   - phase0_baby_babble_sft.jsonl
   - kids_group_physics_sft.jsonl
   - baby_babble_phase0.jsonl
   - kids_math_games_sft.jsonl
   - tongue_primer_sft.jsonl
   - book_six_tongues_sft.jsonl
   - tongue_curriculum_v2.jsonl
3. Add the dataset to your notebook
4. Enable GPU T4 x2 accelerator
5. Run all cells
"""

# %% [markdown]
# # SCBE Twin Training — SmolLM2-360M-Instruct
# One of Izack's twins. The 360M "outer electron" — knowledge carrier.

# %% Cell 1: Install
# !pip install -q transformers trl peft bitsandbytes datasets accelerate huggingface_hub

# %% Cell 2: Imports & Config
import json
import logging
import time
import torch
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("twin360")

MODEL_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"
OUTPUT_DIR = Path("/kaggle/working/scbe-twin-360m")

# Find data — try Kaggle dataset paths
DATA_CANDIDATES = [
    Path("/kaggle/input/scbe-training-data"),
    Path("/kaggle/input/scbe-training-data/sft"),
    Path("/content/scbe-training-data"),
    Path("training-data/sft"),
]
DATA_ROOT = None
for p in DATA_CANDIDATES:
    if p.exists():
        DATA_ROOT = p
        break
assert DATA_ROOT is not None, f"No data found! Tried: {DATA_CANDIDATES}"
log.info(f"Data root: {DATA_ROOT}")

TRAINING_FILES = [
    "phase0_baby_babble_sft.jsonl",
    "kids_group_physics_sft.jsonl",
    "baby_babble_phase0.jsonl",
    "kids_math_games_sft.jsonl",
    "tongue_primer_sft.jsonl",
    "book_six_tongues_sft.jsonl",
    "tongue_curriculum_v2.jsonl",
]

# %% Cell 3: Load Data
records = []
for fname in TRAINING_FILES:
    fpath = DATA_ROOT / fname
    if not fpath.exists():
        log.warning(f"  Skip: {fname}")
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            msgs = obj.get("messages", [])
            if msgs:
                records.append({"messages": msgs})
    log.info(f"  {fname}: {len(records)} total")

log.info(f"Total records: {len(records)}")

eval_size = min(500, len(records) // 20)
train_records = records[:-eval_size]
eval_records = records[-eval_size:]
log.info(f"Train: {len(train_records)}, Eval: {len(eval_records)}")

# %% Cell 4: Load Model + Tokenizer
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)
model = prepare_model_for_kbit_training(model)

lora_config = LoraConfig(
    r=16, lora_alpha=32, lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    bias="none", task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_config)
trainable, total = model.get_nb_trainable_parameters()
log.info(f"Trainable: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

# %% Cell 5: Prepare Dataset
from datasets import Dataset

def format_record(example):
    text = tokenizer.apply_chat_template(example["messages"], tokenize=False, add_generation_prompt=False)
    return {"text": text}

train_ds = Dataset.from_list(train_records).map(format_record, remove_columns=["messages"])
eval_ds = Dataset.from_list(eval_records).map(format_record, remove_columns=["messages"])

# %% Cell 6: Train
from trl import SFTConfig, SFTTrainer

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

training_args = SFTConfig(
    output_dir=str(OUTPUT_DIR),
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.05,
    weight_decay=0.01,
    max_seq_length=512,
    logging_steps=25,
    save_steps=500,
    eval_strategy="steps",
    eval_steps=500,
    save_total_limit=3,
    bf16=True,
    optim="paged_adamw_8bit",
    report_to="none",
    dataset_text_field="text",
    packing=True,
    seed=137,
)

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=eval_ds,
    processing_class=tokenizer,
)

t0 = time.time()
trainer.train()
log.info(f"Done in {(time.time()-t0)/60:.1f} min")

# %% Cell 7: Save
final_dir = OUTPUT_DIR / "final_adapter"
trainer.save_model(str(final_dir))
tokenizer.save_pretrained(str(final_dir))

# %% Cell 8: Test
model.eval()
for prompt in ["What are the Sacred Tongues?", "Explain the harmonic wall.", "Who is Polly?"]:
    msgs = [{"role": "user", "content": prompt}]
    inp = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(inp, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=150, temperature=0.7, do_sample=True)
    resp = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    print(f"\nQ: {prompt}\nA: {resp[:300]}\n{'─'*60}")

# %% Cell 9: Push to HuggingFace (optional)
# from huggingface_hub import login
# login(token="hf_YOUR_TOKEN")
# model.push_to_hub("issdandavis/scbe-twin-360m")
# tokenizer.push_to_hub("issdandavis/scbe-twin-360m")
