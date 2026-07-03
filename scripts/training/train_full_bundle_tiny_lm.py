#!/usr/bin/env python
"""Train a tiny generative LM from scratch on the full SCBE coding bundle.

This is the next step after the classifier probe:
  - random initialization
  - local GPU if available
  - token-level causal language modeling
  - prompt -> response samples saved with held-out loss

Honest scope:
  This is a small seed LM. It proves the bundle can train a generator; it is not
  a finished general coder.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
from collections import Counter
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset


ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "artifacts" / "full_coding_systems_bundle" / "training_bundle.jsonl"
OUT_DIR = ROOT / "artifacts" / "full_coding_systems_bundle" / "tiny_lm"
SPECIALS = ["<PAD>", "<BOS>", "<EOS>", "<UNK>", "<PROMPT>", "<RESPONSE>", "<LANE>", "<TASK>"]


def token_re() -> re.Pattern[str]:
    return re.compile(r"[A-Za-z0-9_:'-]+|[{}()[\].,;:+\-*/%=<>!&|#]|\\n|\S")


def tokenize(text: str) -> list[str]:
    text = str(text or "").replace("\n", " \\n ")
    return token_re().findall(text)


def detokenize(tokens: list[str]) -> str:
    out = []
    for tok in tokens:
        if tok == "\\n":
            out.append("\n")
        elif tok in {".", ",", ":", ";", ")", "]", "}"}:
            if out:
                out[-1] = out[-1].rstrip()
            out.append(tok + " ")
        elif tok in {"(", "[", "{"}:
            out.append(tok)
        else:
            out.append(tok + " ")
    return "".join(out).replace(" \n ", "\n").strip()


def read_rows(limit: int | None = None) -> list[dict]:
    rows = []
    with BUNDLE.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
                if limit is not None and len(rows) >= limit:
                    break
    return rows


def balance_by_task(rows: list[dict], min_task_rows: int, seed: int = 31) -> list[dict]:
    if min_task_rows <= 0:
        return rows
    by_task: dict[str, list[dict]] = {}
    for row in rows:
        by_task.setdefault(row["task"], []).append(row)
    rng = random.Random(seed)
    balanced = list(rows)
    for task_rows in by_task.values():
        if len(task_rows) >= min_task_rows:
            continue
        needed = min_task_rows - len(task_rows)
        for _ in range(needed):
            balanced.append(rng.choice(task_rows))
    rng.shuffle(balanced)
    return balanced


def format_row(row: dict) -> list[str]:
    text = [
        "<BOS>",
        "<LANE>",
        row["lane"],
        "<TASK>",
        row["task"],
        "<PROMPT>",
        *tokenize(row["prompt"])[:220],
        "<RESPONSE>",
        *tokenize(row["response"])[:260],
        "<EOS>",
    ]
    return text


def build_vocab(rows: list[dict], max_vocab: int) -> dict[str, int]:
    counts = Counter()
    for row in rows:
        counts.update(format_row(row))
    vocab_tokens = SPECIALS + [tok for tok, _ in counts.most_common(max_vocab) if tok not in SPECIALS]
    return {tok: i for i, tok in enumerate(vocab_tokens[:max_vocab])}


def encode(tokens: list[str], vocab: dict[str, int]) -> list[int]:
    unk = vocab["<UNK>"]
    return [vocab.get(tok, unk) for tok in tokens]


class SeqDataset(Dataset):
    def __init__(self, rows: list[dict], vocab: dict[str, int], max_len: int):
        self.items = []
        for row in rows:
            ids = encode(format_row(row), vocab)
            if len(ids) < 8:
                continue
            self.items.append(ids[:max_len])
        self.pad = vocab["<PAD>"]
        self.max_len = max_len

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        ids = self.items[idx]
        x = ids[:-1]
        y = ids[1:]
        response_id = self.vocab_response_id
        try:
            response_pos = ids.index(response_id)
        except ValueError:
            response_pos = 0
        # Only train assistant response tokens. Prompt/prefix targets are masked.
        for i in range(min(response_pos, len(y))):
            y[i] = self.pad
        pad_len = self.max_len - 1 - len(x)
        if pad_len > 0:
            x = x + [self.pad] * pad_len
            y = y + [self.pad] * pad_len
        return torch.tensor(x, dtype=torch.long), torch.tensor(y, dtype=torch.long)

    @property
    def vocab_response_id(self) -> int:
        return 5


class TinyLM(nn.Module):
    def __init__(self, vocab_size: int, emb: int, hidden: int, pad_idx: int, layers: int = 1, dropout: float = 0.0):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, emb, padding_idx=pad_idx)
        self.rnn = nn.GRU(
            emb,
            hidden,
            num_layers=layers,
            batch_first=True,
            dropout=dropout if layers > 1 else 0.0,
        )
        self.norm = nn.LayerNorm(hidden)
        self.head = nn.Linear(hidden, vocab_size)

    def forward(self, x: torch.Tensor, h=None):
        z = self.embed(x)
        y, h = self.rnn(z, h)
        return self.head(self.norm(y)), h


def split_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    rng = random.Random(19)
    shuffled = list(rows)
    rng.shuffle(shuffled)
    cut = int(len(shuffled) * 0.9)
    return shuffled[:cut], shuffled[cut:]


def evaluate(model: TinyLM, loader: DataLoader, loss_fn, device: torch.device) -> float:
    model.eval()
    total_loss = 0.0
    total_tokens = 0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            logits, _ = model(x)
            loss = loss_fn(logits.reshape(-1, logits.size(-1)), y.reshape(-1))
            valid = (y != loss_fn.ignore_index).sum().item()
            total_loss += loss.item() * max(1, valid)
            total_tokens += max(1, valid)
    return total_loss / max(1, total_tokens)


def generate(
    model: TinyLM,
    vocab: dict[str, int],
    prompt: str,
    device: torch.device,
    max_new: int = 120,
    lane: str | None = None,
    task: str | None = None,
) -> str:
    inv = {v: k for k, v in vocab.items()}
    prefix = ["<BOS>"]
    if lane:
        prefix.extend(["<LANE>", lane])
    if task:
        prefix.extend(["<TASK>", task])
    ids = encode([*prefix, "<PROMPT>", *tokenize(prompt)[:180], "<RESPONSE>"], vocab)
    x = torch.tensor([ids], dtype=torch.long, device=device)
    model.eval()
    with torch.no_grad():
        _, h = model(x)
        cur = x[:, -1:]
        out = []
        for _ in range(max_new):
            logits, h = model(cur, h)
            next_id = int(torch.argmax(logits[:, -1, :], dim=-1).item())
            tok = inv.get(next_id, "<UNK>")
            if tok in {"<EOS>", "<PROMPT>", "<RESPONSE>", "<LANE>", "<TASK>", "<BOS>", "<PAD>"}:
                break
            out.append(tok)
            cur = torch.tensor([[next_id]], dtype=torch.long, device=device)
    return detokenize(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--max-len", type=int, default=384)
    parser.add_argument("--max-vocab", type=int, default=5000)
    parser.add_argument("--emb", type=int, default=128)
    parser.add_argument("--hidden", type=int, default=256)
    parser.add_argument("--layers", type=int, default=1)
    parser.add_argument("--dropout", type=float, default=0.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--min-task-rows", type=int, default=240)
    args = parser.parse_args()

    torch.manual_seed(29)
    random.seed(29)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    source_rows = read_rows(args.limit or None)
    rows = balance_by_task(source_rows, args.min_task_rows)
    train_rows, test_rows = split_rows(rows)
    vocab = build_vocab(train_rows, args.max_vocab)
    train_ds = SeqDataset(train_rows, vocab, args.max_len)
    test_ds = SeqDataset(test_rows, vocab, args.max_len)
    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=args.batch)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = TinyLM(len(vocab), args.emb, args.hidden, vocab["<PAD>"], layers=args.layers, dropout=args.dropout).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=0.01)
    loss_fn = nn.CrossEntropyLoss(ignore_index=vocab["<PAD>"])

    history = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        total = 0.0
        batches = 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            opt.zero_grad(set_to_none=True)
            logits, _ = model(x)
            loss = loss_fn(logits.reshape(-1, logits.size(-1)), y.reshape(-1))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            total += float(loss.item())
            batches += 1
        test_loss = evaluate(model, test_loader, loss_fn, device)
        history.append({"epoch": epoch, "train_loss": total / max(1, batches), "test_loss": test_loss, "test_ppl": math.exp(min(20, test_loss))})

    samples = [
        {
            "prompt": "Language: python Function name: add_two Doc: Add two numbers. Write the function.",
            "generation": generate(model, vocab, "Language: python Function name: add_two Doc: Add two numbers. Write the function.", device),
        },
        {
            "prompt": "Convert this python code into SCBE phase tokens: def f(a,b): return a + b",
            "generation": generate(model, vocab, "Convert this python code into SCBE phase tokens: def f(a,b): return a + b", device),
        },
        {
            "prompt": "Decode this SCBE conlang sentence into executable meaning: KO kor-vael AV A_2 AV B_3 RU ru-thar CA bip'a DR draum-sel",
            "generation": generate(model, vocab, "Decode this SCBE conlang sentence into executable meaning: KO kor-vael AV A_2 AV B_3 RU ru-thar CA bip'a DR draum-sel", device),
        },
    ]

    param_count = sum(p.numel() for p in model.parameters())
    torch.save({"model": model.state_dict(), "config": vars(args), "vocab": vocab, "param_count": param_count}, OUT_DIR / "tiny_lm.pt")
    (OUT_DIR / "vocab.json").write_text(json.dumps(vocab, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "samples.json").write_text(json.dumps(samples, indent=2, ensure_ascii=False), encoding="utf-8")
    receipt = {
        "ok": True,
        "kind": "full_bundle_tiny_lm",
        "honest_scope": "Small from-scratch token LM; proves generative training path, not finished coding skill.",
        "device": str(device),
        "config": vars(args),
        "counts": {
            "source_rows": len(source_rows),
            "rows": len(rows),
            "train": len(train_ds),
            "test": len(test_ds),
            "vocab": len(vocab),
            "parameters": param_count,
        },
        "history": history,
        "final": history[-1],
        "artifacts": {
            "model": str(OUT_DIR / "tiny_lm.pt"),
            "vocab": str(OUT_DIR / "vocab.json"),
            "samples": str(OUT_DIR / "samples.json"),
        },
    }
    (OUT_DIR / "receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    print("FULL_BUNDLE_TINY_LM_DONE")
    print(f"device: {device} rows: {len(rows)} vocab: {len(vocab)} params: {param_count:,}")
    print(f"final_test_loss: {history[-1]['test_loss']:.4f} ppl: {history[-1]['test_ppl']:.2f}")
    print(f"receipt: {OUT_DIR / 'receipt.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
