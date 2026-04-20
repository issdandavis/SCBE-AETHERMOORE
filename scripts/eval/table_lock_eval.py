"""Table-lock evaluator for Sacred Tongue coding models.

Scoreboard shared across all training routes. Measures whether a model has
memorized the fixed truth tables in src/tongues/role_registry.py.

Usage:
    python scripts/eval/table_lock_eval.py --model_path artifacts/code-flow-v1/checkpoint-200
    python scripts/eval/table_lock_eval.py --hf_id Qwen/Qwen2.5-0.5B
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.tongues.role_registry import (
    OPCODE_RUNTIME_MAP,
    PARADIGM_ISOMORPHISM_MAP,
    SPIRIT_NARRATIVE_MAP,
)

PROMPT_TEMPLATES = {
    "paradigm_isomorphism": [
        "The paradigm isomorphism language for tongue {tongue} is",
        "Tongue {tongue} maps to paradigm language:",
        "{tongue} paradigm ->",
    ],
    "spirit_narrative": [
        "The spirit narrative language for tongue {tongue} is",
        "Tongue {tongue} narrative language:",
        "{tongue} spirit ->",
    ],
    "opcode_runtime": [
        "The opcode runtime for tongue {tongue} is",
        "Tongue {tongue} opcode runtime:",
        "{tongue} opcode ->",
    ],
}

MAPS = {
    "paradigm_isomorphism": PARADIGM_ISOMORPHISM_MAP,
    "spirit_narrative": SPIRIT_NARRATIVE_MAP,
    "opcode_runtime": OPCODE_RUNTIME_MAP,
}


def load_model(source: str, device: str = "cuda"):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(source)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    mdl = AutoModelForCausalLM.from_pretrained(
        source,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    ).to(device)
    mdl.eval()
    return tok, mdl


def score_cell(tokenizer, model, prompts: list[str], expected: str, max_new: int = 6) -> dict:
    """Try each prompt template; keep the best hit. Case-insensitive contains."""
    import torch

    best = {"correct": False, "got": "", "prompt": ""}
    expected_norm = expected.strip().lower()

    for p in prompts:
        inputs = tokenizer(p, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=max_new,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
            )
        completion = tokenizer.decode(
            out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
        )
        got_norm = completion.strip().lower()
        correct = expected_norm in got_norm[: len(expected_norm) + 20]
        if correct:
            return {"correct": True, "got": completion.strip(), "prompt": p}
        if not best["got"]:
            best = {"correct": False, "got": completion.strip(), "prompt": p}

    return best


def evaluate(tokenizer, model) -> dict:
    results = {}
    total_cells = 0
    total_correct = 0

    for map_name, table in MAPS.items():
        map_results = {}
        templates = PROMPT_TEMPLATES[map_name]
        for tongue, expected in table.items():
            prompts = [t.format(tongue=tongue) for t in templates]
            cell = score_cell(tokenizer, model, prompts, expected)
            cell["expected"] = expected
            cell["tongue"] = tongue
            map_results[tongue] = cell
            total_cells += 1
            if cell["correct"]:
                total_correct += 1
        results[map_name] = map_results

    results["_summary"] = {
        "total_cells": total_cells,
        "correct": total_correct,
        "score": total_correct / total_cells if total_cells else 0.0,
    }
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_path", type=str, default=None)
    ap.add_argument("--hf_id", type=str, default=None)
    ap.add_argument("--device", type=str, default="cuda")
    ap.add_argument("--output", type=str, default=None)
    args = ap.parse_args()

    source = args.model_path or args.hf_id
    if not source:
        print("ERROR: --model_path or --hf_id required", file=sys.stderr)
        sys.exit(2)

    print(f"Loading: {source}")
    tok, mdl = load_model(source, device=args.device)
    print(f"Evaluating {sum(len(t) for t in MAPS.values())} truth-table cells...")
    results = evaluate(tok, mdl)

    summary = results["_summary"]
    print(f"\nTABLE LOCK: {summary['correct']}/{summary['total_cells']} = {summary['score']:.1%}")

    for map_name, cells in results.items():
        if map_name.startswith("_"):
            continue
        hits = sum(1 for c in cells.values() if c["correct"])
        print(f"  {map_name}: {hits}/{len(cells)}")
        for tongue, cell in cells.items():
            mark = "+" if cell["correct"] else "-"
            got_preview = cell["got"][:40].replace("\n", " ")
            print(f"    [{mark}] {tongue} -> {cell['expected']:<12} got: {got_preview!r}")

    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2))
        print(f"\nWrote: {args.output}")


if __name__ == "__main__":
    main()
