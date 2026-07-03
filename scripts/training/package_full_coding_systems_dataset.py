#!/usr/bin/env python
"""Package the full coding-systems bundle into a trainable dataset release.

This turns the working bundle into an artifact that can be used by local,
Colab, or Hugging Face jobs:
  - deterministic train/validation/test JSONL splits
  - SHA-256 hashes for every split
  - dataset card
  - run config
  - handoff manifest
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "artifacts" / "full_coding_systems_bundle" / "training_bundle.jsonl"
OUT_DIR = ROOT / "artifacts" / "full_coding_systems_bundle" / "dataset_release"


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def to_chat_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "messages": [
            {
                "role": "system",
                "content": "You are training inside SCBE-AETHERMOORE. Preserve source provenance, binary views, SCBE tokens, verifier gates, and honest scope.",
            },
            {"role": "user", "content": row["prompt"]},
            {"role": "assistant", "content": row["response"]},
        ],
        "metadata": {
            "lane": row["lane"],
            "task": row["task"],
            "source": row.get("metadata", {}).get("source", {}),
            "validated": row.get("metadata", {}).get("validated", False),
        },
    }


def split_rows(rows: list[dict], seed: int) -> tuple[list[dict], list[dict], list[dict]]:
    by_lane: dict[str, list[dict]] = {}
    for row in rows:
        by_lane.setdefault(row["lane"], []).append(row)
    rng = random.Random(seed)
    train: list[dict] = []
    val: list[dict] = []
    test: list[dict] = []
    for lane_rows in by_lane.values():
        lane_rows = list(lane_rows)
        rng.shuffle(lane_rows)
        n = len(lane_rows)
        val_n = max(1, int(n * 0.08)) if n >= 10 else 0
        test_n = max(1, int(n * 0.08)) if n >= 10 else 0
        test.extend(lane_rows[:test_n])
        val.extend(lane_rows[test_n : test_n + val_n])
        train.extend(lane_rows[test_n + val_n :])
    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    return train, val, test


def write_card(path: Path, counts: dict, files: dict) -> None:
    path.write_text(
        "\n".join(
            [
                "# SCBE Full Coding Systems Bundle",
                "",
                "A source-grounded multi-view dataset for SCBE-AETHERMOORE coding systems.",
                "",
                "## Contents",
                "",
                "- Rosetta/conlang to executable program rows",
                "- CodeSearchNet-derived code/doc rows",
                "- Binary views: UTF-8, UTF-16LE, UTF-32LE, bytes, hex, bits, nibbles, base64, base64url, ASCII85, byte histograms, SHA-256",
                "- Labyrinth curriculum paths",
                "- Verifier-gate prediction rows",
                "- Official/free language manual source pointers",
                "- GitHub user guide source lane",
                "- Recovered books/patents/SCBE docs with hashes and provenance",
                "",
                "## Honest Scope",
                "",
                "This is a training substrate, not proof of model improvement. Model claims require held-out evaluation after training.",
                "",
                "Recovered and lore rows are context/provenance lanes, not execution proof.",
                "",
                "## Counts",
                "",
                "```json",
                json.dumps(counts, indent=2),
                "```",
                "",
                "## Files",
                "",
                "```json",
                json.dumps(files, indent=2),
                "```",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=101)
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = list(iter_jsonl(BUNDLE))
    train, val, test = split_rows(rows, args.seed)
    splits = {"train": train, "validation": val, "test": test}
    files = {}
    chat_files = {}
    for name, split_rows_ in splits.items():
        path = OUT_DIR / f"{name}.jsonl"
        write_jsonl(path, split_rows_)
        files[name] = {"path": str(path), "rows": len(split_rows_), "sha256": sha256_file(path)}
        chat_path = OUT_DIR / f"{name}_chat.jsonl"
        write_jsonl(chat_path, [to_chat_row(row) for row in split_rows_])
        chat_files[f"{name}_chat"] = {"path": str(chat_path), "rows": len(split_rows_), "sha256": sha256_file(chat_path)}

    lane_counts = Counter(row["lane"] for row in rows)
    task_counts = Counter(row["task"] for row in rows)
    counts = {
        "total": len(rows),
        "splits": {name: len(split_rows_) for name, split_rows_ in splits.items()},
        "lanes": dict(lane_counts.most_common()),
        "tasks": dict(task_counts.most_common()),
    }
    all_files = {**files, **chat_files}
    card_path = OUT_DIR / "README.md"
    write_card(card_path, counts, all_files)

    run_config = {
        "dataset": "scbe_full_coding_systems_bundle",
        "recommended_start": "small local/Colab SFT or tokenizer pretraining probe",
        "train_file": files["train"]["path"],
        "validation_file": files["validation"]["path"],
        "test_file": files["test"]["path"],
        "chat_train_file": chat_files["train_chat"]["path"],
        "objectives": [
            "prompt_to_response",
            "code_to_binary_views",
            "code_to_scbe_tokens",
            "path_to_goal",
            "predict_verifier_gate",
        ],
        "do_not_claim": [
            "general coder improvement before held-out eval",
            "manual source copied in full",
            "recovered lore as execution proof",
        ],
    }
    config_path = OUT_DIR / "run_config.json"
    config_path.write_text(json.dumps(run_config, indent=2), encoding="utf-8")

    manifest = {
        "ok": True,
        "kind": "scbe_full_coding_systems_dataset_release",
        "seed": args.seed,
        "counts": counts,
        "files": all_files,
        "dataset_card": str(card_path),
        "run_config": str(config_path),
    }
    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("FULL_CODING_SYSTEMS_DATASET_RELEASE_DONE")
    print(f"rows: {len(rows)} train/val/test: {len(train)}/{len(val)}/{len(test)}")
    print(f"manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
