#!/usr/bin/env python
"""CLI for the local full-bundle tiny LM.

This makes the seed model usable from the terminal:

  python scripts/training/full_bundle_tiny_lm_cli.py \
    --lane coding --task code_to_scbe_tokens \
    --prompt "Convert this python code into SCBE phase tokens: def f(a,b): return a+b"

Every run writes a receipt so generations are inspectable and reproducible.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import torch

from train_full_bundle_tiny_lm import TinyLM, generate


ROOT = Path(__file__).resolve().parents[2]
LM_DIR = ROOT / "artifacts" / "full_coding_systems_bundle" / "tiny_lm"
OUT_DIR = LM_DIR / "cli_runs"


def load_model():
    checkpoint = torch.load(LM_DIR / "tiny_lm.pt", map_location="cuda" if torch.cuda.is_available() else "cpu")
    vocab = checkpoint["vocab"]
    config = checkpoint["config"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TinyLM(
        len(vocab),
        config["emb"],
        config["hidden"],
        vocab["<PAD>"],
        layers=config.get("layers", 1),
        dropout=config.get("dropout", 0.0),
    ).to(device)
    model.load_state_dict(checkpoint["model"])
    model.eval()
    return model, vocab, config, device


def binary_views(text: str) -> str:
    data = text.encode("utf-8", errors="replace")
    sample = data[:96]
    payload = {
        "utf8": text,
        "bytes": list(sample),
        "hex": sample.hex(),
        "bits": "".join(f"{byte:08b}" for byte in sample[:32]),
        "nibbles": " ".join(f"{byte >> 4:x} {byte & 15:x}" for byte in sample[:32]),
        "base64": base64.b64encode(sample).decode("ascii"),
        "base64url": base64.urlsafe_b64encode(sample).decode("ascii"),
        "ascii85": base64.a85encode(sample).decode("ascii", errors="replace"),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    return json.dumps(payload, ensure_ascii=False)


def extract_encode_target(prompt: str) -> str | None:
    match = re.search(r"Encode\s+(.+?)\s+into binary views\.?$", prompt, flags=re.I | re.S)
    if match:
        return match.group(1).strip()
    return None


def deterministic_guard(lane: str, task: str, prompt: str, raw_generation: str) -> tuple[str, dict]:
    lower = prompt.lower()
    if lane == "binary" and task == "code_to_binary_views":
        target = extract_encode_target(prompt)
        if target:
            return binary_views(target), {"applied": True, "reason": "exact_binary_encoder"}
    if lane == "github_user_guide" and "pull request" in lower:
        return "https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/getting-started/best-practices-for-pull-requests", {
            "applied": True,
            "reason": "github_pull_request_official_source",
        }
    if lane == "coding" and task == "code_to_scbe_tokens":
        if "+" in prompt and "return" in lower:
            return "KO kor-vael AV av-sai lang:python RU ru-thar CA bip'fn CA bip'a CA bip'out DR draum-sel", {
                "applied": True,
                "reason": "exact_scbe_add_token_bridge",
            }
        if "*" in prompt and "return" in lower:
            return "KO kor-vael AV av-sai lang:python RU ru-thar CA bip'fn CA bip'i CA bip'out DR draum-sel", {
                "applied": True,
                "reason": "exact_scbe_mul_token_bridge",
            }
    return raw_generation, {"applied": False, "reason": "model_output_used"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--max-new", type=int, default=160)
    parser.add_argument("--raw", action="store_true", help="return raw model generation without deterministic guards")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model, vocab, config, device = load_model()
    raw_generation = generate(
        model,
        vocab,
        args.prompt,
        device,
        max_new=args.max_new,
        lane=args.lane,
        task=args.task,
    )
    if args.raw:
        generation = raw_generation
        guard = {"applied": False, "reason": "raw_requested"}
    else:
        generation, guard = deterministic_guard(args.lane, args.task, args.prompt, raw_generation)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    request_id = hashlib.sha256(f"{now}:{args.lane}:{args.task}:{args.prompt}".encode("utf-8")).hexdigest()[:12]
    receipt = {
        "ok": True,
        "kind": "full_bundle_tiny_lm_cli_generation",
        "created_at": now,
        "request_id": request_id,
        "device": str(device),
        "model_config": config,
        "request": {
            "lane": args.lane,
            "task": args.task,
            "prompt": args.prompt,
            "max_new": args.max_new,
            "raw": args.raw,
        },
        "guard": guard,
        "raw_generation": raw_generation,
        "generation": generation,
    }
    receipt_path = OUT_DIR / f"generation_{now}_{request_id}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    print(generation)
    print(f"\nreceipt: {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
