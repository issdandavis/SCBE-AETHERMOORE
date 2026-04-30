"""
Agent Bus replay — deterministic postmortem from events.jsonl.

Reads the signed audit log and reconstructs:
  - Per-task-type counts and success rates
  - Per-provider call distribution
  - Token usage totals
  - Latency percentiles (p50, p95)
  - Breaker state transitions
  - Identity history (which agents wrote, what algorithms they used)

Pure read-only. Does not re-execute anything. Use this for:
  - Debugging "what was the bus doing at 3am?"
  - Verifying agreed-upon contracts (e.g., "we never made an HF call without HF_TOKEN set")
  - Generating training data from real bus history

Schema-version aware: skips events the validator rejects rather than
crashing on a bad payload.
"""

from __future__ import annotations

import json
import logging
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("scbe.agent_bus.replay")


def _within(ts: Optional[str], from_ts: Optional[str], to_ts: Optional[str]) -> bool:
    if ts is None:
        return True
    if from_ts and ts < from_ts:
        return False
    if to_ts and ts > to_ts:
        return False
    return True


def replay_log(
    path: Path,
    *,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
    group_by_task: bool = False,
) -> Dict[str, Any]:
    """Reconstruct state from a JSONL log. Returns a structured report dict."""
    from agents.agent_bus_schema import validate_event

    if not path.exists():
        return {"error": f"log not found: {path}"}

    events: List[Dict[str, Any]] = []
    skipped_invalid = 0
    skipped_oor = 0  # out of range

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                skipped_invalid += 1
                continue
            ts = rec.get("timestamp")
            if not _within(ts, from_ts, to_ts):
                skipped_oor += 1
                continue
            v = validate_event(rec)
            if not v.ok:
                skipped_invalid += 1
                continue
            events.append(rec)

    total = len(events)
    if total == 0:
        return {
            "path": str(path),
            "total_events": 0,
            "skipped_invalid": skipped_invalid,
            "skipped_out_of_range": skipped_oor,
            "from_ts": from_ts,
            "to_ts": to_ts,
        }

    # Aggregate metrics
    successes = sum(1 for e in events if e.get("success"))
    durations = [float(e.get("duration_seconds", 0) or 0) for e in events]
    tokens_in = [int(e.get("tokens_in", 0) or 0) for e in events]
    tokens_out = [int(e.get("tokens_out", 0) or 0) for e in events]

    by_provider = Counter(e.get("llm_provider") or "(none)" for e in events)
    by_task = Counter(e.get("task_type", "?") for e in events)
    by_agent = Counter(e.get("_agent_id", "(unsigned)") for e in events)
    by_alg = Counter(e.get("_sig_alg", "(unsigned)") for e in events)

    # Breaker state transitions (where state appears as open/half_open)
    breaker_open_events = sum(
        1 for e in events if any(s in ("open", "half_open") for s in (e.get("breaker_state") or {}).values())
    )

    def _pctile(values: List[float], p: float) -> float:
        if not values:
            return 0.0
        s = sorted(values)
        k = max(0, min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1)))))
        return float(s[k])

    report: Dict[str, Any] = {
        "path": str(path),
        "from_ts": from_ts or events[0].get("timestamp"),
        "to_ts": to_ts or events[-1].get("timestamp"),
        "total_events": total,
        "skipped_invalid": skipped_invalid,
        "skipped_out_of_range": skipped_oor,
        "success_rate": round(successes / total, 3) if total else 0.0,
        "successes": successes,
        "failures": total - successes,
        "duration_seconds": {
            "mean": round(statistics.fmean(durations), 3) if durations else 0.0,
            "p50": round(_pctile(durations, 50), 3),
            "p95": round(_pctile(durations, 95), 3),
            "max": round(max(durations), 3) if durations else 0.0,
        },
        "tokens": {
            "in_total": sum(tokens_in),
            "out_total": sum(tokens_out),
            "out_per_event_mean": round(statistics.fmean(tokens_out), 1) if tokens_out else 0.0,
        },
        "providers": dict(by_provider),
        "tasks": dict(by_task),
        "agents": dict(by_agent),
        "signature_algorithms": dict(by_alg),
        "breaker_open_events": breaker_open_events,
    }

    if group_by_task:
        per_task: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "success": 0, "duration_total": 0.0, "tokens_out_total": 0}
        )
        for e in events:
            t = e.get("task_type", "?")
            per_task[t]["count"] += 1
            if e.get("success"):
                per_task[t]["success"] += 1
            per_task[t]["duration_total"] += float(e.get("duration_seconds", 0) or 0)
            per_task[t]["tokens_out_total"] += int(e.get("tokens_out", 0) or 0)
        report["by_task_detail"] = {
            t: {
                "count": d["count"],
                "success_rate": round(d["success"] / d["count"], 3) if d["count"] else 0.0,
                "avg_duration": round(d["duration_total"] / d["count"], 3) if d["count"] else 0.0,
                "avg_tokens_out": round(d["tokens_out_total"] / d["count"], 1) if d["count"] else 0.0,
            }
            for t, d in per_task.items()
        }

    return report
