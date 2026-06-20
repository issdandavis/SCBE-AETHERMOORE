"""qlora_vtc_finetune: QLoRA fine-tune a small coder model on the VERIFIED-trajectory corpus.

Colab-runnable (free T4 fits qwen2.5-coder:1.5b in 4-bit). Trains ONLY on execution-verified records
(every line of the VTC jsonl already passed held-out hidden tests), saves the LoRA adapter + the exact
training config, and -- the point of the whole exercise -- can run the lift measurement at the end:
base vs base+adapter on held-out problems via python/helm/vtc_lift.

    # in Colab, after !pip install -q transformers peft trl bitsandbytes datasets accelerate
    python scripts/training/qlora_vtc_finetune.py \
        --data training-data/sft/vtc_mbpp_refined.jsonl \
        --base-model Qwen/Qwen2.5-Coder-1.5B-Instruct \
        --out adapters/vtc-qwen15

Heavy ML deps are imported lazily inside the functions that need them, so `--help` and the unit-tested
record formatter work without a GPU stack installed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# Qwen2.5 attention + MLP projection names -- the standard LoRA target set for this family.
QWEN_TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def load_records(data_path: str | Path) -> List[Dict[str, Any]]:
    """Read the VTC jsonl. Every record is {messages:[...], meta:{verified:True,...}}."""
    records: List[Dict[str, Any]] = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def assert_all_verified(records: Sequence[Dict[str, Any]]) -> int:
    """Refuse to train on anything unverified -- the corpus's entire value is that it is execution-true."""
    bad = [i for i, r in enumerate(records) if not r.get("meta", {}).get("verified")]
    if bad:
        raise ValueError("refusing to train: %d unverified records (e.g. index %s)" % (len(bad), bad[:5]))
    return len(records)


def to_chat_examples(records: Sequence[Dict[str, Any]], tokenizer: Any) -> List[Dict[str, str]]:
    """Render each record's message list through the model's own chat template -> a 'text' field for SFT.
    The full write->run->repair turn sequence is kept verbatim, so the model learns the LOOP."""
    out: List[Dict[str, str]] = []
    for r in records:
        text = tokenizer.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=False)
        out.append({"text": text})
    return out


def train(
    data_path: str,
    base_model: str,
    out_dir: str,
    epochs: float = 3.0,
    lr: float = 2e-4,
    lora_r: int = 16,
    lora_alpha: int = 32,
    batch_size: int = 1,
    grad_accum: int = 8,
    max_seq_len: int = 2048,
    seed: int = 0,
) -> Dict[str, Any]:
    """QLoRA SFT on the verified corpus. Saves adapter + training_config.json. Returns the config."""
    import torch  # noqa: F401  (imported for side effect / availability check)
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    records = load_records(data_path)
    n = assert_all_verified(records)

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    examples = to_chat_examples(records, tokenizer)
    dataset = Dataset.from_list(examples)

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=__import__("torch").bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(base_model, quantization_config=bnb, device_map="auto")

    peft_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=QWEN_TARGET_MODULES,
    )

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sft_config = SFTConfig(
        output_dir=str(out),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=lr,
        max_seq_length=max_seq_len,
        logging_steps=5,
        save_strategy="epoch",
        bf16=True,
        seed=seed,
        report_to="none",
        dataset_text_field="text",
    )
    trainer = SFTTrainer(model=model, args=sft_config, train_dataset=dataset, peft_config=peft_config)
    trainer.train()
    trainer.save_model(str(out))
    tokenizer.save_pretrained(str(out))

    config = {
        "base_model": base_model,
        "data": str(data_path),
        "records_trained": n,
        "epochs": epochs,
        "learning_rate": lr,
        "lora_r": lora_r,
        "lora_alpha": lora_alpha,
        "target_modules": QWEN_TARGET_MODULES,
        "batch_size": batch_size,
        "grad_accum": grad_accum,
        "max_seq_len": max_seq_len,
        "seed": seed,
        "note": "Trained ONLY on execution-verified VTC trajectories (assert_all_verified passed).",
    }
    (out / "training_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config


def hf_ask(base_model: str, adapter_dir: Optional[str], max_new_tokens: int = 512) -> Any:
    """Build an ask(prompt)->str backed by a HF model (optionally + LoRA adapter), for vtc_lift.
    Apples-to-apples: base and base+adapter run on the SAME transformers backend."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(adapter_dir or base_model)
    model = AutoModelForCausalLM.from_pretrained(base_model, device_map="auto", torch_dtype=torch.bfloat16)
    if adapter_dir:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, adapter_dir)
    model.eval()

    def ask(prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(
            model.device
        )
        with torch.no_grad():
            gen = model.generate(
                inputs, max_new_tokens=max_new_tokens, do_sample=False, pad_token_id=tokenizer.eos_token_id
            )
        text = tokenizer.decode(gen[0][inputs.shape[1] :], skip_special_tokens=True)
        from python.helm.free_generator import strip_to_code

        return strip_to_code(text)

    return ask


def run_lift(
    base_model: str, adapter_dir: str, corpus: str, limit: int, rounds: int, out_path: Optional[str]
) -> Dict[str, Any]:
    """Measure base vs base+adapter on held-out problems and print the honest report."""
    from python.helm.public_bench import pull_mbpp
    from python.helm.vtc_lift import corpus_task_ids, held_out, measure_vtc_lift, render

    problems = held_out(pull_mbpp(limit=limit), corpus_task_ids(corpus))
    report = measure_vtc_lift(hf_ask(base_model, None), hf_ask(base_model, adapter_dir), problems, rounds=rounds)
    print(render(report))
    if out_path:
        slim = {k: v for k, v in report.items() if k not in ("base", "trained")}
        Path(out_path).write_text(json.dumps(slim, indent=2), encoding="utf-8")
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-qlora-vtc", description="QLoRA fine-tune on the verified VTC corpus")
    ap.add_argument("--data", default="training-data/sft/vtc_mbpp_refined.jsonl")
    ap.add_argument("--base-model", default="Qwen/Qwen2.5-Coder-1.5B-Instruct")
    ap.add_argument("--out", default="adapters/vtc-qwen15", help="adapter output dir")
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--measure-lift", action="store_true", help="after training, run base vs base+adapter on held-out")
    ap.add_argument("--lift-limit", type=int, default=260)
    ap.add_argument("--lift-rounds", type=int, default=3)
    ap.add_argument("--lift-out", default=None)
    a = ap.parse_args(list(argv) if argv is not None else None)

    cfg = train(
        a.data,
        a.base_model,
        a.out,
        epochs=a.epochs,
        lr=a.lr,
        lora_r=a.lora_r,
        lora_alpha=a.lora_alpha,
    )
    print("TRAINED  %d verified records -> %s" % (cfg["records_trained"], a.out))
    print("  config -> %s/training_config.json" % a.out)
    if a.measure_lift:
        run_lift(a.base_model, a.out, a.data, a.lift_limit, a.lift_rounds, a.lift_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
