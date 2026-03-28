# /// script
# dependencies = [
#   "datasets>=3.3.2",
#   "transformers>=4.49.0",
#   "trl>=0.19.1",
#   "peft>=0.14.0",
#   "accelerate>=1.3.0",
#   "trackio>=0.5.0"
# ]
# ///

"""Seed SFT launcher for Polly chat.

Use locally for smoke runs or submit through Hugging Face Jobs after publishing the
seed dataset to the Hub. Defaults are intentionally small and LoRA-based.
"""

from __future__ import annotations

import os
from pathlib import Path

from datasets import load_dataset
from peft import LoraConfig
from transformers import AutoTokenizer
from trl import SFTConfig, SFTTrainer


BASE_MODEL = os.getenv("POLLY_BASE_MODEL", "issdandavis/scbe-pivot-qwen-0.5b")
TARGET_MODEL = os.getenv("POLLY_TARGET_MODEL", "issdandavis/polly-chat-qwen-0.5b")
DATASET_MODE = os.getenv("POLLY_DATASET_MODE", "local")
LOCAL_DATASET = os.getenv(
    "POLLY_LOCAL_DATASET",
    str(Path(__file__).resolve().parents[1] / "training-data" / "sft" / "polly_chat_seed.jsonl"),
)
HUB_DATASET_ID = os.getenv("POLLY_HUB_DATASET_ID", "issdandavis/polly-chat-seed")
OUTPUT_DIR = os.getenv("POLLY_OUTPUT_DIR", "artifacts/training/polly-chat-qwen-0.5b")
PUSH_TO_HUB = os.getenv("POLLY_PUSH_TO_HUB", "0") == "1"


def load_training_dataset():
    if DATASET_MODE == "hub":
        return load_dataset(HUB_DATASET_ID, split="train")
    return load_dataset("json", data_files=LOCAL_DATASET, split="train")


def main() -> None:
    dataset = load_training_dataset()
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True)

    trainer = SFTTrainer(
        model=BASE_MODEL,
        processing_class=tokenizer,
        train_dataset=dataset,
        peft_config=LoraConfig(
            r=16,
            lora_alpha=32,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
        ),
        args=SFTConfig(
            output_dir=OUTPUT_DIR,
            hub_model_id=TARGET_MODEL,
            push_to_hub=PUSH_TO_HUB,
            learning_rate=2e-4,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=8,
            num_train_epochs=3,
            warmup_ratio=0.03,
            logging_steps=5,
            save_strategy="epoch",
            max_length=1024,
            report_to="trackio",
            project="polly-chat",
            run_name="polly-chat-seed-sft",
        ),
    )

    trainer.train()

    if PUSH_TO_HUB:
        trainer.push_to_hub()


if __name__ == "__main__":
    main()
