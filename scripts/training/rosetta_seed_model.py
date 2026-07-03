#!/usr/bin/env python
"""Rosetta Seed Model: train a tiny conlang+code model from random weights.

This is intentionally small and honest:
  - no pretrained model
  - no cloud
  - synthetic closed-world conlang/code curriculum
  - verifier judges predicted programs by execution semantics

The model learns:
  conlang phase grammar -> valid/invalid
  CA words / word chains -> executable program class
  program class -> Python code template
  program + inputs -> result class

It is not a general language model. It is a seed proof that a model can be born
inside the conlang/opcode substrate and trained toward executable meaning.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / "artifacts" / "rosetta_seed"


@dataclass(frozen=True)
class Program:
    name: str
    ca_words: tuple[str, ...]
    code: str
    fn: Callable[[int, int], int]


PROGRAMS: list[Program] = [
    Program("add", ("bip'a",), "def f(a,b): return a + b", lambda a, b: a + b),
    Program("mul", ("bip'i",), "def f(a,b): return a * b", lambda a, b: a * b),
    Program("sub", ("rahn",), "def f(a,b): return a - b", lambda a, b: a - b),
    Program("max", ("voth",), "def f(a,b): return max(a, b)", lambda a, b: max(a, b)),
    Program("min", ("mira",), "def f(a,b): return min(a, b)", lambda a, b: min(a, b)),
    Program("add_inc", ("bip'a", "sul'a"), "def f(a,b): return (a + b) + 1", lambda a, b: a + b + 1),
    Program("mul_dec", ("bip'i", "dor'a"), "def f(a,b): return (a * b) - 1", lambda a, b: a * b - 1),
    Program("add_clamp", ("bip'a", "klik'ra"), "def f(a,b): return min(max(a + b, 0), 9)", lambda a, b: min(max(a + b, 0), 9)),
    Program("mul_clamp", ("bip'i", "klik'ra"), "def f(a,b): return min(max(a * b, 0), 9)", lambda a, b: min(max(a * b, 0), 9)),
    Program("sub_abs", ("rahn", "lum'a"), "def f(a,b): return abs(a - b)", lambda a, b: abs(a - b)),
]

PROGRAM_BY_NAME = {program.name: program for program in PROGRAMS}
PROGRAM_INDEX = {program.name: i for i, program in enumerate(PROGRAMS)}
INVALID_PROGRAM = len(PROGRAMS)
PROGRAM_LABELS = [program.name for program in PROGRAMS] + ["INVALID"]
RESULT_VALUES = list(range(-10, 82)) + ["INVALID"]
RESULT_INDEX = {value: i for i, value in enumerate(RESULT_VALUES)}
INVALID_RESULT = RESULT_INDEX["INVALID"]


def phase_sentence(program: Program, a: int, b: int, variant: int = 0) -> list[str]:
    intent = "kor-vael" if variant % 2 == 0 else "ko-build"
    permit = "ru-thar" if variant % 3 else "ru-allow"
    seal = "draum-sel" if variant % 2 == 0 else "dr-seal"
    return [
        "KO",
        intent,
        "AV",
        f"A_{a}",
        "AV",
        f"B_{b}",
        "RU",
        permit,
        *sum((["CA", word] for word in program.ca_words), []),
        "DR",
        seal,
    ]


def make_invalid(program: Program, a: int, b: int, kind: int) -> list[str]:
    base = phase_sentence(program, a, b, kind)
    if kind % 4 == 0:
        # CA before RU: illegal phase order.
        return ["KO", "kor-vael", "AV", f"A_{a}", "AV", f"B_{b}", "CA", program.ca_words[0], "RU", "ru-thar", "DR", "draum-sel"]
    if kind % 4 == 1:
        # Missing DR seal.
        return base[:-2]
    if kind % 4 == 2:
        # Unknown CA word.
        mutated = list(base)
        mutated[mutated.index(program.ca_words[0])] = "blorf"
        return mutated
    # Wrong lane after seal.
    return base + ["CA", "bip'a"]


def build_records() -> list[dict]:
    records: list[dict] = []
    for p_idx, program in enumerate(PROGRAMS):
        for a in range(10):
            for b in range(10):
                result = program.fn(a, b)
                for variant in range(2):
                    tokens = phase_sentence(program, a, b, variant)
                    records.append(
                        {
                            "tokens": tokens,
                            "text": " ".join(tokens),
                            "a": a,
                            "b": b,
                            "valid": 1,
                            "program": program.name,
                            "program_idx": p_idx,
                            "result": result,
                            "result_idx": RESULT_INDEX[result],
                            "code": program.code,
                            "code_idx": p_idx,
                            "split": "test" if ((a * 13 + b * 7 + p_idx * 5 + variant) % 11 == 0) else "train",
                        }
                    )
                if (a + b + p_idx) % 3 == 0:
                    tokens = make_invalid(program, a, b, a + b + p_idx)
                    records.append(
                        {
                            "tokens": tokens,
                            "text": " ".join(tokens),
                            "a": a,
                            "b": b,
                            "valid": 0,
                            "program": "INVALID",
                            "program_idx": INVALID_PROGRAM,
                            "result": "INVALID",
                            "result_idx": INVALID_RESULT,
                            "code": "INVALID",
                            "code_idx": INVALID_PROGRAM,
                            "split": "test" if ((a * 5 + b * 3 + p_idx) % 7 == 0) else "train",
                        }
                    )
    random.Random(7).shuffle(records)
    return records


def build_feature_vocab(records: list[dict]) -> dict[str, int]:
    feats: set[str] = set()
    for rec in records:
        tokens = rec["tokens"]
        for token in tokens:
            feats.add(f"tok:{token}")
        for left, right in zip(tokens, tokens[1:]):
            feats.add(f"bi:{left}>{right}")
        for idx, token in enumerate(tokens[:16]):
            feats.add(f"pos:{idx}:{token}")
        feats.add(f"first:{tokens[0] if tokens else '<EMPTY>'}")
        feats.add(f"last:{tokens[-1] if tokens else '<EMPTY>'}")
    return {feat: i for i, feat in enumerate(sorted(feats))}


def vectorize(records: list[dict], vocab: dict[str, int]) -> np.ndarray:
    x = np.zeros((len(records), len(vocab)), dtype=np.float32)
    for row, rec in enumerate(records):
        tokens = rec["tokens"]
        feats = []
        feats.extend(f"tok:{token}" for token in tokens)
        feats.extend(f"bi:{left}>{right}" for left, right in zip(tokens, tokens[1:]))
        feats.extend(f"pos:{idx}:{token}" for idx, token in enumerate(tokens[:16]))
        feats.append(f"first:{tokens[0] if tokens else '<EMPTY>'}")
        feats.append(f"last:{tokens[-1] if tokens else '<EMPTY>'}")
        for feat in feats:
            col = vocab.get(feat)
            if col is not None:
                x[row, col] += 1.0
        norm = math.sqrt(max(1, len(feats)))
        x[row] /= norm
    return x


def one_hot(labels: np.ndarray, classes: int) -> np.ndarray:
    y = np.zeros((len(labels), classes), dtype=np.float32)
    y[np.arange(len(labels)), labels] = 1.0
    return y


def softmax(logits: np.ndarray) -> np.ndarray:
    z = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(z)
    return exp / exp.sum(axis=1, keepdims=True)


def init_params(rng: np.random.Generator, d_in: int, h: int) -> dict[str, np.ndarray]:
    scale1 = math.sqrt(2.0 / max(1, d_in))
    scaleh = math.sqrt(2.0 / h)
    return {
        "w1": rng.normal(0, scale1, (d_in, h)).astype(np.float32),
        "b1": np.zeros(h, dtype=np.float32),
        "wv": rng.normal(0, scaleh, (h, 2)).astype(np.float32),
        "bv": np.zeros(2, dtype=np.float32),
        "wp": rng.normal(0, scaleh, (h, len(PROGRAM_LABELS))).astype(np.float32),
        "bp": np.zeros(len(PROGRAM_LABELS), dtype=np.float32),
        "wr": rng.normal(0, scaleh, (h, len(RESULT_VALUES))).astype(np.float32),
        "br": np.zeros(len(RESULT_VALUES), dtype=np.float32),
        "wc": rng.normal(0, scaleh, (h, len(PROGRAM_LABELS))).astype(np.float32),
        "bc": np.zeros(len(PROGRAM_LABELS), dtype=np.float32),
    }


def forward(x: np.ndarray, params: dict[str, np.ndarray]) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    z1 = x @ params["w1"] + params["b1"]
    h = np.tanh(z1)
    return h, {
        "valid": h @ params["wv"] + params["bv"],
        "program": h @ params["wp"] + params["bp"],
        "result": h @ params["wr"] + params["br"],
        "code": h @ params["wc"] + params["bc"],
    }


def train(
    x: np.ndarray,
    y_valid: np.ndarray,
    y_program: np.ndarray,
    y_result: np.ndarray,
    y_code: np.ndarray,
    epochs: int,
    hidden: int,
    lr: float,
    seed: int,
) -> tuple[dict[str, np.ndarray], list[float]]:
    rng = np.random.default_rng(seed)
    params = init_params(rng, x.shape[1], hidden)
    velocity = {k: np.zeros_like(v) for k, v in params.items()}
    losses: list[float] = []
    n = x.shape[0]
    batch_size = min(256, n)

    for epoch in range(epochs):
        order = rng.permutation(n)
        epoch_losses = []
        for start in range(0, n, batch_size):
            idx = order[start : start + batch_size]
            xb = x[idx]
            targets = {
                "valid": y_valid[idx],
                "program": y_program[idx],
                "result": y_result[idx],
                "code": y_code[idx],
            }
            h, logits = forward(xb, params)
            probs = {name: softmax(value) for name, value in logits.items()}
            loss = 0.0
            grads_logits = {}
            for name, target in targets.items():
                p = np.clip(probs[name], 1e-8, 1.0)
                loss += float(-(target * np.log(p)).sum(axis=1).mean())
                grads_logits[name] = (probs[name] - target) / len(xb)
            epoch_losses.append(loss)

            grads: dict[str, np.ndarray] = {}
            grads["wv"] = h.T @ grads_logits["valid"]
            grads["bv"] = grads_logits["valid"].sum(axis=0)
            grads["wp"] = h.T @ grads_logits["program"]
            grads["bp"] = grads_logits["program"].sum(axis=0)
            grads["wr"] = h.T @ grads_logits["result"]
            grads["br"] = grads_logits["result"].sum(axis=0)
            grads["wc"] = h.T @ grads_logits["code"]
            grads["bc"] = grads_logits["code"].sum(axis=0)
            dh = (
                grads_logits["valid"] @ params["wv"].T
                + grads_logits["program"] @ params["wp"].T
                + grads_logits["result"] @ params["wr"].T
                + grads_logits["code"] @ params["wc"].T
            )
            dz = dh * (1.0 - h * h)
            grads["w1"] = xb.T @ dz
            grads["b1"] = dz.sum(axis=0)

            for key in params:
                velocity[key] = 0.9 * velocity[key] + grads[key]
                params[key] -= lr * velocity[key]
        losses.append(float(np.mean(epoch_losses)))
    return params, losses


def predict(x: np.ndarray, params: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    _, logits = forward(x, params)
    return {name: softmax(value).argmax(axis=1) for name, value in logits.items()}


def evaluate(records: list[dict], x: np.ndarray, params: dict[str, np.ndarray]) -> dict:
    pred = predict(x, params)
    valid_true = np.array([rec["valid"] for rec in records], dtype=np.int64)
    program_true = np.array([rec["program_idx"] for rec in records], dtype=np.int64)
    result_true = np.array([rec["result_idx"] for rec in records], dtype=np.int64)
    code_true = np.array([rec["code_idx"] for rec in records], dtype=np.int64)

    valid_acc = float((pred["valid"] == valid_true).mean())
    program_acc = float((pred["program"] == program_true).mean())
    result_acc = float((pred["result"] == result_true).mean())
    code_acc = float((pred["code"] == code_true).mean())

    verifier_pass = 0
    valid_total = 0
    invalid_reject = 0
    invalid_total = 0
    examples = []
    for i, rec in enumerate(records):
        predicted_valid = int(pred["valid"][i])
        predicted_program_idx = int(pred["program"][i])
        predicted_result_idx = int(pred["result"][i])
        predicted_code_idx = int(pred["code"][i])
        predicted_program = PROGRAM_LABELS[predicted_program_idx]
        predicted_result = RESULT_VALUES[predicted_result_idx]
        if rec["valid"]:
            valid_total += 1
            if predicted_valid == 1 and predicted_program in PROGRAM_BY_NAME:
                computed = PROGRAM_BY_NAME[predicted_program].fn(rec["a"], rec["b"])
                if computed == rec["result"]:
                    verifier_pass += 1
        else:
            invalid_total += 1
            if predicted_valid == 0:
                invalid_reject += 1
        if len(examples) < 12:
            examples.append(
                {
                    "text": rec["text"],
                    "truth": {
                        "valid": bool(rec["valid"]),
                        "program": rec["program"],
                        "result": rec["result"],
                        "code": rec["code"],
                    },
                    "pred": {
                        "valid": bool(predicted_valid),
                        "program": predicted_program,
                        "result": predicted_result,
                        "code": PROGRAM_LABELS[predicted_code_idx],
                    },
                }
            )
    return {
        "valid_acc": round(valid_acc, 4),
        "program_acc": round(program_acc, 4),
        "result_acc": round(result_acc, 4),
        "code_acc": round(code_acc, 4),
        "verifier_exec_pass": round(verifier_pass / max(1, valid_total), 4),
        "invalid_reject": round(invalid_reject / max(1, invalid_total), 4),
        "valid_total": valid_total,
        "invalid_total": invalid_total,
        "examples": examples,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=260)
    parser.add_argument("--hidden", type=int, default=96)
    parser.add_argument("--lr", type=float, default=0.09)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    records = build_records()
    train_records = [rec for rec in records if rec["split"] == "train"]
    test_records = [rec for rec in records if rec["split"] == "test"]
    vocab = build_feature_vocab(train_records)
    x_train = vectorize(train_records, vocab)
    x_test = vectorize(test_records, vocab)

    y_train_valid = one_hot(np.array([rec["valid"] for rec in train_records]), 2)
    y_train_program = one_hot(np.array([rec["program_idx"] for rec in train_records]), len(PROGRAM_LABELS))
    y_train_result = one_hot(np.array([rec["result_idx"] for rec in train_records]), len(RESULT_VALUES))
    y_train_code = one_hot(np.array([rec["code_idx"] for rec in train_records]), len(PROGRAM_LABELS))

    params, losses = train(
        x_train,
        y_train_valid,
        y_train_program,
        y_train_result,
        y_train_code,
        epochs=args.epochs,
        hidden=args.hidden,
        lr=args.lr,
        seed=args.seed,
    )
    train_metrics = evaluate(train_records, x_train, params)
    test_metrics = evaluate(test_records, x_test, params)

    dataset_path = ARTIFACT_DIR / "dataset.jsonl"
    with dataset_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    model_path = ARTIFACT_DIR / "model.npz"
    np.savez_compressed(model_path, **params)

    receipt = {
        "ok": True,
        "kind": "rosetta_seed_from_scratch",
        "description": "Tiny random-initialized NumPy MLP trained on conlang phase grammar + CA opcode chains + code/result labels.",
        "honest_scope": "Closed-world seed proof; not a general coder or general language model.",
        "config": vars(args),
        "counts": {
            "records": len(records),
            "train": len(train_records),
            "test": len(test_records),
            "features": len(vocab),
            "programs": len(PROGRAMS),
        },
        "artifacts": {
            "dataset": str(dataset_path),
            "model": str(model_path),
        },
        "final_loss": round(losses[-1], 6),
        "train": train_metrics,
        "test": test_metrics,
    }
    receipt_path = ARTIFACT_DIR / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")

    examples_path = ARTIFACT_DIR / "examples.json"
    examples_path.write_text(json.dumps(test_metrics["examples"], indent=2, ensure_ascii=False), encoding="utf-8")

    print("ROSETTA_SEED_DONE")
    print(f"records train/test: {len(train_records)}/{len(test_records)}")
    print(f"features: {len(vocab)} hidden: {args.hidden} epochs: {args.epochs}")
    print(f"final_loss: {losses[-1]:.4f}")
    print("heldout:")
    for key in ["valid_acc", "program_acc", "code_acc", "result_acc", "verifier_exec_pass", "invalid_reject"]:
        print(f"  {key}: {test_metrics[key]}")
    print(f"receipt: {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
