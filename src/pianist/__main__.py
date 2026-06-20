"""CLI entry point: ``python -m pianist [--operator human|markov|cloud] [--out file.jsonl]``."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Iterable, Optional

from .operators import CloudOperator, HumanOperator, MarkovOperator, Operator
from .piano import Pianist, PhysicalError


def _build_operator(name: str, stdin: Iterable[str]) -> Operator:
    if name == "human":
        return HumanOperator(lines=iter(stdin), echo=lambda m: print(m, file=sys.stderr))
    if name == "markov":
        return MarkovOperator()
    if name == "cloud":
        return CloudOperator()
    raise SystemExit(f"unknown operator {name!r}; choose human, markov, or cloud")


def _serialize_event(t_ms: int, action) -> str:
    payload = {"t_ms": t_ms, "kind": action.kind}
    for attr in ("finger", "key", "velocity", "pedal", "pedal_value", "duration_ms"):
        value = getattr(action, attr)
        if value not in (None, 0, 0.0, 80) or (attr == "velocity" and action.kind == "press"):
            payload[attr] = value
    return json.dumps(payload)


def run(operator: Operator, pianist: Pianist, out_stream: Optional[object] = None) -> int:
    """Drive ``pianist`` with ``operator`` until the operator returns None."""
    actions_executed = 0
    while True:
        action = operator.next_action(pianist.state())
        if action is None:
            break
        try:
            pianist.execute(action)
        except PhysicalError as exc:
            print(f"[pianist] refused: {exc}", file=sys.stderr)
            continue
        actions_executed += 1
        if out_stream is not None:
            out_stream.write(_serialize_event(pianist.now_ms, action) + "\n")
    return actions_executed


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="pianist", description="Drive a mechanical pianist.")
    parser.add_argument("--operator", default="markov", choices=("human", "markov", "cloud"))
    parser.add_argument("--out", help="write a JSONL event log to this path (default: stdout)")
    args = parser.parse_args(argv)

    operator = _build_operator(args.operator, sys.stdin)
    pianist = Pianist()

    if args.out:
        with open(args.out, "w", encoding="utf-8") as out_stream:
            n = run(operator, pianist, out_stream)
    else:
        n = run(operator, pianist, sys.stdout)
    print(f"[pianist] {n} actions executed, final time {pianist.now_ms} ms", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
