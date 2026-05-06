#!/usr/bin/env python3
"""Tokenizer audit for the coding-verification eval contract.

Open follow-up from `project_v6e_gate_result_2026_05_06` memory:
"recommend tokenizer audit before next SFT spend." Both v6e (raw 2/12)
and v6f (raw 1/12) leave the bare model at floor on the contract; the
question is whether tokenization itself makes some discipline targets
unreachable for SFT.

For each unique required/forbidden token in the contract:

1. Tokenize with the same tokenizer the production model uses (default
   Qwen2.5-Coder-7B-Instruct) both with and without leading space — this
   is the same dual-form ``build_bad_words_ids`` uses for suppression.
2. Record the BPE piece count and the actual pieces.
3. Classify:
   - **atomic** — single piece in either form. SFT can train on this as
     a unit; suppression via ``bad_words_ids`` is reliable.
   - **fragmented** — multiple pieces in both forms. SFT must learn the
     full piece sequence; suppression catches first-piece-only and the
     model can dodge by emitting an alternate first piece.
4. Cross-reference with the contract structure: which prompts contain
   each token, whether it is on the required or forbidden side.

The report tells us *before* the next SFT spend whether the tokens we
are training the model to emit (or suppress) are atomically addressable
or whether SFT is fighting the tokenizer.

Usage::

    python scripts/eval/tokenizer_audit_coding_contract.py \\
        --contract-path config/model_training/coding_verification_eval_contract.json \\
        --model-id Qwen/Qwen2.5-Coder-7B-Instruct \\
        --output-dir artifacts/tokenizer_audit
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def _tokenize_dual(tokenizer, token: str) -> dict[str, Any]:
    """Tokenize a literal both with and without a leading space.

    Returns a dict with piece counts and the literal pieces. BPE-family
    tokenizers (like Qwen2.5) treat 'foo' and ' foo' as different
    sequences — a token that appears mid-sentence in training will
    almost always be the leading-space form.
    """

    out: dict[str, Any] = {"literal": token}
    for label, surface in [("nospace", token), ("space", " " + token)]:
        ids = tokenizer.encode(surface, add_special_tokens=False)
        pieces = tokenizer.convert_ids_to_tokens(ids)
        out[label] = {
            "n_pieces": len(ids),
            "ids": ids,
            "pieces": pieces,
        }
    out["min_pieces"] = min(out["nospace"]["n_pieces"], out["space"]["n_pieces"])
    out["atomic"] = out["min_pieces"] == 1
    return out


def _classify(audit: dict[str, Any]) -> str:
    """Classify based on the tokenization profile.

    - atomic: addressable as a single token in some surface form
    - bigram: 2 pieces in best form
    - fragmented: 3+ pieces in best form
    """

    n = audit["min_pieces"]
    if n <= 1:
        return "atomic"
    if n == 2:
        return "bigram"
    return "fragmented"


def audit_contract(
    contract_path: Path,
    tokenizer,
) -> dict[str, Any]:
    """Run the audit over a contract; return the structured result."""

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    prompts = contract.get("prompts", [])

    required_to_prompts: dict[str, list[str]] = defaultdict(list)
    forbidden_to_prompts: dict[str, list[str]] = defaultdict(list)
    for p in prompts:
        pid = p.get("id", "<unknown>")
        for t in p.get("required", []):
            required_to_prompts[t].append(pid)
        for t in p.get("forbidden", []):
            forbidden_to_prompts[t].append(pid)

    required_audit = {
        t: {**_tokenize_dual(tokenizer, t), "in_prompts": ids}
        for t, ids in required_to_prompts.items()
    }
    forbidden_audit = {
        t: {**_tokenize_dual(tokenizer, t), "in_prompts": ids}
        for t, ids in forbidden_to_prompts.items()
    }

    def _summarize(audit_map: dict[str, Any]) -> dict[str, Any]:
        atomic = [t for t, a in audit_map.items() if a["atomic"]]
        bigram = [t for t, a in audit_map.items() if _classify(a) == "bigram"]
        fragmented = [t for t, a in audit_map.items() if _classify(a) == "fragmented"]
        return {
            "n_unique": len(audit_map),
            "n_atomic": len(atomic),
            "n_bigram": len(bigram),
            "n_fragmented": len(fragmented),
            "atomic_tokens": sorted(atomic),
            "bigram_tokens": sorted(bigram),
            "fragmented_tokens": sorted(fragmented),
        }

    return {
        "contract_id": contract.get("contract_id"),
        "model_id": getattr(tokenizer, "name_or_path", "unknown"),
        "n_prompts": len(prompts),
        "required": {
            "summary": _summarize(required_audit),
            "details": required_audit,
        },
        "forbidden": {
            "summary": _summarize(forbidden_audit),
            "details": forbidden_audit,
        },
    }


def render_markdown_report(audit: dict[str, Any]) -> str:
    """Render a human-readable report. Used by the CLI; tests can
    inspect the structured audit dict directly."""

    lines: list[str] = []
    lines.append(f"# Tokenizer Audit: {audit['contract_id']}")
    lines.append("")
    lines.append(f"**Model**: `{audit['model_id']}`  ")
    lines.append(f"**Prompts in contract**: {audit['n_prompts']}")
    lines.append("")

    for side in ("required", "forbidden"):
        s = audit[side]["summary"]
        lines.append(f"## {side.title()} tokens")
        lines.append("")
        lines.append(
            f"- unique: **{s['n_unique']}**  "
            f"  atomic: **{s['n_atomic']}** ({100 * s['n_atomic'] / max(s['n_unique'], 1):.0f}%)  "
            f"  bigram: {s['n_bigram']}  "
            f"  fragmented (>=3 pieces): **{s['n_fragmented']}**"
        )
        lines.append("")
        if s["fragmented_tokens"]:
            lines.append(f"### Fragmented {side} tokens (>=3 pieces — SFT-hard, suppression-leaky)")
            lines.append("")
            for tok in s["fragmented_tokens"]:
                d = audit[side]["details"][tok]
                pieces = d["space"]["pieces"] if d["space"]["n_pieces"] <= d["nospace"]["n_pieces"] else d["nospace"]["pieces"]
                lines.append(f"- `{tok}` -> {d['min_pieces']} pieces: `{pieces}` (in {len(d['in_prompts'])} prompt(s))")
            lines.append("")

    lines.append("## Implications")
    lines.append("")
    f_summary = audit["forbidden"]["summary"]
    if f_summary["n_fragmented"] > 0:
        lines.append(
            f"- {f_summary['n_fragmented']}/{f_summary['n_unique']} forbidden tokens are fragmented. "
            "`bad_words_ids` only blocks the FIRST piece of each forbidden sequence, so the model "
            "can dodge suppression by emitting an alternate first piece. SFT also has to learn the "
            "full piece sequence, not the literal."
        )
    r_summary = audit["required"]["summary"]
    if r_summary["n_fragmented"] > 0:
        lines.append(
            f"- {r_summary['n_fragmented']}/{r_summary['n_unique']} required tokens are fragmented. "
            "The model has to compose them from BPE pieces, which means SFT pressure on the literal "
            "spreads across multiple step positions; the model may learn the first piece only and "
            "drift on subsequent ones."
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract-path",
        type=Path,
        default=Path("config/model_training/coding_verification_eval_contract.json"),
    )
    parser.add_argument("--model-id", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/tokenizer_audit"),
    )
    args = parser.parse_args()

    if not args.contract_path.exists():
        print(f"contract not found: {args.contract_path}", file=sys.stderr)
        return 1

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    audit = audit_contract(args.contract_path, tokenizer)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    contract_stem = args.contract_path.stem
    json_path = args.output_dir / f"{contract_stem}_tokenizer_audit.json"
    md_path = args.output_dir / f"{contract_stem}_tokenizer_audit.md"

    json_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown_report(audit), encoding="utf-8")

    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print()
    # Print a brief summary instead of the full Markdown — Windows cp1252
    # console can't render the BPE leading-space sentinel character (U+0120)
    # that real Qwen-style tokenizers emit. The full report is in the .md file.
    for side in ("required", "forbidden"):
        s = audit[side]["summary"]
        print(
            f"{side:>10}: {s['n_unique']:>3} unique  | "
            f"atomic {s['n_atomic']:>3}  bigram {s['n_bigram']:>3}  fragmented {s['n_fragmented']:>3}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
