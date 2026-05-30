"""Command-line interface for the Polly Pad runtime."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from .audit import append_event, default_ledger_path, export_ledger, iter_events, verify_ledger
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

    audit = sub.add_parser("audit", help="Manage Polly Pad audit receipts.")
    audit_sub = audit.add_subparsers(dest="audit_command", required=True)

    audit_append = audit_sub.add_parser("append", help="Append one audit receipt.")
    audit_append.add_argument("--ledger", default=str(default_ledger_path()))
    audit_append.add_argument("--actor", required=True)
    audit_append.add_argument("--action", required=True)
    audit_append.add_argument("--subject", required=True)
    audit_append.add_argument("--payload-json", default="{}")

    audit_list = audit_sub.add_parser("list", help="List audit receipts.")
    audit_list.add_argument("--ledger", default=str(default_ledger_path()))

    audit_verify = audit_sub.add_parser("verify", help="Verify audit hash continuity.")
    audit_verify.add_argument("--ledger", default=str(default_ledger_path()))

    audit_export = audit_sub.add_parser("export", help="Export audit ledger as JSON.")
    audit_export.add_argument("--ledger", default=str(default_ledger_path()))

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

    if args.command == "audit":
        if args.audit_command == "append":
            try:
                payload = json.loads(args.payload_json)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid --payload-json: {exc}") from exc
            if not isinstance(payload, dict):
                raise SystemExit("--payload-json must decode to a JSON object")
            receipt = append_event(
                args.ledger,
                actor=args.actor,
                action=args.action,
                subject=args.subject,
                payload=payload,
            )
            _print_json(receipt.__dict__)
            return 0

        if args.audit_command == "list":
            _print_json([receipt.__dict__ for receipt in iter_events(args.ledger)])
            return 0

        if args.audit_command == "verify":
            result = verify_ledger(args.ledger)
            _print_json(result.__dict__)
            return 0 if result.ok else 2

        if args.audit_command == "export":
            _print_json(export_ledger(args.ledger))
            return 0

    raise AssertionError(f"unhandled command: {args.command}")
