#!/usr/bin/env python3
"""
SCBE Headless Browser Swarm Runner
====================================

Terminal-based headless browser swarm for multi-AI cloud agents.
Runs N browser agents in parallel, each executing tasks from a shared queue,
feeding telemetry/drift/audio/event logs back into the SCBE governance pipeline.

Features:
- N concurrent headless browser agents (configurable)
- Task queue with priority dispatch
- 24hr autonomous cycles with configurable rest periods
- All actions audited via canonical 21D state transitions
- Training data (SFT) generated from every agent decision
- Byzantine consensus: agents vote on suspicious pages
- Event log → JSONL for downstream model training

Usage:
    python agents/browser/swarm_runner.py --agents 3 --cycle-hours 24 --rest-minutes 30
    python agents/browser/swarm_runner.py --agents 1 --tasks tasks.json --mock

Author: Issac Davis
Date: 2026-02-23
Part of SCBE-AETHERMOORE (USPTO #63/961,403)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from enum import Enum

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from agents.browser.fleet_coordinator import AetherbrowseFleet, FleetCoordinatorConfig
from agents.browser.session_manager import AetherbrowseSessionConfig

# Canonical state auditing
try:
    from src.harmonic.canonical_state import (
        build_canonical_state,
        audit_state_transition,
        safe_origin,
        compute_ds_squared,
        get_auditor,
        CanonicalState,
    )
    CANONICAL_AVAILABLE = True
except ImportError:
    CANONICAL_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("SWARM")


# ═══════════════════════════════════════════════════════════════
# Task Types
# ═══════════════════════════════════════════════════════════════

class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    DREAM = "dream"  # AI plays the game for training data


@dataclass
class SwarmTask:
    """A unit of work for a browser agent."""
    task_id: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    action: str = "navigate"  # navigate, click, type, scroll, screenshot, script
    target: str = ""          # URL or selector
    value: str = ""           # text to type or script payload
    context: Dict[str, Any] = field(default_factory=dict)
    max_retries: int = 2
    timeout_s: float = 30.0

    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"task-{uuid.uuid4().hex[:8]}"


@dataclass
class TaskResult:
    """Result from executing a SwarmTask."""
    task_id: str
    agent_id: str
    success: bool
    decision: str = "ALLOW"
    ds_squared: float = 0.0
    duration_s: float = 0.0
    output: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(tz=None).isoformat()


# ═══════════════════════════════════════════════════════════════
# Event Logger (SFT training data + telemetry)
# ═══════════════════════════════════════════════════════════════

class SwarmEventLogger:
    """Writes JSONL event logs for downstream training and monitoring."""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now(tz=None).strftime("%Y-%m-%d")
        self.event_path = log_dir / f"swarm_events_{today}.jsonl"
        self.sft_path = log_dir / f"swarm_sft_{today}.jsonl"
        self._event_count = 0

    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        record = {
            "ts": datetime.now(tz=None).isoformat(),
            "type": event_type,
            "seq": self._event_count,
            **data,
        }
        with open(self.event_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        self._event_count += 1

    def log_sft(self, instruction: str, response: str, metadata: Dict[str, Any] = None) -> None:
        """Log an SFT training pair from agent behavior."""
        record = {
            "instruction": instruction,
            "response": response,
            "metadata": metadata or {},
            "ts": datetime.now(tz=None).isoformat(),
            "source": "swarm_browser",
        }
        with open(self.sft_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    @property
    def event_count(self) -> int:
        return self._event_count


# ═══════════════════════════════════════════════════════════════
# Byzantine Consensus
# ═══════════════════════════════════════════════════════════════

class ByzantineVoter:
    """Simple 2/3 majority voting for suspicious content detection."""

    def __init__(self):
        self._votes: Dict[str, List[str]] = {}  # url → [agent decisions]

    def cast_vote(self, url: str, agent_id: str, decision: str) -> None:
        key = url[:200]  # truncate
        if key not in self._votes:
            self._votes[key] = []
        self._votes[key].append(decision)

    def consensus(self, url: str, min_votes: int = 2) -> Optional[str]:
        key = url[:200]
        votes = self._votes.get(key, [])
        if len(votes) < min_votes:
            return None
        # 2/3 majority
        from collections import Counter
        counts = Counter(votes)
        most_common, count = counts.most_common(1)[0]
        if count >= len(votes) * 2 / 3:
            return most_common
        return "QUARANTINE"  # no consensus → quarantine


# ═══════════════════════════════════════════════════════════════
# Swarm Runner
# ═══════════════════════════════════════════════════════════════

@dataclass
class SwarmConfig:
    """Configuration for the browser swarm."""
    num_agents: int = 3
    cycle_hours: float = 24.0
    rest_minutes: float = 30.0
    backend: str = "mock"  # mock, cdp, playwright, auto
    host: str = "127.0.0.1"
    port: int = 9222
    safe_radius: float = 0.92
    log_dir: str = "training/swarm_logs"
    headless: bool = True
    max_tasks_per_cycle: int = 1000


class SwarmRunner:
    """Orchestrates N browser agents running tasks in 24hr cycles.

    Architecture:
        SwarmRunner
          ├── AetherbrowseFleet (N sessions)
          ├── Task Queue (priority heap)
          ├── ByzantineVoter (consensus)
          ├── SwarmEventLogger (JSONL)
          └── StateTransitionAuditor (canonical 21D)
    """

    def __init__(self, config: SwarmConfig):
        self.config = config
        self.fleet: Optional[AetherbrowseFleet] = None
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.voter = ByzantineVoter()
        self.event_logger = SwarmEventLogger(Path(config.log_dir))
        self.results: List[TaskResult] = []
        self._running = False
        self._cycle_count = 0
        self._total_tasks = 0

    async def initialize(self) -> bool:
        """Spin up the browser fleet."""
        fleet_config = FleetCoordinatorConfig(
            size=self.config.num_agents,
            backend=self.config.backend,
            host=self.config.host,
            port=self.config.port,
            safe_radius=self.config.safe_radius,
        )
        self.fleet = AetherbrowseFleet(fleet_config)
        ok = await self.fleet.initialize()
        if ok:
            logger.info(
                f"Fleet initialized: {self.config.num_agents} agents, "
                f"backend={self.config.backend}, safe_radius={self.config.safe_radius}"
            )
            self.event_logger.log_event("fleet_init", {
                "num_agents": self.config.num_agents,
                "backend": self.config.backend,
            })
        return ok

    async def shutdown(self) -> None:
        """Gracefully shut down the fleet."""
        if self.fleet:
            await self.fleet.shutdown()
        self._running = False
        logger.info(f"Swarm shut down. Total tasks: {self._total_tasks}, cycles: {self._cycle_count}")
        self.event_logger.log_event("fleet_shutdown", {
            "total_tasks": self._total_tasks,
            "cycles": self._cycle_count,
            "total_events": self.event_logger.event_count,
        })

    def enqueue_task(self, task: SwarmTask) -> None:
        """Add a task to the priority queue."""
        # Lower number = higher priority
        priority_map = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.NORMAL: 2,
            TaskPriority.LOW: 3,
            TaskPriority.DREAM: 4,
        }
        p = priority_map.get(task.priority, 2)
        self.task_queue.put_nowait((p, task.task_id, task))

    def enqueue_tasks(self, tasks: Sequence[SwarmTask]) -> None:
        for task in tasks:
            self.enqueue_task(task)

    async def _execute_task(self, task: SwarmTask) -> TaskResult:
        """Execute a single task via the fleet, with auditing."""
        start = time.monotonic()
        agent_result = {}
        decision = "ALLOW"
        ds2 = 0.0

        try:
            agent_result = await asyncio.wait_for(
                self.fleet.execute(
                    action=task.action,
                    target=task.target,
                    value=task.value or None,
                    context=task.context,
                ),
                timeout=task.timeout_s,
            )
            decision = agent_result.get("decision", "ALLOW")
        except asyncio.TimeoutError:
            decision = "DENY"
            agent_result = {"error": "timeout"}
        except Exception as e:
            decision = "DENY"
            agent_result = {"error": str(e)}

        duration = time.monotonic() - start

        # Canonical 21D audit
        if CANONICAL_AVAILABLE:
            try:
                before = safe_origin()
                risk = 0.0 if decision == "ALLOW" else (0.5 if decision == "QUARANTINE" else 0.9)
                after = build_canonical_state(
                    u=[0.0] * 6,
                    theta=[0.0] * 6,
                    risk_aggregate=risk,
                    stabilization=1.0 / (1.0 + risk),
                )
                ds_result = compute_ds_squared(before, after)
                ds2 = ds_result["ds_squared"]
                audit_state_transition(
                    before=before,
                    after=after,
                    decision=decision,
                    agent_id=task.task_id,
                    metadata={"action": task.action, "target": task.target[:100]},
                )
            except Exception:
                pass

        # Byzantine voting for navigation tasks
        if task.action == "navigate" and task.target.startswith("http"):
            session = self.fleet._select_session() if self.fleet.sessions else None
            agent_id = session.config.agent_id if session else "unknown"
            self.voter.cast_vote(task.target, agent_id, decision)

        result = TaskResult(
            task_id=task.task_id,
            agent_id=agent_result.get("session_id", "fleet"),
            success=decision in ("ALLOW", "WARN"),
            decision=decision,
            ds_squared=ds2,
            duration_s=round(duration, 3),
            output=agent_result,
            error=agent_result.get("error", ""),
        )

        # Log event
        self.event_logger.log_event("task_result", {
            "task_id": task.task_id,
            "action": task.action,
            "target": task.target[:100],
            "decision": decision,
            "ds_squared": ds2,
            "duration_s": result.duration_s,
            "success": result.success,
        })

        # Generate SFT pair from the interaction
        self.event_logger.log_sft(
            instruction=f"Browser agent task: {task.action} on '{task.target[:80]}'. Decision?",
            response=f"Decision: {decision}. ds²={ds2:.4f}. Duration: {result.duration_s}s. "
                     f"{'Success' if result.success else 'Failed: ' + result.error[:60]}",
            metadata={
                "task_id": task.task_id,
                "priority": task.priority.value,
                "ds_squared": ds2,
            },
        )

        self.results.append(result)
        self._total_tasks += 1
        return result

    async def run_cycle(self) -> Dict[str, Any]:
        """Run one cycle: drain the task queue, then rest."""
        self._cycle_count += 1
        cycle_start = time.monotonic()
        cycle_results = []
        tasks_this_cycle = 0

        logger.info(f"=== Cycle {self._cycle_count} START ({self.task_queue.qsize()} tasks queued) ===")
        self.event_logger.log_event("cycle_start", {
            "cycle": self._cycle_count,
            "queue_size": self.task_queue.qsize(),
        })

        while not self.task_queue.empty() and tasks_this_cycle < self.config.max_tasks_per_cycle:
            _, _, task = await self.task_queue.get()
            result = await self._execute_task(task)
            cycle_results.append(result)
            tasks_this_cycle += 1

            if tasks_this_cycle % 10 == 0:
                logger.info(f"  [{tasks_this_cycle}] tasks completed this cycle")

        cycle_duration = time.monotonic() - cycle_start
        success_count = sum(1 for r in cycle_results if r.success)
        deny_count = sum(1 for r in cycle_results if r.decision == "DENY")

        summary = {
            "cycle": self._cycle_count,
            "tasks": tasks_this_cycle,
            "success": success_count,
            "denied": deny_count,
            "duration_s": round(cycle_duration, 1),
            "avg_ds_squared": sum(r.ds_squared for r in cycle_results) / max(1, len(cycle_results)),
        }

        logger.info(
            f"=== Cycle {self._cycle_count} END: {tasks_this_cycle} tasks, "
            f"{success_count} OK, {deny_count} DENIED, {cycle_duration:.1f}s ==="
        )
        self.event_logger.log_event("cycle_end", summary)

        return summary

    async def run_continuous(self, initial_tasks: Optional[List[SwarmTask]] = None) -> None:
        """Run continuous 24hr cycles until stopped."""
        self._running = True

        if initial_tasks:
            self.enqueue_tasks(initial_tasks)

        cycle_duration = timedelta(hours=self.config.cycle_hours)
        rest_duration = timedelta(minutes=self.config.rest_minutes)

        logger.info(
            f"Starting continuous operation: "
            f"cycle={self.config.cycle_hours}h, rest={self.config.rest_minutes}m"
        )

        while self._running:
            cycle_start = datetime.now(tz=None)

            # If queue is empty, generate dream tasks (AI plays game for training)
            if self.task_queue.empty():
                dream_tasks = self._generate_dream_tasks()
                self.enqueue_tasks(dream_tasks)

            summary = await self.run_cycle()

            # Rest period
            elapsed = datetime.now(tz=None) - cycle_start
            remaining = cycle_duration - elapsed
            if remaining.total_seconds() > 0 and self._running:
                rest_s = min(rest_duration.total_seconds(), remaining.total_seconds())
                logger.info(f"Rest period: {rest_s/60:.0f} minutes")
                self.event_logger.log_event("rest_start", {"duration_s": rest_s})
                await asyncio.sleep(rest_s)

    def _generate_dream_tasks(self) -> List[SwarmTask]:
        """Generate 'dream' tasks — AI plays game scenarios for training data."""
        dream_urls = [
            "about:blank",  # will be replaced with actual game URLs
        ]
        tasks = []
        for i, url in enumerate(dream_urls):
            tasks.append(SwarmTask(
                priority=TaskPriority.DREAM,
                action="navigate",
                target=url,
                context={"mode": "dream", "purpose": "training_data_generation"},
            ))
        return tasks

    def stop(self) -> None:
        """Signal the swarm to stop after current cycle."""
        self._running = False
        logger.info("Stop signal received. Will halt after current cycle.")

    def status(self) -> Dict[str, Any]:
        """Get swarm status."""
        audit_count = 0
        if CANONICAL_AVAILABLE:
            audit_count = get_auditor().count
        return {
            "running": self._running,
            "cycles_completed": self._cycle_count,
            "total_tasks": self._total_tasks,
            "queue_size": self.task_queue.qsize(),
            "results_buffered": len(self.results),
            "events_logged": self.event_logger.event_count,
            "audit_entries": audit_count,
            "fleet_summary": self.fleet.summary() if self.fleet else {},
        }


# ═══════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="SCBE Browser Swarm Runner")
    parser.add_argument("--agents", type=int, default=3, help="Number of browser agents")
    parser.add_argument("--cycle-hours", type=float, default=24.0, help="Hours per cycle")
    parser.add_argument("--rest-minutes", type=float, default=30.0, help="Rest between cycles (minutes)")
    parser.add_argument("--backend", default="mock", choices=["mock", "cdp", "playwright", "auto"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--tasks", type=str, help="JSON file with initial tasks")
    parser.add_argument("--log-dir", default="training/swarm_logs")
    parser.add_argument("--max-tasks", type=int, default=1000, help="Max tasks per cycle")
    parser.add_argument("--mock", action="store_true", help="Force mock backend")
    parser.add_argument("--one-cycle", action="store_true", help="Run one cycle then exit")
    args = parser.parse_args()

    backend = "mock" if args.mock else args.backend

    config = SwarmConfig(
        num_agents=args.agents,
        cycle_hours=args.cycle_hours,
        rest_minutes=args.rest_minutes,
        backend=backend,
        host=args.host,
        port=args.port,
        log_dir=args.log_dir,
        max_tasks_per_cycle=args.max_tasks,
    )

    runner = SwarmRunner(config)

    # Load initial tasks
    initial_tasks = None
    if args.tasks:
        task_path = Path(args.tasks)
        if task_path.exists():
            raw = json.loads(task_path.read_text())
            initial_tasks = [
                SwarmTask(
                    action=t.get("action", "navigate"),
                    target=t.get("target", ""),
                    value=t.get("value", ""),
                    priority=TaskPriority(t.get("priority", "normal")),
                    context=t.get("context", {}),
                )
                for t in raw
            ]
            logger.info(f"Loaded {len(initial_tasks)} tasks from {task_path}")

    # Initialize
    ok = await runner.initialize()
    if not ok:
        logger.error("Fleet initialization failed.")
        return

    try:
        if args.one_cycle:
            if initial_tasks:
                runner.enqueue_tasks(initial_tasks)
            elif runner.task_queue.empty():
                runner.enqueue_tasks(runner._generate_dream_tasks())
            await runner.run_cycle()
        else:
            await runner.run_continuous(initial_tasks)
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        status = runner.status()
        logger.info(f"Final status: {json.dumps(status, indent=2, default=str)}")
        await runner.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
