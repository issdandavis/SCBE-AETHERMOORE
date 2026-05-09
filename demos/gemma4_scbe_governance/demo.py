"""SCBE-Gemma4 governance demo — single-prompt CLI.

  python demos/gemma4_scbe_governance/demo.py \\
      --intent "Add x and y" \\
      --gemma-model gemma3:1b \\
      --slm-model qwen2.5-coder:0.5b

The intent flows: NL -> SCBE LatticeRouter (band/op/tongue with v3 NONE
escape hatch) -> if ALLOW, Gemma -> printed transcript; if QUARANTINE,
typed reason printed and Gemma is never called.

Designed to require nothing exotic: a local Ollama server with one SLM
(any 0.5B-1.5B coder model) and one Gemma variant. Use --no-gemma to
exercise the gate alone with no LLM call.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from demos.gemma4_scbe_governance.lib import (  # noqa: E402
    GemmaClient,
    govern_and_generate,
)
from src.cli.slm_router import LatticeRouter, OllamaAdapter  # noqa: E402

_DEFAULT_DUMMY_ARGS = {"a": "x", "b": "y", "xs": "data", "fn": "f", "init": "z"}


def _parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--intent",
        required=True,
        help="natural-language prompt to govern + send to Gemma",
    )
    p.add_argument(
        "--args-json",
        default="",
        help="JSON object of template args; default covers common var names",
    )
    p.add_argument(
        "--slm-model",
        default="qwen2.5-coder:0.5b",
        help="Ollama model id used by the SCBE governance gate (band/op/tongue)",
    )
    p.add_argument(
        "--gemma-model",
        default="gemma3:1b",
        help="Ollama model id used for the actual response (any Gemma variant)",
    )
    p.add_argument(
        "--ollama-host",
        default="http://localhost:11434",
        help="Ollama server URL — same host used for both SLM and Gemma",
    )
    p.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        help="SLM confidence floor; below this the gate quarantines",
    )
    p.add_argument(
        "--no-gemma",
        action="store_true",
        help="exercise the governance gate only; do not call Gemma",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="print machine-readable JSON only (no human summary)",
    )
    return p.parse_args(argv)


def _build_router(args: argparse.Namespace) -> LatticeRouter:
    adapter = OllamaAdapter(model=args.slm_model, host=args.ollama_host)
    return LatticeRouter(adapter, min_confidence=args.min_confidence)


def _build_gemma(args: argparse.Namespace) -> Optional[GemmaClient]:
    if args.no_gemma:
        return None
    return GemmaClient(model=args.gemma_model, host=args.ollama_host)


def _print_human_summary(result) -> None:
    print(f"=== SCBE-Gemma4 governance demo ===")
    print(f"intent      : {result.intent}")
    print(f"verdict     : {result.verdict}")
    if result.verdict == "ALLOW" and result.routing is not None:
        r = result.routing
        print(f"  band      : {r['op_band']}")
        print(f"  op        : {r['op_name']}")
        print(f"  tongue    : {r['dst_tongue']}")
        print(f"  confidence: {r['confidence']:.2f}")
    elif result.verdict == "QUARANTINE":
        print(f"  reason    : {result.error_type}")
        msg = (result.error_message or "")[:240]
        if msg:
            print(f"  message   : {msg}")
    if result.gemma_response is not None:
        print(f"\n--- Gemma ({result.gemma_model}) ---")
        print(result.gemma_response.rstrip())
    elif result.gemma_model and result.verdict == "ALLOW":
        err = result.extra.get("gemma_error")
        if err:
            print(f"\n--- Gemma error ({result.gemma_model}) ---\n{err}")
    print(f"\nelapsed: {result.elapsed_s:.2f}s")


def main(argv: Optional[list] = None) -> int:
    args = _parse_args(argv)
    template_args = json.loads(args.args_json) if args.args_json else dict(_DEFAULT_DUMMY_ARGS)
    router = _build_router(args)
    gemma = _build_gemma(args)
    result = govern_and_generate(
        intent=args.intent,
        args=template_args,
        router=router,
        gemma_client=gemma,
    )
    if args.json:
        print(result.to_json())
    else:
        _print_human_summary(result)
    # Exit non-zero on QUARANTINE so shell-pipe callers can branch.
    return 0 if result.verdict == "ALLOW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
