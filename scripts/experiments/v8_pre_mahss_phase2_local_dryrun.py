"""Local dry-run for v8-pre Phase 2.

Runs the full parser -> MAHSS retrieval -> prefix construction pipeline
on every v6g eval prompt and prints what the model would actually see.
No LLM is invoked. The point is to verify the prefixes are sensible
before spending l4x1 inference time."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from python.scbe.mahss_role_pinned_memory import (  # noqa: E402
    V6G_DISTRACTORS,
    RolePinnedMemory,
)
from python.scbe.mahss_v8_pre_prompt_parser import format_mahss_prefix, parse_prompt  # noqa: E402

DIM = 4096

CONTRACT_PATH = _REPO_ROOT / "config" / "model_training" / "coding_verification_eval_contract.json"


def build_per_prompt_memory_from_schema(schema):
    """Build memory bound from PARSED schema (not from answer key)."""

    mem = RolePinnedMemory(dim=DIM)
    # Register all distractors so retrieval has a realistic candidate set
    for role, options in V6G_DISTRACTORS.items():
        mem.register_distractors(role, options)
    # Bind only what the parser extracted from the prompt
    for role, filler in schema.to_role_filler_pairs():
        # If filler not in distractor vocab, register it on the fly
        if filler not in V6G_DISTRACTORS.get(role, ()):
            mem.register_filler(role, filler)
        mem.bind(role, filler)
    return mem


def retrieve_for_schema(mem, schema):
    """Run retrieval per role for the counts the schema requested."""

    counts = schema.role_counts()
    out: dict[str, list[str]] = {}
    for role, n in counts.items():
        ranks = mem.query(role, top_k=max(5, n + 2))
        out[role] = [name for name, _ in ranks[:n]]
    return out


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    prompts = contract["prompts"]

    print(f"== v8-pre Phase 2 LOCAL DRY-RUN (no LLM) ==")
    print(f"contract: {contract['contract_id']}, n_prompts={len(prompts)}\n")

    rows = []
    coverage_sum = 0
    coverage_total = 0

    for entry in prompts:
        pid = entry["id"]
        prompt = entry["prompt"]
        required = entry["required"]

        schema = parse_prompt(prompt)
        mem = build_per_prompt_memory_from_schema(schema)
        retrieved = retrieve_for_schema(mem, schema)
        prefix = format_mahss_prefix(schema, retrieved)

        # Coverage: how many of the contract's `required` tokens are
        # mentioned (case-insensitive substring) in the MAHSS prefix?
        prefix_lower = prefix.lower()
        covered = [r for r in required if r.lower() in prefix_lower]
        coverage_sum += len(covered)
        coverage_total += len(required)

        rows.append(
            {
                "id": pid,
                "mode": schema.mode,
                "tongues": list(schema.tongues),
                "languages": list(schema.languages),
                "identifiers": list(schema.identifiers),
                "slots": list(schema.slots),
                "metrics": list(schema.metrics),
                "keywords": list(schema.keywords),
                "retrieved": retrieved,
                "prefix": prefix,
                "required": required,
                "covered": covered,
                "coverage_pct": round(len(covered) / max(1, len(required)), 4),
            }
        )

        print(f"--- {pid} (mode={schema.mode}) ---")
        print(f"  parsed:    tongues={list(schema.tongues)}  langs={list(schema.languages)}")
        print(f"             slots={list(schema.slots)[:6]}  metrics={list(schema.metrics)}")
        print(f"             idents={list(schema.identifiers)}  keywords={list(schema.keywords)[:6]}")
        if prefix:
            print(f"  prefix:    {prefix.strip()}")
        else:
            print(f"  prefix:    <empty>")
        print(
            f"  coverage:  {len(covered)}/{len(required)} required-tokens hinted by MAHSS prefix"
            f"  ({len(covered) / max(1, len(required)):.0%})"
        )
        if covered:
            print(f"             covered: {covered}")
        print()

    overall = coverage_sum / max(1, coverage_total)
    print(f"== Overall MAHSS-prefix coverage of contract.required: {coverage_sum}/{coverage_total} = {overall:.0%} ==")

    out_dir = _REPO_ROOT / "artifacts" / "mahss_v8_pre"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "phase2_local_dryrun.json").write_text(
        json.dumps(
            {
                "contract_id": contract["contract_id"],
                "n_prompts": len(prompts),
                "overall_required_coverage": round(overall, 4),
                "coverage_sum": coverage_sum,
                "coverage_total": coverage_total,
                "by_prompt": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nreceipt: {out_dir / 'phase2_local_dryrun.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
