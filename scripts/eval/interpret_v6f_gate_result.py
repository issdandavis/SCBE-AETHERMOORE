#!/usr/bin/env python3
"""Parse the gate_report event from a coding-agent training job's logs and
emit a clean verdict + recommendation.

Designed for jobs run with ``evaluation.production_shim_gate=true``: the
report payload includes both ``pass_rate`` (shim+model) and
``raw_pass_rate`` (bare model), so this script makes the comparison
explicit.

Usage::

    python scripts/eval/interpret_v6f_gate_result.py <job_id>

The job_id is what ``hf jobs ps`` prints — for v6f this was
``69fb49a046974e2a21d27a1a``. The script shells out to ``hf jobs logs``
to fetch the full log, then extracts the single ``"event": "gate_report"``
JSON line and the ``"event": "training_complete"`` summary.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Any


def _fetch_logs(job_id: str) -> str:
    res = subprocess.run(
        ["hf", "jobs", "logs", job_id],
        capture_output=True,
        text=True,
        check=False,
    )
    return (res.stdout or "") + "\n" + (res.stderr or "")


def _find_event(logs: str, event_name: str) -> dict[str, Any] | None:
    """Find the last JSON line whose top-level ``event`` key matches.

    The inline gate prints one event per prompt plus a final ``gate_report``
    and ``training_complete``. Scan backwards so we always pick the final
    summary, not an interim per-prompt event.
    """

    pattern = re.compile(r'\{"event":\s*"' + re.escape(event_name) + r'"[^\n]*\}')
    matches = pattern.findall(logs)
    for raw in reversed(matches):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            continue
    return None


def _verdict(report: dict[str, Any]) -> tuple[str, list[str]]:
    """Map a gate report to (verdict, advice)."""

    summary = report.get("report", report)
    pass_rate = float(summary.get("pass_rate", 0.0) or 0.0)
    raw_pass_rate = float(summary.get("raw_pass_rate", 0.0) or 0.0)
    must_pass_all_ok = bool(summary.get("must_pass_all_ok", False))
    overall_pass = bool(summary.get("overall_pass", False))
    minimum = float(summary.get("minimum_pass_rate", 0.7) or 0.7)
    production_shim = bool(summary.get("production_shim_gate", False))

    advice: list[str] = []

    if not production_shim:
        advice.append(
            "report did not include production_shim_gate=true — this was a "
            "legacy scaffolded-gate run; pass_rate is fake-pass, not real."
        )

    advice.append(
        f"shim+model pass_rate = {pass_rate:.3f} vs threshold {minimum:.2f}; "
        f"bare-model raw_pass_rate = {raw_pass_rate:.3f}"
    )

    if overall_pass and pass_rate >= 0.95 and raw_pass_rate >= 0.5:
        verdict = "GREEN: ship"
        advice.append(
            "shim clears with high margin AND bare model also exceeds 0.5 — "
            "SFT internalized the discipline. Flip push_adapter=true on next "
            "run; shim is belt-and-suspenders rather than load-bearing."
        )
    elif overall_pass and pass_rate >= minimum:
        verdict = "AMBER: ship via shim"
        advice.append(
            "shim+model clears the threshold but bare model is below 0.5. "
            "The shim is the load-bearing component; production must keep "
            "the shim in the inference path. Flip push_adapter=true; ship "
            "as 'shim-required' adapter."
        )
    elif not must_pass_all_ok:
        verdict = "RED: must_pass missed"
        advice.append(
            "at least one must_pass prompt failed even with shim ON. "
            "Check per-prompt 'attempts' to see if best-of-N exhausted; "
            "if first_passing_index == None on a must_pass prompt, the "
            "model genuinely cannot produce that envelope — increase "
            "marker_negative dose or revisit the contract definition."
        )
    else:
        verdict = "RED: below minimum"
        advice.append(
            f"shim pass_rate {pass_rate:.3f} below minimum {minimum:.2f}. "
            "Inspect per-prompt failures to see whether continuation drift "
            "(forbidden tokens after prefix) or capability gap (missing "
            "required tokens). Continuation drift -> raise gate_suppress_forbidden "
            "to true. Capability gap -> more SFT or contract revision."
        )

    if pass_rate > 0 and raw_pass_rate > 0:
        lift = pass_rate - raw_pass_rate
        advice.append(f"shim lift over bare model: +{lift * 100:.1f} pp ({raw_pass_rate:.3f} -> {pass_rate:.3f})")

    return verdict, advice


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_id", help="HF Jobs job id (e.g. 69fb49a046974e2a21d27a1a)")
    parser.add_argument("--json", action="store_true", help="emit raw JSON")
    args = parser.parse_args()

    logs = _fetch_logs(args.job_id)
    if not logs.strip():
        print(f"no logs returned for job {args.job_id}", file=sys.stderr)
        return 1

    gate_event = _find_event(logs, "gate_report")
    training_complete = _find_event(logs, "training_complete")

    if gate_event is None:
        print(f"no gate_report event found in logs for {args.job_id}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"gate_report": gate_event, "training_complete": training_complete}, indent=2))
        return 0

    report = gate_event.get("report", gate_event)
    verdict, advice = _verdict(report)

    print(f"=== v6f-class gate result: {args.job_id} ===")
    print(f"verdict: {verdict}")
    print()
    for line in advice:
        print(f"  - {line}")

    if training_complete:
        s = training_complete.get("summary", {})
        print()
        print("training summary:")
        print(f"  profile_id        : {s.get('profile_id')}")
        print(f"  base_model        : {s.get('base_model')}")
        print(f"  train_rows_used   : {s.get('train_rows_used')}")
        print(f"  global_step       : {s.get('global_step')}")
        print(f"  training_loss     : {s.get('training_loss')}")
        print(f"  pushed_adapter    : {s.get('pushed_adapter')}")
        print(f"  gate_overall_pass : {s.get('gate_overall_pass')}")
        print(f"  gate_pass_rate    : {s.get('gate_pass_rate')}")
        print(f"  gate_n_pass/total : {s.get('gate_n_pass')}/{s.get('gate_n_total')}")

    fails = [r for r in report.get("results", []) if not r.get("ok")]
    if fails:
        print()
        print(f"failed prompts ({len(fails)}):")
        for r in fails[:10]:
            missing = r.get("missing_required", [])
            triggered = r.get("triggered_forbidden", [])
            attempts = r.get("attempts")
            attempts_str = ""
            if attempts:
                attempts_str = f" attempts={[a['ok'] for a in attempts]}"
            print(f"  - {r.get('id')}: missing={missing} triggered={triggered}{attempts_str}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
