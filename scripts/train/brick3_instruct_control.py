"""Brick3 control — clean-sheet Qwen2.5-0.5B-Instruct + drill_langues_full.

Simple-chemistry control. No warm-start, no weighted maps, no curriculum mix.
One reagent (Instruct base), one solvent (drill_langues_full), one product.

Delta vs brick3_local:
    brick3_local = Qwen2.5-0.5B BASE + warm-start from brick2 + drill_langues_full
    brick3_instruct_control = Qwen2.5-0.5B INSTRUCT + clean LoRA + drill_langues_full

Same steps (500), same LoRA rank (r=16), same LR (1e-4), same batch/accum.
Only the base changes. If the Instruct prior matters, eval_loss and
structural pass_rate diverge from brick3. If not, we know the bottleneck
is data, not prior.

Usage:
    python scripts/train/brick3_instruct_control.py

Artifacts land at artifacts/training/brick3_instruct_control/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer

REPO = Path(__file__).resolve().parents[2]
TRAIN = REPO / "training-data" / "sft" / "drill_langues_full_train.sft.jsonl"
HOLDOUT = REPO / "training-data" / "sft" / "drill_langues_full_holdout.sft.jsonl"
OUT = REPO / "artifacts" / "training" / "brick3_instruct_control"

BASE = "Qwen/Qwen2.5-0.5B-Instruct"
MAX_STEPS = 500
LR = 1e-4
LORA_R = 16
LORA_ALPHA = 32
BATCH = 4
GRAD_ACCUM = 4
BLOCK = 256


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    if not TRAIN.exists():
        raise SystemExit(f"missing train file: {TRAIN}")
    if not HOLDOUT.exists():
        raise SystemExit(f"missing holdout file: {HOLDOUT}")

    OUT.mkdir(parents=True, exist_ok=True)
    print(f"[brick3-ic] base={BASE}")
    print(f"[brick3-ic] train={TRAIN} ({sum(1 for _ in TRAIN.open(encoding='utf-8'))} rows)")
    print(f"[brick3-ic] holdout={HOLDOUT} ({sum(1 for _ in HOLDOUT.open(encoding='utf-8'))} rows)")

    tokenizer = AutoTokenizer.from_pretrained(BASE, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        BASE,
        torch_dtype=dtype,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
    )

    lora = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    train_ds = Dataset.from_list(load_jsonl(TRAIN))
    eval_ds = Dataset.from_list(load_jsonl(HOLDOUT))

    cfg = SFTConfig(
        output_dir=str(OUT),
        max_steps=MAX_STEPS,
        per_device_train_batch_size=BATCH,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LR,
        lr_scheduler_type="cosine",
        warmup_steps=25,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=100,
        save_total_limit=3,
        max_length=BLOCK,
        bf16=torch.cuda.is_available(),
        report_to=[],
    )

    trainer = SFTTrainer(
        model=model,
        args=cfg,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        processing_class=tokenizer,
    )
    trainer.train()
    trainer.save_model(str(OUT / "final"))

    state = {
        "base": BASE,
        "train_rows": len(train_ds),
        "eval_rows": len(eval_ds),
        "max_steps": MAX_STEPS,
        "lora_r": LORA_R,
        "lr": LR,
        "log_history": trainer.state.log_history,
    }
    (OUT / "trainer_state_final.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"[brick3-ic] done -> {OUT}")


if __name__ == "__main__":
    main()
