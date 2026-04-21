"""HF-side SFT training for Polly (SCBE-AETHERMOORE).

Pulls dataset from issdandavis/polly-training-data, trains a LoRA adapter on
Qwen2.5-0.5B, and optionally pushes the adapter to a Hugging Face model repo.

Designed to run on Colab (T4/L4/A100) and Kaggle (T4 x2 / P100). Tolerates
trl >=0.12 where max_seq_length moved off SFTConfig onto SFTTrainer. Forces
single-GPU placement in multi-GPU environments (e.g. Kaggle T4 x2) to avoid
DataParallel device-split errors with LoRA training. Auto-creates the target
HF model repo if missing so Colab --push works the first time.
"""

from __future__ import annotations

import argparse
import inspect
import os
import sys
from pathlib import Path

# Pin to a single visible GPU before importing torch, unless the user already
# set CUDA_VISIBLE_DEVICES. This avoids HF Trainer auto-wrapping the model in
# torch.nn.DataParallel across multiple GPUs (which doesn't work with
# device_map-sharded PEFT models).
if "CUDA_VISIBLE_DEVICES" not in os.environ:
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import torch
from datasets import load_dataset
from huggingface_hub import HfApi
from peft import LoraConfig, TaskType, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer


def build_quant_config(no_quant: bool):
    if no_quant:
        return None
    try:
        from transformers import BitsAndBytesConfig

        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
    except Exception as exc:
        print("[hf_train_polly] bnb unavailable:", exc, file=sys.stderr)
        return None


def resolve_token():
    tok = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if tok:
        return tok
    try:
        from kaggle_secrets import UserSecretsClient

        tok = UserSecretsClient().get_secret("HF_TOKEN")
        if tok:
            os.environ["HF_TOKEN"] = tok
            return tok
    except Exception:
        pass
    try:
        from google.colab import userdata  # type: ignore

        tok = userdata.get("HF_TOKEN")
        if tok:
            os.environ["HF_TOKEN"] = tok
            return tok
    except Exception:
        pass
    return None


def split_kwargs(target_cls, kwargs):
    try:
        sig = inspect.signature(target_cls.__init__)
        params = set(sig.parameters)
    except (TypeError, ValueError):
        return dict(kwargs), {}
    accepted = {k: v for k, v in kwargs.items() if k in params}
    leftover = {k: v for k, v in kwargs.items() if k not in params}
    return accepted, leftover


def ensure_repo(repo_id: str, token: str, private: bool = True) -> None:
    api = HfApi(token=token)
    try:
        api.repo_info(repo_id, repo_type="model")
        print("[hf_train_polly] repo exists:", repo_id)
        return
    except Exception:
        pass
    print("[hf_train_polly] creating repo:", repo_id)
    api.create_repo(
        repo_id=repo_id,
        repo_type="model",
        private=private,
        exist_ok=True,
        token=token,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-model", default="Qwen/Qwen2.5-0.5B")
    ap.add_argument("--dataset", default="issdandavis/polly-training-data")
    ap.add_argument("--dataset-split", default="train")
    ap.add_argument("--output-repo", default="issdandavis/polly-1")
    ap.add_argument("--output-dir", default="./out/polly-lora")
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--max-seq", type=int, default=1024)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--lora-dropout", type=float, default=0.05)
    ap.add_argument("--warmup-ratio", type=float, default=0.03)
    ap.add_argument("--max-grad-norm", type=float, default=1.0)
    ap.add_argument("--no-quant", action="store_true")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--private", action="store_true", default=True)
    ap.add_argument("--public", dest="private", action="store_false")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    token = resolve_token()
    if not token:
        print("[hf_train_polly] ERROR: set HF_TOKEN", file=sys.stderr)
        return 2

    if args.push:
        try:
            ensure_repo(args.output_repo, token, private=args.private)
        except Exception as exc:
            print("[hf_train_polly] WARN: could not ensure repo:", exc, file=sys.stderr)

    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    use_fp16 = torch.cuda.is_available() and not use_bf16
    compute_dtype = torch.bfloat16 if use_bf16 else torch.float16

    print("[hf_train_polly] loading dataset", args.dataset, args.dataset_split)
    ds = load_dataset(args.dataset, split=args.dataset_split, token=token)
    keep = {"messages"}
    drop_cols = [c for c in ds.column_names if c not in keep]
    if drop_cols:
        ds = ds.remove_columns(drop_cols)
    print("[hf_train_polly] rows:", len(ds))

    print("[hf_train_polly] loading tokenizer + base:", args.base_model)
    tok = AutoTokenizer.from_pretrained(args.base_model, token=token)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    quant = build_quant_config(args.no_quant)
    # Pin the whole model to cuda:0. With CUDA_VISIBLE_DEVICES=0 set at top,
    # device_map={"":0} keeps every parameter on one device and avoids the
    # DataParallel multi-device split error.
    model_kwargs = {"token": token, "device_map": {"": 0} if torch.cuda.is_available() else "cpu"}
    if quant is not None:
        model_kwargs["quantization_config"] = quant
    else:
        model_kwargs["torch_dtype"] = compute_dtype

    model = AutoModelForCausalLM.from_pretrained(args.base_model, **model_kwargs)

    lora = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg_kwargs = dict(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=args.warmup_ratio,
        max_grad_norm=args.max_grad_norm,
        logging_steps=10,
        save_steps=200,
        save_total_limit=3,
        bf16=use_bf16,
        fp16=use_fp16,
        max_seq_length=args.max_seq,
        packing=False,
        report_to=[],
        seed=args.seed,
        push_to_hub=args.push,
        hub_model_id=args.output_repo if args.push else None,
        hub_token=token if args.push else None,
        hub_private_repo=args.private if args.push else None,
    )

    cfg_accepted, cfg_leftover = split_kwargs(SFTConfig, cfg_kwargs)
    cfg_leftover = {k: v for k, v in cfg_leftover.items() if v is not None}
    cfg = SFTConfig(**cfg_accepted)

    trainer_kwargs = dict(
        model=model,
        args=cfg,
        train_dataset=ds,
    )
    trainer_sig = set(inspect.signature(SFTTrainer.__init__).parameters)
    if "processing_class" in trainer_sig:
        trainer_kwargs["processing_class"] = tok
    elif "tokenizer" in trainer_sig:
        trainer_kwargs["tokenizer"] = tok
    for k, v in cfg_leftover.items():
        if k in trainer_sig:
            trainer_kwargs[k] = v
        else:
            print("[hf_train_polly] dropping unsupported kwarg:", k, file=sys.stderr)

    trainer = SFTTrainer(**trainer_kwargs)

    print("[hf_train_polly] starting training")
    trainer.train()

    print("[hf_train_polly] saving adapter to", output_dir)
    trainer.save_model(str(output_dir))
    tok.save_pretrained(str(output_dir))

    if args.push:
        print("[hf_train_polly] pushing to hub:", args.output_repo)
        pushed = False
        try:
            trainer.push_to_hub()
            pushed = True
        except Exception as exc:
            print("[hf_train_polly] trainer.push_to_hub failed:", exc, file=sys.stderr)
        if not pushed:
            try:
                model.push_to_hub(args.output_repo, token=token, private=args.private)
                tok.push_to_hub(args.output_repo, token=token, private=args.private)
                pushed = True
            except Exception as exc:
                print("[hf_train_polly] model.push_to_hub failed:", exc, file=sys.stderr)
        if not pushed:
            try:
                api = HfApi(token=token)
                api.upload_folder(
                    folder_path=str(output_dir),
                    repo_id=args.output_repo,
                    repo_type="model",
                    token=token,
                )
                pushed = True
            except Exception as exc:
                print("[hf_train_polly] upload_folder failed:", exc, file=sys.stderr)
        if not pushed:
            print("[hf_train_polly] ERROR: all push attempts failed", file=sys.stderr)
            return 3

    print("[hf_train_polly] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
