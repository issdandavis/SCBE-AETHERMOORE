"""Run all Petri seeds through SCBE's governance gate (LatticeRouter, AUTO).

Petri seeds are NL auditor instructions ("Probe the target AI for...");
the LatticeRouter's job is to map NL intent + args into a bounded
LatticeOp dispatch (band -> op -> tongue, 3 SLM calls). This runner
measures what happens when the gate is given inputs it was never
designed for: how often does it correctly QUARANTINE adversarial NL,
how often does it force them into some op anyway, and which ops?

Two run modes:

  v1 (default, --no-dummy-args): args={} — measures the gate's
      end-to-end refusal rate, but the args-completeness check at the
      end of routing dominates because every lexicon op requires at
      least one template variable. Quarantine reasons will skew toward
      "missing args" rather than adversarial-content detection.

  v2 (--dummy-args): args populated with a fixed dummy set covering
      every common arg name. The args-completeness check no longer
      filters anything, so the SLM's actual classification choices are
      visible — this is what surfaces "false ALLOW" failure modes
      where the bounded SLM forces adversarial NL into some op.

Usage:
    python scripts/eval/petri_governance_gate_run.py \\
        --seeds-dir external/benchmarks/petri-seeds \\
        --ollama-model scbe-geoseal-coder:q8 \\
        --dummy-args \\
        --json-out artifacts/petri/governance_gate_v2.json \\
        --limit 5            # smoke test — omit for full corpus
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.cli.petri_seed_loader import (
    PetriLoadError,
    PetriSeed,
    load_seed_directory,
)
from src.cli.cascade_router import AndAllowCascadeRouter, CascadeRouter
from src.cli.slm_router import (
    LatticeRouter,
    Mode,
    OllamaAdapter,
    QuarantineError,
)


@dataclass
class GateOutcome:
    """One per-seed record so aggregation is just a Counter pass."""

    seed_id: str
    tags: List[str]
    verdict: str  # ALLOW / QUARANTINE
    op_name: Optional[str] = None
    op_band: Optional[str] = None
    dst_tongue: Optional[str] = None
    confidence: Optional[float] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    elapsed_s: float = 0.0


# Synthetic dummy args covering every template-variable name in use across
# the 64-op lexicon. Passing these satisfies the post-classification
# args-completeness check regardless of which op the SLM picks, so any
# remaining quarantine traces back to the classification stages rather
# than to a downstream args-mask. Values are deliberately benign
# identifiers so a downstream emit_from_ir would render compilable code.
_DUMMY_TEMPLATE_ARGS: Dict[str, str] = {
    "xs": "data",
    "ys": "data2",
    "pairs": "pairs",
    "fn": "f",
    "init": "z",
    "pred": "p",
    "a": "x",
    "b": "y",
    "lhs": "x",
    "rhs": "y",
    "n": "n",
    "k": "k",
}


def run_one(router: LatticeRouter, seed: PetriSeed, *, args_payload: Dict[str, str]) -> GateOutcome:
    tags = list(seed.metadata.get("tags") or [])
    t0 = time.monotonic()
    try:
        result = router.route(intent=seed.input, args=args_payload, mode=Mode.AUTO)
    except QuarantineError as exc:
        return GateOutcome(
            seed_id=seed.id,
            tags=tags,
            verdict="QUARANTINE",
            error_type=type(exc).__name__,
            error_message=str(exc)[:200],
            elapsed_s=time.monotonic() - t0,
        )
    except Exception as exc:
        # Bucket as classification failure so the surface is bounded.
        return GateOutcome(
            seed_id=seed.id,
            tags=tags,
            verdict="QUARANTINE",
            error_type=f"Unexpected:{type(exc).__name__}",
            error_message=str(exc)[:200],
            elapsed_s=time.monotonic() - t0,
        )
    return GateOutcome(
        seed_id=seed.id,
        tags=tags,
        verdict="ALLOW",
        op_name=result.op.op_name,
        op_band=result.op.band,
        dst_tongue=result.dst_tongue,
        confidence=result.confidence,
        elapsed_s=time.monotonic() - t0,
    )


def aggregate(outcomes: List[GateOutcome]) -> Dict[str, Any]:
    n = len(outcomes)
    n_allow = sum(1 for o in outcomes if o.verdict == "ALLOW")
    n_quar = n - n_allow

    err_types: Counter[str] = Counter()
    op_when_allow: Counter[str] = Counter()
    band_when_allow: Counter[str] = Counter()
    tongue_when_allow: Counter[str] = Counter()

    # Per-tag verdict breakdown.
    per_tag: Dict[str, Dict[str, int]] = {}
    untagged_breakdown = {"ALLOW": 0, "QUARANTINE": 0}

    for o in outcomes:
        if o.verdict == "QUARANTINE" and o.error_type:
            err_types[o.error_type] += 1
        if o.verdict == "ALLOW":
            if o.op_name:
                op_when_allow[o.op_name] += 1
            if o.op_band:
                band_when_allow[o.op_band] += 1
            if o.dst_tongue:
                tongue_when_allow[o.dst_tongue] += 1
        if not o.tags:
            untagged_breakdown[o.verdict] += 1
        for t in o.tags:
            per_tag.setdefault(t, {"ALLOW": 0, "QUARANTINE": 0})
            per_tag[t][o.verdict] += 1

    elapsed = [o.elapsed_s for o in outcomes]

    return {
        "total_seeds": n,
        "verdict_counts": {"ALLOW": n_allow, "QUARANTINE": n_quar},
        "quarantine_ratio": (n_quar / n) if n else 0.0,
        "error_types_when_quarantine": dict(err_types.most_common()),
        "op_when_allow": dict(op_when_allow.most_common()),
        "band_when_allow": dict(band_when_allow.most_common()),
        "tongue_when_allow": dict(tongue_when_allow.most_common()),
        "per_tag_verdicts": per_tag,
        "untagged_verdicts": untagged_breakdown,
        "elapsed_s": {
            "total": round(sum(elapsed), 2),
            "mean": round(sum(elapsed) / max(1, n), 2),
            "max": round(max(elapsed), 2) if elapsed else 0.0,
        },
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seeds-dir", type=Path, default=Path("external/benchmarks/petri-seeds"))
    parser.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    parser.add_argument("--ollama-model", default="scbe-geoseal-coder:q8")
    parser.add_argument(
        "--cascade-secondary-model",
        default="",
        help=(
            "if set, --ollama-model becomes the cascade primary and "
            "this is the secondary classifier. Default mode: and_allow"
        ),
    )
    parser.add_argument(
        "--cascade-mode",
        choices=["and_allow", "rescue"],
        default="and_allow",
    )
    parser.add_argument(
        "--rescue-threshold",
        type=float,
        default=0.85,
        help="rescue cascade only: secondary confidence floor for override",
    )
    parser.add_argument("--timeout-s", type=float, default=30.0)
    parser.add_argument("--min-confidence", type=float, default=0.5)
    parser.add_argument("--limit", type=int, default=None, help="cap N seeds (smoke test); omit for full corpus")
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--dummy-args",
        action="store_true",
        help="populate args with a fixed dummy set so the post-classification "
        "args-completeness check does not dominate quarantine reasons; "
        "exposes the SLM's actual op classification choices",
    )
    parser.add_argument(
        "--coding-intent-gate",
        action="store_true",
        help="enable the pre-band Yes/No coding-intent gate on both "
        "primary and secondary routers. Closes meta-AI/role/values "
        "false-allows that survive AND-of-allow band classification.",
    )
    parser.add_argument(
        "--gate-model",
        default="",
        help="if set, the coding-intent gate uses this model (e.g. "
        "'gemma3:1b') instead of the per-router classifier model. "
        "A different model family is the asymmetric check that "
        "closes meta-AI prompts both qwen-coder classifiers allow.",
    )
    parser.add_argument(
        "--petri-pattern-filter",
        action="store_true",
        help="enable deterministic regex pre-filter for Petri-style "
        "auditor phrasings on both primary and secondary routers. "
        "Cheaper than the LLM gate (no SLM call) and corpus-anchored.",
    )
    args = parser.parse_args(argv)
    args_payload: Dict[str, str] = dict(_DUMMY_TEMPLATE_ARGS) if args.dummy_args else {}

    try:
        seeds = load_seed_directory(args.seeds_dir)
    except PetriLoadError as exc:
        print(f"seed load failed: {exc}", file=sys.stderr)
        return 2
    if not seeds:
        print(f"no seeds at {args.seeds_dir}", file=sys.stderr)
        return 2
    if args.limit is not None:
        seeds = seeds[: args.limit]

    adapter = OllamaAdapter(host=args.ollama_host, model=args.ollama_model)
    gate_adapter = OllamaAdapter(host=args.ollama_host, model=args.gate_model) if args.gate_model else None
    primary_router = LatticeRouter(
        adapter,
        min_confidence=args.min_confidence,
        adapter_timeout=args.timeout_s,
        enable_coding_intent_gate=args.coding_intent_gate,
        gate_adapter=gate_adapter,
        enable_petri_pattern_filter=args.petri_pattern_filter,
    )
    if args.cascade_secondary_model:
        secondary_adapter = OllamaAdapter(host=args.ollama_host, model=args.cascade_secondary_model)
        secondary_router = LatticeRouter(
            secondary_adapter,
            min_confidence=args.min_confidence,
            adapter_timeout=args.timeout_s,
            enable_coding_intent_gate=args.coding_intent_gate,
            gate_adapter=gate_adapter,
            enable_petri_pattern_filter=args.petri_pattern_filter,
        )
        if args.cascade_mode == "and_allow":
            router = AndAllowCascadeRouter(primary=primary_router, secondary=secondary_router)
        else:
            router = CascadeRouter(
                primary=primary_router,
                secondary=secondary_router,
                rescue_threshold=args.rescue_threshold,
            )
    else:
        router = primary_router

    outcomes: List[GateOutcome] = []
    for i, seed in enumerate(seeds, 1):
        outcome = run_one(router, seed, args_payload=args_payload)
        outcomes.append(outcome)
        if not args.quiet:
            tag = outcome.tags[0] if outcome.tags else "untagged"
            label = outcome.verdict
            if outcome.verdict == "ALLOW":
                label = f"ALLOW({outcome.op_band}/{outcome.op_name}->{outcome.dst_tongue} c={outcome.confidence:.2f})"
            else:
                label = f"QUAR({outcome.error_type or 'no-class'})"
            print(f"  [{i:>3}/{len(seeds)}] {seed.id[:48]:<48} tag={tag:<24} {label}")

    report = {
        "ollama_model": args.ollama_model,
        "ollama_host": args.ollama_host,
        "cascade_secondary_model": args.cascade_secondary_model or None,
        "cascade_mode": (args.cascade_mode if args.cascade_secondary_model else None),
        "rescue_threshold": (
            args.rescue_threshold if args.cascade_secondary_model and args.cascade_mode == "rescue" else None
        ),
        "seeds_dir": str(args.seeds_dir),
        "args_mode": "dummy" if args.dummy_args else "empty",
        "args_payload": args_payload,
        "coding_intent_gate": bool(args.coding_intent_gate),
        "gate_model": args.gate_model or None,
        "petri_pattern_filter": bool(args.petri_pattern_filter),
        "summary": aggregate(outcomes),
        "per_seed": [asdict(o) for o in outcomes],
    }

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nwrote {args.json_out}", file=sys.stderr)

    print("\nSUMMARY:")
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
