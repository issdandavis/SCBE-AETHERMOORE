#!/usr/bin/env python3
"""Hugging Face long-run training driver with local training + growth monitoring.

This script trains a lightweight hashed-embedding softmax model over JSONL records,
tracks growth over epochs, and optionally uploads artifacts to a Hugging Face model repo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

try:
    from huggingface_hub import HfApi, get_token
except Exception:  # noqa: BLE001
    HfApi = None  # type: ignore[assignment]
    get_token = None  # type: ignore[assignment]


TOKEN_RE = re.compile(r"[A-Za-z0-9_:/.-]+")
DEFAULT_PATTERNS = ("training/**/*.jsonl", "training-data/**/*.jsonl")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hugging Face long-run trainer")
    parser.add_argument("--dataset-repo", required=True, help="HF dataset repo identifier")
    parser.add_argument("--model-repo", required=True, help="HF model repo identifier")
    parser.add_argument("--duration-hours", type=float, default=8.0, help="Run duration budget")
    parser.add_argument("--run-dir", default="training/runs/huggingface", help="Run directory for artifacts")
    parser.add_argument("--plan", default=None, help="Optional extra run metadata JSON path")
    parser.add_argument("--epochs", type=int, default=12, help="Training epochs")
    parser.add_argument("--embedding-dim", type=int, default=256, help="Hashed embedding dimension")
    parser.add_argument("--learning-rate", type=float, default=0.15, help="Initial SGD learning rate")
    parser.add_argument("--val-ratio", type=float, default=0.2, help="Validation ratio")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--max-samples", type=int, default=40000, help="Maximum records to load")
    parser.add_argument(
        "--local-glob",
        action="append",
        default=[],
        help="Glob pattern for local training data (repeatable). Defaults to training/**/*.jsonl + training-data/**/*.jsonl",
    )
    parser.add_argument("--push-to-hub", dest="push_to_hub", action="store_true", help="Upload artifacts to Hugging Face model repo")
    parser.add_argument("--no-push-to-hub", dest="push_to_hub", action="store_false", help="Skip HF upload")
    parser.set_defaults(push_to_hub=True)
    return parser.parse_args()


def _sid(v: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", v).strip("-") or "run"


def _text_from_record(row: dict[str, Any]) -> str:
    # SFT instruction-response format
    inst = row.get("instruction")
    resp = row.get("response")
    if isinstance(inst, str) and isinstance(resp, str):
        text = f"{inst.strip()} {resp.strip()}".strip()
        if text:
            return text

    # Chat-messages format
    msgs = row.get("messages")
    if isinstance(msgs, list):
        parts: list[str] = []
        for m in msgs:
            if not isinstance(m, dict):
                continue
            role = str(m.get("role", "")).strip().lower()
            content = str(m.get("content", "")).strip()
            if not content:
                continue
            if role in {"user", "assistant", "system"}:
                parts.append(content)
        joined = " ".join(parts).strip()
        if joined:
            return joined

    parts: list[str] = []
    for key in (
        "dataset",
        "event_type",
        "message",
        "reason",
        "product",
        "status",
        "run_id",
        "images_dir",
        "run_manifest",
    ):
        val = row.get(key)
        if val is not None:
            parts.append(str(val))
    payload = row.get("event_payload")
    if payload is not None:
        if isinstance(payload, dict):
            parts.append(json.dumps(payload, sort_keys=True))
        else:
            parts.append(str(payload))
    targets = row.get("targets")
    if isinstance(targets, list):
        parts.extend(str(x) for x in targets)
    return " ".join(parts).strip()


def _label_from_record(row: dict[str, Any]) -> str:
    # SFT format labels
    cat = str(row.get("category", "")).strip()
    if cat:
        return cat
    if isinstance(row.get("meta"), dict):
        source_type = str(row["meta"].get("source_type", "")).strip()
        if source_type:
            return source_type

    for key in ("event_type", "dataset", "status"):
        val = str(row.get(key, "")).strip()
        if val:
            return val
    return "unknown"


def load_samples(patterns: list[str], max_samples: int) -> list[tuple[str, str, str]]:
    items: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for pattern in patterns:
        for path in sorted(Path(".").glob(pattern)):
            if not path.is_file():
                continue
            try:
                with path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            row = json.loads(line)
                        except Exception:  # noqa: BLE001
                            continue
                        if not isinstance(row, dict):
                            continue
                        text = _text_from_record(row)
                        label = _label_from_record(row)
                        if not text:
                            continue
                        key = hashlib.sha256(f"{label}::{text}".encode("utf-8")).hexdigest()
                        if key in seen:
                            continue
                        seen.add(key)
                        items.append((text, label, str(path)))
                        if len(items) >= max_samples:
                            return items
            except Exception:  # noqa: BLE001
                continue
    return items


def augment_samples(samples: list[tuple[str, str, str]], min_count: int) -> list[tuple[str, str, str]]:
    if len(samples) >= min_count:
        return samples
    out = list(samples)
    for text, label, src in samples:
        toks = _tokenize(text)
        if len(toks) < 6:
            continue
        cuts = [len(toks) // 2, max(1, len(toks) // 3), max(1, (2 * len(toks)) // 3)]
        variants = [
            " ".join(toks[: cuts[0]]),
            " ".join(toks[cuts[0] :]),
            " ".join(toks[: cuts[1]] + toks[cuts[2] :]),
            " ".join(toks[::2]),
        ]
        for v in variants:
            if len(v.strip()) < 12:
                continue
            out.append((v, label, f"{src}#aug"))
            if len(out) >= min_count:
                return out
    while len(out) < min_count:
        out.append(random.choice(samples))
    return out


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def hashed_embedding(text: str, dim: int) -> np.ndarray:
    vec = np.zeros((dim,), dtype=np.float32)
    for tok in _tokenize(text):
        h = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(h[:4], byteorder="big", signed=False) % dim
        sign = -1.0 if (h[4] & 1) else 1.0
        vec[idx] += sign
    n = float(np.linalg.norm(vec))
    if n > 0:
        vec /= n
    return vec


def vectorize(texts: list[str], dim: int) -> np.ndarray:
    mat = np.zeros((len(texts), dim), dtype=np.float32)
    for i, t in enumerate(texts):
        mat[i] = hashed_embedding(t, dim)
    return mat


def softmax(logits: np.ndarray) -> np.ndarray:
    x = logits - logits.max(axis=1, keepdims=True)
    ex = np.exp(x)
    return ex / ex.sum(axis=1, keepdims=True)


def cross_entropy(probs: np.ndarray, y: np.ndarray) -> float:
    eps = 1e-9
    rows = np.arange(y.shape[0])
    return float(-np.mean(np.log(probs[rows, y] + eps)))


def accuracy(probs: np.ndarray, y: np.ndarray) -> float:
    pred = np.argmax(probs, axis=1)
    return float(np.mean((pred == y).astype(np.float32)))


def train_model(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    epochs: int,
    learning_rate: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, float]]]:
    rng = np.random.default_rng(seed)
    n_classes = int(max(y_train.max(initial=0), y_val.max(initial=0))) + 1
    dim = x_train.shape[1]
    w = rng.normal(loc=0.0, scale=0.01, size=(n_classes, dim)).astype(np.float32)
    b = np.zeros((n_classes,), dtype=np.float32)

    history: list[dict[str, float]] = []
    n = x_train.shape[0]
    one_hot = np.zeros((n, n_classes), dtype=np.float32)
    one_hot[np.arange(n), y_train] = 1.0

    for epoch in range(1, epochs + 1):
        lr = learning_rate * (0.97 ** (epoch - 1))
        logits = x_train @ w.T + b
        probs = softmax(logits)
        loss_train = cross_entropy(probs, y_train)
        acc_train = accuracy(probs, y_train)

        grad = (probs - one_hot) / float(n)
        grad_w = grad.T @ x_train
        grad_b = grad.mean(axis=0)
        w -= lr * grad_w
        b -= lr * grad_b

        val_probs = softmax(x_val @ w.T + b)
        loss_val = cross_entropy(val_probs, y_val)
        acc_val = accuracy(val_probs, y_val)
        history.append(
            {
                "epoch": float(epoch),
                "learning_rate": float(lr),
                "train_loss": float(loss_train),
                "train_accuracy": float(acc_train),
                "val_loss": float(loss_val),
                "val_accuracy": float(acc_val),
            }
        )
    return w, b, history


def upload_to_hf(model_repo: str, run_dir: Path, token: str, report: dict[str, Any]) -> dict[str, Any]:
    if HfApi is None:
        return {"status": "skipped", "reason": "huggingface_hub not installed"}
    api = HfApi(token=token)
    branch_prefix = f"training_runs/{_sid(report['run_id'])}"
    try:
        api.create_repo(repo_id=model_repo, repo_type="model", exist_ok=True)
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "reason": f"create_repo: {exc}"}

    uploaded: list[str] = []
    for name in ("hf_training_metrics.json", "model_weights.npz", "label_map.json", "training_growth_summary.md"):
        p = run_dir / name
        if not p.exists():
            continue
        api.upload_file(
            path_or_fileobj=str(p),
            path_in_repo=f"{branch_prefix}/{name}",
            repo_id=model_repo,
            repo_type="model",
            commit_message=f"Add training artifact {name} for {report['run_id']}",
        )
        uploaded.append(f"{branch_prefix}/{name}")
    return {"status": "ok", "uploaded_files": uploaded}


def main() -> int:
    args = parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)

    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    patterns = args.local_glob or list(DEFAULT_PATTERNS)
    samples = load_samples(patterns, max_samples=args.max_samples)
    if len(samples) < 8:
        raise RuntimeError(f"Not enough samples for training (found {len(samples)}). Add more JSONL data first.")
    if len(samples) < 24:
        samples = augment_samples(samples, min_count=24)

    random.shuffle(samples)
    texts = [s[0] for s in samples]
    labels = [s[1] for s in samples]
    label_names = sorted(set(labels))
    label_to_id = {v: i for i, v in enumerate(label_names)}
    y = np.array([label_to_id[v] for v in labels], dtype=np.int64)

    x = vectorize(texts, args.embedding_dim)
    split = max(1, int((1.0 - args.val_ratio) * len(samples)))
    split = min(split, len(samples) - 1)
    x_train, x_val = x[:split], x[split:]
    y_train, y_val = y[:split], y[split:]

    w, b, history = train_model(
        x_train=x_train,
        y_train=y_train,
        x_val=x_val,
        y_val=y_val,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        seed=args.seed,
    )

    first = history[0]
    best = max(history, key=lambda m: m["val_accuracy"])
    last = history[-1]
    growth = {
        "val_accuracy_gain": round(last["val_accuracy"] - first["val_accuracy"], 6),
        "val_loss_drop": round(first["val_loss"] - last["val_loss"], 6),
        "best_val_accuracy": round(best["val_accuracy"], 6),
        "best_epoch": int(best["epoch"]),
    }
    growth_confirmed = bool((growth["val_accuracy_gain"] > 0.01) or (growth["val_loss_drop"] > 0.02))

    report: dict[str, Any] = {
        "provider": "huggingface",
        "status": "completed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "dataset_repo": args.dataset_repo,
        "model_repo": args.model_repo,
        "duration_hours": args.duration_hours,
        "run_dir": str(run_dir),
        "input_plan": args.plan,
        "data": {
            "patterns": patterns,
            "sample_count": len(samples),
            "train_count": int(x_train.shape[0]),
            "val_count": int(x_val.shape[0]),
            "label_count": len(label_names),
            "labels": label_names,
        },
        "training": {
            "epochs": args.epochs,
            "embedding_dim": args.embedding_dim,
            "learning_rate": args.learning_rate,
            "seed": args.seed,
            "history": history,
        },
        "growth": {"confirmed": growth_confirmed, **growth},
    }

    (run_dir / "label_map.json").write_text(json.dumps(label_to_id, indent=2), encoding="utf-8")
    np.savez(run_dir / "model_weights.npz", w=w, b=b)
    (run_dir / "hf_training_metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (run_dir / "training_growth_summary.md").write_text(
        "\n".join(
            [
                "# HF Training Growth Summary",
                "",
                f"- run_id: `{run_id}`",
                f"- samples: `{len(samples)}` (train `{x_train.shape[0]}`, val `{x_val.shape[0]}`)",
                f"- labels: `{len(label_names)}`",
                f"- first val_accuracy: `{first['val_accuracy']:.4f}`",
                f"- last val_accuracy: `{last['val_accuracy']:.4f}`",
                f"- best val_accuracy: `{best['val_accuracy']:.4f}` (epoch {int(best['epoch'])})",
                f"- val_loss drop: `{growth['val_loss_drop']:.4f}`",
                f"- growth_confirmed: `{growth_confirmed}`",
            ]
        ),
        encoding="utf-8",
    )

    hf_token = os.getenv("HF_TOKEN", "").strip()
    if not hf_token and get_token is not None:
        try:
            hf_token = (get_token() or "").strip()
        except Exception:  # noqa: BLE001
            hf_token = ""
    upload_result = {"status": "skipped", "reason": "HF_TOKEN missing or upload disabled"}
    if args.push_to_hub and hf_token:
        upload_result = upload_to_hf(args.model_repo, run_dir, hf_token, report)
    report["huggingface_upload"] = upload_result
    (run_dir / "hf_training_metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("HF long-run training completed.")
    print("Run dir:", run_dir)
    print("Growth confirmed:", growth_confirmed)
    print("Val accuracy first/last:", f"{first['val_accuracy']:.4f}", "->", f"{last['val_accuracy']:.4f}")
    print("Val loss first/last:", f"{first['val_loss']:.4f}", "->", f"{last['val_loss']:.4f}")
    print("HF upload:", upload_result.get("status"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
