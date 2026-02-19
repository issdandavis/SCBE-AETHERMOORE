#!/usr/bin/env python3
"""
Linux kernel antivirus monitor (Falco/eBPF JSON feed -> SCBE decisions).

Examples:
  # read Falco JSON lines from stdin
  falco -o json_output=true | python scripts/linux_kernel_antivirus_monitor.py --input -

  # replay captured event file
  python scripts/linux_kernel_antivirus_monitor.py --input artifacts/falco_events.jsonl --alerts-only
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.linux_enforcement_hooks import LinuxEnforcementHooks
from agents.linux_kernel_event_bridge import LinuxKernelAntivirusBridge


def _iter_lines(path: str) -> Iterable[str]:
    if path == "-":
        for line in sys.stdin:
            yield line
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            yield line


def main() -> int:
    parser = argparse.ArgumentParser(description="Linux SCBE kernel antivirus monitor")
    parser.add_argument("--input", default="-", help="JSONL file path or '-' for stdin")
    parser.add_argument("--alerts-only", action="store_true", help="Emit only non-ALLOW actions")
    parser.add_argument("--max-events", type=int, default=0, help="0 means unlimited")
    parser.add_argument("--host-default", default="linux-node")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--include-kernel-event", action="store_true", help="Include normalized KernelEvent in output")
    parser.add_argument("--emit-enforcement", action="store_true", help="Include enforcement command emitters in output")
    parser.add_argument("--apply-enforcement", action="store_true", help="Execute emitted enforcement commands")
    parser.add_argument("--quarantine-dir", default="/var/quarantine/scbe", help="Quarantine directory for artifact isolation")
    parser.add_argument("--enforcement-cooldown", type=float, default=15.0, help="Seconds to suppress duplicate enforcement for a process")
    args = parser.parse_args()

    bridge = LinuxKernelAntivirusBridge()
    enforcer = None
    if args.emit_enforcement or args.apply_enforcement:
        enforcer = LinuxEnforcementHooks(
            apply_enforcement=args.apply_enforcement,
            quarantine_dir=args.quarantine_dir,
            cooldown_seconds=args.enforcement_cooldown,
        )

    seen = 0
    emitted = 0
    errors = 0
    enforcement_emitted = 0
    enforcement_applied = 0
    enforcement_failed = 0

    for raw in _iter_lines(args.input):
        if args.max_events and seen >= args.max_events:
            break
        line = (raw or "").strip()
        if not line:
            continue
        seen += 1
        try:
            decision = bridge.evaluate_json_line(line, host_default=args.host_default)
        except Exception as exc:  # noqa: BLE001
            errors += 1
            err = {"error": str(exc), "raw": line[:2000]}
            print(json.dumps(err), file=sys.stderr)
            continue

        payload = {
            "host": decision.kernel_event.host,
            "pid": decision.kernel_event.pid,
            "process_name": decision.kernel_event.process_name,
            "operation": decision.kernel_event.operation,
            "target": decision.kernel_event.target,
            "decision": decision.result.decision,
            "kernel_action": decision.result.kernel_action,
            "cell_state": decision.result.cell_state,
            "suspicion": decision.result.suspicion,
            "antibody_load_prev": round(decision.previous_antibody_load, 4),
            "antibody_load_now": round(decision.result.turnstile.antibody_load, 4),
            "membrane_stress": round(decision.result.turnstile.membrane_stress, 4),
            "notes": list(decision.result.notes),
        }
        if args.include_kernel_event:
            payload["kernel_event"] = decision.kernel_event.__dict__

        if enforcer is not None:
            plan = enforcer.handle(decision)
            if plan.commands:
                enforcement_emitted += 1
            if plan.applied:
                enforcement_applied += 1
            if plan.failures:
                enforcement_failed += 1
            payload["enforcement"] = plan.to_dict()

        if args.alerts_only and payload["kernel_action"] == "ALLOW":
            continue

        emitted += 1
        if args.pretty:
            print(json.dumps(payload, indent=2))
        else:
            print(json.dumps(payload, separators=(",", ":")))

    summary = {
        "events_seen": seen,
        "events_emitted": emitted,
        "errors": errors,
        "enforcement_emitted": enforcement_emitted,
        "enforcement_applied": enforcement_applied,
        "enforcement_failed": enforcement_failed,
    }
    print(json.dumps(summary), file=sys.stderr)
    if errors:
        return 2
    if args.apply_enforcement and enforcement_failed:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
