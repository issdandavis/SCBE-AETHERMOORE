#!/usr/bin/env python3
"""
Prompt Injection to Bit-Signature Pipeline

Ingests public prompt-injection datasets and produces a bit-level mapping
by running each prompt through the Six Sacred Tongues bijective tokenizer.

Every byte of the UTF-8 text becomes exactly one token per tongue. Because
the tokenizer is bijective, the tokens can be reversed back to bits with
no loss. This produces a deterministic per-prompt signature that can be
analyzed for statistical regularities that distinguish attacks from benign
prompts.

Datasets supported (all Apache-2.0 or MIT, auth-free):
  1. neuralchemy/Prompt-injection-dataset  (29 categories, flagship)
  2. deepset/prompt-injections              (binary, 662 rows)
  3. jackhhao/jailbreak-classification      (~1.3K rows)
  4. reshabhs/SPML_Chatbot_Prompt_Injection (system+user pairs)

Run:
  pip install datasets huggingface_hub
  python injection_to_bits.py --out injection_bit_signatures.jsonl
  python injection_to_bits.py --out small.jsonl --limit 500
  python injection_to_bits.py --source deepset --out deepset_bits.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

# --- Six Sacred Tongues bijective tokenizer -------------------------------

TONGUE_META = {
    "KO": {"seed": 0xC01,  "weight": 1.000},
    "AV": {"seed": 0xA71,  "weight": 1.618},
    "RU": {"seed": 0xB03,  "weight": 2.618},
    "CA": {"seed": 0xC0DE, "weight": 4.236},
    "UM": {"seed": 0xDEAD, "weight": 6.854},
    "DR": {"seed": 0xFACE, "weight": 11.090},
}
TONGUES = list(TONGUE_META.keys())

CONSONANTS = ["k", "n", "r", "s", "t", "m", "l", "v", "z", "ch", "th", "sh", "br", "dr", "gl", "ph"]
VOWELS = ["a", "e", "i", "o", "u", "ae", "ei", "ou"]


def _build_table(tongue: str) -> list[str]:
    rng = random.Random(TONGUE_META[tongue]["seed"])
    prefix = tongue.lower()
    pool: set[str] = set()
    ordered: list[str] = []
    for c1 in CONSONANTS:
        for v1 in VOWELS:
            for c2 in CONSONANTS:
                for v2 in VOWELS:
                    tok = f"{prefix}-{c1}{v1}{c2}{v2}"
                    if tok in pool:
                        continue
                    pool.add(tok)
                    ordered.append(tok)
    rng.shuffle(ordered)
    return ordered[:256]


TABLES: dict[str, list[str]] = {t: _build_table(t) for t in TONGUES}


def encode_bytes(data: bytes, tongue: str) -> list[str]:
    table = TABLES[tongue]
    return [table[b] for b in data]


# --- Bit-level signature ---------------------------------------------------


def shannon_entropy(byte_counts: Counter) -> float:
    total = sum(byte_counts.values())
    if total == 0:
        return 0.0
    ent = 0.0
    for c in byte_counts.values():
        if c == 0:
            continue
        p = c / total
        ent -= p * math.log2(p)
    return ent


def bit_histogram(data: bytes) -> list[int]:
    """16-element list: [pos0_zeros, pos0_ones, ..., pos7_zeros, pos7_ones]."""
    hist = [0] * 16
    for b in data:
        for i in range(8):
            bit = (b >> i) & 1
            hist[2 * i + bit] += 1
    return hist


def compute_signature(data: bytes) -> dict[str, Any]:
    byte_counts = Counter(data)
    parity_per_tongue = {}
    for t in TONGUES:
        even = sum(1 for b in data if b % 2 == 0)
        odd = len(data) - even
        parity_per_tongue[t] = {"even": even, "odd": odd}
    phi_sum = 0.0
    for i, t in enumerate(TONGUES):
        count = sum(1 for b in data if b % 6 == i)
        phi_sum += TONGUE_META[t]["weight"] * count
    return {
        "hex_sha256": hashlib.sha256(data).hexdigest(),
        "bit_histogram": bit_histogram(data),
        "byte_entropy": round(shannon_entropy(byte_counts), 6),
        "token_parity": parity_per_tongue,
        "phi_weight_sum": round(phi_sum, 6),
    }


# --- Dataset loaders -------------------------------------------------------


def load_deepset() -> Iterable[dict[str, Any]]:
    from datasets import load_dataset
    ds = load_dataset("deepset/prompt-injections")
    for split_name in ds:
        split = ds[split_name]
        for i, row in enumerate(split):
            yield {
                "source": "deepset/prompt-injections",
                "split": split_name,
                "row_idx": i,
                "text": row.get("text") or "",
                "label": "malicious" if row.get("label", 0) == 1 else "benign",
                "category": None,
            }


def load_jackhhao() -> Iterable[dict[str, Any]]:
    from datasets import load_dataset
    ds = load_dataset("jackhhao/jailbreak-classification")
    for split_name in ds:
        split = ds[split_name]
        for i, row in enumerate(split):
            prompt = row.get("prompt") or row.get("text") or ""
            t = (row.get("type") or row.get("label") or "").strip().lower()
            label = "jailbreak" if "jail" in t or "malicious" in t else "benign"
            yield {
                "source": "jackhhao/jailbreak-classification",
                "split": split_name,
                "row_idx": i,
                "text": prompt,
                "label": label,
                "category": t or None,
            }


def load_neuralchemy(config: str = "core") -> Iterable[dict[str, Any]]:
    from datasets import load_dataset
    try:
        ds = load_dataset("neuralchemy/Prompt-injection-dataset", config)
    except Exception:
        ds = load_dataset("neuralchemy/Prompt-injection-dataset")
    for split_name in ds:
        split = ds[split_name]
        for i, row in enumerate(split):
            text = row.get("text") or row.get("prompt") or ""
            label_raw = row.get("label") or row.get("is_malicious")
            if isinstance(label_raw, bool):
                label = "malicious" if label_raw else "benign"
            elif isinstance(label_raw, (int, float)):
                label = "malicious" if int(label_raw) == 1 else "benign"
            else:
                label = str(label_raw or "unknown").lower()
            yield {
                "source": "neuralchemy/Prompt-injection-dataset",
                "split": split_name,
                "row_idx": i,
                "text": text,
                "label": label,
                "category": row.get("category") or row.get("attack_type") or None,
            }


def load_spml() -> Iterable[dict[str, Any]]:
    from datasets import load_dataset
    ds = load_dataset("reshabhs/SPML_Chatbot_Prompt_Injection")
    for split_name in ds:
        split = ds[split_name]
        for i, row in enumerate(split):
            user = row.get("User Prompt") or row.get("user_prompt") or row.get("prompt") or ""
            system = row.get("System Prompt") or row.get("system_prompt") or ""
            combined = (f"[SYSTEM] {system}\n[USER] {user}" if system else user).strip()
            label_raw = row.get("Prompt injection") or row.get("label") or row.get("injection")
            if isinstance(label_raw, (int, float)):
                label = "malicious" if int(label_raw) == 1 else "benign"
            elif isinstance(label_raw, str):
                label = "malicious" if label_raw.lower() in ("1", "true", "yes", "malicious") else "benign"
            else:
                label = "unknown"
            yield {
                "source": "reshabhs/SPML_Chatbot_Prompt_Injection",
                "split": split_name,
                "row_idx": i,
                "text": combined,
                "label": label,
                "category": row.get("category") or None,
            }


LOADERS = {
    "deepset": load_deepset,
    "jackhhao": load_jackhhao,
    "neuralchemy": load_neuralchemy,
    "spml": load_spml,
}


# --- Pipeline --------------------------------------------------------------


def process_record(rec: dict[str, Any], max_bytes: int = 2048) -> dict[str, Any] | None:
    text = (rec.get("text") or "").strip()
    if not text:
        return None
    data = text.encode("utf-8", errors="replace")
    if len(data) > max_bytes:
        data = data[:max_bytes]
    try:
        ko = encode_bytes(data, "KO")
        av = encode_bytes(data, "AV")
        ru = encode_bytes(data, "RU")
        ca = encode_bytes(data, "CA")
        um = encode_bytes(data, "UM")
        dr = encode_bytes(data, "DR")
    except Exception:
        return None
    sig = compute_signature(data)
    return {
        "id": f"{rec['source']}:{rec.get('split','')}:{rec['row_idx']}",
        "source": rec["source"],
        "split": rec.get("split"),
        "text": text[:2048],
        "label": rec.get("label") or "unknown",
        "category": rec.get("category"),
        "byte_len": len(data),
        "ko_tokens": ko,
        "av_tokens": av,
        "ru_tokens": ru,
        "ca_tokens": ca,
        "um_tokens": um,
        "dr_tokens": dr,
        "bit_signature": sig,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Prompt injection -> Six Tongues -> bit signature")
    ap.add_argument("--source", choices=sorted(LOADERS.keys()) + ["all"], default="all")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0, help="Cap rows per source (0 = no cap)")
    ap.add_argument("--max-bytes", type=int, default=2048)
    args = ap.parse_args()

    sources = list(LOADERS.keys()) if args.source == "all" else [args.source]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total_in = 0
    total_out = 0
    per_label: Counter = Counter()
    per_source: Counter = Counter()

    with out_path.open("w", encoding="utf-8") as f:
        for src in sources:
            loader = LOADERS[src]
            count = 0
            try:
                iterator = loader()
            except Exception as e:
                print(f"[skip] {src}: {e}", file=sys.stderr)
                continue
            for rec in iterator:
                total_in += 1
                if args.limit and count >= args.limit:
                    break
                out = process_record(rec, max_bytes=args.max_bytes)
                if not out:
                    continue
                f.write(json.dumps(out, ensure_ascii=False) + "\n")
                total_out += 1
                count += 1
                per_label[out["label"]] += 1
                per_source[src] += 1
            print(f"[{src}] wrote {count} rows", file=sys.stderr)

    print(f"\n-- summary --", file=sys.stderr)
    print(f"  input rows:  {total_in}", file=sys.stderr)
    print(f"  output rows: {total_out}", file=sys.stderr)
    print(f"  per source:  {dict(per_source)}", file=sys.stderr)
    print(f"  per label:   {dict(per_label)}", file=sys.stderr)
    print(f"  wrote: {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
