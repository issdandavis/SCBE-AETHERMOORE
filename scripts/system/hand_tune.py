"""
Hand-tune a LoRA adapter on SmolLM2-360M or Qwen2.5-Coder-7B.

Usage:
    # 360M (fast, ~5 min per adapter)
    python scripts/system/hand_tune.py --adapter coder
    python scripts/system/hand_tune.py --adapter lawbot
    python scripts/system/hand_tune.py --adapter commerce

    # 7B (better quality, ~30-60 min per adapter on 1660 Ti 6GB)
    python scripts/system/hand_tune.py --adapter coder --model 7b
    python scripts/system/hand_tune.py --adapter commerce --model 7b --epochs 2

    # Use SCBE-format data (richer, includes English variants)
    python scripts/system/hand_tune.py --adapter commerce --model 7b --scbe

    # Dry run to check data
    python scripts/system/hand_tune.py --adapter coder --model 7b --dry-run
"""

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Model configs
# ---------------------------------------------------------------------------

MODEL_CONFIGS = {
    "360m": {
        "base": "C:/Users/issda/SCBE-AETHERMOORE/models/smollm2-360m-instruct",
        "adapter_base": "F:/scbe-rag/adapters",
        "suffix": "360m",
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        "batch_size": 1,
        "grad_accum": 4,
        "lr": 2e-4,
        "max_seq_length": 512,
        "fp16": True,
        "bf16": False,
        "gradient_checkpointing": False,
        "optim": "adamw_torch",
    },
    "7b": {
        "base": "Qwen/Qwen2.5-Coder-7B-Instruct",  # downloads from HF on first run
        "adapter_base": "F:/scbe-rag/adapters",
        "suffix": "7b",
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        # Qwen2.5 uses these attention projection names
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        "batch_size": 1,
        "grad_accum": 8,    # effective batch = 8 to compensate for tiny real batch
        "lr": 1e-4,          # lower LR for larger model
        "max_seq_length": 512,
        "fp16": False,
        "bf16": True,        # 7B needs bf16 for numerical stability
        "gradient_checkpointing": True,  # essential for 6GB VRAM
        "optim": "paged_adamw_8bit",     # 8-bit optimizer = ~2GB VRAM saved
    },
}

ADAPTER_CONFIGS = {
    "coder": {
        "data_plain": "training-data/hand_tune/coder/examples.jsonl",
        "data_scbe": None,  # no SCBE variant for coder yet
        "system": "You are a precise coding assistant. Write clean, working code with brief explanations.",
        "description": "General coding assistant — Python, JS, SQL, React",
    },
    "lawbot": {
        "data_plain": "training-data/hand_tune/lawbot/examples.jsonl",
        "data_scbe": None,
        "system": "You are a helpful legal information assistant. Always clarify you provide general information, not legal advice, and recommend consulting an attorney for specific situations.",
        "description": "Legal information assistant — business structure, contracts, compliance",
    },
    "commerce": {
        "data_plain": "training-data/hand_tune/commerce/examples.jsonl",
        "data_scbe": "training-data/hand_tune/commerce/commerce_sft_scbe.jsonl",
        "system": (
            "You are a commerce and web development assistant. "
            "You help with Square payments, Stripe, frontend/backend code, security, and checkout processing. "
            "You NEVER recommend selling below cost + $3 minimum profit."
        ),
        "description": "Commerce assistant — Stripe, Square, haggling, profit floor enforcement",
    },
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_plain_examples(jsonl_path: str, system_prompt: str) -> list[dict]:
    """Load simple {prompt, response} pairs and format as chat."""
    examples = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ex = json.loads(line)
            examples.append({
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": ex["prompt"]},
                    {"role": "assistant", "content": ex["response"]},
                ]
            })
    return examples


def load_scbe_examples(jsonl_path: str) -> list[dict]:
    """Load SCBE-format records (already have messages[])."""
    examples = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ex = json.loads(line)
                if "messages" in ex:
                    examples.append({"messages": ex["messages"]})
            except json.JSONDecodeError:
                continue
    return examples


def load_examples(adapter_name: str, use_scbe: bool) -> list[dict]:
    cfg = ADAPTER_CONFIGS[adapter_name]
    scbe_path = cfg.get("data_scbe")
    plain_path = cfg["data_plain"]

    examples = []

    if use_scbe and scbe_path and Path(scbe_path).exists():
        scbe = load_scbe_examples(scbe_path)
        plain = load_plain_examples(plain_path, cfg["system"])
        # Merge: SCBE records first, then plain for coverage
        examples = scbe + plain
        print(f"  SCBE records: {len(scbe)}")
        print(f"  Plain records: {len(plain)}")
    else:
        if use_scbe and scbe_path:
            print(f"  WARNING: SCBE data not found at {scbe_path}, falling back to plain")
        examples = load_plain_examples(plain_path, cfg["system"])
        print(f"  Plain records: {len(examples)}")

    return examples


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(adapter_name: str, model_key: str, epochs: int, dry_run: bool, use_scbe: bool) -> None:
    adapter_cfg = ADAPTER_CONFIGS[adapter_name]
    model_cfg = MODEL_CONFIGS[model_key]

    suffix = model_cfg["suffix"]
    output_dir = str(Path(model_cfg["adapter_base"]) / f"{adapter_name}-{suffix}")

    print(f"\n=== Hand-tuning: {adapter_name} ({model_key}) ===")
    print(f"  Base:    {model_cfg['base']}")
    print(f"  Output:  {output_dir}")
    print(f"  Desc:    {adapter_cfg['description']}")

    examples = load_examples(adapter_name, use_scbe)
    print(f"  Total examples: {len(examples)}")

    if dry_run:
        print("\nDRY RUN — not training. Example 0:")
        print(json.dumps(examples[0], indent=2))
        return

    if len(examples) < 2:
        print("ERROR: Need at least 2 examples. Add more to your JSONL files.")
        sys.exit(1)

    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    print("\nLoading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_cfg["base"], trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    print(f"Loading model in 4-bit ({'bf16' if model_cfg['bf16'] else 'fp16'} compute)...")
    compute_dtype = torch.bfloat16 if model_cfg["bf16"] else torch.float16
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_cfg["base"],
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model.config.use_cache = False

    if model_cfg["gradient_checkpointing"]:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    lora_config = LoraConfig(
        r=model_cfg["lora_r"],
        lora_alpha=model_cfg["lora_alpha"],
        lora_dropout=model_cfg["lora_dropout"],
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=model_cfg["target_modules"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Format as text
    def format_example(ex: dict) -> str:
        return tokenizer.apply_chat_template(
            ex["messages"], tokenize=False, add_generation_prompt=False
        )

    texts = [format_example(e) for e in examples]
    dataset = Dataset.from_dict({"text": texts})

    if len(dataset) >= 4:
        split = dataset.train_test_split(test_size=min(0.2, 2 / len(dataset)))
        train_ds, eval_ds = split["train"], split["test"]
    else:
        train_ds, eval_ds = dataset, dataset

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    training_args = SFTConfig(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=model_cfg["batch_size"],
        gradient_accumulation_steps=model_cfg["grad_accum"],
        gradient_checkpointing=model_cfg["gradient_checkpointing"],
        learning_rate=model_cfg["lr"],
        fp16=model_cfg["fp16"],
        bf16=model_cfg["bf16"],
        optim=model_cfg["optim"],
        logging_steps=1,
        save_strategy="epoch",
        eval_strategy="epoch" if len(eval_ds) > 0 else "no",
        warmup_ratio=0.1,
        max_seq_length=model_cfg["max_seq_length"],
        dataset_text_field="text",
        report_to="none",
        dataloader_pin_memory=False,  # saves VRAM on small GPU
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds if len(eval_ds) > 0 else None,
    )

    print(f"\nTraining for {epochs} epoch(s)...")
    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"\nAdapter saved to: {output_dir}")
    print(f"\nNext steps:")
    if model_key == "7b":
        print(f"  Merge + export for Ollama:")
        print(f"    python scripts/system/merge_to_gguf.py --adapter {adapter_name}")
        print(f"  Or serve via model_server.py:")
        print(f"    python scripts/system/model_server.py  (port 8010)")
    else:
        print(f"    python scripts/system/model_server.py  (port 8010)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Hand-tune a LoRA adapter")
    parser.add_argument(
        "--adapter", choices=list(ADAPTER_CONFIGS.keys()), required=True,
        help="Which adapter to train"
    )
    parser.add_argument(
        "--model", choices=["360m", "7b"], default="360m",
        help="Base model size (default: 360m)"
    )
    parser.add_argument(
        "--epochs", type=int, default=3,
        help="Training epochs (default: 3, recommend 2 for 7b)"
    )
    parser.add_argument(
        "--scbe", action="store_true",
        help="Use SCBE-format training data (richer, includes tongue weights + English variants)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show data sample, don't train"
    )
    args = parser.parse_args()

    # Recommend epochs for 7b
    if args.model == "7b" and args.epochs == 3:
        print("TIP: For 7b, 2 epochs is usually enough and faster. Use --epochs 2 to reduce training time.")

    train(args.adapter, args.model, args.epochs, args.dry_run, args.scbe)


if __name__ == "__main__":
    main()
