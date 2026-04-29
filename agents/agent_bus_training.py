"""
Agent Bus self-training — perf-triggered fine-tunes.

The bus continually appends signed BusEvent records to artifacts/agent-bus/events.jsonl.
This module reads that ledger, computes a rolling performance score, and when the
score drops below a threshold, kicks off a training run via existing scripts:

  - Failure data → scripts/codebase_to_sft.py (extends SFT corpus)
  - Training run → scripts/hf_training_loop.py
  - Growth gate → scripts/monitor_training_growth.py

The trigger is conservative on purpose:
  - never auto-triggers more than once per cooldown window (default 1 hour)
  - never spawns a training run on top of a still-running one
  - writes a sentinel file artifacts/agent-bus/training/in_progress.lock

This is the *trigger*, not the trainer. We delegate the actual training to the
existing pipeline so improvements there flow through without code changes here.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("scbe.agent_bus.training")

EVENTS_LOG = Path("artifacts/agent-bus/events.jsonl")
TRAINING_DIR = Path("artifacts/agent-bus/training")
LOCK_FILE = TRAINING_DIR / "in_progress.lock"

# Defaults match the conservative envelope you'd want for autonomous training.
DEFAULT_WINDOW_EVENTS = 50
DEFAULT_SUCCESS_FLOOR = 0.7  # below this → trigger
DEFAULT_COOLDOWN_SECONDS = 3600  # one trigger per hour max
DEFAULT_MIN_FAILURES = 5  # need at least this many failures to bother


@dataclass
class PerformanceWindow:
    total: int
    successes: int
    failures: int
    success_rate: float
    avg_duration: float
    avg_tokens_out: float
    breaker_open_count: int

    @property
    def needs_training(self) -> bool:
        return self.failures >= DEFAULT_MIN_FAILURES and self.success_rate < DEFAULT_SUCCESS_FLOOR


class TrainingTrigger:
    """Reads bus events, decides whether to retrain."""

    def __init__(
        self,
        events_log: Path = EVENTS_LOG,
        cooldown: float = DEFAULT_COOLDOWN_SECONDS,
        success_floor: float = DEFAULT_SUCCESS_FLOOR,
        window: int = DEFAULT_WINDOW_EVENTS,
    ) -> None:
        self.events_log = events_log
        self.cooldown = cooldown
        self.success_floor = success_floor
        self.window = window
        self._last_trigger_at: float = 0.0

    def measure(self) -> Optional[PerformanceWindow]:
        """Compute a perf window over the last N events. Returns None if no data."""
        events = self._tail_events(self.window)
        if not events:
            return None
        total = len(events)
        successes = sum(1 for e in events if e.get("success"))
        failures = total - successes
        durations = [float(e.get("duration_seconds", 0) or 0) for e in events]
        tokens_out = [int(e.get("tokens_out", 0) or 0) for e in events]
        breaker_open = sum(
            1 for e in events if any(s in ("open", "half_open") for s in (e.get("breaker_state") or {}).values())
        )
        return PerformanceWindow(
            total=total,
            successes=successes,
            failures=failures,
            success_rate=successes / total if total else 1.0,
            avg_duration=sum(durations) / total if total else 0.0,
            avg_tokens_out=sum(tokens_out) / total if total else 0.0,
            breaker_open_count=breaker_open,
        )

    def should_trigger(self, perf: PerformanceWindow) -> bool:
        if not perf.needs_training:
            return False
        if (time.time() - self._last_trigger_at) < self.cooldown:
            return False
        if LOCK_FILE.exists():
            return False
        return True

    def trigger(self, perf: PerformanceWindow, *, dry_run: bool = False) -> Dict[str, Any]:
        """Kick off SFT extension + training. Returns a summary dict."""
        TRAINING_DIR.mkdir(parents=True, exist_ok=True)
        report = {
            "triggered_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "perf": {
                "total": perf.total,
                "successes": perf.successes,
                "failures": perf.failures,
                "success_rate": round(perf.success_rate, 3),
            },
            "dry_run": dry_run,
        }
        if dry_run:
            logger.info("training trigger (dry run): %s", report)
            return report

        LOCK_FILE.write_text(json.dumps(report), encoding="utf-8")
        self._last_trigger_at = time.time()

        steps = []
        steps.append(
            self._run_step(
                "sft_extend",
                [sys.executable, "scripts/codebase_to_sft.py", "--out", "training-data/sft_codebase.jsonl"],
            )
        )
        steps.append(
            self._run_step(
                "training_loop",
                [sys.executable, "scripts/hf_training_loop.py", "--steps", "500"],
            )
        )
        steps.append(
            self._run_step(
                "growth_check",
                [sys.executable, "scripts/monitor_training_growth.py"],
            )
        )
        report["steps"] = steps
        try:
            LOCK_FILE.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("could not clear lock file: %s", exc)
        return report

    def _run_step(self, name: str, cmd: List[str]) -> Dict[str, Any]:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, check=False)
            return {
                "name": name,
                "exit_code": proc.returncode,
                "stdout_tail": (proc.stdout or "")[-500:],
                "stderr_tail": (proc.stderr or "")[-500:],
            }
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.warning("training step %s failed: %s", name, exc)
            return {"name": name, "error": str(exc)}

    def _tail_events(self, n: int) -> List[Dict[str, Any]]:
        if not self.events_log.exists():
            return []
        try:
            lines = self.events_log.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            logger.warning("could not read %s: %s", self.events_log, exc)
            return []
        out: List[Dict[str, Any]] = []
        for line in lines[-n:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out
