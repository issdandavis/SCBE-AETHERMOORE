"""Command-line interface for the Polly Pad runtime."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from .runtime import (
    LANGS,
    MODE_TOOLS,
    PAD_MODES,
    PAD_MODE_TONGUE,
    harmonic_cost,
    pad_namespace_key,
    plan_tri_directional,
    scbe_decide,
)


def _parse_state(raw: str) -> tuple[float, ...]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) != 6:
        raise argparse.ArgumentTypeError("state must contain exactly 6 comma-separated numbers")
    try:
        return tuple(float(p) for p in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("state values must be numeric") from exc


def _print_json(payload: object) -> None:
    print(json.dumps(payload, sort_keys=True, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scbe-polly-pad",
        description="Polly Pad agent workspace CLI.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("modes", help="List Polly Pad modes, tongues, and tools.")

    decide = sub.add_parser("decide", help="Compute the SCBE three-tier decision.")
    decide.add_argument("--d-star", type=float, required=True)
    decide.add_argument("--coherence", type=float, required=True)
    decide.add_argument("--h-eff", type=float, required=False)
    decide.add_argument("--radius", type=float, default=1.5)

    namespace = sub.add_parser("namespace", help="Generate a deterministic pad namespace key.")
    namespace.add_argument("--unit-id", required=True)
    namespace.add_argument("--mode", choices=PAD_MODES, required=True)
    namespace.add_argument("--lang", choices=LANGS, required=True)
    namespace.add_argument("--epoch", type=int, required=True)

    trace = sub.add_parser("trace", help="Run tri-directional trace planning.")
    trace.add_argument("--state", type=_parse_state, required=True)
    trace.add_argument("--d-star", type=float, required=True)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "modes":
        _print_json(
            {
                mode: {
                    "tongue": PAD_MODE_TONGUE[mode],
                    "tools": MODE_TOOLS[mode],
                }
                for mode in PAD_MODES
            }
        )
        return 0

    if args.command == "decide":
        h_eff = args.h_eff if args.h_eff is not None else harmonic_cost(args.d_star, args.radius)
        _print_json(
            {
                "decision": scbe_decide(args.d_star, args.coherence, h_eff),
                "d_star": args.d_star,
                "coherence": args.coherence,
                "h_eff": h_eff,
            }
        )
        return 0

    if args.command == "namespace":
        _print_json(
            {
                "namespace": pad_namespace_key(args.unit_id, args.mode, args.lang, args.epoch),
                "unit_id": args.unit_id,
                "mode": args.mode,
                "lang": args.lang,
                "epoch": args.epoch,
            }
        )
        return 0

    if args.command == "trace":
        result = plan_tri_directional(args.state, args.d_star)
        _print_json(
            {
                "decision": result.decision,
                "triadic_distance": result.triadic_distance,
                "valid_count": result.valid_count,
                "agreement": result.agreement,
                "traces": [
                    {
                        "direction": trace.direction,
                        "result": trace.result,
                        "path": trace.path,
                        "missed_required": trace.missed_required,
                        "cost": trace.cost,
                        "coherence": trace.coherence,
                    }
                    for trace in result.traces
                ],
            }
        )
        return 0

    raise AssertionError(f"unhandled command: {args.command}")
