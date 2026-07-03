#!/usr/bin/env python
"""Train a tiny from-scratch probe on the full coding-systems bundle.

Purpose:
  - prove the expanded bundle is learnable
  - use the manual parameter bank as deterministic seed features
  - avoid claiming generative capability before a real fine-tune

Predicts:
  - lane
  - task
  - validated flag
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BUNDLE_DIR = ROOT / "artifacts" / "full_coding_systems_bundle"
BUNDLE = BUNDLE_DIR / "training_bundle.jsonl"
PARAM_BANK = BUNDLE_DIR / "manual_parameter_bank.json"
OUT_DIR = BUNDLE_DIR / "probe_model"


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_:'-]{2,}", str(text))[:500]


def softmax(logits: np.ndarray) -> np.ndarray:
    z = logits - logits.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def one_hot(y: np.ndarray, classes: int) -> np.ndarray:
    out = np.zeros((len(y), classes), dtype=np.float32)
    out[np.arange(len(y)), y] = 1.0
    return out


def load_data(max_vocab: int):
    rows = list(iter_jsonl(BUNDLE))
    bank = json.loads(PARAM_BANK.read_text(encoding="utf-8"))
    seed_vectors = {item["token"]: np.array(item["seed_vector_16"], dtype=np.float32) for item in bank["manual_vectors"]}
    counts = Counter()
    for row in rows:
        counts.update(tokenize(row["prompt"]))
        counts.update(tokenize(row["response"]))
    vocab_tokens = [tok for tok, _ in counts.most_common(max_vocab)]
    vocab = {tok: i for i, tok in enumerate(vocab_tokens)}
    lanes = sorted({row["lane"] for row in rows})
    tasks = sorted({row["task"] for row in rows})
    lane_idx = {v: i for i, v in enumerate(lanes)}
    task_idx = {v: i for i, v in enumerate(tasks)}
    x = np.zeros((len(rows), len(vocab) + 16), dtype=np.float32)
    y_lane = np.zeros(len(rows), dtype=np.int64)
    y_task = np.zeros(len(rows), dtype=np.int64)
    y_valid = np.zeros(len(rows), dtype=np.int64)
    for r, row in enumerate(rows):
        toks = tokenize(row["prompt"]) + tokenize(row["response"])
        seed = np.zeros(16, dtype=np.float32)
        seed_hits = 0
        for tok in toks:
            if tok in vocab:
                x[r, vocab[tok]] += 1.0
            if tok in seed_vectors:
                seed += seed_vectors[tok]
                seed_hits += 1
        norm = math.sqrt(max(1, len(toks)))
        x[r, : len(vocab)] /= norm
        if seed_hits:
            x[r, len(vocab) :] = seed / seed_hits
        y_lane[r] = lane_idx[row["lane"]]
        y_task[r] = task_idx[row["task"]]
        y_valid[r] = 1 if row.get("metadata", {}).get("validated") else 0
    order = np.random.default_rng(11).permutation(len(rows))
    split = int(len(rows) * 0.85)
    return rows, x, y_lane, y_task, y_valid, order[:split], order[split:], lanes, tasks


def init(rng, d, h, lane_n, task_n):
    return {
        "w1": rng.normal(0, math.sqrt(2 / d), (d, h)).astype(np.float32),
        "b1": np.zeros(h, dtype=np.float32),
        "wl": rng.normal(0, math.sqrt(2 / h), (h, lane_n)).astype(np.float32),
        "bl": np.zeros(lane_n, dtype=np.float32),
        "wt": rng.normal(0, math.sqrt(2 / h), (h, task_n)).astype(np.float32),
        "bt": np.zeros(task_n, dtype=np.float32),
        "wv": rng.normal(0, math.sqrt(2 / h), (h, 2)).astype(np.float32),
        "bv": np.zeros(2, dtype=np.float32),
    }


def forward(x, p):
    z = x @ p["w1"] + p["b1"]
    h = np.tanh(z)
    return h, {"lane": h @ p["wl"] + p["bl"], "task": h @ p["wt"] + p["bt"], "valid": h @ p["wv"] + p["bv"]}


def train(x, y_lane, y_task, y_valid, train_idx, lanes, tasks, epochs, hidden, lr):
    rng = np.random.default_rng(23)
    p = init(rng, x.shape[1], hidden, len(lanes), len(tasks))
    vel = {k: np.zeros_like(v) for k, v in p.items()}
    batch = min(256, len(train_idx))
    yl = one_hot(y_lane, len(lanes))
    yt = one_hot(y_task, len(tasks))
    yv = one_hot(y_valid, 2)
    losses = []
    for _ in range(epochs):
        order = rng.permutation(train_idx)
        epoch_losses = []
        for start in range(0, len(order), batch):
            idx = order[start : start + batch]
            xb = x[idx]
            h, logits = forward(xb, p)
            targets = {"lane": yl[idx], "task": yt[idx], "valid": yv[idx]}
            probs = {k: softmax(v) for k, v in logits.items()}
            grads_logits = {}
            loss = 0.0
            for k, target in targets.items():
                prob = np.clip(probs[k], 1e-8, 1)
                loss += float(-(target * np.log(prob)).sum(axis=1).mean())
                grads_logits[k] = (probs[k] - target) / len(idx)
            epoch_losses.append(loss)
            grads = {
                "wl": h.T @ grads_logits["lane"],
                "bl": grads_logits["lane"].sum(axis=0),
                "wt": h.T @ grads_logits["task"],
                "bt": grads_logits["task"].sum(axis=0),
                "wv": h.T @ grads_logits["valid"],
                "bv": grads_logits["valid"].sum(axis=0),
            }
            dh = grads_logits["lane"] @ p["wl"].T + grads_logits["task"] @ p["wt"].T + grads_logits["valid"] @ p["wv"].T
            dz = dh * (1 - h * h)
            grads["w1"] = xb.T @ dz
            grads["b1"] = dz.sum(axis=0)
            for key in p:
                vel[key] = 0.9 * vel[key] + grads[key]
                p[key] -= lr * vel[key]
        losses.append(float(np.mean(epoch_losses)))
    return p, losses


def metrics(x, y_lane, y_task, y_valid, idx, p):
    _, logits = forward(x[idx], p)
    pred_lane = softmax(logits["lane"]).argmax(axis=1)
    pred_task = softmax(logits["task"]).argmax(axis=1)
    pred_valid = softmax(logits["valid"]).argmax(axis=1)
    return {
        "lane_acc": round(float((pred_lane == y_lane[idx]).mean()), 4),
        "task_acc": round(float((pred_task == y_task[idx]).mean()), 4),
        "valid_acc": round(float((pred_valid == y_valid[idx]).mean()), 4),
        "n": int(len(idx)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=220)
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--lr", type=float, default=0.08)
    parser.add_argument("--max-vocab", type=int, default=1600)
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows, x, y_lane, y_task, y_valid, train_idx, test_idx, lanes, tasks = load_data(args.max_vocab)
    p, losses = train(x, y_lane, y_task, y_valid, train_idx, lanes, tasks, args.epochs, args.hidden, args.lr)
    np.savez_compressed(OUT_DIR / "model.npz", **p)
    receipt = {
        "ok": True,
        "kind": "full_bundle_probe",
        "honest_scope": "Small classifier probe over expanded bundle; not a generative model.",
        "config": vars(args),
        "counts": {"rows": len(rows), "features": x.shape[1], "lanes": lanes, "tasks": tasks},
        "final_loss": round(losses[-1], 6),
        "train": metrics(x, y_lane, y_task, y_valid, train_idx, p),
        "test": metrics(x, y_lane, y_task, y_valid, test_idx, p),
    }
    (OUT_DIR / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("FULL_BUNDLE_PROBE_DONE")
    print(f"rows: {len(rows)} features: {x.shape[1]} hidden: {args.hidden}")
    print(f"final_loss: {losses[-1]:.4f}")
    print("heldout:", receipt["test"])
    print(f"receipt: {OUT_DIR / 'receipt.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
