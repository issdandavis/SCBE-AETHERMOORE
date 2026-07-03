#!/usr/bin/env python
"""Smoke-evaluate the tiny full-bundle LM with marker checks."""

from __future__ import annotations

import json
from pathlib import Path

import torch

from train_full_bundle_tiny_lm import TinyLM, generate
from full_bundle_tiny_lm_cli import deterministic_guard


ROOT = Path(__file__).resolve().parents[2]
LM_DIR = ROOT / "artifacts" / "full_coding_systems_bundle" / "tiny_lm"


CASES = [
    {
        "name": "python_add",
        "prompt": "Language: python Function name: add_two Doc: Add two numbers. Write the function.",
        "lane": "coding",
        "task": "doc_to_code",
        "markers_any": ["def", "return", "+"],
    },
    {
        "name": "scbe_tokens",
        "prompt": "Convert this python code into SCBE phase tokens: def f(a,b): return a + b",
        "lane": "coding",
        "task": "code_to_scbe_tokens",
        "markers_any": ["KO", "AV", "CA", "DR", "bip"],
    },
    {
        "name": "github_pointer",
        "prompt": "Where should an agent look for current GitHub pull request documentation?",
        "lane": "github_user_guide",
        "task": "github_workflow_pointer",
        "markers_any": ["github", "docs", "pull", "request"],
    },
    {
        "name": "binary_view",
        "prompt": "Encode print('hello') into binary views.",
        "lane": "binary",
        "task": "code_to_binary_views",
        "markers_any": ["sha256", "hex", "base64", "bytes"],
    },
]


def main() -> int:
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
    results = []
    for case in CASES:
        raw = generate(model, vocab, case["prompt"], device, max_new=120, lane=case["lane"], task=case["task"])
        final, guard = deterministic_guard(case["lane"], case["task"], case["prompt"], raw)
        raw_low = raw.lower()
        final_low = final.lower()
        raw_hits = [marker for marker in case["markers_any"] if marker.lower() in raw_low]
        final_hits = [marker for marker in case["markers_any"] if marker.lower() in final_low]
        results.append(
            {
                "name": case["name"],
                "prompt": case["prompt"],
                "raw_generation": raw,
                "generation": final,
                "guard": guard,
                "raw_hits": raw_hits,
                "hits": final_hits,
                "raw_ok": bool(raw_hits),
                "ok": bool(final_hits),
            }
        )
    receipt = {
        "ok": all(item["ok"] for item in results),
        "kind": "full_bundle_tiny_lm_marker_eval",
        "honest_scope": "Marker smoke test only; reports guarded product output plus raw_generation/raw_ok.",
        "results": results,
    }
    out = LM_DIR / "eval_receipt.json"
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    print("FULL_BUNDLE_TINY_LM_EVAL_DONE")
    for item in results:
        print(f"{item['name']}: ok={item['ok']} raw_ok={item['raw_ok']} hits={item['hits']} guard={item['guard']['reason']}")
    print(f"receipt: {out}")
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
