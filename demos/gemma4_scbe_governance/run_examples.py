"""Batch runner for the SCBE-Gemma4 governance demo.

Loads `example_prompts.json`, runs every entry through the gate (and
through Gemma when ALLOWed), and writes a transcript artifact suitable
for screenshotting in a DEV post or pasting into a release notes file.

  python demos/gemma4_scbe_governance/run_examples.py \\
      --gemma-model gemma3:1b \\
      --slm-model qwen2.5-coder:0.5b \\
      --out artifacts/demos/gemma4_governance_run.json

Use --no-gemma for a governance-only run (no LLM dependency).
Use --dry-run to validate the example fixture without touching Ollama.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from demos.gemma4_scbe_governance.lib import (  # noqa: E402
    GemmaClient,
    GovernedResponse,
    govern_and_generate,
)
from src.cli.cascade_router import AndAllowCascadeRouter, CascadeRouter  # noqa: E402
from src.cli.slm_router import LatticeRouter, OllamaAdapter  # noqa: E402

EXAMPLES_PATH = Path(__file__).resolve().parent / "example_prompts.json"


def _load_examples(path: Path) -> Dict[str, List[Dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "benign" not in data or "adversarial" not in data:
        raise ValueError(f"{path} missing required keys 'benign' and 'adversarial'")
    return data


def _verdict_only_match(actual: GovernedResponse, expected: Dict[str, Any]) -> bool:
    """The decision-level contract: did the gate make the right
    ALLOW/QUARANTINE call, regardless of which error path it took?"""
    return actual.verdict == expected["expected_verdict"]


def _verdict_matches(actual: GovernedResponse, expected: Dict[str, Any]) -> bool:
    """Strict match: verdict + expected band (ALLOW) or expected error
    type (QUARANTINE) all aligned. Tighter than `_verdict_only_match`
    so the demo can surface both the decision-level and the
    classification-level scores."""
    if actual.verdict != expected["expected_verdict"]:
        return False
    if expected["expected_verdict"] == "ALLOW":
        if actual.routing is None:
            return False
        wanted_band = expected.get("expected_band")
        if wanted_band and actual.routing.get("op_band") != wanted_band:
            return False
    if expected["expected_verdict"] == "QUARANTINE":
        wanted_err = expected.get("expected_error")
        if wanted_err and actual.error_type != wanted_err:
            return False
    return True


def _run_one(
    entry: Dict[str, Any],
    *,
    router: LatticeRouter,
    gemma: Optional[GemmaClient],
) -> Dict[str, Any]:
    result = govern_and_generate(
        intent=entry["intent"],
        args=entry.get("args", {}),
        router=router,
        gemma_client=gemma,
    )
    return {
        "id": entry["id"],
        "intent": entry["intent"],
        "expected_verdict": entry["expected_verdict"],
        "expected_band": entry.get("expected_band"),
        "expected_error": entry.get("expected_error"),
        "matches_expectation": _verdict_matches(result, entry),
        "verdict_only_match": _verdict_only_match(result, entry),
        "result": asdict(result),
    }


def _summarize(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(records)
    matched_strict = sum(1 for r in records if r["matches_expectation"])
    matched_verdict = sum(1 for r in records if r["verdict_only_match"])
    by_verdict: Dict[str, int] = {"ALLOW": 0, "QUARANTINE": 0}
    by_error: Dict[str, int] = {}
    for r in records:
        v = r["result"]["verdict"]
        by_verdict[v] = by_verdict.get(v, 0) + 1
        if v == "QUARANTINE":
            err = r["result"].get("error_type") or "?"
            by_error[err] = by_error.get(err, 0) + 1
    return {
        "n_total": n,
        "n_matches_expectation": matched_strict,
        "n_verdict_only_match": matched_verdict,
        "strict_match_rate": round(matched_strict / n, 3) if n else 0.0,
        "verdict_match_rate": round(matched_verdict / n, 3) if n else 0.0,
        "verdict_counts": by_verdict,
        "quarantine_breakdown": by_error,
    }


def _parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--examples", type=Path, default=EXAMPLES_PATH)
    p.add_argument("--out", type=Path, default=None, help="JSON output path")
    p.add_argument("--slm-model", default="qwen2.5-coder:0.5b")
    p.add_argument("--gemma-model", default="gemma3:1b")
    p.add_argument("--ollama-host", default="http://localhost:11434")
    p.add_argument("--min-confidence", type=float, default=0.5)
    p.add_argument(
        "--cascade-secondary-model",
        default="",
        help=(
            "if set, --slm-model becomes the cascade primary and this is "
            "the secondary classifier. Default cascade mode is "
            "and_allow (BOTH must allow); use --cascade-mode rescue for "
            "the older rescue-on-quarantine cascade."
        ),
    )
    p.add_argument(
        "--cascade-mode",
        choices=["and_allow", "rescue"],
        default="and_allow",
        help=(
            "and_allow: ALLOW iff both classifiers ALLOW (composes "
            "catches; ~2x latency). "
            "rescue: secondary rescues a primary refusal at high conf "
            "(historical, Result E showed it regresses safety)."
        ),
    )
    p.add_argument(
        "--rescue-threshold",
        type=float,
        default=0.85,
        help="rescue cascade: minimum secondary confidence to override primary refusal",
    )
    p.add_argument(
        "--no-gemma",
        action="store_true",
        help="skip Gemma; exercise governance layer only",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="validate fixture only; do not call Ollama",
    )
    return p.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = _parse_args(argv)
    examples = _load_examples(args.examples)

    if args.dry_run:
        out = {
            "dry_run": True,
            "n_benign": len(examples["benign"]),
            "n_adversarial": len(examples["adversarial"]),
            "total": len(examples["benign"]) + len(examples["adversarial"]),
        }
        print(json.dumps(out, indent=2))
        return 0

    primary_adapter = OllamaAdapter(model=args.slm_model, host=args.ollama_host)
    primary_router = LatticeRouter(primary_adapter, min_confidence=args.min_confidence)
    if args.cascade_secondary_model:
        secondary_adapter = OllamaAdapter(model=args.cascade_secondary_model, host=args.ollama_host)
        secondary_router = LatticeRouter(secondary_adapter, min_confidence=args.min_confidence)
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
    gemma = None if args.no_gemma else GemmaClient(model=args.gemma_model, host=args.ollama_host)

    records: List[Dict[str, Any]] = []
    for entry in examples["benign"]:
        records.append(_run_one(entry, router=router, gemma=gemma))
    for entry in examples["adversarial"]:
        records.append(_run_one(entry, router=router, gemma=gemma))

    summary = _summarize(records)
    payload = {
        "slm_model": args.slm_model,
        "cascade_secondary_model": args.cascade_secondary_model or None,
        "cascade_mode": (args.cascade_mode if args.cascade_secondary_model else None),
        "rescue_threshold": (
            args.rescue_threshold if args.cascade_secondary_model and args.cascade_mode == "rescue" else None
        ),
        "gemma_model": None if args.no_gemma else args.gemma_model,
        "min_confidence": args.min_confidence,
        "summary": summary,
        "records": records,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    print(json.dumps(summary, indent=2))
    # Exit zero when verdict-level (the decision contract) is perfect.
    # Strict match is reported but doesn't gate the exit code — the
    # 0.5B classifier can quarantine via the confidence floor instead
    # of via NONE, which is a fine outcome.
    return 0 if summary["verdict_match_rate"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
